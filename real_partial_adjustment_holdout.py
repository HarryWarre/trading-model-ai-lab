"""Post-selection holdout for transaction-cost-aware partial adjustment."""
import numpy as np
import pandas as pd

ANN = 252
LOOKBACK = 20
LAMBDAS = [1.0, 0.5, 0.25, 0.10]
COST_BPS = {"SP500": 5.0, "WTI": 10.0}
HOLDOUT_START = "2021-01-01"
HOLDOUT_END = "2025-12-31"


def load_prices():
    sp = pd.read_csv("fred_sp500.csv", parse_dates=["observation_date"])
    sp["SP500"] = pd.to_numeric(sp["SP500"], errors="coerce")
    sp = sp.set_index("observation_date")["SP500"]
    wti = pd.read_csv("wti_daily_latest.csv", parse_dates=["Date"])
    wti["WTI"] = pd.to_numeric(wti["Price"], errors="coerce")
    wti = wti.set_index("Date")["WTI"]
    prices = pd.concat([sp, wti], axis=1).sort_index().loc["2016-09-06":HOLDOUT_END]
    prices[prices <= 0] = np.nan
    return prices.dropna()


def target_weights(prices):
    returns = np.log(prices).diff()
    vol = returns.rolling(20).std() * np.sqrt(ANN)
    return (np.sign(np.log(prices / prices.shift(LOOKBACK)))
            * (0.10 / vol.clip(lower=0.02))).clip(-1, 1)


def partial_adjust(target, speed):
    position = target.copy() * np.nan
    current = pd.Series(0.0, index=target.columns)
    for i, (_, row) in enumerate(target.iterrows()):
        available = row.notna()
        current.loc[available] += speed * (row.loc[available] - current.loc[available])
        position.iloc[i] = current
    return position.shift(1).fillna(0.0)


def sparse_weights(target):
    schedule = pd.Series(False, index=target.index)
    schedule.iloc[::LOOKBACK] = True
    return target.where(schedule).ffill().shift(1).fillna(0.0)


def evaluate(weights, prices, model):
    returns = np.log(prices).diff()
    turnover = weights.diff().abs().fillna(weights.abs())
    gross = (weights * returns).mean(axis=1)
    costs = sum(turnover[a] * COST_BPS[a] * 1e-4
                for a in prices.columns) / len(prices.columns)
    net = (gross - costs).loc[HOLDOUT_START:HOLDOUT_END].dropna()
    equity = np.exp(net.cumsum())
    dd = equity / equity.cummax() - 1.0
    yearly = net.groupby(net.index.year).sum().map(np.exp).sub(1.0)
    return {
        "model": model,
        "holdout_start": str(net.index[0].date()),
        "holdout_end": str(net.index[-1].date()),
        "observations": len(net),
        "net_total_return": equity.iloc[-1] - 1.0,
        "net_annualized_return": equity.iloc[-1] ** (ANN / len(net)) - 1.0,
        "net_sharpe": np.sqrt(ANN) * net.mean() / net.std(),
        "net_max_drawdown": dd.min(),
        "annualized_turnover": turnover.loc[net.index].mean().mean() * ANN,
        "positive_year_fraction": (yearly > 0).mean(),
        "worst_year_return": yearly.min(),
    }, yearly


def run():
    prices = load_prices()
    target = target_weights(prices)
    rows, yearly_rows = [], []
    configs = [(f"partial_{speed:.2f}", partial_adjust(target, speed))
               for speed in LAMBDAS]
    configs.append(("sparse_20", sparse_weights(target)))
    for model, weights in configs:
        summary, yearly = evaluate(weights, prices, model)
        rows.append(summary)
        yearly_rows.extend({"model": model, "year": int(year), "net_return": value}
                           for year, value in yearly.items())
    return pd.DataFrame(rows), pd.DataFrame(yearly_rows)


if __name__ == "__main__":
    summary, yearly = run()
    summary.to_csv("real_partial_adjustment_holdout_summary.csv", index=False)
    yearly.to_csv("real_partial_adjustment_holdout_years.csv", index=False)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print(yearly.pivot(index="year", columns="model", values="net_return").to_string(
        float_format=lambda x: f"{x:,.4f}"))
