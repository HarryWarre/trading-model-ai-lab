# Research 020 — independent HistData 2024 confirmation

## Decision

The locked full-adjustment TSMOM portfolio earned a positive net return under
all three adjacent fixed-EST session boundaries in an independent 2024 feed.
Both EURUSD and USDJPY were positive under every boundary. This is useful
directional replication, but the pre-registered confirmation criterion is
rejected: median Sharpe is 0.463 rather than greater than 0.5, and the primary
stationary-bootstrap probability of a positive mean is only 66.24%, below 95%.

The model remains a research candidate. It is not statistically confirmed and
is not ready for production.

## Paper mechanism and hypothesis

Moskowitz, Ooi and Pedersen (2012) argue that time-series momentum reflects
return persistence over comparable trading periods. Research 019 demonstrated
that EPSOFT daily results were sensitive to session construction. A genuine
economic signal should therefore retain its sign when both provider and
calendar period change and when adjacent daily boundaries are used.

Issue #33 registered the model, costs, boundary variants and decision rule
before performance was calculated. No asset, lookback or boundary was chosen
after results.

## Data and provenance

- HistData Generic ASCII M1 BID OHLC for EURUSD and USDJPY, calendar 2024.
- The holdout is entirely after the EPSOFT 2007–2023 archive used previously.
- HistData documents timestamps as Eastern Standard Time without daylight
  saving adjustments.
- HistData documents M1 volume as zero/unusable, so session quality is based on
  observed minute coverage rather than volume.
- ZIP and extracted CSV SHA-256 values are locked in code. The downloader also
  retains HistData's official per-file status report.
- EURUSD contains 372,379 rows with no duplicate timestamps. USDJPY contains
  372,083 rows and 60 duplicated timestamps; each duplicate is byte-equivalent
  at the parsed row level and is deterministically removed. Conflicting
  duplicates would stop the run.

This is real BID OHLC, not simulated market data. It is not executable bid/ask
history. The 4.4-pip transaction cost is synthetic; financing, slippage and
market impact are unavailable.

## Session construction

Minute bars are aggregated into fixed-EST sessions ending at 16:00, 17:00 or
18:00. A session must contain at least 1,000 observed M1 bars. All variants
retain 260 common sessions; median coverage is 1,433–1,436 minutes. The lowest
accepted count is 1,020 minutes.

For minute set \(M_s\):

\[
O_s=O_{\min M_s},\quad H_s=\max_{m\in M_s}H_m,\quad
L_s=\min_{m\in M_s}L_m,\quad C_s=C_{\max M_s}.
\]

Because the source is fixed EST rather than New York civil time, the 16:00 and
18:00 variants directly stress the one-hour seasonal ambiguity around the
primary 17:00 fixed-EST boundary.

## Locked model

\[
s_{i,t}=\operatorname{sign}\left(\log(C_{i,t}/C_{i,t-20})\right),
\qquad
w^*_{i,t}=\operatorname{clip}\left(s_{i,t}\frac{0.10}{\hat\sigma_{i,t}},-1,1\right).
\]

The signal uses 20 completed sessions and a 20-session volatility estimate.
The target is delayed one session and earns the next open-to-open return.

\[
r^{net}_{i,t}=w^*_{i,t-1}\log(O_{i,t+1}/O_{i,t})
-|w^*_{i,t-1}-w^*_{i,t-2}|\frac{4.4\,\text{pip}_i}{O_{i,t}}.
\]

The portfolio is equal weighted. Annualization is 252. The deterministic
20-session warm-up is excluded from performance and inference because no
investable signal exists during that interval.

## Results

Investable sample: 2024-01-30 through 2024-12-29, 238 observations.

| Fixed EST close | Gross return | Net return | Sharpe | Max DD | Turnover/year |
|---:|---:|---:|---:|---:|---:|
| 16:00 | +3.88% | +2.67% | 0.464 | -3.35% | 34.70 |
| 17:00 | +3.31% | +2.02% | 0.359 | -4.00% | 37.16 |
| 18:00 | +3.74% | +2.61% | 0.463 | -3.39% | 32.80 |

Asset standalone net returns:

| Fixed EST close | EURUSD | USDJPY |
|---:|---:|---:|
| 16:00 | +3.20% | +2.15% |
| 17:00 | +1.47% | +2.57% |
| 18:00 | +2.62% | +2.60% |

Unlike the EPSOFT session audit, sign robustness passes and performance is not
concentrated entirely in USDJPY.

## Statistical validation

The primary 17:00 series was evaluated using 5,000 deterministic stationary-
bootstrap samples with expected block length 20 sessions, following
Politis–Romano to preserve short-range serial dependence.

- Probability that the mean net return is positive: 66.24%.
- 95% CI for annualized mean: [-7.23%, +11.05%].

The interval crosses zero widely. The one-year sample cannot distinguish a
stable alpha from favorable noise.

## Pre-registered decision

| Requirement | Result | Pass |
|---|---:|:---:|
| Portfolio positive at all boundaries | yes | yes |
| Median Sharpe > 0.5 | 0.463 | no |
| Each asset positive in >=2 boundaries | both 3/3 | yes |
| Primary probability positive >=95% | 66.24% | no |

Overall hypothesis: **rejected**.

## QA and limitations

- Source CSV hashes are checked before parsing.
- OHLC invariants and duplicate timestamps are checked.
- Only identical USDJPY duplicates are removed.
- Tests cover session aggregation, minimum coverage, deterministic bootstrap,
  non-negative costs, execution lag and the exact decision rule.
- Cost drag is positive under every boundary.
- Minute volume cannot support capacity analysis. No capacity number is made up.
- BID-only bars prevent direct spread measurement.
- One calendar year is too short for reliable regime, crash or multiple-testing
  inference.

## Next step

The independent 2024 result restores some confidence in the sign of the
20-session signal, but not in statistical significance. The next valid test
should acquire a broader post-2024 bid/ask or continuous-futures panel and keep
this specification frozen. The 2024 HistData sample must not be reused to
select a different lookback, asset subset or session boundary.

## References

- Moskowitz, Ooi and Pedersen (2012), *Time Series Momentum*.
- Politis and Romano (1994), *The Stationary Bootstrap*.
- HistData, *Data Files: Detailed Specification* and FAQ.
- Philippe Remy, *FX-1-Minute-Data* (Apache-2.0 downloader/API wrapper).
