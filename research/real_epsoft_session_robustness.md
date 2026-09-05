# Research 018 — session-definition robustness audit

## Outcome

Research 017's full-adjustment result is materially sensitive to the EPSOFT
calendar-row convention. The aggregate portfolio remains positive under all
three preregistered session definitions, but return and Sharpe fall sharply as
inactive/stub candles are removed, and EURUSD becomes negative. The robustness
criterion fails and the candidate is downgraded.

## Why the audit was necessary

The EPSOFT files have 365/366 rows per year. Friday candles have zero OHLC range,
Saturday candles are short and low-range, and Sunday–Thursday carry the full
active candles. Therefore a 20-row signal is not automatically a 20-trading-day
signal comparable with the time-series momentum literature.

The economic model is unchanged from Moskowitz, Ooi and Pedersen; this round
tests whether its apparent result survives defensible data-session mappings.

- Moskowitz, Ooi and Pedersen, *Time Series Momentum*:
  https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- EPSOFT source repository:
  https://github.com/EPSOFT/Database-Currency-Pair

## Preregistered rules

1. `calendar_all`: retain the archive exactly as supplied.
2. `nonzero_range`: retain a date only when both assets have `High > Low`.
3. `full_session`: retain Sunday through Thursday; remove zero-range Friday and
   short Saturday candles.

Each variant uses its own median 2017–2020 observation count for annualization.
The model is fixed: EURUSD/USDJPY, full adjustment, 20 retained observations for
signal and volatility, 10% target volatility, 1x cap, close-t signal, next-open
execution and 4.4-pip cost.

Robustness required every portfolio and every standalone asset sleeve to have
positive net return and Sharpe under all session definitions.

## Results

| Session rule | Bars/year | OOS observations | Net return | Annualized return | Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| Calendar all | 365 | 788 | +17.75% | +7.86% | 1.233 | -7.56% |
| Nonzero range | 313 | 675 | +8.21% | +3.73% | 0.589 | -10.24% |
| Full session | 261 | 562 | +2.49% | +1.15% | 0.184 | -8.40% |

The original calendar-row return falls by more than half under the objective
nonzero-range filter and by about 86% under the five-full-session definition.

Asset sleeves:

| Session rule | EURUSD net / Sharpe | USDJPY net / Sharpe |
|---|---:|---:|
| Calendar all | +5.45% / 0.316 | +31.49% / 1.547 |
| Nonzero range | -0.91% / -0.055 | +18.16% / 0.939 |
| Full session | -8.97% / -0.567 | +15.39% / 0.809 |

All portfolio variants remain positive, but the all-asset criterion fails.
USDJPY is the only robust positive sleeve.

## QA

- `calendar_all` exactly reconciles the Research 017 full/4.4-pip result to
  numerical tolerance `1e-12`.
- Session filters have strictly decreasing sample sizes: 365, 313 and 261
  annualized observations.
- `nonzero_range` contains no zero-range EURUSD rows.
- `full_session` contains only Sunday–Thursday source labels.
- All outputs are deterministic, unique and finite.

## Interpretation and limitations

The calendar-all backtest benefited from treating inactive and stub candles as
ordinary lookback observations. Those rows change signal horizon, volatility
scaling and trade timing. This is a data-model alignment problem, not evidence
that one weekday itself predicts returns.

The full-session mapping is a conservative interpretation of this export and
may still not match the broker's intended daily-session semantics. A definitive
mapping requires provider documentation or reconstruction from intraday bars.
Bid-only prices, synthetic costs and the two-asset universe remain additional
limitations.

## Decision

Downgrade the full daily model from a positive external-validation candidate to
`provisional / session-definition unresolved`. Do not quote +20.87% or +17.75%
without the calendar-row caveat. The defensible range across the 4.4-pip session
audit is +2.49% to +17.75%, with Sharpe 0.184 to 1.233.

Next acquire provider-documented session boundaries or resample intraday data
into daily candles before further model development. Do not tune the weekday
filter on this holdout.

## Reproduction

`python real_epsoft_session_robustness.py`

Outputs:

- `real_epsoft_session_robustness_results.csv`
- `real_epsoft_session_robustness_attribution.csv`
- `real_epsoft_session_robustness_summary.csv`

QA tests are in `test_real_epsoft_session_robustness.py`.
