# Research 036 — reproducible CFTC rebuild on 15 CFD proxies

**Status:** completed rebuild; rejected as an alpha candidate. This uses a reused 2024 development panel.

## Mechanism

CFTC speculative positioning may proxy demand or hedging imbalance. The model adds net leveraged-money (FX) or managed-money (gold) positions divided by open interest to the existing 5-session Ridge+VIX forecast. The Tuesday report is available only after three calendar days, and a prior-only expanding z-score needs eight reports. Seven FX pairs and gold are mapped; other seven assets receive zero. USDJPY, USDCHF, and USDCAD are sign-inverted to match their CFD quotes.

## Cost and result

All costs use (TC_t=\sum_i c_{i,t}|w_{i,t}-w_{i,t-1}|), plus one final liquidation.

| Measure | Result |
|---|---:|
| Net return | +4.63% |
| Sharpe | 0.559 |
| Max drawdown | -5.62% |
| Cost | 1.00% log |
| Annual turnover | 38.01× |
| Decisions | 61 |

Returns remain +3.59% at 2× cost and +1.53% at 4× cost. But the 5,000-draw fixed-seed i.i.d. bootstrap has only 73.08% probability of positive mean, CI [-8.10%, +15.23%] annualized, so the 95% standard fails.

CFTC also does not show reliable incremental benefit versus corrected Ridge+VIX: annualized paired difference -0.62 points; paired bootstrap positive only 34.54% (CI [-3.84%, +2.51%]).

High-VIX sessions return -1.83%; one chronological phase is negative. No filter is selected. The source-to-cost pipeline is now reproducible, but this is not an alpha candidate. HistData is BID-only and CFTC open interest is not executable CFD capacity.
