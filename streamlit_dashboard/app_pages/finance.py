from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard_utils import cached_models, load_finance, parse_csv_upload
from modeling import _finance_frame, forecast_finance

st.title("Finance forecast")
st.caption("Three-month expense estimates with budget comparisons. Forecasts are planning aids, not accounting advice.")

choice = st.segmented_control("Data source", ["Fictional sample", "Upload CSV"], default="Fictional sample", key="finance_source")
history = load_finance()
if choice == "Upload CSV":
    uploaded = st.file_uploader(
        "Upload monthly expenses (CSV)",
        type=["csv"],
        key="finance_upload",
        help="Required: month, department, expense_amount, budget_amount. Use anonymized data only.",
    )
    if uploaded is not None:
        try:
            history = parse_csv_upload(uploaded)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
    else:
        st.info("Select a CSV or switch back to the fictional sample.")
        st.stop()

try:
    clean = _finance_frame(history)
    if clean.groupby("department").size().min() < 3:
        raise ValueError("Each department needs at least three monthly observations.")
    _, model, report = cached_models()
    horizon = int(st.select_slider("Forecast horizon (months)", options=[1, 2, 3], value=3))
    forecasts = forecast_finance(clean, model, horizon=horizon)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

latest_month = clean["month"].max()
latest_spend = clean.loc[clean["month"].eq(latest_month), "expense_amount"].sum()
next_month = forecasts["month"].min()
next_rows = forecasts[forecasts["month"].eq(next_month)]
next_total = next_rows["forecast_expense"].sum()
next_budget = next_rows["budget_amount"].sum()

with st.container(horizontal=True):
    st.metric("Departments", f"{clean['department'].nunique()}", border=True)
    st.metric("Latest monthly expenses", f"₹{latest_spend:,.0f}", border=True)
    st.metric("Next-month forecast", f"₹{next_total:,.0f}", border=True)
    st.metric("Forecast vs budget", f"₹{next_total - next_budget:+,.0f}", border=True)

st.subheader("Department forecast")
st.dataframe(
    forecasts,
    hide_index=True,
    column_config={
        "forecast_expense": st.column_config.NumberColumn("Forecast expense", format="₹%,.0f"),
        "budget_amount": st.column_config.NumberColumn("Budget", format="₹%,.0f"),
    },
    alt="Forecast monthly expense and budget by department",
)

actual = clean.groupby("month", as_index=False)["expense_amount"].sum().rename(columns={"expense_amount": "amount"})
actual["series"] = "Actual"
future = forecasts.groupby("month", as_index=False)["forecast_expense"].sum().rename(columns={"forecast_expense": "amount"})
future["series"] = "Forecast"
chart = pd.concat([actual.tail(18), future], ignore_index=True)
st.line_chart(chart, x="month", y="amount", color="series", alt="Actual and forecast organization-wide expenses")
st.caption(f"Chronological holdout MAE on synthetic training data: ₹{report['evaluation']['finance']['mae']:,.0f}. Uploaded data is not used to retrain the model.")
st.download_button(
    "Download forecast CSV",
    forecasts.to_csv(index=False).encode("utf-8"),
    file_name="opsintel_expense_forecast.csv",
    mime="text/csv",
    icon=":material/download:",
)
