# Research 025 — REER currency value on 2025 CFD proxies

## Decision

The preregistered hypothesis is **rejected**. The locked portfolio earned a small
positive return and survived doubled transaction cost, but failed cross-asset
robustness and statistical-confidence requirements. It remains a diagnostic,
not a candidate model.

## Paper and economic mechanism

Chernov, Dahlquist and Lochstoer, *Pricing Currency Risks* (Journal of Finance,
2023; NBER Working Paper 28260), describes currency expected returns with three
signals including real-exchange-rate mean reversion and evaluates a
cross-sectional value strategy sorted on the real exchange rate:

- https://www.nber.org/papers/w28260
- https://doi.org/10.1111/jofi.13190

The mechanism is slow correction of real currency misvaluation. A currency
that has appreciated unusually far in real terms relative to its own history
is expected to have a lower subsequent return than a currency that has become
unusually cheap. This differs from the interest-differential mechanism tested
in Research 023 and the trend mechanism rejected in Research 021.

BIS constructs REER from trade-weighted nominal exchange rates adjusted for
relative consumer prices. An increase is a real appreciation. BIS also warns
that the index level relative to 100 does not itself identify valuation, so the
test uses each currency's deviation from its own lagged history:

- https://data.bis.org/topics/EER

## Locked model

For currency \(c\) and REER observation month \(m\):

\[
d_{c,m}=\log(REER_{c,m})-
\frac{1}{60}\sum_{j=1}^{60}\log(REER_{c,m-j}),
\qquad v_{c,m}=-d_{c,m}.
\]

AUD, EUR, GBP, JPY and USD are ranked by \(v\). The two most undervalued
currencies receive +0.25, the two most overvalued receive -0.25, and the median
currency receives zero. Currency exposures are mapped to AUDUSD, EURUSD,
GBPUSD and USDJPY, then scaled to gross instrument exposure one.

An observation for month \(m\) is unavailable until the first fixed-EST session
of month \(m+3\). Thus two full calendar months elapse before use. The trailing
mean excludes the current observation. Positions use the next session's
open-to-open return.

Net log return is

\[
r^{net}_{t+1}=\sum_i w_{i,t}\Delta\log P_{i,t+1}
+\sum_i w_{i,t}(r^{base}_{i,t}-r^{quote}_{i,t})\frac{D_t}{365}
-\sum_i |\Delta w_{i,t}|\frac{4.4\,pip_i}{P_{i,t}}.
\]

The rate accrual reuses the locked Research 023 interbank-rate panel and is not
a broker swap quote.

## Data and reproducibility

- 2025 HistData M1 BID bars and fixed-EST 17:00 sessions are reused unchanged
  from Research 023.
- Monthly BIS broad REER is downloaded through FRED: RBAUBIS, RBXMBIS,
  RBGBBIS, RBJPBIS and RBUSBIS.
- Every input file is SHA-256 checked.
- REER history spans January 1994 through July 2026; the 60-month warm-up first
  yields an effective signal in April 1999.
- The holdout has 258 active sessions from 2025-01-01 through 2025-12-29.
- The target changed only three times during 2025.
- Code was compiled; four model/lag/hash tests and independent result
  assertions passed.

Current-history REER is not a vintage database and may contain revisions. The
2025 market sample was already examined in Research 023, so this is a newly
preregistered mechanism test on an exposed return period, not an untouched
holdout.

## Preregistered results

| Criterion | Result | Pass |
|---|---:|:---:|
| Net return at 1x cost > 0 | +0.98% | yes |
| At least 3/4 leave-one-out portfolios > 0 | 2/4 | **no** |
| Bootstrap P(mean > 0) >= 95% | 61.52% | **no** |
| Net return at 2x cost > 0 | +0.89% | yes |

All four conditions were required, so the hypothesis is rejected.

Main portfolio diagnostics:

| Metric | Result |
|---|---:|
| Spot return | +2.32% |
| Theoretical carry contribution | -1.23% log |
| Net return | +0.98% |
| Sharpe | 0.262 |
| Maximum drawdown | -3.60% |
| Annualized turnover | 2.11 |
| Bootstrap 95% annualized-mean interval | [-4.60%, +7.04%] |

## Robustness and attribution

| Asset component | Net return |
|---|---:|
| EURUSD | +2.92% |
| AUDUSD | +1.04% |
| USDJPY | -0.43% |
| GBPUSD | -2.47% |

Leave-one-out return was positive only when USDJPY or GBPUSD was excluded.
Removing EURUSD produced -2.28%, showing material dependence on the best
component. Selecting EURUSD after observing this table is prohibited.

Cost stress was +1.07% at zero transaction cost, +0.98% at locked cost and
+0.89% at doubled cost. Low turnover explains cost robustness; it does not
establish alpha.

Using the previously locked Research 024 VIX classification, low-VIX return
was +1.92% while high-VIX return was -0.92% across only 36 high-VIX sessions.
This is descriptive because VIX conditioning was not an entry rule and the
sample is small. No VIX gate is added.

## Capacity and implementation limits

Capacity cannot be quantified. HistData has no ask, broker swap, order book,
depth or CFD ADV. BIS REER is a macro valuation input, not executable liquidity.
The 4.4-pip cost is a locked synthetic spread and theoretical interbank carry
can differ materially from retail CFD financing.

## Conclusion

REER value has a positive point estimate and low turnover, but the result is
not broad across assets and its bootstrap uncertainty is large. It is not
promoted to a broad CFD alpha candidate. A future confirmation would require
an untouched period, point-in-time/vintage macro inputs, and broker-specific
Bid/Ask plus swap histories.
