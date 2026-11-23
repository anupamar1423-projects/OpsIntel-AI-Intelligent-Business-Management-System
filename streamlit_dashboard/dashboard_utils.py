"""Shared, validated data access for the Streamlit analytics pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from modeling import ARTIFACT_DIR, DATA_DIR, load_models

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_ROWS = 100_000


@st.cache_data(ttl="5m")
def load_operations() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "operations_synthetic.csv", parse_dates=["timestamp"])


@st.cache_data(ttl="5m")
def load_finance() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "finance_synthetic.csv", parse_dates=["month"])


@st.cache_data(ttl="5m")
def load_vendors() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "vendors_synthetic.csv")


@st.cache_resource
def cached_models():
    return load_models()


def parse_csv_upload(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        raise ValueError("Choose a CSV file first.")
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValueError("CSV uploads are limited to 10 MB.")
    try:
        frame = pd.read_csv(uploaded_file, nrows=MAX_UPLOAD_ROWS + 1)
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        raise ValueError("Could not read this CSV. Save it as UTF-8 CSV and check its columns.") from exc
    if frame.empty:
        raise ValueError("The uploaded CSV has no rows.")
    if len(frame) > MAX_UPLOAD_ROWS:
        raise ValueError("CSV uploads are limited to 100,000 rows.")
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if len(set(frame.columns)) != len(frame.columns):
        raise ValueError("Column names must be unique after trimming spaces.")
    return frame


def model_report() -> dict:
    return cached_models()[2]


def clear_cached_models() -> None:
    cached_models.clear()


def project_data_files():
    return sorted(DATA_DIR.glob("*.csv"))
