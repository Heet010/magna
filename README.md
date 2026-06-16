# OEM Financial-Report Executive-Summary Agent

An AI agent that reads the financial reports of three automotive OEMs —
**BMW Group, Mercedes-Benz Group, Volkswagen Group** (full-year 2025 + Q1 2026) —
and produces an executive summary with a comparison table of the requested KPIs,
using **only** the source PDFs.

The agent is built on the **OpenAI API** (`gpt-4o-mini` by default; set
`AGENT_MODEL=gpt-4o` for higher accuracy on the figures). It is told to use
equivalent KPIs when an exact metric isn't disclosed and to flag every such
substitution, to mark quarterly-absent figures as **"Not Reported"**, and undisclosed
figures as **"N/A"**.

## How it works

```
Financial Reports/*.pdf
        │  1. extract text (PyMuPDF) + keep only finance-relevant pages (bilingual EN/DE)
        ▼
filtered report text  ──2. one Claude call per company (both periods)──▶  structured KPIs
        │                  (system prompt = agent description; structured output schema)
        ▼
output/executive_summary.md   +   output/executive_summary.xlsx   (6 data columns)
```

- `config.py` — companies, report files, the 10 metrics, model, budgets.
- `src/pdf_extractor.py` — scores every page by financial keywords, keeps the top
  pages within a character budget (full reports are 400–670 pages).
- `src/prompts.py` — the **agent description** (system prompt) and the **task prompt**.
- `src/schema.py` — the structured-output schema the model must return.
- `src/agent.py` — the OpenAI call (`chat.completions.parse`, strict structured output).
- `src/report_generator.py` — Markdown + Excel renderers.
- `src/pipeline.py` / `run.py` — orchestration and CLI.

## Setup

```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Git Bash:            source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env            # then put your OPENAI_API_KEY in .env
```

## Run

```bash
python run.py                      # all 3 companies -> Markdown + Excel in output/
python run.py --inspect            # show page-filtering stats only (no API key needed)
python run.py --no-cache           # ignore cached agent results, re-call the API
python run.py --company "BMW Group"
```

Outputs land in `output/`:
- `executive_summary.md` — the table + substitution notes
- `executive_summary.xlsx` — formatted workbook (substitutions highlighted) + notes sheet
- `cache/*.json` — per-company structured extractions (delete or `--no-cache` to refresh)

## The requested metrics (table rows)

Revenue · EBIT/Operating Result · Operating Margin · Cash Metric · Net Liquidity ·
Return on Capital · Cost of Capital · EPS · Dividend per Share · Market Cap @ €100/share.

Columns: full-year 2025 **and** Q1 2026 for each of the 3 companies (6 data columns).

See [`docs/DELIVERABLES.md`](docs/DELIVERABLES.md) for the agent description and the
exact prompt used (the submission artifact).
