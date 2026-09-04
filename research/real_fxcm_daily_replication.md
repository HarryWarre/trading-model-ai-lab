# Research 005 — independent FXCM daily OHLC replication

## Purpose

Prior rounds used a single public broker-style H4 feed. This round tests the
same paper-driven TSMOM construction on an independent provider sample to
separate model behavior from feed-specific artifacts.

FXCM's public MarketData repository documents daily Bid/Ask candles, UTC
timestamps and indicative pricing. The provider warns that the sample uses
the lowest spreads available to Active Trader accounts, so it is not a
universal executable quote history.

## Pre-registered replication

Use daily BidClose for AUDUSD, EURUSD, GBPUSD and USDJPY, 2017–2020. Compare
continuous daily signal updates with a sparse schedule that rebalances every
L days, for L in {3, 5, 10}. Volatility is a 20-day realized standard
deviation, target volatility 10%, per-sleeve cap 1x, one-day execution lag,
and a fixed 2.2-pip cost per unit turnover. JPY pairs use 0.01 pip size;
non-JPY pairs use 0.0001. The final 30% is OOS.

## Reproduction

```bash
python real_fxcm_daily_replication.py
pytest -q test_real_fxcm_daily_replication.py
```

## OOS findings

| Lookback | Schedule | Gross total | Net total | Net Sharpe | Max DD | Turnover/year |
|---:|---|---:|---:|---:|---:|---:|
| 3 days | continuous | +16.52% | +12.08% | 1.580 | -3.76% | 119.1 |
| 3 days | sparse | +2.90% | +0.15% | 0.020 | -5.08% | 83.8 |
| 5 days | continuous | +3.16% | +0.09% | 0.012 | -5.96% | 93.7 |
| 5 days | sparse | -8.91% | -10.52% | -1.623 | -11.39% | 54.9 |
| 10 days | continuous | -5.50% | -7.65% | -1.137 | -9.69% | 71.6 |
| 10 days | sparse | -10.32% | -11.11% | -1.429 | -18.93% | 27.6 |

The 3-day continuous result is positive after the fixed 2.2-pip assumption,
but it is one configuration on only 370 OOS observations and is not promoted
as a model. The 5- and 10-day configurations do not confirm it. The strong
dispersion relative to the prior H4 feed is evidence that conclusions are
feed- and horizon-dependent; an independent sample with a longer common
history is required before any claim of robustness.

This is an independent OHLC robustness check, not a claim that FXCM sample
prices represent a particular broker's fills. Results should be interpreted
alongside the prior H4 feed, not pooled as if they were independent markets.
