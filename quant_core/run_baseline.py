"""Command-line runner for routine lightweight strategy experiments."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .strategies import run_cost_stress, trailing_momentum


def parse_costs(value: str) -> list[float]:
    costs = [float(item.strip()) for item in value.split(",") if item.strip()]
    if not costs or any(cost < 0 for cost in costs):
        raise ValueError("costs must contain non-negative numbers")
    return costs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lookback", type=int, default=12)
    parser.add_argument("--costs", default="0,0.0001,0.0002,0.0004")
    parser.add_argument("--min-assets", type=int, default=15)
    args = parser.parse_args()

    panel = pd.read_csv(args.panel)
    costs = parse_costs(args.costs)
    results = run_cost_stress(
        panel,
        lambda history: trailing_momentum(history, lookback=args.lookback),
        costs,
        min_assets=args.min_assets,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
