# Research 011 — partial-adjustment TSMOM on a locked 2021–2025 holdout

## Literature and mechanism

Gârleanu & Pedersen (2013) derive an optimal dynamic portfolio principle for
predictable returns with transaction costs: trade partially toward a moving
target. The economic mechanism is a trade-off between decaying expected
return and the immediate cost of reaching the frictionless target.

## Falsifiable hypothesis

Using the already identified 20-day TSMOM target, partial adjustment should
reduce turnover and improve net holdout Sharpe relative to full daily
adjustment. It should also be compared with the previously studied sparse
20-day schedule. Speeds 1.00, 0.50, 0.25 and 0.10 were declared before
examining the new holdout; all are reported and none is silently selected.

## Locked data and assumptions

S&P 500 is downloaded from FRED and WTI spot from the EIA-attributed
`datasets/oil-prices` package. The model uses prior history from September
2016, but evaluation is locked to the five complete calendar years 2021–2025,
which were not present in the earlier S&P 500 repository. WTI non-positive
prices are converted to missing before log returns; the holdout begins after
that event.

Target: sign of 20-day return times 10%/20-day realized volatility, capped at
1x. Execution is lagged one day. Synthetic costs remain 5 bps SP500 and 10
bps WTI per unit turnover.

## Reproduction

```bash
python real_partial_adjustment_holdout.py
pytest -q test_real_partial_adjustment_holdout.py
```

## Locked-holdout findings

| Model | Net total | Ann. return | Sharpe | Max DD | Turnover/year | Positive years |
|---|---:|---:|---:|---:|---:|---:|
| full adjustment (1.00) | +14.32% | +2.74% | 0.357 | -7.90% | 25.34 | 4/5 |
| partial 0.50 | +17.55% | +3.32% | 0.474 | -7.55% | 16.12 | 5/5 |
| partial 0.25 | +19.78% | +3.71% | 0.564 | -8.22% | 10.77 | 4/5 |
| partial 0.10 | +16.50% | +3.13% | 0.524 | -9.42% | 6.48 | 4/5 |
| sparse-20 | +10.33% | +2.00% | 0.248 | -18.91% | 6.61 | 2/5 |

All three pre-declared partial speeds improved holdout Sharpe relative to full
adjustment and sparse-20. Partial-0.25 had the highest total return and Sharpe,
while partial-0.50 was positive in all five calendar years. Because four
speeds were tested, neither is promoted as an optimized parameter; the result
supports the partial-adjustment model class rather than a specific speed.

This remains a spot/index proxy test. The holdout is valid for model sequence
tracking but is not a substitute for continuous-futures and CFD Bid/Ask data.
