# Research 015 — FXCM bid/ask holdout for partial adjustment

## Outcome

The preregistered model-class hypothesis is rejected. Partial adjustment cuts
turnover materially, but only the slowest speed improves Sharpe versus full
adjustment in the 2020 broker-feed holdout. Selecting that one speed after the
result would be post-selection, so no model is promoted.

## Paper mechanism

Gârleanu and Pedersen show that with predictable returns and trading costs, the
optimal dynamic portfolio trades partially toward an aim portfolio instead of
fully chasing a moving frictionless target. This test applies the partial-trade
mechanism to the 20-session TSMOM target of Moskowitz, Ooi and Pedersen.

- Gârleanu and Pedersen, *Dynamic Trading with Predictable Returns and
  Transaction Costs*:
  https://pages.stern.nyu.edu/~lpederse/papers/DynamicTrading.pdf
- Moskowitz, Ooi and Pedersen, *Time Series Momentum*:
  https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- FXCM description of historical FX/CFD candle data:
  https://www.fxcm.com/markets/algorithmic-trading/market-data/

## Preregistered design

- Instruments: AUDUSD, EURUSD, GBPUSD and USDJPY.
- Source: valid FXCM daily Bid/Ask OHLC archives.
- 2017–2019 used for history/warm-up; 2020 is the evaluation period.
- Signal: sign of the trailing 20-session close-to-close return.
- Risk: 20-session volatility, 10% target, 1x cap.
- Adjustment speeds: 1.00, 0.50, 0.25 and 0.10; all reported.
- Signal is observed at close `t`, traded at open `t+1`, and earns the following
  open-to-open return.
- Cost is observed half-spread at `BidOpen`/`AskOpen` multiplied by absolute
  position change. A 2x-spread stress is also reported.
- Crossed quotes are counted and floored at zero cost, never treated as rebates.
- Annualization is 308 sessions, the median yearly row count observed only in
  2017–2019. The unusual archive labels are not silently forced to 252.

Mechanism support required at least two of three partial speeds to beat full
adjustment on 1x-cost net Sharpe and median turnover reduction of at least 25%.
The separate investability gate required at least one partial speed to remain
net-positive at 2x spread.

## Holdout results

| Speed | Net return 1x | Sharpe 1x | Net return 2x | Sharpe 2x | Turnover/year |
|---:|---:|---:|---:|---:|---:|
| 1.00 | +0.99% | 0.188 | -0.24% | -0.045 | 58.76 |
| 0.50 | -0.19% | -0.039 | -1.06% | -0.215 | 42.95 |
| 0.25 | -0.63% | -0.140 | -1.24% | -0.277 | 30.75 |
| 0.10 | +1.28% | 0.327 | +0.92% | 0.234 | 17.79 |

OOS runs from 2020-01-01 to 2020-12-29 with 305 usable forward returns.

- Sharpe wins versus full adjustment: 1/3 partial speeds; criterion fails.
- Median partial-speed turnover reduction: 47.66%; criterion passes.
- Positive partial configurations under 2x spread: 1/3; investability gate
  passes narrowly.
- Combined mechanism hypothesis: rejected.

The speed-0.10 result is descriptive only. It cannot override the failed
model-class criterion and one-year sample.

## Data QA

The downloader workspace also contained files named as FXCM archives for six
indices, USOil and XAUUSD. Their first bytes were HTML (`<!`), not the gzip magic
bytes, so all were excluded. `validate_gzip_csv` now rejects these payloads and
checks required columns before any model code runs.

Across valid FX archives there are 12 crossed open quotes: AUDUSD 3, EURUSD 1,
GBPUSD 3 and USDJPY 5. They are disclosed and cost-clipped to zero. In 2020,
median observed open spreads are 2.9 pips AUDUSD, 2.9 EURUSD, 7.2 GBPUSD and
4.0 USDJPY. The wide open/rollover spreads make this test more conservative
than the earlier fixed 2.2-pip assumption.

## Limitations

- One crisis year cannot establish persistent alpha or support a confidence
  interval with useful power.
- FXCM prices are broker-specific and may be indicative rather than executable
  for another account or venue.
- Financing, slippage beyond quoted spread and market impact are omitted.
- The archives have unusual session-date labels and about 308 rows/year; the
  chronological order is usable, but daily calendar attribution needs a source
  specification before combining with another feed.
- Crossed quotes are evidence of feed imperfections even though the conservative
  cost rule prevents them from improving PnL.

## Decision and next step

Retain partial adjustment as a turnover-control component, not as proof of
alpha. Do not choose speed 0.10 from this test. The next validation should lock
a speed before obtaining a post-2020 broker holdout, include financing, and
obtain valid index/commodity bid/ask archives from a documented endpoint.

## Reproduction

`python real_fxcm_partial_adjustment_holdout.py`

Outputs:

- `real_fxcm_partial_adjustment_holdout_results.csv`
- `real_fxcm_partial_adjustment_holdout_summary.csv`

QA tests are in `test_real_fxcm_partial_adjustment_holdout.py`.
