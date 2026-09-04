"""Lower-turnover TSMOM using paper-consistent holding horizons on real FX OHLC."""
import numpy as np
import pandas as pd

PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY"]
LOOKBACKS = [6, 12, 30]
ANN = 6 * 252


def load_prices():
    out = {}
    for pair in PAIRS:
        x = pd.read_csv(f"{pair}_h4.csv")
        x["timestamp_utc"] = pd.to_datetime(x["Date"], utc=True)
        x["close"] = x["close"] / 100000.0
        x = x.sort_values("timestamp_utc").drop_duplicates("timestamp_utc")
        out[pair] = x.set_index("timestamp_utc")["close"]
    return pd.concat(out, axis=1).dropna()


def evaluate(pnl, turnover, gross, split, name, lookback, cost_pips):
    oos = pnl.iloc[split:].dropna()
    equity = np.exp(oos.cumsum())
    dd = equity / equity.cummax() - 1.0
    pip_drag = (turnover * 0.0001 / prices_global).mean(axis=1).iloc[split:].sum()
    gross_log = gross.iloc[split:].sum()
    return {
        "model": name,
        "lookback_h4": lookback,
        "rebalance_every_h4": lookback if name == "sparse" else 1,
        "cost_pips": cost_pips,
        "oos_start": str(oos.index[0].date()),
        "oos_end": str(oos.index[-1].date()),
        "gross_total_return": np.exp(gross_log) - 1.0,
        "net_total_return": equity.iloc[-1] - 1.0,
        "net_annualized_return": equity.iloc[-1] ** (ANN / len(oos)) - 1.0,
        "net_sharpe": np.sqrt(ANN) * oos.mean() / oos.std(),
        "net_max_drawdown": dd.min(),
        "annualized_turnover": turnover.iloc[split:].mean().mean() * ANN,
        "breakeven_cost_pips": gross_log / pip_drag if pip_drag > 0 else np.nan,
    }


def run(lookback, cost_pips=2.2):
    global prices_global
    prices_global = load_prices()
    returns = np.log(prices_global).diff()
    vol = returns.rolling(60).std() * np.sqrt(ANN)
    direction = np.sign(np.log(prices_global / prices_global.shift(lookback)))
    candidate = (direction * (0.10 / vol.clip(lower=0.02))).clip(-1, 1)
    continuous = candidate.shift(1).fillna(0.0)
    rebalance = pd.Series(False, index=prices_global.index)
    rebalance.iloc[::lookback] = True
    sparse_candidate = candidate.where(rebalance)
    sparse = sparse_candidate.ffill().shift(1).fillna(0.0)
    split = int(len(returns) * 0.70)
    rows = []
    for name, weights in [("continuous", continuous), ("sparse", sparse)]:
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = (weights * returns).mean(axis=1)
        costs = (turnover * cost_pips * 0.0001 / prices_global).mean(axis=1)
        rows.append(evaluate(gross - costs, turnover, gross, split, name, lookback, cost_pips))
    return rows


if __name__ == "__main__":
    result = pd.DataFrame(sum((run(lb) for lb in LOOKBACKS), []))
    result.to_csv("real_fx_tsmom_sparse_rebalance_results.csv", index=False)
    print(result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
