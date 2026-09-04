# Research 008 — annual walk-forward robustness for index/oil proxies

## Motivation

Research 007 used one 70/30 split and produced positive S&P 500/WTI proxy
results. Bailey et al. show that selecting attractive backtests can lead to
overfitting, while the Deflated Sharpe Ratio literature highlights selection
bias and non-normal returns. This round does not select a winner; it reports
all previously declared lookbacks across four forward calendar-year folds.

## Protocol

The fixed TSMOM specifications from Research 007 are evaluated in 2016, 2017,
2018 and 2019. The pre-2016 history supplies trailing returns and volatility;
there is no yearly refit or parameter optimization. Results are reported for
SP500, WTI and the equal-weight portfolio, with the same one-day lag and
synthetic costs (5 bps SP500, 10 bps WTI).

The primary robustness statistics are the fraction of positive test years,
median annual return, worst annual return, median annual Sharpe and mean
turnover. A high aggregate Sharpe from one split is insufficient if annual
folds are unstable or one asset supplies all performance.

## Reproduction

```bash
python real_reference_walkforward.py
pytest -q test_real_reference_walkforward.py
```

## Results

| Model | Lookback | Positive years | Median year | Worst year | Median Sharpe | Turnover/year |
|---|---:|---:|---:|---:|---:|---:|
| continuous | 5 | 2/4 | -0.25% | -10.44% | -0.045 | 62.0 |
| continuous | 10 | 3/4 | +1.74% | -1.13% | 0.218 | 38.2 |
| continuous | 20 | 3/4 | +3.89% | -6.96% | 0.492 | 24.0 |
| sparse | 5 | 2/4 | -0.36% | -6.56% | 0.029 | 27.7 |
| sparse | 10 | 2/4 | +0.33% | -3.15% | 0.025 | 13.5 |
| sparse | 20 | 3/4 | +4.37% | -0.12% | 0.612 | 7.0 |

The attractive single-split result is not uniform. Five-day continuous TSMOM
has a negative median year. The 20-day sparse configuration is the most
stable of the six declared variants, but this is a descriptive comparison,
not a newly selected production parameter. Its portfolio returns were +3.71%,
+5.03%, +7.16% and -0.12% in 2016–2019. Both assets contributed in 2016 and
2018; SP500 drove 2017 while WTI offset SP500 in 2019.

The exercise is a forward-fold diagnostic, not a formal PBO or DSR estimate;
six configurations and four years are too few for a reliable CSCV estimate.
