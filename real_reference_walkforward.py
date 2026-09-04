"""Annual walk-forward robustness for S&P 500 and WTI TSMOM proxies."""
import numpy as np
import pandas as pd

from real_reference_index_oil_replication import ASSET_COST_BPS, load_prices

LOOKBACKS = [5, 10, 20]
TEST_YEARS = [2016, 2017, 2018, 2019]
ANN = 252


def strategy_returns(lookback, sparse):
    prices = load_prices()
    r = np.log(prices).diff()
    vol = r.rolling(20).std() * np.sqrt(ANN)
    candidate = (np.sign(np.log(prices / prices.shift(lookback)))
                 * (0.10 / vol.clip(lower=0.02))).clip(-1, 1)
    if sparse:
        schedule = pd.Series(False, index=prices.index)
        schedule.iloc[::lookback] = True
        weights = candidate.where(schedule).ffill().shift(1).fillna(0.0)
    else:
        weights = candidate.shift(1).fillna(0.0)
    turnover = weights.diff().abs().fillna(weights.abs())
    gross = weights * r
    net = gross.copy()
    for asset in prices.columns:
        net[asset] -= turnover[asset] * ASSET_COST_BPS[asset] * 1e-4
    return net, turnover


def fold_metric(series, turnover, entity, model, lookback, year):
    x = series.loc[series.index.year == year].dropna()
    t = turnover.loc[turnover.index.year == year]
    equity = np.exp(x.cumsum())
    dd = equity / equity.cummax() - 1.0
    return {
        "entity": entity,
        "model": model,
        "lookback_days": lookback,
        "test_year": year,
        "test_observations": len(x),
        "net_return": equity.iloc[-1] - 1.0,
        "sharpe": np.sqrt(ANN) * x.mean() / x.std(),
        "max_drawdown": dd.min(),
        "annualized_turnover": t.mean() * ANN,
    }


def run():
    rows = []
    for lookback in LOOKBACKS:
        for sparse in [False, True]:
            model = "sparse" if sparse else "continuous"
            net, turnover = strategy_returns(lookback, sparse)
            for year in TEST_YEARS:
                for asset in net.columns:
                    rows.append(fold_metric(net[asset], turnover[asset], asset,
                                            model, lookback, year))
                rows.append(fold_metric(net.mean(axis=1), turnover.mean(axis=1),
                                        "portfolio", model, lookback, year))
    return pd.DataFrame(rows)


def summarize(folds):
    p = folds[folds.entity == "portfolio"]
    return (p.groupby(["model", "lookback_days"])
            .agg(positive_year_fraction=("net_return", lambda x: (x > 0).mean()),
                 median_year_return=("net_return", "median"),
                 worst_year_return=("net_return", "min"),
                 median_year_sharpe=("sharpe", "median"),
                 mean_turnover=("annualized_turnover", "mean"))
            .reset_index())


if __name__ == "__main__":
    folds = run()
    summary = summarize(folds)
    folds.to_csv("real_reference_walkforward_folds.csv", index=False)
    summary.to_csv("real_reference_walkforward_summary.csv", index=False)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
