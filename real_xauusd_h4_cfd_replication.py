"""Paper-driven TSMOM replication on public XAUUSD H4 OHLC."""
import numpy as np
import pandas as pd

LOOKBACKS = [6, 12, 30]
ANN = 6 * 252
SYNTHETIC_COST_BPS = 5.0  # round-trip cost per unit turnover, no bid/ask history


def load_prices():
    x = pd.read_csv("XAUUSD_h4.csv")
    x["timestamp_utc"] = pd.to_datetime(x["Date"], utc=True)
    x["close"] = x["close"] / 100000.0
    x = x.sort_values("timestamp_utc").drop_duplicates("timestamp_utc")
    return x.set_index("timestamp_utc")["close"]


def metric(net, gross, turnover, split, model, lookback, cost_bps):
    oos = net.iloc[split:].dropna()
    equity = np.exp(oos.cumsum())
    dd = equity / equity.cummax() - 1.0
    gross_log = gross.iloc[split:].sum()
    bps_drag = turnover.iloc[split:].sum() * 1e-4
    return {
        "model": model,
        "lookback_h4": lookback,
        "cost_bps_per_unit_turnover": cost_bps,
        "oos_start": str(oos.index[0].date()),
        "oos_end": str(oos.index[-1].date()),
        "gross_total_return": np.exp(gross_log) - 1.0,
        "net_total_return": equity.iloc[-1] - 1.0,
        "net_annualized_return": equity.iloc[-1] ** (ANN / len(oos)) - 1.0,
        "net_sharpe": np.sqrt(ANN) * oos.mean() / oos.std(),
        "net_max_drawdown": dd.min(),
        "annualized_turnover": turnover.iloc[split:].mean() * ANN,
        "breakeven_cost_bps": gross_log / bps_drag if bps_drag > 0 else np.nan,
        "oos_observations": len(oos),
    }


def run(lookback, cost_bps=SYNTHETIC_COST_BPS):
    prices = load_prices()
    returns = np.log(prices).diff()
    vol = returns.rolling(60).std() * np.sqrt(ANN)
    candidate = (np.sign(np.log(prices / prices.shift(lookback)))
                 * (0.10 / vol.clip(lower=0.02))).clip(-1, 1)
    continuous = candidate.shift(1).fillna(0.0)
    schedule = pd.Series(False, index=prices.index)
    schedule.iloc[::lookback] = True
    sparse = candidate.where(schedule).ffill().shift(1).fillna(0.0)
    split = int(len(prices) * 0.70)
    rows = []
    for name, weights in [("continuous", continuous), ("sparse", sparse)]:
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = weights * returns
        net = gross - turnover * cost_bps * 1e-4
        rows.append(metric(net, gross, turnover, split, name, lookback, cost_bps))
    return rows


if __name__ == "__main__":
    out = pd.DataFrame(sum((run(lb) for lb in LOOKBACKS), []))
    out.to_csv("real_xauusd_h4_cfd_replication_results.csv", index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
