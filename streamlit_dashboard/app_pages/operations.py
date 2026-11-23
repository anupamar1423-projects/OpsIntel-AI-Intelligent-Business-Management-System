from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard_utils import cached_models, load_operations, parse_csv_upload
from modeling import feature_operations, score_operations

st.title("Operations AI")
st.caption("Unsupervised pipeline anomaly scoring for human review. This page does not trigger recovery actions.")

sample = load_operations()
choice = st.segmented_control("Data source", ["Fictional sample", "Upload CSV"], default="Fictional sample", key="ops_source")
frame = sample
if choice == "Upload CSV":
    uploaded = st.file_uploader(
        "Upload pipeline runs (CSV)",
        type=["csv"],
        key="ops_upload",
        help="Required: duration_minutes, rows_processed, status. Optional: timestamp, pipeline_id, is_anomaly.",
    )
    if uploaded is not None:
        try:
            frame = parse_csv_upload(uploaded)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
    else:
        st.info("Select a CSV or switch back to the fictional sample.")
        st.stop()

try:
    feature_operations(frame)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

model, _, report = cached_models()
scored = score_operations(frame, model)
flagged = scored[scored["flagged"]]
failed = int(scored["status"].astype(str).str.lower().eq("failed").sum())

with st.container(horizontal=True):
    st.metric("Runs analyzed", f"{len(scored):,}", border=True)
    st.metric("Flagged for review", f"{len(flagged):,}", border=True)
    st.metric("Failed runs", f"{failed:,}", border=True)
    st.metric("Holdout ROC-AUC", f"{report['evaluation']['operations']['roc_auc']:.3f}", border=True)

if "timestamp" in scored.columns:
    timeline = scored.copy()
    timeline["timestamp"] = pd.to_datetime(timeline["timestamp"], errors="coerce")
    timeline = timeline.dropna(subset=["timestamp"]).sort_values("timestamp")
    if not timeline.empty:
        st.line_chart(timeline, x="timestamp", y="anomaly_score", color="flagged", alt="Pipeline anomaly score over time; higher values are more unusual")

st.subheader("Runs to review")
if flagged.empty:
    st.success("The model did not flag any rows. This is not proof that every run is normal.")
else:
    st.dataframe(
        flagged.head(500),
        hide_index=True,
        column_config={
            "anomaly_score": st.column_config.NumberColumn("Anomaly score", format="%.3f"),
            "duration_minutes": st.column_config.NumberColumn("Duration (min)", format="%.2f"),
        },
        alt="Pipeline runs flagged by the anomaly model for human review",
    )

st.download_button(
    "Download scored CSV",
    scored.to_csv(index=False).encode("utf-8"),
    file_name="opsintel_scored_pipeline_runs.csv",
    mime="text/csv",
    icon=":material/download:",
)
st.warning("Model thresholds can produce false alarms or miss real failures. Confirm alerts against operational context before taking action.", icon=":material/warning:")
