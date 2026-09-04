"""Independent daily OHLC replication using FXCM's published sample candles."""
import gzip
import numpy as np
import pandas as pd

PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY"]
LOOKBACKS = [3, 5, 10]
ANN = 252


def load_prices():
    data = {}
    for pair in PAIRS:
        frames = []
        for year in range(2017, 2021):
            with gzip.open(f"fxcm_{pair}_{year}.csv.gz", "rt") as fh:
                x = pd.read_csv(fh)
            x["timestamp_utc"] = pd.to_datetime(x["DateTime"], dayfirst=False, utc=True)
            frames.append(x[["timestamp_utc", "BidClose"]])
        x = (pd.concat(frames).sort_values("timestamp_utc")
             .drop_duplicates("timestamp_utc").set_index("timestamp_utc"))
        data[pair] = x["BidClose"]
    return pd.concat(data, axis=1).dropna()


def metric(pnl, gross, turnover, prices, split, name, lookback, cost_pips):
    oos = pnl.iloc[split:].dropna()
    equity = np.exp(oos.cumsum())
    dd = equity / equity.cummax() - 1.0
    pip_size = pd.DataFrame(
        {p: (0.01 if p.endswith("JPY") else 0.0001) for p in prices.columns},
        index=prices.index,
    )
    pip_drag = (turnover * pip_size / prices).mean(axis=1).iloc[split:].sum()
    gross_log = gross.iloc[split:].sum()
    return {
        "model": name,
        "lookback_days": lookback,
        "cost_pips_per_unit_turnover": cost_pips,
        "oos_start": str(oos.index[0].date()),
        "oos_end": str(oos.index[-1].date()),
        "gross_total_return": np.exp(gross_log) - 1.0,
        "net_total_return": equity.iloc[-1] - 1.0,
        "net_annualized_return": equity.iloc[-1] ** (ANN / len(oos)) - 1.0,
        "net_sharpe": np.sqrt(ANN) * oos.mean() / oos.std(),
        "net_max_drawdown": dd.min(),
        "annualized_turnover": turnover.iloc[split:].mean().mean() * ANN,
        "breakeven_cost_pips": gross_log / pip_drag if pip_drag > 0 else np.nan,
        "oos_observations": len(oos),
    }


def run(lookback, cost_pips=2.2):
    prices = load_prices()
    returns = np.log(prices).diff()
    vol = returns.rolling(20).std() * np.sqrt(ANN)
    candidate = (np.sign(np.log(prices / prices.shift(lookback)))
                 * (0.10 / vol.clip(lower=0.02))).clip(-1, 1)
    continuous = candidate.shift(1).fillna(0.0)
    schedule = pd.Series(False, index=prices.index)
    schedule.iloc[::lookback] = True
    sparse = candidate.where(schedule).ffill().shift(1).fillna(0.0)
    split = int(len(returns) * 0.70)
    rows = []
    for name, weights in [("continuous", continuous), ("sparse", sparse)]:
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = (weights * returns).mean(axis=1)
        pip_size = pd.DataFrame(
            {p: (0.01 if p.endswith("JPY") else 0.0001) for p in prices.columns},
            index=prices.index,
        )
        costs = (turnover * cost_pips * pip_size / prices).mean(axis=1)
        rows.append(metric(gross - costs, gross, turnover, prices, split,
                           name, lookback, cost_pips))
    return rows


if __name__ == "__main__":
    out = pd.DataFrame(sum((run(lb) for lb in LOOKBACKS), []))
    out.to_csv("real_fxcm_daily_replication_results.csv", index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
