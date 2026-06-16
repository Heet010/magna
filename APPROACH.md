# How this project works (complete approach)

A walkthrough of *why* the project is built the way it is and *how* each piece works —
written for you, not for submission.

## 1. The problem in one line

Read 6 large PDFs (3 OEMs × full-year 2025 + Q1 2026), pull 10 specific financial
KPIs out of each, and lay them side by side in one table — using only the PDFs, with
each company's own KPI names, and flagging anything substituted or missing.

Two things make it hard:
1. **The reports are huge** — 434 / 409 / 673 pages for the annual reports. You can't
   (and shouldn't) feed all of that to a model.
2. **Every company names things differently**, and Volkswagen's report is in **German**.

## 2. The architecture (RAG-lite, not vector RAG)

```
Financial Reports/*.pdf
   │
   │  (1) EXTRACT + FILTER  — src/pdf_extractor.py
   │      read text per page, score each page by financial keywords,
   │      keep the highest-signal pages within a character budget
   ▼
filtered text per report  (≈50k tokens each, tables kept intact)
   │
   │  (2) EXTRACT KPIs  — src/agent.py  (one OpenAI call per company)
   │      system prompt = analyst role; user prompt = metrics + both reports;
   │      response constrained to a JSON schema (src/schema.py)
   ▼
structured KPIs per company  →  cached in output/cache/*.json
   │
   │  (3) RENDER  — src/report_generator.py
   ▼
output/executive_summary.md   +   .xlsx   +   verification.md
```

**Why page-filtering instead of classic embedding/vector RAG?** With only 6 known
documents and a 128k-token model context, the right move is *lexical retrieval at page
granularity*, not chunk-and-embed:
- **Tables stay whole.** A revenue number is meaningless without its column header
  (FY2025 vs FY2024, Group vs segment). Fixed-size chunking splits the number from its
  header and produces confident wrong answers — the #1 failure mode of RAG on
  financial extraction. Keeping whole pages preserves the table context.
- **We need guaranteed coverage of 10 metrics**, not "top-k most similar chunks."
- **The corpus is tiny and closed**, so a vector DB is pure overhead.

So this *is* retrieval-augmented — just with a cheaper, more precise retriever.

## 3. Stage 1 — PDF extraction & page filtering (`src/pdf_extractor.py`)

- Uses **PyMuPDF** (`fitz`) to pull selectable text per page (these PDFs have real
  text, not scans, so no OCR is needed).
- `_score_page()` scores every page by counting weighted **financial keywords**, in
  **English and German** (e.g. `revenue`/`umsatzerlöse`, `net liquidity`/`nettoliquidität`,
  `earnings per share`/`ergebnis je aktie`).
- A **co-occurrence bonus** boosts the dedicated "Information on shares / dividend"
  page (the one carrying the dividend proposal + EPS + share count together) so it
  survives the budget cut — these pages are otherwise crowded out by the dense
  financial statements. This is the fix that made dividend/EPS/market-cap appear.
- The front ~12 pages get a bias (they hold the "at a glance" KPI highlights).
- Pages are taken highest-score-first until the **character budget** (`config.PER_REPORT_CHAR_BUDGET`,
  200k chars ≈ 50k tokens) is hit, then re-sorted into document order. Each page is
  wrapped with a `===== PAGE N =====` marker so the model can cite where a figure came
  from.

Check what gets kept without spending an API call:
```bash
python run.py --inspect
```

## 4. Stage 2 — the extraction agent (`src/agent.py`, `src/prompts.py`, `src/schema.py`)

- **One OpenAI call per company**, covering both report periods together — so the
  model aligns the quarterly figures with the same KPI vocabulary it found in the
  annual report.
- **System prompt** (`AGENT_DESCRIPTION`) = the analyst persona + the rules:
  source-only, substitute-and-flag, "Not Reported" for quarterly gaps, "N/A" for
  non-disclosure, quote the verbatim KPI term, cite the page.
- **Task prompt** (`build_task_prompt`) = the 10 metric definitions + the two reports'
  filtered text.
- **Structured outputs**: `client.beta.chat.completions.parse(..., response_format=CompanyExtraction)`
  forces the reply to match the Pydantic schema in `src/schema.py` — no brittle text
  parsing, and every metric reliably carries `value`, `source_term`, `source_page`,
  `status`, `note`.
- **Caching**: each company's result is saved to `output/cache/*.json`. Re-runs reuse
  it (so tweaking the report layout is free); `--no-cache` forces fresh API calls.

## 5. Stage 3 — rendering (`src/report_generator.py`)

- `render_markdown` → the 6-column comparison table + a "Substituted & equivalent KPIs"
  section.
- `render_excel` → a formatted workbook (substitutions highlighted amber, N/A greyed)
  plus a "Notes & Substitutions" sheet.
- `render_verification` / `print_verification` → an audit view pairing every figure
  with the exact KPI term and the **source PDF page**, for fast spot-checking.

## 6. Running it

```bash
python -m venv .venv && source .venv/Scripts/activate   # (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
cp .env.example .env                 # add OPENAI_API_KEY

python run.py                        # all 3 companies -> output/
python run.py --no-cache             # re-call the API (ignore cache)
python run.py --verify               # print figure+page spot-check from cache
python run.py --inspect              # page-filter stats only (no API key)
```

Model is set in `config.py` / `.env` via `AGENT_MODEL`:
- `gpt-4o-mini` (default) — cheap/fast; fine for a draft.
- `gpt-4o` — more accurate on the numbers and on arithmetic (market-cap computation);
  recommended for the final run.

## 7. How to verify the output (important)

The numbers come from a model, so always spot-check before trusting:
1. `python run.py --verify` → see each figure with its cited page.
2. Open the matching PDF in `Financial Reports/` and jump to that page.
3. Note: the **printed page label is offset** from the PDF page index (by ~2 in the
   VW report), so the model's cited page is the PDF index, not the footer number.

## 8. Known limitations & how to harden

- **Self-reported pages can be wrong.** The cited page is a great pointer but the model
  can mis-cite on a wrong extraction. (Possible add-on: reject any `source_page` not in
  the retrieved page set, to catch hallucinated citations.)
- **Computed cells are done in Python, not by the model.** Operating margin
  (EBIT ÷ revenue) and market cap (€100 × shares outstanding) are recomputed in
  `src/compute.py` from the extracted inputs, so they no longer depend on the model's
  arithmetic. This means accuracy hinges on the *inputs* (revenue, EBIT, share count)
  being right — still worth spot-checking those three.
- **Keyword retrieval can miss unusual phrasing.** Mitigated with bilingual keywords +
  the co-occurrence bonus; a hybrid keyword+embedding scorer would raise recall further
  but is overkill for 6 docs.
- **Group vs segment figures.** The agent is told to prefer consolidated group numbers;
  still worth confirming Revenue/EBIT are group-level, not a segment.

## 9. File map

| File | Role |
| --- | --- |
| `config.py` | companies, report files, the 10 metrics, model, budgets |
| `src/pdf_extractor.py` | text extraction + bilingual page filtering |
| `src/prompts.py` | agent description (system) + task prompt builder |
| `src/schema.py` | structured-output schema (Pydantic) |
| `src/agent.py` | the OpenAI call + caching |
| `src/report_generator.py` | Markdown + Excel + verification renderers |
| `src/pipeline.py` | orchestration (`run`, `write_reports`, `load_cached`) |
| `run.py` | CLI (`--inspect`, `--verify`, `--no-cache`, `--company`) |
| `scripts/make_deliverables.py` | regenerates `docs/DELIVERABLES.md` from the live prompts |
| `output/` | generated reports + per-company cache |
