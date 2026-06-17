"""Streamlit web app: upload report PDFs, get the executive-summary table.

Run locally:  streamlit run app.py
Deploy:       Streamlit Community Cloud or Hugging Face Spaces, with the
              OPENAI_API_KEY set as a secret.
"""
from __future__ import annotations

import gc
import os
import shutil
import tempfile
from pathlib import Path

import streamlit as st

import config
from src.pipeline import run_on_files
from src.report_generator import excel_bytes, render_markdown

MAX_FILE_MB = 40          # reject oversized uploads instead of risking an OOM crash
PERIOD_KEY = {"Full year (annual)": "FY2025", "Quarter (interim)": "Q1-2026"}

# Server-side API key (set as a secret on the host).
try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass


def guess_company(name: str) -> str:
    n = name.lower()
    if "bmw" in n:
        return "BMW Group"
    if "mercedes" in n or "mbg" in n:
        return "Mercedes-Benz Group"
    if "volkswagen" in n or "vw" in n:
        return "Volkswagen Group"
    return ""


def guess_period_index(name: str) -> int:
    n = name.lower()
    quarterly = ("q1", "q2", "q3", "q4", "quarter", "interim", "zwischen")
    return 1 if any(t in n for t in quarterly) else 0


st.set_page_config(page_title="OEM Financial Summary Agent", layout="wide")
st.title("📊 OEM Financial Summary Agent")
st.caption(
    "Upload company financial-report PDFs (full-year and/or quarterly). The agent "
    "reads only the uploaded files and builds a comparable KPI table."
)

uploads = st.file_uploader(
    "Upload report PDFs", type="pdf", accept_multiple_files=True,
    help=f"Up to {MAX_FILE_MB} MB per file.",
)

if uploads:
    oversized = [f.name for f in uploads if f.size > MAX_FILE_MB * 1_000_000]
    if oversized:
        st.error(f"These files exceed {MAX_FILE_MB} MB: {', '.join(oversized)}. "
                 "Please upload smaller PDFs.")
        st.stop()

    st.subheader("Label each file")
    st.write("Set the company and which report period each PDF is.")
    labels: list[tuple] = []
    for i, f in enumerate(uploads):
        c1, c2, c3 = st.columns([3, 2, 2])
        c1.markdown(f"📄 **{f.name}**")
        company = c2.text_input("Company", value=guess_company(f.name), key=f"co{i}")
        period = c3.selectbox("Period", list(PERIOD_KEY), index=guess_period_index(f.name),
                              key=f"pe{i}")
        labels.append((f, company.strip(), PERIOD_KEY[period]))

    if st.button("Generate summary", type="primary"):
        unlabelled = [f.name for f, c, _ in labels if not c]
        if unlabelled:
            st.error(f"Please enter a company name for: {', '.join(unlabelled)}")
            st.stop()

        tmpdir = tempfile.mkdtemp(prefix="oem_")
        try:
            # Write uploads to temp files and group them by company/period.
            file_map: dict[str, dict[str, str]] = {}
            for f, company, period_key in labels:
                path = Path(tmpdir) / f"{company}_{period_key}.pdf".replace(" ", "_")
                path.write_bytes(f.getbuffer())
                file_map.setdefault(company, {})[period_key] = str(path)

            with st.status("Running the agent…", expanded=True) as status:
                status.write(f"Companies: {', '.join(file_map)}")
                extractions = run_on_files(
                    file_map,
                    progress=lambda c: status.write(f"✓ extracted {c}"),
                )
                status.update(label="Done", state="complete")

            st.subheader("Executive summary")
            st.markdown(render_markdown(extractions))

            col1, col2 = st.columns(2)
            col1.download_button(
                "⬇️ Download Excel", data=excel_bytes(extractions),
                file_name="executive_summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            col2.download_button(
                "⬇️ Download Markdown", data=render_markdown(extractions),
                file_name="executive_summary.md", mime="text/markdown",
            )
        except Exception as exc:  # noqa: BLE001 — surface any failure to the user
            st.error(f"Something went wrong: {exc}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
            gc.collect()
else:
    st.info("Upload one or more PDF reports to begin.")
