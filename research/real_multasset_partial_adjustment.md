# Research 013 — cross-asset H4 partial-adjustment replication

## Mechanism and hypothesis

Research 011 found that the Gârleanu–Pedersen partial-adjustment principle
improved a locked S&P 500/WTI holdout. This round asks whether that improvement
transfers to the existing higher-frequency FX/gold sample. If the model class
is robust, slower adjustment should reduce turnover and improve net results
relative to full adjustment across more than one lookback.

## Pre-declared design

Portfolio: AUDUSD, EURUSD, GBPUSD, USDJPY and XAUUSD H4. Lookbacks 6, 12 and
30 bars; adjustment speeds 1.00, 0.50, 0.25 and 0.10; 60-bar volatility,
10% target, 1x sleeve cap and one-bar lag. Final 30% is OOS.

Synthetic cost assumptions are unchanged from prior rounds: 2.2 pips per unit
turnover for FX with correct JPY pip size, and 5 bps for XAUUSD. Every one of
the 12 configurations is reported; no OOS speed or lookback is selected.

The source CSV uses instrument-specific integer encodings: 100,000 for
non-JPY FX, 1,000 for USDJPY and 100 for XAUUSD. The loader normalizes these
before any price-dependent cost calculation. Earlier return calculations were
scale-invariant; their legacy USDJPY cost convention also offset the scale by
using a 0.0001 numerator, but new multi-asset code uses explicit economic pip
sizes and normalized prices.

## Reproduction

```bash
python real_multasset_partial_adjustment.py
pytest -q test_real_multasset_partial_adjustment.py
```

## OOS findings

| Lookback | Speed 1.00 net / turnover | Best partial net / turnover | Best speed |
|---:|---:|---:|---:|
| 6 H4 | -23.77% / 499.2 | -4.82% / 117.9 | 0.10 |
| 12 H4 | -12.30% / 349.8 | -5.50% / 172.0 | 0.25 |
| 30 H4 | -17.27% / 236.9 | -11.38% / 71.9 | 0.10 |

Partial adjustment reduced turnover and net loss relative to full adjustment
for every lookback, but all 12 OOS configurations had negative return and
negative Sharpe. The transaction-cost-control mechanism transfers; profitable
alpha does not transfer to this five-asset H4 sample. The displayed best speed
within each row is descriptive and is not selected for deployment.

This is a cross-asset robustness test on the already observed 2012–2022 feed,
not a second locked holdout. Broker Bid/Ask and executable fills remain absent.
