"""Structured-output schema the agent must return (enforced via the OpenAI API).

The Field descriptions below are sent to the model as the JSON schema, so they are
instructions, not just documentation.
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
    shares_outstanding: str = Field(
        description="Total number of shares outstanding/issued as a plain integer "
        "(e.g. '561135000'), used to compute market cap. Include all share classes "
        "where there are several (ordinary + preferred). Use '' if not in the text."
    )
    metrics: List[Metric] = Field(description="One entry per requested metric (10 total).")


class CompanyExtraction(BaseModel):
    company: str
    full_year: PeriodMetrics
    last_quarter: PeriodMetrics
    summary_note: str = Field(
        description="2-4 sentences flagging which outputs used a substituted/equivalent KPI."
    )
