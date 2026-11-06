import json

import pandas as pd
import streamlit as st

from .data import load_sources
from .io import ROOT, require, theme
from .retrieval import Retriever, investigate


@st.cache_resource
def retrieval_index():
    return Retriever(load_sources())


def main():
    theme("Casebook", "Version-aware evidence for software support investigations")
    require(ROOT / "reports/metrics.json", "casebook run")
    require(ROOT / "models/keyword.joblib", "casebook run")
    require(ROOT / "data/processed/sources.json", "casebook run")
    metrics = json.loads((ROOT / "reports/metrics.json").read_text())
    cols = st.columns(3)
    cols[0].metric("Evidence chunks", f"{metrics['sources']:,}")
    cols[1].metric("Sampled public issues", metrics["operational"]["sampled_issues"])
    cols[2].metric("Benchmark questions", metrics["evaluation"]["questions"])
    tabs = st.tabs(["Investigate", "Retrieval evaluation", "Issue sample", "Recorded examples"])
    with tabs[0]:
        question = st.text_area(
            "Describe the problem",
            "How do I configure a custom SSL certificate authority bundle for TLS verification?",
        )
        version = st.selectbox("Documentation version", ["0.28.1", "0.27.2"])
        historical = st.checkbox("Limit evidence to a historical date")
        cutoff = st.date_input("Evidence cutoff") if historical else None
        generative = st.checkbox(
            "Generate a diagnostic question locally",
            help="Downloads a local model if necessary. Generated text is unverified and requires review.",
        )
        if st.button("Prepare investigation", type="primary"):
            with st.spinner("Finding source evidence"):
                result = investigate(
                    retrieval_index(),
                    question,
                    version,
                    str(cutoff) if cutoff else None,
                    "local" if generative else "extractive",
                )
            if result["status"] == "insufficient_evidence":
                st.warning(
                    "Insufficient evidence. Gather the exact version, traceback and a minimal reproducer."
                )
            for e in result["evidence"]:
                with st.expander(f"{e['title']} · {e['version']}", expanded=True):
                    st.code(e["quote"], language=None)
                    st.link_button("Open original source", e["url"])
            if result["generated_diagnostic_question"]:
                st.warning("Generated diagnostic question — review before use")
                st.write(result["generated_diagnostic_question"])
            st.write("Missing context", result["missing_information"])
            st.caption(result["limitations"])
            st.download_button(
                "Download investigation trace", json.dumps(result, indent=2), "investigation.json"
            )
    with tabs[1]:
        st.dataframe(pd.DataFrame(metrics["evaluation"]["retrieval"]), hide_index=True)
        st.caption(metrics["evaluation"]["caveat"])
        st.dataframe(pd.read_csv(ROOT / "reports/workflow_evaluation.csv"), hide_index=True)
    with tabs[2]:
        st.caption(metrics["operational"]["sampling"])
        st.dataframe(pd.read_csv(ROOT / "reports/issue_categories.csv"), hide_index=True)
        st.dataframe(pd.read_csv(ROOT / "data/processed/issues.csv"), hide_index=True)
    with tabs[3]:
        st.json(json.loads((ROOT / "reports/investigation_examples.json").read_text()))
