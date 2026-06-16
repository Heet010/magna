"""Extract and filter the financially-relevant text from the report PDFs.

Each page is scored by financial keywords (English and German); the highest-scoring
pages are kept up to a character budget, preserving table context.
"""
from __future__ import annotations

from dataclasses import dataclass

import fitz  # PyMuPDF

KEYWORDS: dict[str, float] = {
    # income statement / revenue / EBIT
    "revenue": 3, "umsatzerlöse": 3, "umsatz": 1, "net sales": 2,
    "ebit": 3, "operating result": 3, "operating profit": 3,
    "operatives ergebnis": 3, "operating margin": 3, "return on sales": 3,
    "umsatzrendite": 3, "income statement": 2, "gewinn- und verlustrechnung": 2,
    # cash / liquidity
    "free cash flow": 3, "net cash flow": 2, "industrial free cash flow": 3,
    "net liquidity": 3, "nettoliquidität": 3, "net financial": 2,
    "net industrial": 2, "cash flow": 1, "netto-cashflow": 2,
    "liquidity": 1, "liquidität": 1,
    # return-on-capital / value-based KPIs
    "return on capital": 3, "roce": 3, "rona": 3, "return on equity": 2,
    "value contribution": 3, "wertbeitrag": 3, "economic value": 3,
    "value added": 2, "kapitalrendite": 3, "gesamtkapitalrendite": 3,
    "return on net assets": 3,
    # cost of capital / hurdle
    "cost of capital": 3, "kapitalkosten": 3, "wacc": 3, "hurdle": 2,
    # per-share / investor metrics (boosted — these pages hold EPS, the dividend
    # proposal and the share count, and are easily crowded out)
    "earnings per share": 4, "ergebnis je aktie": 4, "per share": 2,
    "dividend per share": 4, "dividende je aktie": 4, "dividend proposal": 4,
    "dividende je vorzugsaktie": 4, "dividende je stammaktie": 4,
    "dividendenvorschlag": 4, "vorzugsaktie": 2, "stammaktie": 2,
    "dividend": 1, "dividende": 1,
    "market capitalisation": 3, "market capitalization": 3, "marktkapitalisierung": 3,
    "number of shares": 4, "no. of shares": 3, "shares outstanding": 4,
    "shares issued": 3, "issued capital": 3, "no-par value shares": 4,
    "stückaktien": 4, "grundkapital": 3, "anzahl der aktien": 4, "anzahl aktien": 3,
    "information on shares": 3, "the bmw share": 3, "investor relations": 1,
    # navigational anchors for the highlight tables
    "key figures": 2, "kennzahlen": 2, "at a glance": 2, "auf einen blick": 2,
    "key performance indicators": 2, "balance sheet": 1, "bilanz": 1,
}

ALWAYS_KEEP_FIRST = 12  # front pages usually hold the KPI highlights


@dataclass
class FilteredReport:
    company: str
    period: str
    total_pages: int
    kept_pages: list[int]
    text: str
    char_count: int


def _score_page(text: str) -> float:
    low = text.lower()
    score = sum(weight * low.count(kw) for kw, weight in KEYWORDS.items())

    # Bonus for the dedicated investor/share page (dividend + EPS + share count).
    has_share = any(t in low for t in (
        "number of shares", "shares outstanding", "shares issued", "no-par value",
        "stückaktien", "anzahl der aktien", "grundkapital", "share capital"))
    has_payout = any(t in low for t in (
        "dividend per share", "dividend proposal", "dividende je",
        "dividendenvorschlag", "earnings per share", "ergebnis je aktie"))
    if has_share and has_payout:
        score += 12
    elif has_share:
        score += 6
    return score


def filter_report(path, company: str, period: str, char_budget: int) -> FilteredReport:
    """Return the highest-signal pages of a report within a character budget."""
    doc = fitz.open(path)
    total = doc.page_count
    pages = [(i, doc[i].get_text()) for i in range(total)]
    doc.close()

    scored = []
    for i, text in pages:
        score = _score_page(text)
        if i < ALWAYS_KEEP_FIRST:
            score += 5
        scored.append((i, score, text))

    ranked = sorted(scored, key=lambda t: t[1], reverse=True)
    kept: dict[int, str] = {}
    used = 0
    for i, score, text in ranked:
        if score <= 0 or not text.strip():
            continue
        if used + len(text) > char_budget and kept:
            continue
        kept[i] = text
        used += len(text)
        if used >= char_budget:
            break

    ordered = sorted(kept)
    blocks = [f"\n\n===== PAGE {i + 1} =====\n{kept[i]}" for i in ordered]
    return FilteredReport(
        company=company,
        period=period,
        total_pages=total,
        kept_pages=ordered,
        text="".join(blocks),
        char_count=used,
    )
