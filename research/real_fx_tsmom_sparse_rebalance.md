# Research 004 — sparse-rebalance TSMOM on real FX OHLC

## Mechanism and hypothesis

Moskowitz, Ooi & Pedersen (2012) define TSMOM as a signal formed over a
lookback horizon and held for the next period; their original AQR data is
monthly with a one-month holding period. Hurst, Ooi & Pedersen (2017) study
trend following across long horizons and market regimes. The prior CFD
replication re-evaluated the signal every H4 bar, creating very high turnover.

Hypothesis: if the gross signal is real rather than an artifact of frequent
rebalancing, carrying a volatility-scaled position between scheduled
rebalances should retain most gross return while reducing turnover enough to
survive the 2.2-pip synthetic round-trip cost.

## Model

The continuous control updates `w_t = clip(sign(sum_{j=0}^{L-1} r_{t-j}) *
0.10/sigma_60, -1, 1)` each H4 bar. The sparse version computes the same
position only every `L` H4 bars and carries it until the next scheduled
rebalance. Both execute one complete bar after signal formation. There is no
OOS parameter selection.

## Data and validation

AUDUSD, EURUSD, GBPUSD and USDJPY broker-style H4 OHLC, 2012-11-26 through
2022-03-04 UTC; final 30% OOS (2019-05-27 through 2022-03-04); lookbacks 6,
12 and 30 H4 bars; 2.2-pip round-trip costs.

## Reproduction

```bash
python real_fx_tsmom_sparse_rebalance.py
pytest -q test_real_fx_tsmom_sparse_rebalance.py
```

## OOS findings

| Lookback | Schedule | Gross total | Net total | Net Sharpe | Max DD | Turnover/year |
|---:|---|---:|---:|---:|---:|---:|
| 6 | continuous | +9.09% | -20.87% | -1.816 | -23.71% | 518.4 |
| 6 | sparse | +7.49% | -7.39% | -0.581 | -16.87% | 241.9 |
| 12 | continuous | +8.18% | -13.95% | -1.135 | -21.28% | 368.1 |
| 12 | sparse | -2.20% | -9.50% | -0.741 | -18.89% | 124.7 |
| 30 | continuous | -4.74% | -18.15% | -1.508 | -21.90% | 243.9 |
| 30 | sparse | +2.18% | -1.04% | -0.080 | -7.99% | 51.8 |

Sparse rebalancing reduced turnover by roughly 53% to 79%. The 30-bar
lookback had the largest improvement and nearly reached break-even after
costs, but its Sharpe remained negative. The result supports continuing the
holding-horizon investigation; it does not establish profitability.

The sparse schedule is an execution/holding-horizon hypothesis, not an
indicator stack. Findings remain feed-specific and require independent OHLC
replication plus executable spread validation.
