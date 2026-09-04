# Research 014 — risk-adjusted momentum on FX/XAUUSD H4

## Research basis

Dudler, Gmuer and Malamud describe risk-adjusted time-series momentum
(RAMOM) as forming momentum from averages of past futures returns normalized
by volatility. This study tests that economic mechanism against the raw-return
TSMOM control of Moskowitz, Ooi and Pedersen. It is an operational proxy, not
an exact replication: the paper's 64-futures universe and contract histories
are unavailable here.

Primary references:

- Dudler et al., *Risk Adjusted Time Series Momentum*:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2457647
- Moskowitz, Ooi and Pedersen, *Time Series Momentum*:
  https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf

## Mechanism and preregistered hypothesis

Large returns observed in volatile states can dominate a raw cumulative-return
signal even when they contain little persistent information. Normalizing each
past return by risk known before that return should give more comparable weight
to observations across volatility states.

For asset `i`, RAMOM score at bar `t` is:

`RAMOM(i,t,L) = mean[j=0..L-1](r(i,t-j) / sigma(i,t-j-1))`

The trading direction is `sign(RAMOM)`. The matched TSMOM control is
`sign(log(P(t) / P(t-L)))`. Both signals receive the same 10% volatility target,
1x cap, one-bar execution lag, partial-adjustment speed and synthetic CFD cost.

The falsifiable criterion was registered before running results: RAMOM must
have positive median paired Sharpe difference and beat TSMOM in more than half
of the 12 matched lookback/speed configurations.

## Data and validation

- Real public broker-style H4 OHLC: AUDUSD, EURUSD, GBPUSD, USDJPY and XAUUSD.
- Common aligned sample; chronological 70/30 split.
- OOS: 2019-05-28 through 2022-03-04, 4,281 aligned H4 observations.
- Lookbacks: 6, 12 and 30 H4 bars.
- Adjustment speeds: 1.00, 0.50, 0.25 and 0.10; all results reported.
- Volatility window: 60 H4 bars, annualization `6 * 252`.
- FX cost: 2.2 pips per unit turnover; XAUUSD cost: 5 bps.
- Signal at close `t` is shifted one bar before earning return; each RAMOM
  return uses volatility through the preceding bar.

Data SHA-256 checksums are emitted by the QA command and can be used to bind a
rerun to the exact local inputs.

## Results

The preregistered hypothesis is rejected.

- RAMOM beats matched TSMOM on net Sharpe in 3/12 configurations.
- RAMOM beats matched TSMOM on net total return in 3/12 configurations.
- Median paired Sharpe difference: -0.0124.
- Median paired total-return difference: -0.073 percentage points.
- Median paired annualized-turnover difference: -0.16.
- All 12 RAMOM configurations have negative OOS net return.

At lookback 6, RAMOM is worse at every adjustment speed. At lookback 12 it
improves only speed 0.10. At lookback 30 it improves speeds 0.25 and 0.10, but
the resulting net Sharpe values remain negative (-1.232 and -1.163).

## Interpretation

Risk-normalizing formation-period returns does not create a viable H4 FX/gold
signal in this sample. The limited improvement at slow adjustment and longer
lookbacks is insufficient because the underlying net edge remains negative.
The result should be retained as a negative finding; it prevents a paper title
or in-sample best configuration from being mistaken for transferable alpha.

## Limitations and next step

- This is one broker-style feed and one OOS interval, not futures or executable
  bid/ask CFD history.
- Synthetic costs omit financing, time-varying spread and slippage tails.
- Five assets do not reproduce the paper's broad futures diversification.
- The RAMOM specification follows the publicly documented mechanism but is not
  guaranteed to match every implementation detail in the full paper.

Do not tune the RAMOM formula on this OOS sample. The next useful step is an
exact-specification replication on a broad continuous-futures panel, or a new
paper-derived signal with a distinct economic mechanism and a fresh holdout.

## Reproduction

Run:

`python real_multasset_ramom.py`

Outputs:

- `real_multasset_ramom_results.csv`
- `real_multasset_ramom_paired.csv`

QA: `python -m compileall -q real_multasset_ramom.py test_real_multasset_ramom.py`
and the two deterministic test functions in `test_real_multasset_ramom.py`.
