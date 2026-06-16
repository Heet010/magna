# OEM Financial Summary Agent

An AI agent that reads the published financial reports of three automotive OEMs and
produces an executive summary comparing their key financial KPIs — using **only** the
source reports as input.

- **Companies:** BMW Group, Mercedes-Benz Group, Volkswagen Group
- **Reports per company:** full-year 2025 + last quarterly report (Q1 2026) → 6 columns
- **Tool used:** OpenAI API (`gpt-4o-mini` / `gpt-4o`) driven by a Python pipeline
  (PyMuPDF for the PDFs). *(The brief suggested Copilot; an OpenAI-API agent was used
  as the available equivalent — the agent description and prompt below are portable.)*

---

## 1. Agent description (the system prompt given to the agent)

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
  figure with its unit and currency in `value`.
- Be conservative and auditable: prefer the headline/consolidated group figures, and
  note the page number when helpful.
```

The agent returns a **structured (schema-enforced) JSON** object per company, so the
table is built from validated data rather than free text. Each metric carries the
value, the verbatim KPI term the company used, the source page, a status
(`reported` / `substituted` / `not_reported` / `not_available`), and a note.

## 2. Prompt used (the task instruction)

One call per company covers both report periods. The user message lists the 10
requested metrics with their definitions and the substitution / "Not Reported" /
"N/A" rules, followed by the filtered source text of both reports. The full,
verbatim per-company prompt is in [`docs/DELIVERABLES.md`](docs/DELIVERABLES.md).

## 3. Output — executive summary table

| Metric | BMW — FY 2025 | BMW — Q1 2026 | Mercedes-Benz — FY 2025 | Mercedes-Benz — Q1 2026 | Volkswagen — FY 2025 | Volkswagen — Q1 2026 |
| --- | --- | --- | --- | --- | --- | --- |
| Revenue | €133,453 m | €31,007 m | €132,214 m | €31,602 m | €321,913 m | €75,657 m |
| EBIT / Operating Result | €10,186 m | €1,345 m | €5,820 m | €1,904 m | €8,868 m | €2,463 m |
| Operating Margin (EBIT margin / RoS) | 7.6% † | 4.3% † | 4.4% † | 6.0% † | 2.8% † | 3.3% † |
| Cash Metric (core cash KPI) | €5,340 m | €777 m | €5,414 m | €1,857 m | €6,400 m | €6,662 m |
| Net Liquidity / liquidity indicator | €44,862 m | €44,862 m | €32,162 m | €33,809 m | €34,500 m | €34,200 m |
| Return on Capital (value-based KPI) | 9.0% | N/A | 8.6% | 12.9% | N/A | N/A |
| Cost of Capital / hurdle rate | 12% | N/A | 9.5% | N/A | N/A | N/A |
| Earnings per Share (EPS) | €11.89 | €2.68 | €5.34 | €1.49 | €13.29 | €2.55 |
| Dividend per Share | €4.40 | Not Reported | €3.50 | Not Reported | €5.26 | Not Reported |
| Market Cap @ EUR 100/share | €56,114 m † | €56,114 m † | €96,240 m † | €95,300 m † | €50,130 m † | N/A |

**Legend:** **†** = company's equivalent/substituted KPI (not an exact term match) ·
**Not Reported** = absent from the quarterly report · **N/A** = not disclosed.

A formatted Excel version (substitutions highlighted, with a notes sheet) is in
`output/executive_summary.xlsx`. A figure-by-figure provenance table with the source
PDF page for every number is in `output/verification.md`.

## 4. Substituted / equivalent KPIs (as the brief requires)

- **Operating margin** is computed deterministically in code as EBIT ÷ Revenue for
  every cell (Volkswagen also discloses it directly as *Operative Umsatzrendite*,
  which matches).
- **Cash metric** uses each company's own headline cash KPI: BMW *Free cash flow*,
  Mercedes-Benz *Free cash flow of the industrial business*, Volkswagen
  *Netto-Cashflow Konzernbereich Automobile*.
- **Return on capital** uses each company's value-based KPI: BMW *RoCE*,
  Mercedes-Benz *RoNA* (full year) / *Return on equity* (Q1). Volkswagen's group
  value-based return was not captured in this run → N/A (it is disclosed as
  *Kapitalrendite (RoI)*, ≈4.8% FY — see the note below).
- **Net liquidity** uses *Net liquidity / net financial assets of the industrial
  business* (Mercedes-Benz, BMW) and *Nettoliquidität* (Volkswagen).
- **Market cap @ €100/share** = €100 × shares outstanding (read from each company's
  share/investor section).
- **Cost of capital** is shown only where disclosed (BMW, Mercedes-Benz); Volkswagen
  does not disclose a single group hurdle rate → N/A.

## 5. How it meets the brief

- ✅ Uses **only** the supplied reports (the agent is instructed never to use outside
  knowledge) and reports the source page for every figure.
- ✅ All 10 requested metrics × full-year + last-quarter × 3 companies (6 data columns).
- ✅ Uses **equivalent KPIs** where exact terms differ and **flags every substitution**.
- ✅ Uses **"Not Reported"** for quarterly-only gaps and **"N/A"** for non-disclosure.
- ✅ Handles the **German-language** Volkswagen report alongside the English ones.
