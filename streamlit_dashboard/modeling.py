"""Training and inference helpers for reproducible demo models."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ARTIFACT_DIR = ROOT / "artifacts"
OPS_FEATURES = ["duration_minutes", "rows_processed", "failed"]
FINANCE_NUMERIC = ["month_number", "trend_index", "budget_amount", "lag_1", "lag_2", "lag_3", "rolling_3"]
FINANCE_CATEGORICAL = ["department"]
SEED = 20261123


def feature_operations(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"duration_minutes", "rows_processed", "status"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Operations CSV is missing columns: {', '.join(sorted(missing))}")
    out = frame.copy()
    for col in ("duration_minutes", "rows_processed"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    numeric = out[["duration_minutes", "rows_processed"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("Duration and row count must contain finite numbers in every row.")
    if (out["duration_minutes"] < 0).any() or (out["rows_processed"] < 0).any():
        raise ValueError("Duration and row count cannot be negative.")
    status = out["status"].astype(str).str.strip().str.lower()
    allowed = {"success", "failed", "running"}
    if not set(status).issubset(allowed):
        raise ValueError("Status values must be success, failed, or running.")
    out["failed"] = status.eq("failed").astype(int)
    return out[OPS_FEATURES]


def _finance_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"month", "department", "expense_amount", "budget_amount"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Finance CSV is missing columns: {', '.join(sorted(missing))}")
    out = frame.copy()
    out["month"] = pd.to_datetime(out["month"], errors="coerce")
    out["month"] = out["month"].dt.to_period("M").dt.to_timestamp()
    out["expense_amount"] = pd.to_numeric(out["expense_amount"], errors="coerce")
    out["budget_amount"] = pd.to_numeric(out["budget_amount"], errors="coerce")
    numeric = out[["expense_amount", "budget_amount"]].to_numpy(dtype=float)
    if out[["month", "expense_amount", "budget_amount", "department"]].isna().any().any() or not np.isfinite(numeric).all():
        raise ValueError("Finance data has missing or invalid dates, departments, amounts, or budgets.")
    if (out[["expense_amount", "budget_amount"]] < 0).any().any():
        raise ValueError("Expense and budget amounts cannot be negative.")
    out = out.groupby(["month", "department"], as_index=False).agg(
        expense_amount=("expense_amount", "sum"), budget_amount=("budget_amount", "sum")
    )
    out = out.sort_values(["month", "department"]).reset_index(drop=True)
    for department, group in out.groupby("department"):
        periods = group["month"].dt.to_period("M").sort_values().astype(int).to_numpy()
        if len(periods) > 1 and not np.all(np.diff(periods) == 1):
            raise ValueError(f"Department {department} has missing months. Fill the gaps before forecasting.")
    return out


def _finance_features(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for department, group in frame.groupby("department", sort=True):
        group = group.sort_values("month").reset_index(drop=True)
        expenses = group["expense_amount"].astype(float).tolist()
        for i in range(3, len(group)):
            month = group.loc[i, "month"]
            rows.append(
                {
                    "month": month,
                    "department": department,
                    "month_number": month.month,
                    "trend_index": i,
                    "budget_amount": float(group.loc[i, "budget_amount"]),
                    "lag_1": expenses[i - 1],
                    "lag_2": expenses[i - 2],
                    "lag_3": expenses[i - 3],
                    "rolling_3": float(np.mean(expenses[i - 3 : i])),
                    "target": expenses[i],
                }
            )
    result = pd.DataFrame(rows)
    result["month_number"] = np.sin(2 * np.pi * result["month_number"] / 12)
    result["month_cos"] = np.cos(2 * np.pi * pd.to_datetime(result["month"]).dt.month / 12)
    return result


def _make_finance_model() -> Pipeline:
    prep = ColumnTransformer(
        [
            ("numeric", StandardScaler(), FINANCE_NUMERIC),
            ("department", OneHotEncoder(handle_unknown="ignore"), FINANCE_CATEGORICAL),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("features", prep),
            ("regressor", RandomForestRegressor(n_estimators=240, min_samples_leaf=2, random_state=SEED, n_jobs=1)),
        ]
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def train_all() -> dict[str, object]:
    ops_path = DATA_DIR / "operations_synthetic.csv"
    finance_path = DATA_DIR / "finance_synthetic.csv"
    if not ops_path.exists() or not finance_path.exists():
        from generate_dataset import main as generate_data

        generate_data()

    ops = pd.read_csv(ops_path)
    train_end = int(len(ops) * 0.70)
    validation_end = int(len(ops) * 0.80)
    if train_end < 100 or validation_end - train_end < 20 or len(ops) - validation_end < 20:
        raise ValueError("Operations training data needs at least 120 rows for train, validation, and test periods.")
    train_frame = ops.iloc[:train_end]
    validation_frame = ops.iloc[train_end:validation_end]
    test_frame = ops.iloc[validation_end:]
    X_train = feature_operations(train_frame)
    X_test = feature_operations(test_frame)
    y_train = pd.to_numeric(train_frame["is_anomaly"], errors="coerce").astype(int)
    y_test = pd.to_numeric(test_frame["is_anomaly"], errors="coerce").astype(int)
    normal_train = X_train.loc[y_train.eq(0)]
    y_validation = pd.to_numeric(validation_frame["is_anomaly"], errors="coerce").astype(int)
    if len(normal_train) < 100 or y_test.nunique() < 2 or y_validation.nunique() < 2:
        raise ValueError("Operations data needs 100 normal training rows and both classes in validation and test periods.")
    op_model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("isolation_forest", IsolationForest(contamination=0.055, random_state=SEED, n_estimators=250)),
        ]
    )
    op_model.fit(normal_train)
    validation_scores = -op_model.decision_function(feature_operations(validation_frame))
    candidate_thresholds = np.quantile(validation_scores, np.linspace(0.02, 0.98, 97))
    threshold_rows = []
    for threshold in candidate_thresholds:
        candidate_predictions = (validation_scores > threshold).astype(int)
        threshold_rows.append(
            (f1_score(y_validation, candidate_predictions, zero_division=0), float(threshold))
        )
    _, calibrated_threshold = max(threshold_rows, key=lambda item: (item[0], item[1]))
    op_model.score_threshold_ = calibrated_threshold
    op_scores = -op_model.decision_function(X_test)
    op_pred = (op_scores > calibrated_threshold).astype(int)
    op_metrics = {
        "roc_auc": float(roc_auc_score(y_test, op_scores)),
        "precision": float(precision_score(y_test, op_pred, zero_division=0)),
        "recall": float(recall_score(y_test, op_pred, zero_division=0)),
        "f1": float(f1_score(y_test, op_pred, zero_division=0)),
        "train_rows": int(len(train_frame)),
        "normal_train_rows": int(len(normal_train)),
        "validation_rows": int(len(validation_frame)),
        "test_rows": int(len(test_frame)),
        "test_anomaly_rate": float(y_test.mean()),
        "calibrated_threshold": float(calibrated_threshold),
    }

    finance = _finance_frame(pd.read_csv(finance_path))
    feat = _finance_features(finance)
    if len(feat) < 100:
        raise ValueError("Finance training data needs at least 100 usable monthly rows.")
    last_train_month = feat["month"].sort_values().unique()[int(len(feat["month"].unique()) * 0.80) - 1]
    train = feat[feat["month"] <= last_train_month]
    test = feat[feat["month"] > last_train_month]
    model = _make_finance_model()
    model.fit(train[FINANCE_NUMERIC + FINANCE_CATEGORICAL], train["target"])
    pred = model.predict(test[FINANCE_NUMERIC + FINANCE_CATEGORICAL])
    actual = test["target"].to_numpy(dtype=float)
    finance_metrics = {
        "mae": float(mean_absolute_error(actual, pred)),
        "rmse": float(np.sqrt(mean_squared_error(actual, pred))),
        "mape_percent": float(np.mean(np.abs((actual - pred) / np.maximum(np.abs(actual), 1.0))) * 100),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "test_start": str(pd.Timestamp(test["month"].min()).date()),
        "test_end": str(pd.Timestamp(test["month"].max()).date()),
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(op_model, ARTIFACT_DIR / "operations_isolation_forest.joblib", compress=3)
    joblib.dump(model, ARTIFACT_DIR / "finance_random_forest.joblib", compress=3)
    report = {
        "project": "OpsIntel AI",
        "dataset_type": "deterministic synthetic demonstration data; not real company records",
        "seed": SEED,
        "operations_dataset_sha256": _file_sha256(ops_path),
        "finance_dataset_sha256": _file_sha256(finance_path),
        "operations_features": OPS_FEATURES,
        "finance_features": FINANCE_NUMERIC + FINANCE_CATEGORICAL,
        "operations_model": "StandardScaler + IsolationForest, trained on normal rows in the first 70%; threshold calibrated on the next 10%; final 20% held out",
        "finance_model": "OneHotEncoder + StandardScaler + RandomForestRegressor, chronological holdout",
        "evaluation": {"operations": op_metrics, "finance": finance_metrics},
        "limitations": [
            "Synthetic data is for demonstration and cannot establish real business performance.",
            "Anomaly scores require human review; false positives and false negatives are possible.",
            "Forecasts are planning estimates, not accounting advice or guaranteed outcomes.",
            "Vendor recommendation is a transparent weighted ranking, not a trained model.",
        ],
    }
    (ARTIFACT_DIR / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def load_models() -> tuple[Pipeline, Pipeline, dict[str, object]]:
    op_path = ARTIFACT_DIR / "operations_isolation_forest.joblib"
    finance_path = ARTIFACT_DIR / "finance_random_forest.joblib"
    report_path = ARTIFACT_DIR / "training_report.json"
    if not (op_path.exists() and finance_path.exists() and report_path.exists()):
        train_all()
    return (
        joblib.load(op_path),
        joblib.load(finance_path),
        json.loads(report_path.read_text(encoding="utf-8")),
    )


def score_operations(frame: pd.DataFrame, model: Pipeline) -> pd.DataFrame:
    features = feature_operations(frame)
    scores = -model.decision_function(features)
    result = frame.copy()
    result["anomaly_score"] = scores
    threshold = float(getattr(model, "score_threshold_", 0.0))
    result["flagged"] = scores > threshold
    result["review_note"] = np.where(result["flagged"], "Review this run", "No anomaly flagged")
    return result.sort_values("anomaly_score", ascending=False)


def forecast_finance(frame: pd.DataFrame, model: Pipeline, horizon: int = 3) -> pd.DataFrame:
    history = _finance_frame(frame)
    rows: list[dict[str, object]] = []
    for department, group in history.groupby("department", sort=True):
        group = group.sort_values("month").reset_index(drop=True)
        values = group["expense_amount"].astype(float).tolist()
        budgets = group["budget_amount"].astype(float).tolist()
        if len(group) < 3:
            raise ValueError(f"Department {department} needs at least 3 months of history.")
        last_month = pd.Timestamp(group["month"].iloc[-1])
        trend_index = len(group)
        for step in range(horizon):
            month = last_month + pd.offsets.MonthBegin(step + 1)
            budget = budgets[-1] * (1 + 0.002 * (step + 1))
            row = {
                "month_number": np.sin(2 * np.pi * month.month / 12),
                "department": department,
                "trend_index": trend_index + step,
                "budget_amount": budget,
                "lag_1": values[-1],
                "lag_2": values[-2],
                "lag_3": values[-3],
                "rolling_3": float(np.mean(values[-3:])),
            }
            estimate = max(0.0, float(model.predict(pd.DataFrame([row])[FINANCE_NUMERIC + FINANCE_CATEGORICAL])[0]))
            rows.append(
                {
                    "month": pd.Timestamp(month),
                    "department": department,
                    "forecast_expense": round(estimate, 2),
                    "budget_amount": round(budget, 2),
                    "budget_status": "Review" if estimate > budget else "Within budget",
                }
            )
            values.append(estimate)
    return pd.DataFrame(rows)
