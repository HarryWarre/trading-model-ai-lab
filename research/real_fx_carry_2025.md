# Research 023 — two-month-lagged FX carry holdout

## Decision

The preregistered hypothesis is rejected. The four-pair carry ranking lost
3.78% net in the 2025 HistData holdout, with Sharpe -0.475 and maximum drawdown
-10.22%. All four leave-one-pair-out portfolios were negative and the
stationary-bootstrap probability of a positive mean was 29.88%.

Carry is not promoted to a CFD alpha candidate from this test. The result does
not invalidate the broader academic carry premium: this is a small, USD-centric
panel, uses lagged interbank-rate proxies rather than forward discounts, and
does not observe broker swap rates.

## Literature and economic mechanism

Lustig, Roussanov and Verdelhan (2011), *Common Risk Factors in Currency
Markets*, identifies a common slope factor separating high- and low-interest
rate currencies. Burnside, Eichenbaum, Kleshchelski and Rebelo (2011), *Do
Peso Problems Explain the Returns to the Carry Trade?*, defines carry as
borrowing low-rate currencies and lending high-rate currencies and emphasizes
rare/global risk rather than a riskless UIP violation.

Sources:

- https://www.nber.org/papers/w14082
- https://www.nber.org/papers/w14054
- https://fred.stlouisfed.org/series/IR3TIB01USM156N
- https://www.histdata.com/f-a-q/data-files-detailed-specification/

## Locked hypothesis and model

Issue #36 recorded the model and thresholds before return calculation. The
pre-result clarification notes that November 2024 rates become eligible in
January 2025, so the holdout legitimately starts in January rather than March.

For EURUSD, GBPUSD and AUDUSD:

    carry[i,m] = (r_foreign[m] - r_USD[m]) / 100

For USDJPY, whose spot quote direction is reversed:

    carry[USDJPY,m] = (r_USD[m] - r_JPY[m]) / 100

Monthly OECD three-month interbank rates distributed by FRED are lagged by two
full calendar months. Each day, the model buys the highest-carry pair and sells
the lowest-carry pair at weights +0.5 and -0.5. Gross exposure is one and net
exposure is zero.

For the calendar-day interval from session t to t+1:

    pnl[t+1] = sum_i w[i,t] * (
        log(P[i,t+1] / P[i,t]) + carry[i,t] * calendar_days / 365
    ) - transaction_cost[t]

Calendar days, rather than merely row count, ensure weekend interest accrual is
represented. The locked cost is 4.4 pips per unit turnover.

Confirmation required positive net return, at least three of four positive
leave-one-out portfolios, and bootstrap probability of positive mean at least
95%. All three had to pass.

## Data and leakage controls

- Untouched price holdout: HistData 2025 M1 BID for EURUSD, USDJPY, GBPUSD and
  AUDUSD, each ZIP and extracted CSV locked by SHA-256.
- Fixed EST 17:00 sessions, consistent with HistData's fixed-EST timestamp
  specification. The four feeds yield 259 common sessions; 258 have forward
  returns. Minimum accepted daily coverage is 1,000 minutes; observed minima
  are 1,371–1,378 and medians are 1,433–1,437.
- Rates: OECD/FRED IR3TIB01USM156N, IR3TIB01EZM156N,
  IR3TIB01JPM156N, IR3TIB01GBM156N and IR3TIB01AUM156N. Downloaded CSVs are
  hash-locked.
- Rate month m is unavailable until the first session in month m+2. No rate is
  backfilled before that date.
- No changes were made to ranking, quote direction, lag, costs or thresholds
  after seeing returns.

FRED's current-history CSVs are not vintage snapshots. The two-month lag blocks
direct use of unfinished/future months but cannot rule out later historical
revisions. This prevents treating the test as perfectly point-in-time.

## Results

| Spot return | Carry log contribution | Cost drag | Net return | Sharpe | Max DD |
|---:|---:|---:|---:|---:|---:|
| -6.36% | +2.75% | -0.04% | -3.78% | -0.475 | -10.22% |

Interest ordering did not change enough to alter the extremes during the
holdout: the portfolio remained long USDJPY and short EURUSD. GBPUSD and AUDUSD
were never selected. This is a preregistered outcome, not a post-result asset
filter, but it reveals effective concentration in two pairs.

Asset attribution:

| Asset | Net contribution | Sharpe |
|---|---:|---:|
| EURUSD | -5.23% | -1.300 |
| USDJPY | +1.53% | +0.309 |
| GBPUSD | 0.00% | n/a |
| AUDUSD | 0.00% | n/a |

All leave-one-out portfolios lost money: from -1.72% to -4.55%. Excluding an
inactive pair naturally reproduces the main portfolio and is not independent
evidence.

## Robustness, regimes and inference

| Cost multiplier vs locked | Net return | Sharpe |
|---:|---:|---:|
| 0x | -3.75% | -0.471 |
| 0.5x | -3.77% | -0.473 |
| 1x | -3.78% | -0.475 |
| 2x | -3.82% | -0.480 |

The strategy fails even without trading costs. Low turnover (0.97x/year,
including initial establishment) makes spread assumptions immaterial here.

The lagged 20-session USDJPY-volatility regime classifier uses an expanding
60-session median and never gates positions. The classified later sample is
positive in both low-vol (+4.09%, Sharpe 1.267) and high-vol (+0.95%, Sharpe
0.491) states, while the explicitly reported 81-session warm-up loses 8.44%
(Sharpe -3.015). This is descriptive instability, not evidence for a regime
filter; constructing one now would be post-selection.

The 5,000-sample stationary bootstrap uses expected block length 10 sessions.
P(mean > 0) is 29.88%, with annualized mean 95% interval [-16.94%, +9.19%].

## Costs, assumptions and capacity

Theoretical interbank carry is not an observed CFD swap. Real brokers apply
pair-, direction-, day- and account-specific financing markups, including
triple-swap conventions. BID-only bars omit executable ask quotes. Taxes,
slippage beyond the pip charge and nonlinear impact are excluded.

Capacity cannot be estimated from these files: there is no executable order
book, broker volume, ask history or reliable market-impact input. No capacity
number is fabricated.

## Reproduction

    python download_fx_carry_2025.py
    python real_fx_carry_2025.py

`test_real_fx_carry_2025.py` verifies the two-month lag, quote directions,
market neutrality/gross exposure, 2025 holdout, robustness tables, regime
coverage and bootstrap bounds.
