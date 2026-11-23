from __future__ import annotations

import streamlit as st

from dashboard_utils import load_vendors

st.title("Vendor ranking")
st.caption("An explainable comparison score. This is a weighted rule, not a trained vendor model.")

vendors = load_vendors()
categories = ["All categories", *sorted(vendors["category"].unique())]
category = st.selectbox("Vendor category", categories)
view = vendors if category == "All categories" else vendors[vendors["category"].eq(category)].copy()
if view.empty:
    st.info("No vendors match this category.")
    st.stop()

low, high = float(view["unit_price"].min()), float(view["unit_price"].max())
view["price_score"] = 100.0 if high == low else 100 * (high - view["unit_price"]) / (high - low)
view["recommendation_score"] = (
    0.35 * view["reliability"] + 0.30 * view["on_time_rate"]
    + 0.20 * view["quality_score"] + 0.15 * view["price_score"]
).round(1)
view["rank"] = view["recommendation_score"].rank(method="dense", ascending=False).astype(int)
view = view.sort_values(["rank", "unit_price"])

st.info("Weights: reliability 35%, on-time delivery 30%, quality 20%, relative price 15%. Review contract terms and suitability before selecting a supplier.", icon=":material/info:")
st.dataframe(
    view,
    hide_index=True,
    column_config={
        "unit_price": st.column_config.NumberColumn("Unit price", format="₹%,.2f"),
        "recommendation_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
        "rank": st.column_config.NumberColumn("Rank", format="%d"),
    },
    alt="Supplier comparison sorted by transparent weighted score",
)
