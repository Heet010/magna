"""The extraction agent: filtered report text -> structured KPIs via the OpenAI API.

One call per company covers both report periods; results are cached to disk.
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

    # Structured output: the response is constrained to the CompanyExtraction schema.
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
