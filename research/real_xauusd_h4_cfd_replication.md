# Research 006 — XAUUSD CFD-style H4 replication

## Scope and limitation

This round extends the paper-driven TSMOM test from FX to gold. XAUUSD H4
OHLC is sourced from the public `ejtraderLabs/historical-data` repository,
covering 2012-10-26 through 2022-03-04. It is provider-style OHLC with no
bid/ask history, so the cost is a declared synthetic 5 basis points per unit
turnover, not an observed executable spread.

The attempted FXCM daily candle endpoints for XAUUSD and index/oil CFDs
returned HTTP 404. FXCM's public repository documents those products for
sentiment/volume samples, but not this historical candle endpoint. Therefore
this result is not presented as an independent-provider confirmation.

## Hypothesis and model

The same TSMOM mechanism is tested: past returns may persist because of
under-reaction and delayed over-reaction, as discussed by Moskowitz, Ooi &
Pedersen (2012). Volatility is a 60-H4 realized standard deviation, target
volatility 10%, sleeve cap 1x, and one-bar execution lag. Continuous updates
are compared with a sparse schedule that rebalances every L bars, L in {6,
12, 30}. The last 30% is OOS and no parameter is selected from OOS results.

## Reproduction

```bash
python real_xauusd_h4_cfd_replication.py
pytest -q test_real_xauusd_h4_cfd_replication.py
```

## OOS findings

| Lookback | Schedule | Gross total | Net total | Net Sharpe | Max DD | Turnover/year |
|---:|---|---:|---:|---:|---:|---:|
| 6 H4 | continuous | +12.63% | -39.34% | -1.637 | -41.09% | 433.2 |
| 6 H4 | sparse | +11.21% | -15.13% | -0.536 | -30.27% | 189.2 |
| 12 H4 | continuous | +34.55% | -11.12% | -0.389 | -21.26% | 290.3 |
| 12 H4 | sparse | -10.80% | -22.94% | -0.846 | -34.24% | 102.3 |
| 30 H4 | continuous | +9.82% | -17.61% | -0.637 | -27.74% | 201.2 |
| 30 H4 | sparse | -10.64% | -16.16% | -0.564 | -33.72% | 44.6 |

Every configuration has negative OOS Sharpe at the declared 5 bps cost. The
12-bar continuous strategy has positive gross return but its break-even cost
is only 3.58 bps, below the assumed 5 bps. This is a failed robustness
replication for XAUUSD, not evidence against all trend models.

The 5 bps cost is a sensitivity assumption only. Index, oil and agricultural
CFD results remain blocked until a usable OHLC history is obtained.
