"""Structured-output schema the agent must return (validated via Pydantic).

These models are passed to `client.messages.parse(..., output_format=...)` so the
Claude API constrains its response to exactly this shape — no brittle text parsing.
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

# How a single metric resolved against the source report.
MetricStatus = Literal[
    "reported",        # exact metric disclosed in the report
    "substituted",     # exact metric absent; a closest-equivalent KPI used instead
    "not_reported",    # disclosed in the full-year report but not the quarterly one
    "not_available",   # not disclosed anywhere for this company (use "N/A")
]


class Metric(BaseModel):
    metric_key: str = Field(description="Canonical key, e.g. 'revenue', 'ebit'.")
    value: str = Field(
        description="Figure with unit/currency, e.g. '€142,380 m'. "
        "Use 'Not Reported' if quarterly-absent, 'N/A' if undisclosed."
    )
    source_term: str = Field(
        description="The exact KPI name used in the report (verbatim), or '' if none."
    )
    source_page: str = Field(
        description="Page number(s) the figure was read from, taken from the "
        "'===== PAGE N =====' markers in the source text (e.g. '12' or '12, 45'). "
        "Use '' if computed or not available."
    )
    status: MetricStatus
    note: str = Field(
        description="Short note: substitution rationale, page reference, or caveat. "
        "Use an empty string '' if there is nothing to add.",
    )


class PeriodMetrics(BaseModel):
    period: Literal["FY2025", "Q1-2026"]
    currency: str = Field(description="Reporting currency, e.g. 'EUR'.")
    metrics: List[Metric] = Field(description="One entry per requested metric (10 total).")


class CompanyExtraction(BaseModel):
    company: str
    full_year: PeriodMetrics
    last_quarter: PeriodMetrics
    summary_note: str = Field(
        description="2-4 sentences flagging which outputs used a substituted/equivalent KPI."
    )
