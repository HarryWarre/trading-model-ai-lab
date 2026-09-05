# Research 024 — carry crash-risk attribution

## Decision

The preregistered crash-risk signature is rejected at the locked 75th-percentile
VIX definition. The 2025 carry return is negatively skewed and its worst-decile
days are enriched in high-VIX observations, but average return is not lower in
the main high-VIX state. Stationary-bootstrap support for a lower high-VIX mean
is only 49.24%, versus the registered 90% requirement.

This is an attribution study of the already-observed Research 023 return. It
does not create a VIX trading gate and cannot independently confirm alpha.

## Paper and mechanism

Brunnermeier, Nagel and Pedersen, *Carry Trades and Currency Crashes*, argues
that high-minus-low-rate currency positions have negative skew and can unwind
when risk appetite and funding liquidity deteriorate. VIX is an observable
risk-appetite proxy in this test, not a direct funding-liquidity measure.

Primary sources:

- Paper: https://www.nber.org/papers/w14473
- Author-hosted paper: https://markus.scholar.princeton.edu/sites/g/files/toruqf2651/files/carry_trades_currency_crashes.pdf
- VIXCLS: https://fred.stlouisfed.org/series/VIXCLS

## Preregistered hypothesis

Issue #37 required all four conditions:

1. full-sample daily net-return skewness below zero;
2. mean return in high VIX below mean return in low VIX;
3. stationary-bootstrap P(mean_high < mean_low) at least 90%;
4. bottom-decile high-VIX enrichment above one.

Failure of any condition rejects the diagnostic signature.

## Point-in-time design

- The locked Research 023 carry return, costs, rate lag and positions are used
  unchanged.
- Cboe VIX close is obtained through FRED and SHA-256 locked.
- VIX is shifted by one published observation before joining to fixed-EST
  carry sessions.
- At each date, the regime threshold is an expanding historical VIX quantile
  calculated through the preceding observation, with at least 252 observations.
- Main high-VIX threshold: 75th percentile. The 60th and 90th percentiles are
  registered descriptive robustness checks only.
- No regime gates portfolio exposure.

The VIX history runs from 1990-01-02 through 2026-09-03, so all 258 carry
observations receive a lagged, historical-threshold classification.

## Main result

| Statistic | Result | Criterion |
|---|---:|---:|
| Full-sample skewness | -0.609 | pass: < 0 |
| Annualized high-minus-low mean | +0.50 pp | fail: must be < 0 |
| Bootstrap P(high mean < low mean) | 49.24% | fail: must be >= 90% |
| Bottom-decile high-VIX enrichment | 1.93x | pass: > 1 |

At the main 75th-percentile threshold:

| Regime | Observations | Net return | Annualized mean | Sharpe | Skew |
|---|---:|---:|---:|---:|---:|
| Low VIX | 222 | -3.32% | -3.84% | -0.518 | -0.520 |
| High VIX | 36 | -0.48% | -3.34% | -0.312 | -0.769 |

High-VIX returns are more negatively skewed and tail losses are enriched, but
the average high-VIX return is slightly less negative. The 5,000-valid-sample
stationary bootstrap gives a 95% interval of [-58.56%, +61.24%] for the
annualized high-minus-low mean difference. The interval is extremely wide.

The bootstrap draws 10,000 candidate paths with expected block length 10 and
retains the first 5,000 containing both regimes. This avoids undefined regime
means in paths containing no high-VIX observation while preserving the fixed
seed and requested valid sample count.

## Threshold and tail robustness

| VIX threshold | High-VIX obs | High mean | Low mean | Bottom-decile enrichment |
|---:|---:|---:|---:|---:|
| 60th pct | 73 | -9.15% | -1.64% | 2.04x |
| 75th pct — main | 36 | -3.34% | -3.84% | 1.93x |
| 90th pct | 14 | -55.81% | -0.78% | 4.25x |

The 60th and 90th percentile definitions look more consistent with crash-risk
on conditional means, but the preregistered main threshold does not. The 90th
percentile has only 14 observations. Selecting either alternative after the
main failure would be threshold mining.

At the main threshold, high-VIX observations are 13.95% of the sample but
26.92% of bottom-decile loss days and 30.77% of bottom-5% loss days. Thus the
tail-enrichment part of the mechanism appears in descriptive attribution even
though the complete signature fails.

## Assumptions and limitations

- VIX is equity-option implied volatility, not a direct funding-liquidity or
  FX-risk-appetite measure.
- The 2025 carry rule held one concentrated long-USDJPY/short-EURUSD position,
  so this is not a broad cross-section of independent carry trades.
- The same 2025 sample was already inspected in Research 023. Results are
  mechanism diagnostics, not fresh validation.
- Conditional samples, especially the 90th-percentile state, are small.
- The underlying carry P&L still uses theoretical interbank accrual and BID
  bars rather than executable broker swaps and bid/ask quotes.

Capacity remains unquantifiable without order-book depth, executable volume,
broker ADV and market-impact estimates. VIX classification adds no capacity
information.

## Reproduction

    python download_vix_crash_risk.py
    python real_carry_crash_risk.py

`test_real_carry_crash_risk.py` verifies VIX lagging, full alignment, registered
thresholds, exact valid bootstrap count and finite confidence intervals.
