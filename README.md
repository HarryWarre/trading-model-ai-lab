# Trading Model AI Lab

Research lab for international CFD and cross-asset quantitative models using reference futures/spot prices and synthetic CFD execution assumptions.

## Research philosophy

This is a **paper-driven quantitative research lab**, not an indicator-based auto-trading bot project.

Every model must follow:

1. Literature review and replication target.
2. Economic or behavioral mechanism.
3. Formal model specification.
4. Falsifiable prediction.
5. Data and identification design.
6. Leakage-resistant validation.
7. Cost, capacity and regime analysis.
8. Reproducible implementation and research log.

Technical indicators may be used only as measurement features or simple baselines. They are not considered a research contribution by themselves.

## Literature starting points

- Time-series momentum across equity index, currency, commodity and bond futures: Moskowitz, Ooi and Pedersen ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463)).
- Cross-sectional momentum literature: Jegadeesh and Titman ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1919226)).
- Short-term reversal versus longer-term momentum: Jegadeesh and Titman ([Review of Financial Studies](https://academic.oup.com/rfs/article-abstract/38/12/3673/8240327)).

## Round 1 status

Round 1 is an engine/integration test on synthetic 15-minute data. It is not evidence of live-market profitability. The next research round must begin from the literature and replace synthetic data with real reference futures/spot data.

## Run

```bash
python3 src/round1_backtest.py
python3 src/multitimeframe_round1.py
```

## Research standards

All models must document data provenance, timestamp alignment, execution lag, spread, slippage, funding, rollover, leverage, margin, out-of-sample design, robustness checks and failure modes. Backtest returns must not be treated as a promise of future performance.
