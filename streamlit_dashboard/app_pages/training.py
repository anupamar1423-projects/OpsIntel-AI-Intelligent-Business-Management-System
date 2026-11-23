from __future__ import annotations

import streamlit as st

from dashboard_utils import clear_cached_models, model_report, project_data_files
from modeling import train_all

st.title("Model training center")
st.caption("Train the demonstration models from bundled, deterministic synthetic datasets and inspect their holdout metrics.")
st.warning(
    "The included records are generated and contain no real business data. "
    "A good score on synthetic data does not prove real-world accuracy.",
    icon=":material/science:",
)

st.subheader("Datasets included")
for path in project_data_files():
    st.write(f"`{path.name}`")

if st.button("Train / retrain demo models", type="primary", icon=":material/model_training:"):
    try:
        with st.spinner("Training models and calculating chronological holdout metrics…"):
            report = train_all()
        clear_cached_models()
        st.session_state["latest_training_report"] = report
        st.success("Training finished. Model files and evaluation report were refreshed.")
    except (ValueError, OSError, RuntimeError) as exc:
        st.error(f"Training did not finish: {exc}")

try:
    report = st.session_state.get("latest_training_report") or model_report()
except (ValueError, OSError, RuntimeError) as exc:
    st.error(f"Could not load the training report: {exc}")
    st.stop()

left, right = st.columns(2)
with left:
    st.subheader("Operations anomaly model")
    st.json(report["evaluation"]["operations"])
with right:
    st.subheader("Finance forecast model")
    st.json(report["evaluation"]["finance"])

st.subheader("Training design")
st.markdown(
    "- Operations uses **StandardScaler + IsolationForest**, trained on normal rows in the first chronological 80% window. The later 20% is held out.\n"
    "- Finance uses **Random Forest regression** with prior-month expense features and a chronological holdout.\n"
    "- Vendor ordering uses a transparent weighted score because the project has no verified vendor-outcome labels.\n"
    "- Review precision, recall, and false alarms before relying on operational alerts."
)
st.json({"limitations": report["limitations"], "seed": report["seed"]})
