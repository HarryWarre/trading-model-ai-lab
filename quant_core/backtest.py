"""Lightweight, leakage-safe strategy runner for the Quant Lab.

This module intentionally does not fetch data or train models. A strategy only
receives prices available at a decision timestamp and emits cross-asset target
weights. The runner applies those weights to the next observation, making
the execution lag explicit and testable.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

SignalFunction = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class BacktestResult:
    decisions: pd.DataFrame
    weights: pd.DataFrame

    @property
    def net_log_returns(self) -> pd.Series:
        return self.decisions["net_log_return"]

    def summary(self) -> dict:
        returns = self.net_log_returns.dropna()
        equity = np.exp(returns.cumsum())
        std = returns.std()
        return {
            "observations": int(len(returns)),
            "net_return": float(equity.iloc[-1] - 1) if len(equity) else 0.0,
            "mean_log_return": float(returns.mean()) if len(returns) else 0.0,
            "sharpe_per_decision": (
                float(returns.mean() / std) if std and not np.isnan(std) else None
            ),
            "max_drawdown": (
                float((equity / equity.cummax() - 1).min()) if len(equity) else 0.0
            ),
        }


def wide_prices(panel: pd.DataFrame, min_assets: int = 2) -> pd.DataFrame:
    """Validate a long observed-price panel and return complete price snapshots."""
    required = {"timestamp", "asset", "close"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    data = panel.loc[:, ["timestamp", "asset", "close"]].copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="raise")
    data["asset"] = data["asset"].astype(str).str.strip()
    data["close"] = pd.to_numeric(data["close"], errors="raise")
    if (data["close"] <= 0).any():
        raise ValueError("close prices must be positive")
    if data.duplicated(["timestamp", "asset"]).any():
        raise ValueError("panel contains duplicate asset/timestamp observations")
    wide = data.pivot(index="timestamp", columns="asset", values="close").sort_index()
    if wide.shape[1] < min_assets:
        raise ValueError(f"panel has {wide.shape[1]} assets; minimum is {min_assets}")
    # A decision needs a like-for-like cross section. Do not carry stale prices forward.
    return wide.dropna(how="any")


def normalise_targets(raw: pd.Series, assets: pd.Index) -> pd.Series:
    """Return dollar-neutral, unit-gross weights, or all-zero abstention."""
    target = pd.Series(raw, dtype=float).reindex(assets).fillna(0.0)
    if not np.isfinite(target).all():
        raise ValueError("strategy emitted non-finite weights")
    target = target - target.mean()
    gross = target.abs().sum()
    return target / gross if gross > 0 else target * 0.0


def run_cross_sectional(
    panel: pd.DataFrame,
    signal: SignalFunction,
    *,
    one_way_cost: float = 0.0,
    min_assets: int = 2,
) -> BacktestResult:
    """Run one-bar holding periods with an explicit one-bar execution lag.

    one_way_cost is a fraction of capital per unit of turnover. The research
    wrapper translates a documented CFD cost assumption into this comparable
    unit; this generic core does not call a cross-asset 4-pip number universal.
    """
    if one_way_cost < 0:
        raise ValueError("one_way_cost cannot be negative")
    prices = wide_prices(panel, min_assets=min_assets)
    assets = prices.columns
    previous = pd.Series(0.0, index=assets)
    decision_rows = []
    weight_rows = []

    for i in range(len(prices) - 1):
        timestamp = prices.index[i]
        history = prices.iloc[: i + 1].copy()
        raw = signal(history)
        weights = normalise_targets(raw, assets)
        next_timestamp = prices.index[i + 1]
        next_return = np.log(prices.iloc[i + 1] / prices.iloc[i])
        gross = float((weights * next_return).sum())
        turnover = float((weights - previous).abs().sum())
        cost = turnover * one_way_cost
        decision_rows.append({
            "decision_timestamp": timestamp,
            "return_timestamp": next_timestamp,
            "gross_log_return": gross,
            "turnover": turnover,
            "cost_log_return": cost,
            "net_log_return": gross - cost,
        })
        weight_rows.append(weights.rename(timestamp))
        previous = weights

    if not decision_rows:
        raise ValueError("at least two complete timestamps are required")
    weights_frame = pd.DataFrame(weight_rows)
    weights_frame.index.name = "decision_timestamp"
    return BacktestResult(pd.DataFrame(decision_rows), weights_frame)