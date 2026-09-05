# Research 026 — temporal replication of REER currency value

## Decision

The exact Research 025 model fails its preregistered 2024 temporal replication.
The loss is broad, exists before transaction costs, and persists in the pooled
2024–2025 diagnostic. REER value is not a broad CFD alpha candidate.

## Research basis and frozen mechanism

Chernov, Dahlquist and Lochstoer, *Pricing Currency Risks* (Journal of Finance,
2023; NBER Working Paper 28260), studies real-exchange-rate mean reversion as a
currency expected-return signal:

- https://www.nber.org/papers/w28260
- https://doi.org/10.1111/jofi.13190

The model is unchanged from Research 025. For each of AUD, EUR, GBP, JPY and
USD, value is the negative deviation of log BIS REER from its prior 60-month
mean. The current observation is excluded from the baseline, and month \(m\)
becomes investable only from the first fixed-EST session of month \(m+3\).

The two highest value currencies are long, the two lowest are short, and the
median is zero. Currency weights are mapped to AUDUSD, EURUSD, GBPUSD and
USDJPY and normalized to one unit of gross instrument exposure. Returns are
next-session open-to-open, plus the same lagged theoretical interbank carry and
minus 4.4 pip per unit turnover used in Research 025.

No horizon, lag, rank, cost, universe or bootstrap parameter changed after the
2025 result.

## Data and leakage controls

- 2024 HistData M1 BID files are reused with their existing SHA-256 locks.
- Only the four registered FX files are loaded; an initial unnecessary loader
  dependency on XAUUSD/SPXUSD was removed before final QA.
- Daily sessions are reconstructed at fixed EST 17:00 with at least 1,000
  minute observations.
- BIS/FRED REER and interbank-rate files retain their existing hash checks.
- Primary sample: 259 sessions, 2024-01-01 through 2024-12-29.
- Four target changes occurred.
- 2024 had already been used for other signals, so this is independent of the
  REER-value result but is not a pristine market holdout.

## Primary preregistered result

| Criterion | 2024 result | Pass |
|---|---:|:---:|
| Net return at 1x cost > 0 | -7.42% | **no** |
| At least 3/4 leave-one-out > 0 | 0/4 | **no** |
| Bootstrap P(mean > 0) >= 95% | 4.98% | **no** |
| Net return at 2x cost > 0 | -7.55% | **no** |

All four criteria fail.

| Metric | 2024 result |
|---|---:|
| Spot return | -5.37% |
| Theoretical carry contribution | -2.07% log |
| Net return | -7.42% |
| Sharpe | -1.976 |
| Maximum drawdown | -7.35% |
| Annualized turnover | 2.58 |
| Bootstrap 95% annualized-mean interval | [-15.36%, +1.66%] |

Zero-cost return is -7.30%, versus -7.42% at locked cost and -7.55% at doubled
cost. Transaction cost is not the cause of failure.

## Breadth and regime diagnostics

| Asset component | 2024 net return |
|---|---:|
| EURUSD | -1.82% |
| USDJPY | -5.02% |
| GBPUSD | +0.40% |
| AUDUSD | -1.12% |

All four leave-one-out portfolios lose money, ranging from -3.79% to -11.39%.
The result therefore cannot be attributed to one removable bad asset.

At the previously locked Research 024 q75 VIX threshold, low-VIX return is
-6.85% and high-VIX return is -0.61%. High VIX contains only eight sessions,
so the regime split is not suitable for inference or gating.

## Secondary two-year evidence

The exact model earns +0.98% in 2025 but loses -7.42% in 2024. Concatenating
the 517 daily returns gives:

- total return -6.52%;
- Sharpe -0.882;
- stationary-bootstrap P(mean > 0) 12.00%;
- 95% annualized-mean interval [-8.32%, +2.32%].

This pooled result is descriptive because 2025 motivated the replication. It
does not affect the already failed primary decision.

## Capacity and limitations

Capacity remains unquantifiable because HistData provides no ask, broker swap,
order book, depth or CFD ADV. Theoretical interbank carry is not retail broker
financing. BIS/FRED current-history macro series are revisable and are not
vintage snapshots. REER is a trade-weighted macro index rather than an
executable bilateral fair value.

## Conclusion

The positive 2025 point estimate does not replicate one year earlier. The
evidence now argues against promoting this fixed REER-value specification or
selecting its lone positive GBPUSD component. Further work should move to a
different mechanism or obtain genuinely point-in-time macro data and a new,
untouched execution sample.
