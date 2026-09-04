"""Research 001: paper-driven cross-asset time-series momentum model.

Signal and portfolio construction only; execution/backtest is separate.
"""
import numpy as np
import pandas as pd


def tsmom_position(prices, lookback=20, vol_window=60, target_vol=0.10,
                   vol_floor=0.05, max_abs_weight=1.0):
    """Return lagged, volatility-scaled positions for an ordered UTC price panel."""
    log_returns = np.log(prices).diff()
    trailing_return = np.log(prices / prices.shift(lookback))
    realized_vol = log_returns.rolling(vol_window).std() * np.sqrt(252)
    direction = np.sign(trailing_return)
    weight = direction * (target_vol / realized_vol.clip(lower=vol_floor))
    return weight.clip(-max_abs_weight, max_abs_weight).shift(1).fillna(0.0)


def covariance_risk_scale(weights, returns, target_portfolio_vol=0.10,
                          cov_window=60, max_gross=3.0):
    """Scale positions using rolling covariance estimates available at each t."""
    out = weights.copy().astype(float)
    for i in range(cov_window, len(weights)):
        cols = weights.columns
        cov = returns.iloc[i-cov_window:i][cols].cov().to_numpy() * 252
        w = weights.iloc[i].to_numpy()
        port_vol = float(np.sqrt(max(w @ cov @ w, 0.0)))
        scale = target_portfolio_vol / port_vol if port_vol > 0 else 0.0
        out.iloc[i] = w * min(scale, max_gross / max(np.abs(w).sum(), 1e-12))
    return out


def purged_splits(index, train_size, test_size, embargo=0):
    """Yield chronological train/test slices with an embargo gap."""
    start = 0
    n = len(index)
    while start + train_size + embargo + test_size <= n:
        yield slice(start, start + train_size), slice(
            start + train_size + embargo, start + train_size + embargo + test_size)
        start += test_size
