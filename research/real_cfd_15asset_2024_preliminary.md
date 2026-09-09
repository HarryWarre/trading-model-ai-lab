# Research 034 — preliminary 15-asset CFD panel

## Status

This is the first completed model run after expanding the panel. It uses 15 HistData M1 archives for calendar year 2024, resampled to daily closes. WTIUSD remains unavailable; BCOUSD is used as the Brent energy proxy.

## Hypothesis

A cross-sectional signal that combines 20-day return with recent 20-day volatility should rank assets more reliably than raw 20-day return alone.

For asset (i):

[
s^{price}_{i,t} = log(P_{i,t}/P_{i,t-20})
]

[
s^{risk}_{i,t} = s^{price}_{i,t}/sigma_{i,t-20:t}
]

Every five days, the strategy buys the three highest-ranked assets and sells the three lowest-ranked assets with equal weights.

## Data and cost assumptions

- 15 assets: 8 FX, gold, silver, S&P 500, Nasdaq 100, DAX, FTSE 100, Brent.
- 313 complete common calendar days after daily aggregation; the raw panel has 7 missing asset-day cells before forward filling.
- Synthetic all-in cost proxy: 4.4 pip equivalent for FX, 15 bp for gold/index assets, 25 bp for silver/Brent.
- Costs are not broker-specific executable quotes. This is a research stress assumption, not a production cost estimate.
- The run uses BID-style M1 data and does not claim capacity.

## Results

| Model | Net return | Sharpe | Max drawdown | Bootstrap P(mean > 0) |
|---|---:|---:|---:|---:|
| Price-only | -18.98% | -2.383 | -19.81% | 0.2% |
| Risk-adjusted price | -13.37% | -2.022 | -13.69% | 0.9% |

The risk-adjusted score reduced the loss by about 5.61 percentage points and reduced drawdown, but it remained strongly negative. The registered hypothesis is therefore rejected for this panel and period. No asset or regime was selected after seeing results.

## Limitations

This is a preliminary 2024 panel run, not an untouched confirmation holdout. It uses price and volatility only; macro, carry, positioning, funding and volume inputs have not yet been joined to the expanded panel. The next test must add only time-available external inputs, then compare against this fixed baseline using walk-forward validation, 0x/1x/2x/4x cost stress, asset/family leave-one-out and an untouched time block.
