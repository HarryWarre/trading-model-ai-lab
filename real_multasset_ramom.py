"""Risk-adjusted momentum versus raw TSMOM on real FX/XAUUSD H4 OHLC.

This is an operational test of the RAMOM mechanism described by Dudler et al.:
average past returns after ex-ante volatility normalization.  It is not an
exact paper replication because the original futures universe is unavailable.
"""
import numpy as np
import pandas as pd

from real_multasset_partial_adjustment import (
    ANN,
    LOOKBACKS,
    SPEEDS,
    cost_series,
    load_prices,
    partial_adjust,
)

SIGNALS = ("tsmom", "ramom")
VOL_WINDOW = 60
TARGET_VOL = 0.10


def signal_scores(prices, returns, vol, lookback):
    """Return raw cumulative-return and lagged-risk-normalized scores."""
    raw = np.log(prices / prices.shift(lookback))
    # Each return is scaled only by volatility available before that return.
    standardized = returns / vol.shift(1).replace(0.0, np.nan)
    ramom = standardized.rolling(lookback).mean()
    return {"tsmom": raw, "ramom": ramom}


def _metrics(net, turnover, split):
    oos = net.iloc[split:].dropna()
    equity = np.exp(oos.cumsum())
    drawdown = equity / equity.cummax() - 1.0
    yearly = oos.groupby(oos.index.year).sum().map(np.exp).sub(1.0)
    return {
        "oos_start": str(oos.index[0].date()),
        "oos_end": str(oos.index[-1].date()),
        "observations": len(oos),
        "net_total_return": equity.iloc[-1] - 1.0,
        "net_annualized_return": equity.iloc[-1] ** (ANN / len(oos)) - 1.0,
        "net_sharpe": np.sqrt(ANN) * oos.mean() / oos.std(),
        "net_max_drawdown": drawdown.min(),
        "annualized_turnover": turnover.iloc[split:].mean().mean() * ANN,
        "positive_calendar_year_fraction": (yearly > 0).mean(),
    }


def run():
    prices = load_prices()
    returns = np.log(prices).diff()
    vol = returns.rolling(VOL_WINDOW).std() * np.sqrt(ANN)
    split = int(len(prices) * 0.70)
    rows = []

    for lookback in LOOKBACKS:
        scores = signal_scores(prices, returns, vol, lookback)
        for signal_name in SIGNALS:
            target = (np.sign(scores[signal_name])
                      * (TARGET_VOL / vol.clip(lower=0.02))).clip(-1, 1)
            for speed in SPEEDS:
                weights = partial_adjust(target, speed)
                turnover = weights.diff().abs().fillna(weights.abs())
                gross = (weights * returns).mean(axis=1)
                net = gross - cost_series(turnover, prices)
                rows.append({
                    "signal": signal_name,
                    "lookback_h4": lookback,
                    "adjustment_speed": speed,
                    **_metrics(net, turnover, split),
                })
    return pd.DataFrame(rows)


def paired_comparison(results):
    """RAMOM minus TSMOM metrics for every pre-declared matched configuration."""
    index = ["lookback_h4", "adjustment_speed"]
    raw = results[results.signal == "tsmom"].set_index(index)
    risk_adjusted = results[results.signal == "ramom"].set_index(index)
    rows = []
    for key in raw.index:
        rows.append({
            "lookback_h4": key[0],
            "adjustment_speed": key[1],
            "delta_net_total_return": (
                risk_adjusted.loc[key, "net_total_return"]
                - raw.loc[key, "net_total_return"]
            ),
            "delta_net_sharpe": (
                risk_adjusted.loc[key, "net_sharpe"]
                - raw.loc[key, "net_sharpe"]
            ),
            "delta_max_drawdown": (
                risk_adjusted.loc[key, "net_max_drawdown"]
                - raw.loc[key, "net_max_drawdown"]
            ),
            "delta_annualized_turnover": (
                risk_adjusted.loc[key, "annualized_turnover"]
                - raw.loc[key, "annualized_turnover"]
            ),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    result = run()
    paired = paired_comparison(result)
    result.to_csv("real_multasset_ramom_results.csv", index=False)
    paired.to_csv("real_multasset_ramom_paired.csv", index=False)
    print(result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nPaired RAMOM - TSMOM")
    print(paired.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
