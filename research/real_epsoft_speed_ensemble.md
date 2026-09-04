# Research 017 — equal-weight adjustment-speed ensemble

## Outcome

The equal-weight speed ensemble is rejected by its preregistered criterion. It
halves turnover and slightly reduces drawdown, but gives up too much exposure to
the profitable trend signal and underperforms full adjustment on both return
and Sharpe.

The locked full-adjustment benchmark itself is positive on this genuinely later
2021–2023 bid-OHLC holdout. That is useful external evidence for daily 20-session
TSMOM, but the two-asset, bid-only sample is not sufficient for production use.

## Research basis and mechanism

Timmermann discusses why simple forecast combinations can reduce instability
and estimation error when model performance is uncertain. Research 015–016
showed that choosing one adjustment speed from the FXCM sample was unstable.
Therefore this test averages the three previously declared partial-adjustment
positions without fitted weights:

`w_ensemble(t) = [w_0.50(t) + w_0.25(t) + w_0.10(t)] / 3`

Each component obeys the partial-trade recursion motivated by Gârleanu and
Pedersen:

`w_s(t) = w_s(t-1) + s * [target(t) - w_s(t-1)]`

Sources:

- Timmermann, *Forecast Combinations*:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=878546
- Gârleanu and Pedersen, *Dynamic Trading with Predictable Returns and
  Transaction Costs*:
  https://pages.stern.nyu.edu/~lpederse/papers/DynamicTrading.pdf
- EPSOFT daily OHLC repository:
  https://github.com/EPSOFT/Database-Currency-Pair

## Preregistered design

- Instruments: EURUSD and USDJPY, the two assets available as plain daily CSV.
- Source Git blobs: EURUSD `7a0cb1bd65e0419c51539c78da840583a266ec7f`;
  USDJPY `bee114de8fb8363b570fbf799933862afe834a7e`.
- History/warm-up: 2007–2020; untouched holdout: 2021-01-01 onward.
- Common OOS: 2021-01-01 to 2023-02-27, 788 forward-return observations.
- Signal: 20-session TSMOM; volatility: 20 sessions; target: 10%; cap: 1x.
- Close-t signal, next-open execution, following open-to-open return.
- Benchmark: full adjustment speed 1.00.
- Costs: 2.2 pips per unit turnover; stress: 4.4 pips.
- Calendar-day archive with 365 observations/year; weekend rows are retained as
  supplied rather than silently reinterpreted as exchange sessions.

Support required the ensemble to beat full adjustment on both net total return
and Sharpe at 2.2 pips and remain net-positive at 4.4 pips.

## Results

| Model | Cost | Net return | Annualized return | Sharpe | Max DD | Turnover/year |
|---|---:|---:|---:|---:|---:|---:|
| Full | 2.2 pips | +20.87% | +9.18% | 1.432 | -6.25% | 62.30 |
| Full | 4.4 pips | +17.75% | +7.86% | 1.233 | -7.56% | 62.30 |
| Ensemble | 2.2 pips | +11.84% | +5.32% | 1.032 | -5.11% | 30.86 |
| Ensemble | 4.4 pips | +10.40% | +4.69% | 0.912 | -5.88% | 30.86 |

At 2.2 pips, the ensemble's return difference versus full is -9.03 percentage
points and its Sharpe difference is -0.401. The ensemble remains positive under
stress but fails both relative-performance requirements. The hypothesis is
rejected.

Both assets contribute positively at 2.2 pips, but USDJPY dominates:

- Full: EURUSD +8.66%, USDJPY +34.45% standalone.
- Ensemble: EURUSD +2.25%, USDJPY +22.33% standalone.

Standalone returns are diagnostic and do not add to portfolio return because
the portfolio is equal weighted.

## Independent feed QA

EPSOFT returns were compared with the separate FXCM 2017–2020 archive before
the holdout. On 1,230 aligned observations:

| Asset | Same-date return correlation | Median absolute difference |
|---|---:|---:|
| EURUSD | 0.9644 | 4.41 bps |
| USDJPY | 0.9327 | 7.17 bps |

This supports broad price-path consistency but does not prove executable-price
equivalence. All EPSOFT rows pass OHLC ordering, positivity, duplicate and null
checks.

## Interpretation and limitations

The ensemble succeeds as turnover control but not as a risk-adjusted-return
improvement. Equal weighting across speeds is not automatically beneficial when
faster reaction captures a strong trend regime.

The full benchmark result is promising external evidence, not a production
claim:

- Only two currency pairs are present, with USDJPY providing most of the gain.
- Data are BID-only; transaction costs are synthetic rather than observed.
- Financing, slippage tails and market impact are absent.
- The public repository does not provide institutional vendor guarantees.
- The archive includes calendar-day rows and only two full holdout years plus a
  partial 2023 period.
- Full speed is the locked benchmark, but the 20-session design was informed by
  earlier research; broader lab-wide selection risk remains.

## Decision

Reject the equal-speed ensemble. Retain the full daily 20-session TSMOM result as
a research candidate requiring replication on more assets, Ask quotes and a
post-March-2023 holdout. Do not modify weights using this holdout.

## Reproduction

First run `python download_epsoft_daily.py`; the downloader verifies the exact
SHA-256 content hashes before saving either source file. Then run:

`python real_epsoft_speed_ensemble.py`

Outputs:

- `real_epsoft_speed_ensemble_results.csv`
- `real_epsoft_speed_ensemble_attribution.csv`
- `real_epsoft_speed_ensemble_summary.csv`
- `real_epsoft_feed_crosscheck.csv`

QA tests are in `test_real_epsoft_speed_ensemble.py`.
