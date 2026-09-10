"""Pre-registered-style multi-input signal adapters for the lightweight core.

This module does not fit coefficients. Coefficients must be supplied by the
research specification, so strategy development cannot silently tune them on
the test period.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from .strategies import trailing_momentum


def linear_price_context_signal(
    history: pd.DataFrame,
    context_history: pd.DataFrame,
    *,
    price_lookback: int,
    feature_weights: Mapping[str, float],
) -> pd.Series:
    """Combine price momentum with asset-specific context columns.

    Context columns use the form ``feature__ASSET`` (for example
    ``vix__EURUSD``). Each feature is standardized using only context rows
    available to the current decision. Missing features contribute zero.
    """
    score = trailing_momentum(history, lookback=price_lookback).astype(float)
    if context_history.empty or not feature_weights:
        return score
    for feature, coefficient in feature_weights.items():
        columns = [f"{feature}__{asset}" for asset in history.columns]
        available = [column for column in columns if column in context_history]
        if not available:
            continue
        latest = context_history[available].iloc[-1].astype(float)
        mean = context_history[available].astype(float).mean()
        std = context_history[available].astype(float).std(ddof=0).replace(0, np.nan)
        z = ((latest - mean) / std).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        for column in available:
            asset = column.split("__", 1)[1]
            score.loc[asset] += float(coefficient) * float(z.loc[column])
    return score
