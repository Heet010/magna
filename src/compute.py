"""Deterministic recomputation of the two *derived* metrics, so the table never
depends on the model's arithmetic.

- operating_margin = EBIT / Revenue  (both already extracted, in millions)
- market_cap_at_100eur = EUR 100 x shares_outstanding

The model still extracts the raw inputs (revenue, EBIT, share count); we do the
multiplication/division in code and overwrite those two cells.
"""
from __future__ import annotations

import re

from src.schema import CompanyExtraction, Metric, PeriodMetrics

_NOT_NUMERIC = {"n/a", "not reported", "not available", "", "—"}


def _num(s: str) -> float | None:
    """Parse the leading number from a value string, handling EN/DE separators."""
    m = re.search(r"[-+]?\d[\d,. ]*\d|\d", s or "")
    if not m:
        return None
    tok = m.group().replace(" ", "")
    if "," in tok and "." in tok:           # 1,234.56 -> English
        tok = tok.replace(",", "")
    elif "," in tok:
        parts = tok.split(",")
        if all(len(p) == 3 for p in parts[1:]):  # 1,234,567 -> thousands
            tok = tok.replace(",", "")
        else:                                     # 5,26 -> German decimal
            tok = tok.replace(",", ".")
    try:
        return float(tok)
    except ValueError:
        return None


def _millions(s: str) -> float | None:
    """Value expressed in millions (revenue/EBIT are reported in millions)."""
    if not s or s.strip().lower() in _NOT_NUMERIC:
        return None
    n = _num(s)
    if n is None:
        return None
    low = s.lower()
    if any(w in low for w in ("bn", "billion", "mrd", "milliard")):
        return n * 1000
    return n  # assume already in millions


def _count(s: str) -> float | None:
    """Parse a share count, scaling spelled-out magnitudes (million/billion)."""
    if not s or s.strip().lower() in _NOT_NUMERIC:
        return None
    n = _num(s)
    if n is None:
        return None
    low = s.lower()
    for word, mult in (
        ("trillion", 1e12), ("billion", 1e9), ("bn", 1e9), ("milliard", 1e9),
        ("million", 1e6), ("mio", 1e6), ("mn", 1e6),
        ("thousand", 1e3), ("tsd", 1e3),
    ):
        if word in low:
            return n * mult
    return n


def _find(pm: PeriodMetrics, key: str) -> Metric | None:
    return next((m for m in pm.metrics if m.metric_key == key), None)


def _recompute_period(pm: PeriodMetrics) -> None:
    rev = _find(pm, "revenue")
    ebit = _find(pm, "ebit")
    margin = _find(pm, "operating_margin")
    mcap = _find(pm, "market_cap_at_100eur")

    # operating_margin = EBIT / Revenue
    if margin is not None and rev is not None and ebit is not None:
        r, e = _millions(rev.value), _millions(ebit.value)
        if r and e is not None and r != 0:
            margin.value = f"{e / r * 100:.1f}%"
            margin.status = "substituted"
            margin.source_term = margin.source_term or "EBIT / Revenue"
            margin.note = f"Computed in code: EBIT ({ebit.value}) / Revenue ({rev.value})."

    # market_cap_at_100eur = EUR 100 x shares outstanding
    if mcap is not None:
        shares = _count(pm.shares_outstanding)
        if shares and shares > 0:
            mcap.value = f"€{shares * 100 / 1e6:,.0f} m"
            mcap.status = "substituted"
            mcap.source_term = mcap.source_term or "EUR 100 × shares outstanding"
            mcap.note = f"Computed in code: EUR 100 × {shares:,.0f} shares."


def recompute_derived(ex: CompanyExtraction) -> CompanyExtraction:
    """Overwrite operating_margin and market_cap with code-computed values."""
    _recompute_period(ex.full_year)
    _recompute_period(ex.last_quarter)
    return ex
