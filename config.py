"""Central configuration: companies, report files, metrics, model, paths."""
from __future__ import annotations

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "Financial Reports"
OUTPUT_DIR = ROOT / "output"
CACHE_DIR = OUTPUT_DIR / "cache"

# --- Model -----------------------------------------------------------------
# OpenAI model. gpt-4o-mini = cheap/fast default; gpt-4o = more accurate on the
# numbers (recommended for the final submission). Override via AGENT_MODEL env var.
AGENT_MODEL = os.environ.get("AGENT_MODEL", "gpt-4o-mini")

# Budget (in characters) of filtered report text fed to the agent per report.
# ~4 chars/token, so 150k chars ≈ 38k tokens per report; both reports + prompt
# stay well inside gpt-4o-mini's 128k context window.
PER_REPORT_CHAR_BUDGET = 150_000

# --- Companies & reports ---------------------------------------------------
# period keys: "FY2025" = full-year 2025 report, "Q1-2026" = last quarterly report.
COMPANIES: dict[str, dict] = {
    "BMW Group": {
        "language": "en",
        "reports": {
            "FY2025": "BMW-Group-Report-2025-en.pdf",
            "Q1-2026": "BMW_Q1-2026-EN.pdf",
        },
    },
    "Mercedes-Benz Group": {
        "language": "en",
        "reports": {
            "FY2025": "mercedes-benz-annual-report-2025-incl-combined-management-report-mbg-ag.pdf",
            "Q1-2026": "mercedes-benz-interim-report-q1-2026.pdf",
        },
    },
    "Volkswagen Group": {
        "language": "de",
        "reports": {
            "FY2025": "VW_Volkswagen_geschaeftsbericht-2025.pdf",
            "Q1-2026": "VW_Volkswagen_q1-2026.pdf",
        },
    },
}

PERIOD_LABELS = {
    "FY2025": "Full Year 2025",
    "Q1-2026": "Q1 2026 (last quarter)",
}

# --- The 10 requested metrics (canonical keys + display labels) -------------
# Order here drives the rows of the executive-summary table.
METRICS: list[dict[str, str]] = [
    {"key": "revenue", "label": "Revenue"},
    {"key": "ebit", "label": "EBIT / Operating Result"},
    {"key": "operating_margin", "label": "Operating Margin (EBIT margin / RoS)"},
    {"key": "cash_metric", "label": "Cash Metric (core cash KPI)"},
    {"key": "net_liquidity", "label": "Net Liquidity / liquidity indicator"},
    {"key": "return_on_capital", "label": "Return on Capital (value-based KPI)"},
    {"key": "cost_of_capital", "label": "Cost of Capital / hurdle rate"},
    {"key": "eps", "label": "Earnings per Share (EPS)"},
    {"key": "dividend_per_share", "label": "Dividend per Share"},
    {"key": "market_cap_at_100eur", "label": "Market Cap @ EUR 100/share"},
]

METRIC_KEYS = [m["key"] for m in METRICS]
METRIC_LABELS = {m["key"]: m["label"] for m in METRICS}


def report_path(company: str, period: str) -> Path:
    """Absolute path to a company's report PDF for a given period."""
    return REPORTS_DIR / COMPANIES[company]["reports"][period]
