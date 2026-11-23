from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard_utils import cached_models, load_finance, load_operations, load_vendors
from modeling import forecast_finance, score_operations

st.title("Operations intelligence")
st.caption("Interactive demo built from deterministic, fictional business data.")

ops = load_operations()
finance = load_finance()
vendors = load_vendors()
op_model, finance_model, report = cached_models()
scored = score_operations(ops, op_model)
forecast = forecast_finance(finance, finance_model, horizon=1)

with st.container(horizontal=True):
    st.metric("Pipeline runs", f"{len(ops):,}", border=True)
    st.metric("Runs flagged for review", f"{int(scored['flagged'].sum()):,}", border=True)
    st.metric("Departments forecast", f"{forecast['department'].nunique()}", border=True)
    st.metric("Vendors in sample", f"{len(vendors)}", border=True)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Monthly expenses")
        monthly = finance.groupby("month", as_index=False)["expense_amount"].sum()
        st.line_chart(monthly, x="month", y="expense_amount", alt="Fictional monthly expenses across departments")
with right:
    with st.container(border=True):
        st.subheader("Next-month budget signals")
        st.bar_chart(forecast, x="department", y=["forecast_expense", "budget_amount"], alt="Forecast expenses and budgets by department")

with st.container(border=True):
    st.subheader("Model evaluation snapshot")
    op_metrics = report["evaluation"]["operations"]
    fin_metrics = report["evaluation"]["finance"]
    st.write(
        f"Operations ROC-AUC: **{op_metrics['roc_auc']:.3f}** · "
        f"Finance holdout MAE: **₹{fin_metrics['mae']:,.0f}** · Demo dataset: **synthetic**"
    )
    st.caption("Metrics describe generated demonstration data only. They do not promise performance on real company records.")
