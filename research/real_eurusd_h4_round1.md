# Real OHLC Round 1 — EUR/USD H4 TSMOM benchmark

## Data provenance

- Source: https://github.com/ejtraderLabs/historical-data
- File: `EURUSD/EURUSDh4.csv`
- Provider-reported fields: Date, open, high, low, close, tick_volume
- Observations: 14,400
- Range: 2012-11-26 20:00 UTC to 2022-03-04 20:00 UTC
- SHA-256: `47ba339ec14222912b5b2ea43a86944272d09b54162198ceba4c5dd1a8e12f96`
- Data QA: 0 missing values, 0 duplicate timestamps, 0 OHLC consistency errors

## Model

- H4 close-to-close log returns.
- TSMOM lookback grid: 6, 12 and 30 H4 bars.
- Rolling realized volatility: 60 H4 bars, annualized with 6 bars/day and 252 days/year.
- Target volatility: 10%, position cap: 1x.
- One-bar signal/execution lag.
- OOS: final 30% of chronological observations, 2019-05-27 to 2022-03-04.
- Round-trip execution assumption: 2.2 pips, applied as turnover cost.

## Result

All tested lookbacks were negative OOS after the 2.2-pip cost assumption. This is a real-data result for one broker-style EUR/USD H4 feed, not evidence that TSMOM fails universally.

| Lookback | OOS return | Annualized | Sharpe | Max drawdown |
|---:|---:|---:|---:|---:|
| 6 bars | -25.34% | -9.72% | -1.64 | -28.69% |
| 12 bars | -10.93% | -3.97% | -0.65 | -22.88% |
| 30 bars | -14.25% | -5.24% | -0.87 | -21.18% |

## Interpretation

This is the first market-data performance result in the lab. It rejects the current unfiltered H4 TSMOM specification for this sample and feed under the stated costs. It does not justify parameter optimization. Next research should test data-quality/price-scaling assumptions, alternative asset classes, spot-versus-roll attribution where applicable, and a pre-registered regime-conditioned extension.
