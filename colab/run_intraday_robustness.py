"""Lightweight robustness stage for Research 037 Colab outputs."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


def metrics(x: pd.Series) -> dict:
    x = pd.Series(x).dropna()
    equity = np.exp(x.cumsum())
    sd = x.std()
    return {
        "observations": int(len(x)),
        "total_return": float(equity.iloc[-1] - 1),
        "annualized_mean": float(x.mean() * 252 * 16),
        "sharpe": float(np.sqrt(252 * 16) * x.mean() / sd) if sd > 0 else None,
        "max_drawdown": float((equity / equity.cummax() - 1).min()),
    }


def main() -> None:
    root = Path(os.environ.get(
        "QUANT_DRIVE_ROOT", "/content/drive/MyDrive/trading-model-ai-lab"
    ))
    path = root / "intraday_model_decisions.csv"
    if not path.exists():
        raise SystemExit(f"Model decisions not found: {path}. Run model first.")
    data = pd.read_csv(path, parse_dates=["decision"])
    required = {"gross_log_return", "cost_log_return"}
    if not required.issubset(data.columns):
        raise SystemExit(f"Missing robustness columns: {required - set(data.columns)}")

    rows = []
    for multiplier in [0.0, 1.0, 2.0, 4.0]:
        net = data["gross_log_return"] - multiplier * data["cost_log_return"]
        rows.append({"cost_multiplier": multiplier, **metrics(net)})
    stress = pd.DataFrame(rows)
    stress.to_csv(root / "intraday_cost_stress.csv", index=False)

    rng = np.random.default_rng(37038)
    net = data["gross_log_return"] - data["cost_log_return"]
    draws = rng.choice(net.to_numpy(), size=(1000, len(net)), replace=True).mean(axis=1)
    summary = {
        "cost_stress_file": str(root / "intraday_cost_stress.csv"),
        "bootstrap_samples": 1000,
        "bootstrap_probability_positive": float((draws > 0).mean()),
        "bootstrap_ci_mean_log_return": [
            float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))
        ],
        "main_cost_metrics": metrics(net),
    }
    (root / "intraday_robustness_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
