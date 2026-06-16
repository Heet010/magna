#!/usr/bin/env python
"""Generate docs/DELIVERABLES.md from the live prompt constants, so the submission
always shows exactly what the agent was told. Run: python scripts/make_deliverables.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from src.prompts import AGENT_DESCRIPTION, METRIC_GUIDE, build_task_prompt  # noqa: E402

EXAMPLE = build_task_prompt(
    "BMW Group",
    fy_text="<filtered text of the BMW full-year 2025 report — see src/pdf_extractor.py>",
    q_text="<filtered text of the BMW Q1 2026 report>",
)

doc = f"""# Deliverables

This document is the submission artifact: the **agent description**, the **prompt
used**, and where the **output** is produced. All of it is generated from the live
code (`src/prompts.py`) so it matches what the agent actually runs.

## 1. Agent description (system prompt)

The agent is an OpenAI (`{config.AGENT_MODEL}`) agent given this system prompt:

```text
{AGENT_DESCRIPTION.rstrip()}
```

It returns a **structured output** (JSON schema enforced by the API — see
`src/schema.py`): for each company, a `full_year` and a `last_quarter` block, each
with all 10 metrics carrying `value`, `source_term` (the verbatim KPI name used by
the company), `source_page` (the PDF page the figure was read from, for spot-checking),
`status` (`reported` / `substituted` / `not_reported` / `not_available`), and a `note`,
plus a `shares_outstanding` count per period.

Two derived cells — **operating margin** (EBIT ÷ revenue) and **market cap @ €100/share**
(€100 × shares outstanding) — are recomputed deterministically in Python from the
extracted inputs (`src/compute.py`), so the table never depends on the model's
arithmetic.

## 2. Prompt used (task prompt)

One call is made per company, covering both report periods so the model aligns the
quarterly figures with the full-year KPI vocabulary. The user message is built by
`build_task_prompt(...)`. The metric instructions embedded in every prompt:

```text
{METRIC_GUIDE.rstrip()}
```

A complete example task prompt (BMW; the report placeholders are replaced at runtime
with the filtered PDF text):

```text
{EXAMPLE.rstrip()}
```

## 3. Output (the requested table)

Running `python run.py` writes:

- `output/executive_summary.md` — the comparison table (6 data columns: full-year
  2025 and Q1 2026 for each of BMW, Mercedes-Benz, Volkswagen) plus a
  "Substituted & equivalent KPIs" section.
- `output/executive_summary.xlsx` — the same table formatted as a workbook
  (substituted KPIs highlighted) with a "Notes & Substitutions" sheet.

Table conventions: **†** marks a value taken from a company's equivalent/substituted
KPI; **"Not Reported"** = absent from the quarterly report; **"N/A"** = not disclosed.

## 4. How to reproduce

```bash
python -m venv .venv && pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY
python run.py                 # -> output/executive_summary.{{md,xlsx}}
```
"""

out = ROOT / "docs" / "DELIVERABLES.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(doc, encoding="utf-8")
print(f"Wrote {out}")
