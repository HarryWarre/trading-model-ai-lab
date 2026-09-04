"""Decompose TSMOM signal, volatility scaling, and CFD transaction costs.

This is a diagnostic replication of the Kim, Tse & Wald (2016) critique,
using the same real broker-style FX OHLC and OOS interval as prior rounds.
"""
import numpy as np
import pandas as pd


PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY"]
LOOKBACKS = [6, 12, 30]
ANN = 6 * 252


def load_prices():
    series = {}
    for pair in PAIRS:
        x = pd.read_csv(f"{pair}_h4.csv")
        x["timestamp_utc"] = pd.to_datetime(x["Date"], utc=True)
        x["close"] = x["close"] / 100000.0
        x = x.sort_values("timestamp_utc").drop_duplicates("timestamp_utc")
        series[pair] = x.set_index("timestamp_utc")["close"]
    return pd.concat(series, axis=1).dropna()


def metrics(pnl, turnover, prices, split, name, lookback, cap_fraction):
    oos = pnl.iloc[split:].dropna()
    eq = np.exp(oos.cumsum())
    dd = eq / eq.cummax() - 1.0
    # One pip of round-trip cost per unit of absolute position change.
    pip_drag = (turnover * 0.0001 / prices).mean(axis=1).iloc[split:].sum()
    gross_log = pnl.attrs["gross"].iloc[split:].sum()
    breakeven = gross_log / pip_drag if pip_drag > 0 else np.nan
    return {
        "model": name,
        "lookback_h4": lookback,
        "oos_start": str(oos.index[0].date()),
        "oos_end": str(oos.index[-1].date()),
        "gross_total_return": np.exp(gross_log) - 1.0,
        "net_total_return": eq.iloc[-1] - 1.0,
        "net_annualized_return": eq.iloc[-1] ** (ANN / len(oos)) - 1.0,
        "net_sharpe": np.sqrt(ANN) * oos.mean() / oos.std(),
        "net_max_drawdown": dd.min(),
        "annualized_turnover": turnover.iloc[split:].mean().mean() * ANN,
        "breakeven_cost_pips": breakeven,
        "cap_fraction_oos": cap_fraction,
    }


def run(lookback, cost_pips=2.2):
    prices = load_prices()
    returns = np.log(prices).diff()
    vol = returns.rolling(60).std() * np.sqrt(ANN)
    direction = np.sign(np.log(prices / prices.shift(lookback)))

    unscaled = direction.shift(1).fillna(0.0)
    raw_scale = 0.10 / vol.clip(lower=0.02)
    scaled_capped = (direction * raw_scale.clip(upper=1.0)).shift(1).fillna(0.0)
    # A fixed 3x ceiling is a sensitivity diagnostic, not a deployment setting.
    scaled_3x = (direction * raw_scale.clip(upper=3.0)).shift(1).fillna(0.0)
    split = int(len(returns) * 0.70)
    configs = [
        ("unscaled_unit", unscaled, np.nan),
        ("vol_scaled_cap_1x", scaled_capped,
         float((raw_scale.iloc[split:] >= 1.0).mean().mean())),
        ("vol_scaled_cap_3x", scaled_3x,
         float((raw_scale.iloc[split:] >= 3.0).mean().mean())),
    ]

    rows = []
    for name, weights, cap_fraction in configs:
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = (weights * returns).mean(axis=1)
        costs = (turnover * cost_pips * 0.0001 / prices).mean(axis=1)
        net = gross - costs
        net.attrs["gross"] = gross
        rows.append(metrics(net, turnover, prices, split, name, lookback, cap_fraction))
    return rows


if __name__ == "__main__":
    out = pd.DataFrame(sum((run(lb) for lb in LOOKBACKS), []))
    out.to_csv("real_fx_scaling_decomposition_results.csv", index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
