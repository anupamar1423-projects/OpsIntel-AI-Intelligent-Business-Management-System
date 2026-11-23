"""OpsIntel AI interactive analytics and model-training frontend."""

from __future__ import annotations

import streamlit as st
import os

st.set_page_config(
    page_title="OpsIntel AI Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("project_label", "Demo organization")

pages = {
    "Workspace": [
        st.Page("app_pages/home.py", title="Overview", icon=":material/dashboard:", help="Business operations, finance, and model health at a glance."),
        st.Page("app_pages/operations.py", title="Operations AI", icon=":material/monitoring:", help="Score pipeline runs for unusual duration, volume, or failure patterns."),
        st.Page("app_pages/finance.py", title="Finance forecast", icon=":material/finance:", help="Review departmental expense forecasts and budget signals."),
        st.Page("app_pages/vendors.py", title="Vendor ranking", icon=":material/storefront:", help="Compare fictional suppliers using a transparent weighted score."),
    ],
    "AI & governance": [
        st.Page("app_pages/training.py", title="Training center", icon=":material/model_training:", help="Train demo models and inspect temporal holdout metrics and limitations."),
    ],
}

with st.sidebar:
    st.markdown("### OpsIntel AI")
    st.caption("Business operations · finance · AI decision support")
    st.session_state.project_label = st.text_input(
        "Workspace label", value=st.session_state.project_label, max_chars=60
    )
    st.divider()
    st.caption("This analytics frontend uses fictional demo data. Do not upload confidential records to a public demo.")
    django_url = os.getenv("DJANGO_APP_URL", "").strip()
    if django_url.startswith("https://"):
        st.link_button("Open Django business app", django_url, icon=":material/open_in_new:")

page = st.navigation(pages, position="sidebar")
page.run()
