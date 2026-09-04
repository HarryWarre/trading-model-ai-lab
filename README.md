# Trading Model AI Lab

Quant research lab for international CFD research using reference futures/spot prices and synthetic CFD execution assumptions.

## Round 1 status

Round 1 validates the backtesting pipeline on synthetic 15-minute data. It is an engine/integration test, not evidence of live-market profitability.

- Universe: 6 synthetic assets
- Models: trend following, breakout, mean reversion
- Costs: base, conservative, stress
- Validation: 70/30 holdout
- Next gate: replace synthetic prices with real reference data and add rolling walk-forward validation

## Run

```bash
python3 src/round1_backtest.py
```

Outputs are written to `results/round1_results.csv`.

## Research standards

All models must document data provenance, timestamp alignment, execution lag, spread, slippage, funding, rollover, leverage, margin, out-of-sample design, and robustness checks. Backtest returns must not be treated as a promise of future performance.
