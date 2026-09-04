"""Reference-asset TSMOM test for S&P 500 and WTI daily prices."""
import numpy as np
import pandas as pd

LOOKBACKS = [5, 10, 20]
ANN = 252
ASSET_COST_BPS = {"SP500": 5.0, "WTI": 10.0}


def load_prices():
    wti = pd.read_csv("wti_daily.csv", parse_dates=["Date"]).set_index("Date")["Price"]
    sp = pd.read_csv("sp500_daily.csv", parse_dates=["Date"]).set_index("Date")["Adj Close"]
    prices = pd.concat({"SP500": sp, "WTI": wti}, axis=1).sort_index()
    # WTI spot briefly printed below zero in 2020; log-return TSMOM is not
    # defined there, so the common positive-price sample ends before that event.
    prices = prices.loc[(prices.index >= "2012-01-01") & (prices.index <= "2019-12-31")]
    return prices.dropna()


def run(lookback):
    prices = load_prices()
    returns = np.log(prices).diff()
    vol = returns.rolling(20).std() * np.sqrt(ANN)
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
        gross = (weights * returns).mean(axis=1)
        cost = sum(turnover[p] * ASSET_COST_BPS[p] * 1e-4
                   for p in prices.columns) / len(prices.columns)
        net = gross - cost
        oos = net.iloc[split:].dropna()
        equity = np.exp(oos.cumsum())
        dd = equity / equity.cummax() - 1.0
        gross_log = gross.iloc[split:].sum()
        cost_log = cost.iloc[split:].sum()
        rows.append({
            "model": name,
            "lookback_days": lookback,
            "rebalance_every_days": lookback if name == "sparse" else 1,
            "oos_start": str(oos.index[0].date()),
            "oos_end": str(oos.index[-1].date()),
            "gross_total_return": np.exp(gross_log) - 1.0,
            "net_total_return": equity.iloc[-1] - 1.0,
            "net_annualized_return": equity.iloc[-1] ** (ANN / len(oos)) - 1.0,
            "net_sharpe": np.sqrt(ANN) * oos.mean() / oos.std(),
            "net_max_drawdown": dd.min(),
            "annualized_turnover": turnover.iloc[split:].mean().mean() * ANN,
            "cost_drag_log": cost_log,
            "oos_observations": len(oos),
        })
    return rows


if __name__ == "__main__":
    out = pd.DataFrame(sum((run(lb) for lb in LOOKBACKS), []))
    out.to_csv("real_reference_index_oil_replication_results.csv", index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
