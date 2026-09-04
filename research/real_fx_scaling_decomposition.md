# Research 003 — TSMOM volatility-scaling and cost decomposition

## Question

Does the current real-FX result fail because the directional signal has no
gross edge, because volatility scaling is ineffective, or because synthetic
CFD spread costs consume the edge?

Kim, Tse & Wald (2016) report that much of the classic TSMOM result is driven
by volatility scaling rather than directional timing. Moskowitz, Ooi &
Pedersen (2012) scale futures returns to make instruments with different
volatilities comparable. This round directly separates those components.

## Pre-registered models

All variants use `sign` of the trailing cumulative return and execute one H4
bar later:

1. `unscaled_unit`: constant absolute sleeve weight of one.
2. `vol_scaled_cap_1x`: `min(0.10 / sigma_60, 1)`; current CFD baseline.
3. `vol_scaled_cap_3x`: `min(0.10 / sigma_60, 3)`; leverage sensitivity only.

Each is evaluated gross and net of a fixed 2.2-pip round-trip turnover cost.
The test also reports the OOS fraction for which the volatility multiplier is
at its cap and the break-even cost in pips. Lookbacks 6, 12 and 30 H4 bars are
fixed before examining results.

## Data and leakage controls

AUDUSD, EURUSD, GBPUSD and USDJPY broker-style H4 OHLC from 2012-11-26 to
2022-03-04 UTC; final 30% OOS (2019-05-27 to 2022-03-04). Signals and scaling
are shifted one complete bar. No parameter is selected using OOS performance.

## Interpretation rules

- Negative gross return rejects the directional signal for that configuration
  on this feed/sample, independently of spread assumptions.
- Positive gross but negative net return indicates an execution/cost problem.
- A high 1x cap fraction means the supposed volatility-scaled baseline behaves
  mostly like unscaled TSMOM, limiting any conclusion about risk scaling.
- The 3x variant is diagnostic and must not be interpreted as a recommended
  CFD leverage setting.

## OOS findings

| Lookback | Variant | Gross total | Net total | Net Sharpe | Break-even cost |
|---:|---|---:|---:|---:|---:|
| 6 | unscaled | 11.34% | -20.01% | -1.534 | 0.71 pips |
| 6 | scaled, 1x cap | 9.09% | -20.87% | -1.816 | 0.60 pips |
| 12 | unscaled | 13.58% | -10.12% | -0.714 | 1.20 pips |
| 12 | scaled, 1x cap | 8.18% | -13.95% | -1.135 | 0.76 pips |
| 30 | unscaled | -3.92% | -17.78% | -1.293 | negative |
| 30 | scaled, 1x cap | -4.74% | -18.15% | -1.508 | negative |

The 6- and 12-bar signals have positive gross returns but cannot support the
2.2-pip assumption. The 30-bar signal is negative even before costs. The 1x
volatility-scaled configuration hits its cap on 87.85% of OOS asset-bars, so
it is mostly an unscaled sign strategy. Raising the diagnostic cap to 3x
increases gross return for 6 and 12 bars but also raises turnover and produces
more negative net returns. The evidence therefore points to insufficient
edge per trade, not insufficient leverage.

## Reproduction

```bash
python real_fx_scaling_decomposition.py
pytest -q test_real_fx_scaling_decomposition.py
```

This study remains limited by a single public broker-style feed, synthetic
spread costs, four FX pairs and no futures roll/carry decomposition.
