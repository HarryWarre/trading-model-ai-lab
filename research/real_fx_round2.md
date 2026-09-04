# Real OHLC Round 2 — Four-pair FX H4 TSMOM

## Data

Source: https://github.com/ejtraderLabs/historical-data

Pairs: AUDUSD, EURUSD, GBPUSD, USDJPY. Each file contains 14,400 H4 OHLC bars from 2012-11-26 to 2022-03-04 UTC. All files passed zero-missing, zero-duplicate and OHLC consistency checks.

The provider's five-decimal price encoding was normalized by dividing OHLC by 100,000. This is a broker-style reference feed, not a consolidated FX tape.

## Specification

- Per-asset TSMOM lookbacks: 6, 12 and 30 H4 bars.
- Rolling volatility: 60 H4 bars; 10% target; 1x per-asset cap.
- Equal-weight across four currency sleeves.
- One-bar signal/execution lag.
- 2.2 pips round-trip cost assumption.
- Chronological 70/30 split; OOS 2019-05-27 to 2022-03-04.

## Results

| Lookback | OOS return | Annualized | Sharpe | Max drawdown | Annualized turnover |
|---:|---:|---:|---:|---:|---:|
| 6 H4 bars | -20.87% | -7.87% | -1.82 | -23.71% | 518.28 |
| 12 H4 bars | -13.95% | -5.12% | -1.14 | -21.28% | 368.03 |
| 30 H4 bars | -18.15% | -6.77% | -1.51 | -21.90% | 243.88 |

## Interpretation

The unfiltered H4 TSMOM specification is negative across all three pre-registered lookbacks on this four-pair real OHLC sample after costs. Cross-pair diversification did not rescue the signal. The high turnover estimates indicate that the current implementation needs a clearer rebalance/holding rule before any economic comparison with the monthly paper benchmark.

This result is evidence against the current specification for this feed/sample, not against TSMOM universally. No parameter was selected from the OOS ranking.
