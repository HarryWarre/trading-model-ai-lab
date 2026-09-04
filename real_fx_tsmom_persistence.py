"""Paper-driven persistence-conditioned TSMOM on real broker-style OHLC.

The gate tests the mechanism in Moskowitz, Ooi & Pedersen (2012): trend
signals should be more credible when recent returns exhibit positive
autocovariance. All features are lagged before execution; the OOS split and
cost convention match real_fx_round2.py.
"""
import numpy as np
import pandas as pd


PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY"]
LOOKBACKS = [6, 12, 30]
PERSISTENCE_WINDOW = 60
ANN_FACTOR = 6 * 252  # H4 bars per year, six observations/day


def load_pair(path):
    x = pd.read_csv(path)
    x["timestamp_utc"] = pd.to_datetime(x["Date"], utc=True)
    cols = ["open", "high", "low", "close"]
    x[cols] = x[cols] / 100000.0
    return (x.sort_values("timestamp_utc")
             .drop_duplicates("timestamp_utc")
             .set_index("timestamp_utc"))


def _metrics(pnl, turnover, split, model, lookback):
    oos = pnl.iloc[split:].dropna()
    equity = np.exp(oos.cumsum())
    dd = equity / equity.cummax() - 1.0
    return {
        "model": model,
        "lookback_h4": lookback,
        "oos_start": str(oos.index[0].date()),
        "oos_end": str(oos.index[-1].date()),
        "total_return": equity.iloc[-1] - 1.0,
        "annualized_return": equity.iloc[-1] ** (ANN_FACTOR / len(oos)) - 1.0,
        "sharpe": np.sqrt(ANN_FACTOR) * oos.mean() / oos.std(),
        "max_drawdown": dd.min(),
        "annualized_turnover": turnover.iloc[split:].mean().mean() * ANN_FACTOR,
        "oos_observations": len(oos),
    }


def run(lookback, cost_pips=2.2, persistence_window=PERSISTENCE_WINDOW):
    prices = pd.concat(
        {p: load_pair(f"{p}_h4.csv")["close"] for p in PAIRS}, axis=1
    ).dropna()
    returns = np.log(prices).diff()
    vol = returns.rolling(60).std() * np.sqrt(ANN_FACTOR)
    direction = np.sign(np.log(prices / prices.shift(lookback)))

    # Rolling correlation uses information through t; execution is at t+1.
    # The lagged-return relation is the paper-motivated persistence estimate.
    lag1_corr = returns.rolling(persistence_window).corr(returns.shift(1))
    gate = (lag1_corr > 0.0).astype(float)

    base = (direction * (0.10 / vol.clip(lower=0.02))).clip(-1, 1).shift(1).fillna(0)
    gated = (direction * gate * (0.10 / vol.clip(lower=0.02))).clip(-1, 1).shift(1).fillna(0)
    split = int(len(returns) * 0.70)
    rows = []
    for name, weights in [("baseline", base), ("persistence_gate", gated)]:
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = (weights * returns).mean(axis=1)
        costs = (turnover * cost_pips * 0.0001 / prices).mean(axis=1)
        rows.append(_metrics(gross - costs, turnover, split, name, lookback))
    return rows


if __name__ == "__main__":
    result = pd.DataFrame(sum((run(lb) for lb in LOOKBACKS), []))
    result.to_csv("real_fx_tsmom_persistence_results.csv", index=False)
    print(result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
