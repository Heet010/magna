# Deliverables

This document is the submission artifact: the **agent description**, the **prompt
used**, and where the **output** is produced. All of it is generated from the live
code (`src/prompts.py`) so it matches what the agent actually runs.

## 1. Agent description (system prompt)

The agent is an OpenAI (`gpt-4o-mini`) agent given this system prompt:

```text
You are a senior equity research analyst specialising in automotive OEMs. Your job
is to read the financial reports of automotive manufacturers and extract a precise,
comparable set of KPIs for an executive summary.

Operating principles:
- Use ONLY the source report text provided in the user message. Never use outside
  knowledge, prior memory of these companies, or estimates. If a figure is not in
  the provided text, do not invent it.
- Companies use different terminology for the same concept. When the exact requested
  metric is not disclosed, select the company's closest equivalent KPI, set the
  status to "substituted", and explain the substitution in the note (name the KPI
  you used and why it is the right proxy).
- Some metrics appear only in the full-year report, not the quarterly one. If a
  metric is genuinely absent from the quarterly report, return value "Not Reported"
  with status "not_reported".
- If a metric is not disclosed anywhere for a company, return value "N/A" with
  status "not_available".
- Always quote the exact KPI term the company used in `source_term`, and include the
  figure with its unit and currency in `value` (e.g. "€142,380 m", "8.5%", "EUR 4.20").
- Be conservative and auditable: prefer the headline/consolidated group figures, and
  note the page number (shown as "===== PAGE N =====") when helpful.
```

It returns a **structured output** (JSON schema enforced by the API — see
`src/schema.py`): for each company, a `full_year` and a `last_quarter` block, each
with all 10 metrics carrying `value`, `source_term` (the verbatim KPI name used by
the company), `source_page` (the PDF page the figure was read from, for spot-checking),
`status` (`reported` / `substituted` / `not_reported` / `not_available`), and a `note`.

## 2. Prompt used (task prompt)

One call is made per company, covering both report periods so the model aligns the
quarterly figures with the full-year KPI vocabulary. The user message is built by
`build_task_prompt(...)`. The metric instructions embedded in every prompt:

```text
Extract these 10 metrics for EACH period (full year and last quarter):

1. revenue              - Group revenue / net sales / "Umsatzerlöse".
2. ebit                 - EBIT or the company's "Operating Result / Operating Profit
                          / Operatives Ergebnis". State which one.
3. operating_margin     - EBIT margin / Return on Sales / "Umsatzrendite" = EBIT / Revenue.
                          If only the components are given, compute it and note that.
4. cash_metric          - The company's PREFERRED core cash KPI (e.g. Free Cash Flow,
                          Industrial/Automotive Free Cash Flow, Net Cash Flow). Pick the
                          one the company headlines and name it.
5. net_liquidity        - Net liquidity / net financial assets / net industrial liquidity
                          / "Nettoliquidität" — the company's liquidity indicator.
6. return_on_capital    - The company's value-based return-on-capital KPI (e.g. RoCE,
                          RoNA, CFROI, "Wertbeitrag/Value Contribution", return on equity).
                          Name the exact KPI.
7. cost_of_capital      - Cost of capital / WACC / hurdle rate — ONLY where disclosed.
                          Otherwise "N/A" (not_available).
8. eps                  - Earnings per share / "Ergebnis je Aktie".
9. dividend_per_share   - Dividend per share (proposed/paid). May be "Not Reported"
                          in a quarterly report.
10. market_cap_at_100eur- Market capitalisation IF the share price were EUR 100/share,
                          i.e. 100 * (number of shares outstanding). Compute it only if
                          the share count is in the text; otherwise "N/A".

Notes on coverage (do NOT force a value that is not supported by the text):
- One company does not disclose EPS & dividend per share -> use "N/A" there.
- One company's "market cap @ EUR 100/share" is not derivable (share count absent)
  -> use "N/A" there.
```

A complete example task prompt (BMW; the report placeholders are replaced at runtime
with the filtered PDF text):

```text
Company: BMW Group

Extract these 10 metrics for EACH period (full year and last quarter):

1. revenue              - Group revenue / net sales / "Umsatzerlöse".
2. ebit                 - EBIT or the company's "Operating Result / Operating Profit
                          / Operatives Ergebnis". State which one.
3. operating_margin     - EBIT margin / Return on Sales / "Umsatzrendite" = EBIT / Revenue.
                          If only the components are given, compute it and note that.
4. cash_metric          - The company's PREFERRED core cash KPI (e.g. Free Cash Flow,
                          Industrial/Automotive Free Cash Flow, Net Cash Flow). Pick the
                          one the company headlines and name it.
5. net_liquidity        - Net liquidity / net financial assets / net industrial liquidity
                          / "Nettoliquidität" — the company's liquidity indicator.
6. return_on_capital    - The company's value-based return-on-capital KPI (e.g. RoCE,
                          RoNA, CFROI, "Wertbeitrag/Value Contribution", return on equity).
                          Name the exact KPI.
7. cost_of_capital      - Cost of capital / WACC / hurdle rate — ONLY where disclosed.
                          Otherwise "N/A" (not_available).
8. eps                  - Earnings per share / "Ergebnis je Aktie".
9. dividend_per_share   - Dividend per share (proposed/paid). May be "Not Reported"
                          in a quarterly report.
10. market_cap_at_100eur- Market capitalisation IF the share price were EUR 100/share,
                          i.e. 100 * (number of shares outstanding). Compute it only if
                          the share count is in the text; otherwise "N/A".

Notes on coverage (do NOT force a value that is not supported by the text):
- One company does not disclose EPS & dividend per share -> use "N/A" there.
- One company's "market cap @ EUR 100/share" is not derivable (share count absent)
  -> use "N/A" there.


Return a CompanyExtraction object. For BOTH `full_year` and `last_quarter`, provide
all 10 metrics (each with metric_key, value, source_term, source_page, status, note).
For `source_page`, give the page number from the "===== PAGE N =====" marker that
precedes the figure you used, so the value can be spot-checked against the PDF (use
'' only when the value is computed or not available). In `summary_note`, briefly
state which outputs used a substituted/equivalent KPI rather than an exact match.

================ SOURCE: BMW Group — FULL-YEAR 2025 REPORT (filtered) ================
<filtered text of the BMW full-year 2025 report — see src/pdf_extractor.py>

================ SOURCE: BMW Group — LAST QUARTERLY REPORT (Q1 2026, filtered) ======
<filtered text of the BMW Q1 2026 report>
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
python run.py                 # -> output/executive_summary.{md,xlsx}
```
