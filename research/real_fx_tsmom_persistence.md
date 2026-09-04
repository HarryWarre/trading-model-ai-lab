# Research 002 — persistence-conditioned TSMOM on real FX OHLC

## Literature mechanism

Moskowitz, Ooi & Pedersen (2012) motivate time-series momentum through
positive return persistence/autocovariance. Kim, Tse & Wald (2016) caution
that reported TSMOM performance can be driven by volatility scaling rather
than directional timing. Daniel & Moskowitz (2016) document that momentum
crashes are partly forecastable in panic/high-volatility states.

## Falsifiable hypothesis

After the same volatility scaling and realistic round-trip cost, a TSMOM
portfolio whose direction is active only when rolling lag-1 return
autocorrelation is positive will have higher OOS Sharpe and shallower drawdown
than the unconditioned baseline. If not, the proposed persistence gate is not
supported on this feed/sample.

## Model

For asset `i`, let `r_i,t = log(C_i,t/C_i,t-1)` and `s_i,t = sign(sum of the
last L H4 returns)`. Let `rho_i,t` be the 60-observation rolling correlation
between `r_i,t` and `r_i,t-1`. The pre-execution position is:

`w_i,t+1 = clip(s_i,t * 1[rho_i,t > 0] * 0.10/sigma_i,t, -1, 1)`

where `sigma` is 60-bar realized volatility annualized using 6*252 H4
observations/year. A one-bar lag prevents using the close that generated the
return. Portfolio PnL is the equal-weight mean of sleeve PnL less turnover
costs. The fixed cost assumption is 2.2 pips round trip.

## Data and validation

The test uses four real OHLC files from the public `ejtraderLabs/historical-data`
repository: AUDUSD, EURUSD, GBPUSD and USDJPY, H4 bars from 2012-11-26 through
2022-03-04 UTC (14,400 bars per file). The files are broker-style/reference
OHLC, not exchange-traded futures, and have no tick-level spread or executable
fill information. The first 70% is used only for chronology; the final 30%
is OOS. Lookbacks 6, 12 and 30 H4 bars are fixed before evaluation.

## Reproduction

```bash
python real_fx_tsmom_persistence.py
pytest -q test_real_fx_tsmom_persistence.py
```

This is a hypothesis test, not evidence of live profitability. Results remain
feed-specific until replicated on an independent OHLC source and on futures
continuous contracts with explicit roll treatment.
