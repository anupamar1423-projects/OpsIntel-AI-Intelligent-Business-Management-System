"""Create repeatable, fictional training data shaped for OpsIntel AI."""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SEED = 20261123


def generate_operations(path: Path, rows: int = 6000) -> None:
    rng = random.Random(SEED)
    start = datetime(2024, 1, 1)
    pipelines = ["Revenue Sync", "Vendor Import", "Inventory Reconciliation", "Ledger Export"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "pipeline_id", "duration_minutes", "rows_processed", "status", "is_anomaly"],
        )
        writer.writeheader()
        for i in range(rows):
            anomaly = int(rng.random() < 0.055)
            duration = max(0.4, rng.gauss(8.0, 2.2))
            volume = max(50, int(rng.gauss(2400, 550)))
            status = "success"
            if anomaly:
                mode = i % 3
                if mode == 0:
                    duration *= rng.uniform(3.0, 6.0)
                elif mode == 1:
                    volume = max(0, int(volume * rng.uniform(0.02, 0.12)))
                else:
                    status = "failed"
                    duration *= rng.uniform(1.2, 2.5)
            elif rng.random() < 0.018:
                status = "failed"
            stamp = start + timedelta(minutes=i * 18)
            writer.writerow(
                {
                    "timestamp": stamp.isoformat(timespec="minutes"),
                    "pipeline_id": pipelines[i % len(pipelines)],
                    "duration_minutes": round(duration, 2),
                    "rows_processed": volume,
                    "status": status,
                    "is_anomaly": anomaly,
                }
            )


def generate_finance(path: Path, months: int = 60) -> None:
    rng = random.Random(SEED + 1)
    departments = {
        "Operations": (185000, 280000),
        "Engineering": (235000, 340000),
        "Sales": (145000, 225000),
        "Finance": (105000, 160000),
        "Procurement": (125000, 190000),
    }
    start = datetime(2021, 1, 1)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["month", "department", "expense_amount", "budget_amount"],
        )
        writer.writeheader()
        for index in range(months):
            year = start.year + (start.month - 1 + index) // 12
            month = (start.month - 1 + index) % 12 + 1
            season = 1 + 0.07 * math.sin((month - 1) * math.tau / 12)
            for department, (base, budget) in departments.items():
                trend = 1 + index * 0.0035
                amount = base * trend * season * rng.uniform(0.91, 1.10)
                writer.writerow(
                    {
                        "month": f"{year:04d}-{month:02d}-01",
                        "department": department,
                        "expense_amount": round(amount, 2),
                        "budget_amount": round(budget * trend, 2),
                    }
                )


def generate_vendors(path: Path, count: int = 36) -> None:
    rng = random.Random(SEED + 2)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["vendor_name", "category", "unit_price", "reliability", "on_time_rate", "quality_score"],
        )
        writer.writeheader()
        categories = ["Equipment", "Software", "Office supplies", "Logistics"]
        for i in range(count):
            writer.writerow(
                {
                    "vendor_name": f"Sample Supplier {i + 1:02d}",
                    "category": categories[i % len(categories)],
                    "unit_price": round(rng.uniform(2500, 70000), 2),
                    "reliability": round(rng.uniform(58, 99), 1),
                    "on_time_rate": round(rng.uniform(55, 99), 1),
                    "quality_score": round(rng.uniform(60, 99), 1),
                }
            )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    generate_operations(DATA_DIR / "operations_synthetic.csv")
    generate_finance(DATA_DIR / "finance_synthetic.csv")
    generate_vendors(DATA_DIR / "vendors_synthetic.csv")
    print(f"Generated fictional training data in {DATA_DIR}")


if __name__ == "__main__":
    main()
