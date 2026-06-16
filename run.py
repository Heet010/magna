#!/usr/bin/env python
"""CLI entry point.

    python run.py                 # all 3 companies, write Markdown + Excel + verification
    python run.py --no-cache      # ignore cached agent results, re-call the API
    python run.py --company "BMW Group"
    python run.py --inspect       # show PDF page-filtering stats, no API call
    python run.py --verify        # print figure+page spot-check from cache (no API call)
"""
from __future__ import annotations

import argparse

import config


def main() -> None:
    ap = argparse.ArgumentParser(description="OEM financial-report executive-summary agent")
    ap.add_argument("--company", action="append", choices=list(config.COMPANIES),
                    help="Limit to one company (repeatable). Default: all.")
    ap.add_argument("--no-cache", action="store_true",
                    help="Ignore cached agent output and re-call the API.")
    ap.add_argument("--inspect", action="store_true",
                    help="Only show PDF page-filtering stats (no API key needed).")
    ap.add_argument("--verify", action="store_true",
                    help="Print a figure+source-page spot-check from cached results "
                         "(no API call) and refresh output/verification.md.")
    args = ap.parse_args()
    companies = args.company or list(config.COMPANIES)

    if args.inspect:
        from src.pdf_extractor import filter_report
        for company in companies:
            print(f"\n=== {company} ===")
            for period in ("FY2025", "Q1-2026"):
                fr = filter_report(config.report_path(company, period), company, period,
                                   config.PER_REPORT_CHAR_BUDGET)
                print(f"  {period}: {len(fr.kept_pages)}/{fr.total_pages} pages, "
                      f"{fr.char_count:,} chars, first kept pages "
                      f"{[p + 1 for p in fr.kept_pages[:8]]}")
        return

    if args.verify:
        from src.pipeline import load_cached
        from src.report_generator import print_verification, render_verification
        extractions = load_cached(companies)
        print_verification(extractions)
        out = config.OUTPUT_DIR / "verification.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_verification(extractions), encoding="utf-8")
        print(f"\nWrote {out}")
        return

    from src.pipeline import run
    run(companies, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
