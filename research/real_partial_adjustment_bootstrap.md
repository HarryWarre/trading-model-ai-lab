# Research 012 — stationary-bootstrap uncertainty on locked holdout

## Motivation and method

Point estimates from Research 011 do not establish statistical reliability.
Politis & Romano (1994) introduce the stationary bootstrap for inference with
dependent time series. This round resamples common geometric blocks across all
models, preserving paired comparisons and short-run serial dependence.

The fixed 2021–2025 net-return matrix is resampled 2,000 times with expected
block length 20 trading days and seed `20260904`. We report percentile 95%
intervals for annualized arithmetic mean and Sharpe, plus paired intervals for
each partial speed versus full adjustment and sparse-20. The same resampled
indices are used across models.

## Interpretation rule

A point estimate is not treated as statistically established when its 95%
interval crosses zero. Paired probabilities are descriptive bootstrap
frequencies, not multiple-testing-adjusted p-values. No speed is selected from
these results.

## Reproduction

```bash
python real_partial_adjustment_bootstrap.py
pytest -q test_real_partial_adjustment_bootstrap.py
```

## Findings

| Model | Observed Sharpe | 95% Sharpe CI | P(annual mean > 0) |
|---|---:|---:|---:|
| full 1.00 | 0.357 | [-0.385, 1.074] | 82.8% |
| partial 0.50 | 0.474 | [-0.315, 1.228] | 89.2% |
| partial 0.25 | 0.564 | [-0.211, 1.306] | 93.1% |
| partial 0.10 | 0.524 | [-0.253, 1.235] | 91.4% |
| sparse-20 | 0.248 | [-0.595, 1.058] | 72.5% |

Every 95% interval crosses zero. Partial-0.25 has the strongest point estimate
and bootstrap frequency, but its annualized-mean interval is still
[-1.35%, +8.58%]. All paired 95% intervals versus full adjustment and
sparse-20 also cross zero. The holdout evidence is encouraging but does not
meet a conventional 95% statistical-confidence threshold.

The stationary assumption and chosen expected block length remain modeling
assumptions. Results inherit the index/spot proxy and synthetic-cost limits.
