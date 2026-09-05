# Research 019 — H1-reconstructed daily session robustness

## Decision

The pre-registered hypothesis is rejected. The locked 20-session,
full-adjustment TSMOM portfolio is positive only when sessions close at New
York midnight. It is negative under the economically standard New York 17:00
FX close and under UTC midnight. Research 017 therefore remains provisional
and its headline performance must not be treated as session-robust evidence.

## Paper mechanism and falsifiable hypothesis

Moskowitz, Ooi and Pedersen (2012) define time-series momentum from returns
over comparable trading periods. The economic mechanism is gradual information
diffusion and persistence in futures excess returns. If the apparent EPSOFT
FX result represents this mechanism, rather than an archive-calendar artifact,
its sign should not depend on an arbitrary daily cut.

Before running the model, Issue #32 registered the following criterion:

1. Equal-weight portfolio net return must be positive under all three session
   definitions.
2. Median portfolio Sharpe must exceed 0.5.
3. Each asset must be positive under at least two of three definitions.

The model, lookback, cost and holdout were locked; no parameter was selected
after observing results.

## Data and provenance

- Source: EPSOFT `Database-Currency-Pair`, BID H1 OHLCV.
- EURUSD source blob: `bab77995a0d180a102495a53710ed954c726e878`.
- USDJPY source blob: `2c4e813476dff231877f70fd9e32373f959c71bf`.
- Local file SHA-256 values are embedded in `download_epsoft_h1.py` and the
  model module.
- Timestamps contain explicit GMT-0500/GMT-0400 offsets. The loader parses the
  offset before UTC normalization, preserving DST transitions.
- An active hour requires positive reported volume and positive high-low
  range. A reconstructed session requires at least 20 active H1 bars.

This is real historical BID OHLC, not simulated market data. It is not an
executable bid/ask feed. The 4.4-pip round-trip cost is synthetic and deliberately
stressed; financing, slippage and market impact remain unavailable.

## Session construction

For asset \(i\), session \(s\), and active hourly set \(H_s\):

\[
O_s=O_{\min H_s},\quad H_s=\max_{h\in H_s}H_h,\quad
L_s=\min_{h\in H_s}L_h,\quad C_s=C_{\max H_s}.
\]

Three rules are evaluated:

- `new_york_17`: 17:00 New York to 16:59 New York next day.
- `new_york_00`: local New York calendar day.
- `utc_00`: UTC calendar day.

The New York-midnight rule retains fewer observations because the >=20-hour
requirement excludes its short Sunday and Friday fragments. This is a stress
variant, not a recommendation for defining an FX session.

## Locked model

For completed session \(t\):

\[
s_{i,t}=\operatorname{sign}\left(\log(C_{i,t}/C_{i,t-20})\right),
\qquad
w^*_{i,t}=\operatorname{clip}\left(s_{i,t}\frac{0.10}{\hat\sigma_{i,t}},-1,1\right).
\]

The target is shifted one full session. Position \(w_{i,t-1}^*\) earns the
open-to-next-open log return at \(t\). Cost is charged on absolute turnover:

\[
r^{net}_{i,t}=w_{i,t-1}^*\log(O_{i,t+1}/O_{i,t})
-|w_{i,t-1}^*-w_{i,t-2}^*|\frac{4.4\,\text{pip}_i}{O_{i,t}}.
\]

Annualization for each session rule is the median count of valid common
sessions in 2017–2020, entirely before the holdout.

## Holdout results

Holdout begins 2021-01-01 and ends at the common available source date in
February 2023.

| Session close | Obs. | Net return | Sharpe | Max drawdown | Turnover/year |
|---|---:|---:|---:|---:|---:|
| New York 17:00 | 454 | -3.07% | -0.230 | -12.44% | 41.53 |
| New York 00:00 | 350 | +6.70% | 0.445 | -6.10% | 32.49 |
| UTC 00:00 | 450 | -1.44% | -0.109 | -11.56% | 40.57 |

Asset attribution:

| Session close | EURUSD | USDJPY |
|---|---:|---:|
| New York 17:00 | -9.90% | +4.28% |
| New York 00:00 | +0.19% | +13.63% |
| UTC 00:00 | -8.11% | +5.71% |

Only one of three portfolios is positive, median Sharpe is -0.109, and EURUSD
is positive in only one definition. Every registered requirement fails.

## QA and limitations

- Direct tests cover explicit session labels, exact OHLC aggregation,
  incomplete-session rejection, non-negative costs, execution lag, pre-holdout
  annualization and the locked decision rule.
- Reconstructed OHLC invariants and duplicate absolute timestamps are checked.
- Cost drag is positive under every rule.
- The common H1 panel has material missing history. In the holdout, the largest
  gap is 17 calendar days for New York 17:00/UTC and 28 days for New York
  midnight. This weakens calendar-time interpretation and is another reason not
  to promote the result.
- The same two assets and period have now been inspected repeatedly. No further
  parameter search on this holdout is valid confirmatory evidence.

## Conclusion and next step

The positive daily-archive result is not robust to reconstructing trading days
from intraday observations. USDJPY remains positive in all three definitions,
but EURUSD does not, so the portfolio evidence is concentrated rather than
cross-sectional.

The next confirmatory test must freeze the model before acquiring a new,
independent H1 bid/ask panel with materially better session coverage. A broader
continuous-futures panel would better match the original paper's economic
object and permit carry/roll attribution; this EPSOFT holdout must not be reused
for model selection.

## References

- Moskowitz, Ooi and Pedersen (2012), *Time Series Momentum*.
- EPSOFT, *Database-Currency-Pair* source repository.
