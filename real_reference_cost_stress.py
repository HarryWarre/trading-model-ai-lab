"""Transaction-cost stress and break-even analysis for fixed TSMOM proxies."""
import numpy as np
import pandas as pd

from real_reference_index_oil_replication import ASSET_COST_BPS, load_prices

LOOKBACKS = [5, 10, 20]
COST_MULTIPLIERS = [0.5, 1.0, 2.0, 4.0]
ANN = 252
START = "2016-01-01"


def weights_for(lookback, sparse):
    prices = load_prices()
    r = np.log(prices).diff()
    vol = r.rolling(20).std() * np.sqrt(ANN)
    target = (np.sign(np.log(prices / prices.shift(lookback)))
              * (0.10 / vol.clip(lower=0.02))).clip(-1, 1)
    if sparse:
        schedule = pd.Series(False, index=prices.index)
        schedule.iloc[::lookback] = True
        weights = target.where(schedule).ffill().shift(1).fillna(0.0)
    else:
        weights = target.shift(1).fillna(0.0)
    return prices, r, weights


def run():
    rows = []
    for lookback in LOOKBACKS:
        for sparse in [False, True]:
            model = "sparse" if sparse else "continuous"
            prices, r, weights = weights_for(lookback, sparse)
            turnover = weights.diff().abs().fillna(weights.abs())
            gross = (weights * r).mean(axis=1)
            base_cost = sum(turnover[a] * ASSET_COST_BPS[a] * 1e-4
                            for a in prices.columns) / len(prices.columns)
            gross_oos = gross.loc[START:].dropna()
            base_cost_oos = base_cost.reindex(gross_oos.index)
            breakeven_multiplier = gross_oos.sum() / base_cost_oos.sum()
            for multiplier in COST_MULTIPLIERS:
                net = gross_oos - base_cost_oos * multiplier
                equity = np.exp(net.cumsum())
                dd = equity / equity.cummax() - 1.0
                yearly = net.groupby(net.index.year).sum().map(np.exp).sub(1.0)
                rows.append({
                    "model": model,
                    "lookback_days": lookback,
                    "cost_multiplier": multiplier,
                    "sp500_cost_bps": ASSET_COST_BPS["SP500"] * multiplier,
                    "wti_cost_bps": ASSET_COST_BPS["WTI"] * multiplier,
                    "net_total_return": equity.iloc[-1] - 1.0,
                    "net_annualized_return": equity.iloc[-1] ** (ANN / len(net)) - 1.0,
                    "net_sharpe": np.sqrt(ANN) * net.mean() / net.std(),
                    "net_max_drawdown": dd.min(),
                    "positive_year_fraction": (yearly > 0).mean(),
                    "breakeven_cost_multiplier": breakeven_multiplier,
                    "annualized_turnover": turnover.loc[START:].mean().mean() * ANN,
                    "capacity_status": "not_quantifiable_no_volume",
                })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = run()
    out.to_csv("real_reference_cost_stress_results.csv", index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
