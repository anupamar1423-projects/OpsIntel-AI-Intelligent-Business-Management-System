from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from generate_dataset import generate_finance, generate_operations
from modeling import DATA_DIR, _finance_frame, feature_operations, forecast_finance, load_models, score_operations


class DataValidationTests(unittest.TestCase):
    def test_negative_pipeline_values_are_rejected(self):
        bad = pd.DataFrame(
            {"duration_minutes": [-1], "rows_processed": [10], "status": ["success"]}
        )
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            feature_operations(bad)

    def test_unknown_pipeline_status_is_rejected(self):
        bad = pd.DataFrame(
            {"duration_minutes": [2], "rows_processed": [10], "status": ["maybe"]}
        )
        with self.assertRaisesRegex(ValueError, "Status values"):
            feature_operations(bad)

    def test_finance_dates_are_monthly_and_gaps_are_rejected(self):
        bad = pd.DataFrame(
            {
                "month": ["2025-01-01", "2025-03-01"],
                "department": ["Ops", "Ops"],
                "expense_amount": [100, 110],
                "budget_amount": [120, 120],
            }
        )
        with self.assertRaisesRegex(ValueError, "missing months"):
            _finance_frame(bad)


class TrainedModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ops_model, cls.finance_model, cls.report = load_models()

    def test_bundled_datasets_have_expected_size_and_columns(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
            base = Path(temp_dir)
            ops_path, finance_path = base / "ops.csv", base / "finance.csv"
            generate_operations(ops_path, rows=500)
            generate_finance(finance_path, months=24)
            ops = pd.read_csv(ops_path)
            finance = pd.read_csv(finance_path)
        self.assertEqual(len(ops), 500)
        self.assertIn("is_anomaly", ops.columns)
        self.assertEqual(finance["department"].nunique(), 5)

    def test_models_have_heldout_evaluation(self):
        op = self.report["evaluation"]["operations"]
        finance = self.report["evaluation"]["finance"]
        self.assertGreater(op["roc_auc"], 0.5)
        self.assertGreater(op["test_rows"], 0)
        self.assertGreater(finance["mae"], 0)
        self.assertGreater(finance["test_rows"], 0)

    def test_pipeline_scoring_and_three_month_forecast(self):
        ops = pd.read_csv(DATA_DIR / "operations_synthetic.csv")
        finance = pd.read_csv(DATA_DIR / "finance_synthetic.csv", parse_dates=["month"])
        scored = score_operations(ops.head(20), self.ops_model)
        self.assertTrue({"anomaly_score", "flagged", "review_note"}.issubset(scored.columns))
        forecast = forecast_finance(finance, self.finance_model, horizon=3)
        self.assertEqual(len(forecast), finance["department"].nunique() * 3)
        self.assertTrue((forecast["forecast_expense"] >= 0).all())


if __name__ == "__main__":
    unittest.main()
