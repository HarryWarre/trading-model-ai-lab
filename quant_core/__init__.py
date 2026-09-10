"""Reusable lightweight research core."""
from .backtest import (
    BacktestResult,
    run_cross_sectional,
    run_cross_sectional_with_context,
    wide_prices,
)
from .strategies import run_cost_stress, trailing_momentum

__all__ = [
    "BacktestResult", "run_cross_sectional", "run_cross_sectional_with_context",
    "wide_prices", "run_cost_stress", "trailing_momentum",
]
