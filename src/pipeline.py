"""Orchestrates the full run: PDF -> filtered text -> agent -> reports."""
from __future__ import annotations

from dotenv import load_dotenv
from openai import OpenAI

import config
from src.agent import _cache_file, extract_company
from src.compute import recompute_derived
from src.pdf_extractor import filter_report
from src.report_generator import render_excel, render_markdown, render_verification
from src.schema import CompanyExtraction


def run(companies: list[str] | None = None, *, use_cache: bool = True) -> list[CompanyExtraction]:
    """Extract KPIs for the given companies (default: all) and write the reports."""
    load_dotenv()
    companies = companies or list(config.COMPANIES)
    client = OpenAI()

    extractions: list[CompanyExtraction] = []
    for company in companies:
        print(f"\n=== {company} ===")
        fy = filter_report(
            config.report_path(company, "FY2025"), company, "FY2025",
            config.PER_REPORT_CHAR_BUDGET,
        )
        q = filter_report(
            config.report_path(company, "Q1-2026"), company, "Q1-2026",
            config.PER_REPORT_CHAR_BUDGET,
        )
        print(f"  FY2025 : kept {len(fy.kept_pages)}/{fy.total_pages} pages "
              f"({fy.char_count:,} chars)")
        print(f"  Q1-2026: kept {len(q.kept_pages)}/{q.total_pages} pages "
              f"({q.char_count:,} chars)")
        print("  Calling agent…")
        result = extract_company(client, company, fy.text, q.text, use_cache=use_cache)
        recompute_derived(result)
        extractions.append(result)
        print(f"  ✓ extracted ({result.summary_note[:80]}…)")

    write_reports(extractions)
    return extractions


def run_on_files(
    file_map: dict[str, dict[str, str]],
    *,
    use_cache: bool = False,
    progress=None,
) -> list[CompanyExtraction]:
    """Run the agent on uploaded files.

    file_map: {company: {"FY2025": pdf_path, "Q1-2026": pdf_path}} (either period
    may be missing). Used by the web app; does not depend on config's fixed mapping.
    """
    client = OpenAI()
    extractions: list[CompanyExtraction] = []
    for company, periods in file_map.items():
        fy_path = periods.get("FY2025")
        q_path = periods.get("Q1-2026")
        fy_text = (
            filter_report(fy_path, company, "FY2025", config.PER_REPORT_CHAR_BUDGET).text
            if fy_path else "(no full-year report provided)"
        )
        q_text = (
            filter_report(q_path, company, "Q1-2026", config.PER_REPORT_CHAR_BUDGET).text
            if q_path else "(no quarterly report provided)"
        )
        result = extract_company(client, company, fy_text, q_text, use_cache=use_cache)
        recompute_derived(result)
        extractions.append(result)
        if progress:
            progress(company)
    return extractions


def write_reports(extractions: list[CompanyExtraction]) -> None:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = config.OUTPUT_DIR / "executive_summary.md"
    xlsx_path = config.OUTPUT_DIR / "executive_summary.xlsx"
    verify_path = config.OUTPUT_DIR / "verification.md"
    md_path.write_text(render_markdown(extractions), encoding="utf-8")
    verify_path.write_text(render_verification(extractions), encoding="utf-8")
    render_excel(extractions, xlsx_path)
    print(f"\nWrote:\n  {md_path}\n  {xlsx_path}\n  {verify_path}")


def load_cached(companies: list[str] | None = None) -> list[CompanyExtraction]:
    """Load previously extracted results from cache (no API call)."""
    companies = companies or list(config.COMPANIES)
    out: list[CompanyExtraction] = []
    for company in companies:
        cache = _cache_file(company)
        if not cache.exists():
            raise FileNotFoundError(
                f"No cached result for {company} at {cache}. Run `python run.py` first."
            )
        ex = CompanyExtraction.model_validate_json(cache.read_text(encoding="utf-8"))
        out.append(recompute_derived(ex))
    return out
