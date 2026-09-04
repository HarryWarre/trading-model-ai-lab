"""Point-in-time regime diagnostics for fixed S&P 500/WTI TSMOM variants."""
import numpy as np
import pandas as pd

from real_reference_index_oil_replication import load_prices
from real_reference_walkforward import LOOKBACKS, strategy_returns

ANN = 252
START = "2016-01-01"


def regimes():
    prices = load_prices()
    sp_ret = np.log(prices.SP500).diff()
    vol = sp_ret.rolling(60).std() * np.sqrt(ANN)
    # Threshold at t uses only volatility observations available through t-1.
    lagged_vol = vol.shift(1)
    historical_median = lagged_vol.expanding(min_periods=252).median().shift(1)
    high_vol = lagged_vol > historical_median
    trailing_sp = np.log(prices.SP500 / prices.SP500.shift(60)).shift(1)
    equity_down = trailing_sp < 0
    state = pd.Series(index=prices.index, dtype="object")
    state[(~high_vol) & (~equity_down)] = "low_vol_up"
    state[(~high_vol) & equity_down] = "low_vol_down"
    state[high_vol & (~equity_down)] = "high_vol_up"
    state[high_vol & equity_down] = "high_vol_down"
    return state.loc[START:]


def run():
    state = regimes()
    rows = []
    for lookback in LOOKBACKS:
        for sparse in [False, True]:
            model = "sparse" if sparse else "continuous"
            net, _ = strategy_returns(lookback, sparse)
            pnl = net.mean(axis=1).reindex(state.index)
            for regime in ["low_vol_up", "low_vol_down", "high_vol_up", "high_vol_down"]:
                x = pnl[state == regime].dropna()
                rows.append({
                    "model": model,
                    "lookback_days": lookback,
                    "regime": regime,
                    "observations": len(x),
                    "mean_daily_return": x.mean(),
                    "annualized_conditional_return": np.exp(x.mean() * ANN) - 1.0,
                    "conditional_sharpe": np.sqrt(ANN) * x.mean() / x.std(),
                    "positive_day_fraction": (x > 0).mean(),
                    "cumulative_log_contribution": x.sum(),
                })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = run()
    out.to_csv("real_reference_regime_analysis_results.csv", index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
