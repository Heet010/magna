"""The agent's instructions: AGENT_DESCRIPTION is the system prompt and
build_task_prompt produces the per-company user message."""
from __future__ import annotations

# System prompt (the "Agent description")
AGENT_DESCRIPTION = """\
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
"""

# The 10 requested metrics, described for the model
METRIC_GUIDE = """\
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
8. eps                  - Earnings per share / "Ergebnis je Aktie". Check the
                          "Information on shares" / investor section, not just the
                          highlights page.
9. dividend_per_share   - Dividend per share (proposed or paid). Look for the
                          dividend proposal / "Dividendenvorschlag" in the share/
                          investor section of the full-year report. May be
                          "Not Reported" in a quarterly report.
10. market_cap_at_100eur- Market capitalisation IF the share price were EUR 100/share,
                          i.e. EUR 100 * (number of shares outstanding). Actively look
                          for the share count: "number of shares" / "shares
                          outstanding" / "no-par value shares" / issued capital /
                          "Anzahl der Aktien" / "Stückaktien" (usually in the share or
                          equity-notes section). If only EPS and net profit attributable
                          to shareholders are given, you MAY derive shares = net profit /
                          basic EPS. Show your computation in the note. Use "N/A" only
                          if the share count is genuinely not derivable from the text.

Coverage guidance (the source data is consistent with these, but rely on the TEXT,
not on these hints — do not force or suppress a value to match them):
- Exactly ONE company does not disclose EPS & dividend per share in the provided
  reports -> "N/A" for both of that company's EPS and dividend cells. The other two
  companies DO disclose EPS and (in the full-year report) a dividend.
- The "market cap @ EUR 100/share" is derivable for TWO of the three companies and
  not available for ONE.
"""


def build_task_prompt(company: str, fy_text: str, q_text: str) -> str:
    """Assemble the user message for one company (both report periods)."""
    return f"""\
Company: {company}

{METRIC_GUIDE}

Return a CompanyExtraction object. For BOTH `full_year` and `last_quarter`, provide
all 10 metrics (each with metric_key, value, source_term, source_page, status, note)
AND `shares_outstanding` (the total share count as a plain integer, summing all share
classes — this is used to compute market cap in code, so get it from the report; use
'' only if genuinely absent).
For `source_page`, give the page number from the "===== PAGE N =====" marker that
precedes the figure you used, so the value can be spot-checked against the PDF (use
'' only when the value is computed or not available).
Note: `operating_margin` and `market_cap_at_100eur` are recomputed in code from the
revenue, EBIT and shares_outstanding you provide — so make those three inputs as
accurate as possible; still fill the two derived cells with your best value.
In `summary_note`, briefly state which outputs used a substituted/equivalent KPI
rather than an exact match.

================ SOURCE: {company} — FULL-YEAR 2025 REPORT (filtered) ================
{fy_text}

================ SOURCE: {company} — LAST QUARTERLY REPORT (Q1 2026, filtered) ======
{q_text}
"""
