# Research 035 — turnover-cost accounting audit for the 15-asset Ridge+VIX model

**Status:** completed accounting audit; no alpha promotion. This is a reused 2024 development panel, not an untouched holdout.

## Mechanism and correction

The committed Ridge+VIX source charged synthetic spread at the start and end of every five-session block. A retained position could therefore be charged without a trade. The economic definition is instead:

\[
TC_t=\sum_i c_{i,t}|w_{i,t}-w_{i,t-1}|,
\]

plus one terminal liquidation. The signal, 15 assets, horizon, Ridge parameter, expanding training and price-scaled fee schedule were otherwise frozen. This follows the dynamic-trading setting of [Gârleanu and Pedersen](https://www.nber.org/papers/w15205), where costs apply to trading toward holdings, not simply time spent holding.

## Result

| Accounting | Net return | Sharpe | Max DD | Charged cost | Annual turnover |
|---|---:|---:|---:|---:|---:|
| Old block approximation | +4.11% | 0.490 | -5.50% | 2.32% log | 40.21× |
| Corrected turnover cost | +5.42% | 0.642 | -5.31% | 1.07% log | 40.21× |

The correction lowers charged cost 53.9%; 247 of 305 active sessions retained their exact prior portfolio. It is an accounting correction, not a new signal.

## Reconciliation warning

These figures **do not supersede** the earlier Research-034 Ridge+VIX+CFTC output. Reproducing the committed Ridge+VIX source with its written price-scaled fee yields the figures above, while the earlier cached CFTC output used a materially different synthetic cost schedule (15.26% total one-times cost). Code and prior output are therefore not comparable. The prior CFTC output stays provisional until reproduced under one locked cost function.

## Robustness

At 0×/1×/2×/4× cost, corrected net returns are +6.55%/+5.42%/+4.29%/+2.09%. A fixed-seed 5,000-draw i.i.d. bootstrap has only 76.58% probability of positive mean and 95% annualized-mean interval -8.14% to +16.07%; it fails the lab’s 95% evidence threshold.

Low/equal-to-q75 VIX sessions return +7.51%, but 76 high-VIX sessions return -1.91%. The four chronological phases are +3.91%, -1.30%, +2.57%, and +0.20%. No after-the-fact filter is selected.

## Limits

15 HistData 2024 M1 BID-derived daily series are reused; WTI remains unavailable. Panel SHA-256: `9e4067c404c068bed9b3745334883c8db81ba1788e8dad549288c950052e5d9e`; VIX SHA-256: `a8c3cb19429df3cae4982390d35ee5e607a9d54f5c99629ff920ef478cf0cb20`. BID-only data has no executable ask, order book, or volume, so capacity and real CFD costs remain unquantified.

Next: reconcile the CFTC implementation before adding a cost-aware abstention layer, then test on a separate post-2024 holdout.
