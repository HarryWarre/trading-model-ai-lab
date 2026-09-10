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


## Current roadmap: 15+ international CFD assets

The four-currency experiments in Research 030–033 were a validated pilot, not the intended final universe. The next mainline research round is Research 034 ([issue #47](https://github.com/HarryWarre/trading-model-ai-lab/issues/47)).

### Minimum research universe

- FX: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCHF, USDCAD, EURJPY
- Metals: XAUUSD, XAGUSD
- Equity indices: SPXUSD, NAS100USD, GER40, UK100
- Energy: WTIUSD, BRENTUSD

Optional assets such as HK50, FRA40, JP225 and copper will be added only after source and session QA. The final asset list is frozen before model fitting. Missing data is recorded as missing; it is never silently replaced with another asset.

### Model improvements

The next model family will forecast comparable future returns across assets and may choose no trade. A position is allowed only when predicted benefit is larger than a pre-registered estimate of spread, slippage, funding and model uncertainty. Results will be compared with equal-risk, price-only, linear multi-input and fixed nonlinear baselines.

The inputs will be separated into economically meaningful layers: price/volatility, carry or rollover, futures volume/open interest, CFTC positioning where available, macro release data with publication lags, and liquidity/cost conditions. More variables are not automatically better; each layer must have a mechanism and a data-quality test.

### Required validation gates

Every 15+ asset experiment must include an untouched time block after model lock, overlapping-label leakage controls, 0x/1x/2x/4x cost stress, slippage/funding stress, leave-one-asset-out and leave-one-family-out tests, regime and phase checks, bootstrap/multiple-testing controls, and a capacity statement. If executable depth or ADV is unavailable, capacity is explicitly marked unquantifiable.

No model becomes a candidate merely because it has positive backtest return. The all-pass criteria and failure status are recorded in the relevant issue and research note.


## Operating model: automatic research core

Routine research does **not** require a Colab session.

- `quant_core/` is the small reusable engine: it validates panels, gives a strategy only the prices available at each decision, applies weights on the next bar, records turnover and charges a documented comparable cost.
- A new hypothesis only needs a small strategy module plus tests. The core makes the execution lag and no-look-ahead rule the default.
- Google Drive holds large prepared panels and manifests. Colab is reserved for one-off raw-M1 conversion, large retraining or data acquisition—not for every research round.
- A cross-asset “4 pip” assumption must be translated explicitly by each research wrapper; the generic engine refuses to pretend the same pip unit has the same value for FX, gold, oil and indices.

Example:

```python
from quant_core import run_cross_sectional

result = run_cross_sectional(panel, my_signal, one_way_cost=0.0001)
print(result.summary())
```

The first runner test suite is `test_quant_core_backtest.py`. It checks next-bar execution, initial-turnover costs and duplicate-row rejection.


### Baseline and cost stress

The core now includes a locked price-only trailing-momentum baseline and a helper that runs the same strategy at pre-declared cost levels. This baseline is a comparator, not the research contribution. Every future multi-input strategy must report whether it adds value over this baseline under the same execution rules.
