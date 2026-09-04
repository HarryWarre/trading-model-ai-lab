# Research 007 — S&P 500 and WTI reference-asset replication

## Scope

This round extends the CFD lab to two reference assets where free, inspectable
daily data is available: S&P 500 and WTI spot. They are proxies for SPX500
and USOil CFDs, not CFD executable prices or continuous futures contracts.

S&P 500 OHLC/adjusted close is sourced from the public `fja05680/sp500`
repository. WTI daily spot is sourced from the public `datasets/oil-prices`
package, which attributes the series to EIA. The common positive-price sample
is 2012-01-01 through 2019-12-31; the WTI 2020 negative-price event is outside
the sample because log-return TSMOM is undefined for non-positive prices.

## Hypothesis and model

The same paper-driven TSMOM mechanism is tested: prior cumulative returns over
L days determine direction, with 20-day volatility scaling, 10% target, 1x
cap and one-day lag. Continuous updates are compared with rebalancing every L
days, for L in {5, 10, 20}. The final 30% is OOS. This probes whether the
holding-horizon result transfers outside FX/metal.

Costs are declared synthetic assumptions: 5 bps per unit turnover for SP500
and 10 bps for WTI, averaged equally across the two sleeves. No parameter is
selected using OOS results.

## Reproduction

```bash
python real_reference_index_oil_replication.py
pytest -q test_real_reference_index_oil_replication.py
```

## OOS findings

| Lookback | Schedule | Gross | Net | Sharpe | Max DD | Turnover/year |
|---:|---|---:|---:|---:|---:|---:|
| 5 days | continuous | +31.11% | +19.91% | 0.998 | -8.51% | 55.3 |
| 5 days | sparse | +8.38% | +3.70% | 0.202 | -11.44% | 27.4 |
| 10 days | continuous | +17.69% | +10.87% | 0.565 | -8.66% | 36.6 |
| 10 days | sparse | +3.95% | +1.54% | 0.084 | -11.09% | 14.0 |
| 20 days | continuous | +23.14% | +18.65% | 0.933 | -10.71% | 22.6 |
| 20 days | sparse | +10.77% | +9.55% | 0.469 | -9.19% | 6.5 |

All six configurations are net positive in this OOS interval (601
observations). The result supports continuing research on low-turnover trend
exposure outside FX, but it is not a production claim: the sample is short,
the assets are reference spot/index series rather than CFD/futures execution
prices, and the costs are synthetic.

This is a reference-asset robustness test. It must not be presented as an
execution-quality CFD backtest until continuous-futures rolls, contract
specifications and broker Bid/Ask data are added.
