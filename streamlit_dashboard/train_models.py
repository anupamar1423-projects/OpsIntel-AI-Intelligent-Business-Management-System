"""Train bundled demonstration models and save a reproducible report."""

from __future__ import annotations

import json

from modeling import train_all


if __name__ == "__main__":
    report = train_all()
    print(json.dumps(report, indent=2))
    print("Models and evaluation report saved under streamlit_dashboard/artifacts/")
