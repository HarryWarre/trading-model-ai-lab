# Research 009 — point-in-time regime diagnostics

## Literature mechanism

Daniel & Moskowitz (2016) document that momentum crashes cluster after market
declines and during high-volatility panic states. Hurst, Ooi & Pedersen (2017)
report trend-following performance across a wide range of macro and crisis
environments. These findings imply a falsifiable diagnostic: a robust trend
model should not derive all returns from a single benign regime, and its
behavior in high-volatility/down-market states must be explicit.

## Protocol

All six fixed S&P 500/WTI configurations from Research 008 are retained. No
regime gate is added. From 2016 onward, each day is classified using only
information available by the prior close:

- `high_vol`: lagged 60-day S&P 500 volatility exceeds its point-in-time
  expanding historical median;
- `equity_down`: lagged 60-day S&P 500 return is negative.

The cross of these variables creates low/high-volatility and up/down-market
states. We report conditional annualized return, Sharpe, hit rate and
cumulative log-return contribution. Regime thresholds are never computed
from the full sample.

## Reproduction

```bash
python real_reference_regime_analysis.py
pytest -q test_real_reference_regime_analysis.py
```

## Findings

All six fixed configurations were positive in `high_vol_down`, with
conditional Sharpe from 1.22 to 1.55. Five of six were negative in
`high_vol_up`; only sparse-20 remained positive there (conditional Sharpe
0.66). This asymmetry is consistent with trend exposure helping during an
ongoing stressed decline but losing around a high-volatility rebound.

Sparse-20 conditional annualized returns were +1.83% (`low_vol_up`), -18.19%
(`low_vol_down`), +5.40% (`high_vol_up`) and +12.68% (`high_vol_down`). The
`low_vol_down` state has only 37 observations, so its estimate is too sparse
to justify a gate. The result supports collecting a longer regime history;
it does not justify conditionally switching the strategy on or off.

This is descriptive regime attribution, not authorization to optimize a
regime filter. The proxy-data, short-history and synthetic-cost limitations
from Research 007–008 remain unchanged.
