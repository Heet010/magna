"""Extract and filter the financially-relevant text from large report PDFs.

The full-year reports run 400-670 pages, far more than is useful (or affordable)
to send to the model. We score every page by how many financial keywords it
contains (English and German), then keep the highest-scoring pages up to a
character budget. The "at a glance" / key-figures pages near the front are
always kept because they hold the headline KPIs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import fitz  # PyMuPDF

# Keywords that signal a page carries the metrics we care about. Bilingual:
# Mercedes-Benz and BMW publish in English; Volkswagen's annual report is German.
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
    # per-share metrics
    "earnings per share": 3, "ergebnis je aktie": 3, "per share": 1,
    "dividend per share": 3, "dividende je aktie": 3, "dividend": 1,
    "dividende": 1, "market capitalisation": 2, "marktkapitalisierung": 2,
    "no. of shares": 1, "shares outstanding": 1, "anzahl aktien": 1,
    # navigational anchors for the highlight tables
    "key figures": 2, "kennzahlen": 2, "at a glance": 2, "auf einen blick": 2,
    "key performance indicators": 2, "balance sheet": 1, "bilanz": 1,
}

# Always keep these front pages — they usually hold the highlights/KPI summary.
ALWAYS_KEEP_FIRST = 12


@dataclass
class FilteredReport:
    company: str
    period: str
    total_pages: int
    kept_pages: list[int]      # 0-based page indices, in document order
    text: str                  # concatenated text of kept pages
    char_count: int


_word_re = re.compile(r"[^\W\d_]+", re.UNICODE)


def _score_page(text: str) -> float:
    low = text.lower()
    return sum(weight * low.count(kw) for kw, weight in KEYWORDS.items())


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
            score += 5  # bias toward the front-matter highlight pages
        scored.append((i, score, text))

    # Greedily take the best-scoring non-trivial pages until the budget is hit.
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
