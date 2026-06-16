"""The extraction agent: turns filtered report text into structured KPIs via the
OpenAI API.

One call per company covers both report periods, so the model can align the
quarterly figures with the same KPI vocabulary it found in the full-year report.
Results are cached to disk so re-runs (e.g. while tuning the report layout) don't
re-spend API calls.
"""
from __future__ import annotations

from pathlib import Path

from openai import OpenAI

import config
from src.prompts import AGENT_DESCRIPTION, build_task_prompt
from src.schema import CompanyExtraction


def _cache_file(company: str) -> Path:
    slug = company.lower().replace(" ", "_").replace("-", "_")
    return config.CACHE_DIR / f"{slug}.json"


def extract_company(
    client: OpenAI,
    company: str,
    fy_text: str,
    q_text: str,
    *,
    use_cache: bool = True,
) -> CompanyExtraction:
    """Run the agent for one company. Returns validated structured KPIs."""
    cache = _cache_file(company)
    if use_cache and cache.exists():
        return CompanyExtraction.model_validate_json(cache.read_text(encoding="utf-8"))

    task = build_task_prompt(company, fy_text, q_text)

    # Structured outputs: response_format=<Pydantic model> makes the API return JSON
    # that conforms exactly to CompanyExtraction (strict schema) — no text parsing.
    completion = client.beta.chat.completions.parse(
        model=config.AGENT_MODEL,
        max_tokens=8000,
        messages=[
            {"role": "system", "content": AGENT_DESCRIPTION},
            {"role": "user", "content": task},
        ],
        response_format=CompanyExtraction,
    )

    message = completion.choices[0].message
    if message.refusal:
        raise RuntimeError(f"Model refused for {company}: {message.refusal}")
    result = message.parsed
    if result is None:
        raise RuntimeError(
            f"Agent returned no parseable output for {company} "
            f"(finish_reason={completion.choices[0].finish_reason})."
        )

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
