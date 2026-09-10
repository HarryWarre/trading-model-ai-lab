"""Small baseline strategies and cost-stress helpers for routine lab runs."""
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .backtest import BacktestResult, SignalFunction, run_cross_sectional


def trailing_momentum(history: pd.DataFrame, lookback: int = 12) -> pd.Series:
    """Price-only baseline: rank recent log return, no future observations."""
    if lookback < 1:
        raise ValueError("lookback must be positive")
    if len(history) <= lookback:
        return pd.Series(0.0, index=history.columns)
    return (history.iloc[-1].apply(float).pipe(lambda x: x) / history.iloc[-lookback - 1].astype(float)).apply(lambda x: pd.NA if x <= 0 else x).astype("Float64").apply(lambda x: 0.0 if pd.isna(x) else __import__("math").log(float(x)))


def run_cost_stress(
    panel: pd.DataFrame,
    signal: SignalFunction,
    costs: Iterable[float],
    *,
    min_assets: int = 2,
) -> pd.DataFrame:
    """Run the same locked strategy at pre-declared cost levels."""
    rows = []
    for cost in costs:
        result: BacktestResult = run_cross_sectional(
            panel, signal, one_way_cost=float(cost), min_assets=min_assets
        )
        summary = result.summary()
        rows.append({"one_way_cost": float(cost), **summary})
    return pd.DataFrame(rows)
