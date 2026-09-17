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


Command-line baseline runner:

```bash
python -m quant_core.run_baseline \
  --panel data/prepared_panel.csv \
  --output results/price_only_cost_stress.csv \
  --min-assets 15 \
  --costs 0,0.0001,0.0002,0.0004
```

The cost numbers are deliberately passed by the research specification. They are not silently assumed to mean the same monetary amount for every CFD family.


### Multi-input context contract

Strategies that use VIX, rates, macro releases or other external data can call `run_cross_sectional_with_context`. The context table is timestamped; at decision time (t), the strategy receives only rows with timestamp (le t). Duplicate context timestamps fail closed. This keeps the same lightweight runner usable for both price-only baselines and multi-source research.


A pre-registered multi-input adapter is available in `quant_core/multi_input.py`. It combines a locked price lookback with explicitly supplied asset-specific context features such as `vix__EURUSD`. It does not fit weights automatically; coefficients must be declared before the test period.

## Living experiment queue

1. **Research 039 — macro surprise reactions:** highest priority. Requires an immutable historical feed with actual, point-in-time consensus and official release time. Price runner and fail-closed schema are ready.
2. **Research 040 — pre-FOMC drift replication:** completed on the frozen 2024 panel; positive sign but rejected because bootstrap and matched-control confidence gates failed. See issue #57 and `research/real_fomc_drift_2024.md`.
3. **Research 040 confirmation:** rerun the unchanged event definition on the prepared 2023–2025 15-asset panel after that panel passes coverage QA. This expands eight events to 24 but is not an untouched holdout.
4. **Later holdout:** reserve 2026+ events and prices for confirmation after the event model and data contract are locked.

5. **Research 041 — post-FOMC cross-asset reaction:** completed exploratory on the 2024 15-column panel. The 5-minute reaction-following rule and expanding ridge model were both negative after the fixed 4-pip cost; see issue #58 and `research/real_post_fomc_multinput_2024.md`. It used 7 valid events and 14 assets after fail-closed timestamp checks. No alpha or production claim.

Research 041 data note: the current workspace copy of the 2024 panel has SHA-256 `e632e54adb79e027e991bb335a917e9a7a30e16c6ddf33b0daecc9ceeae5d05c`, which differs from an older recorded hash. The current hash is frozen in the new runner and must be reconciled before treating historical results as a canonical replication.

Current data status: 45 hash-locked HistData archives cover 15 assets for 2023–2025, but the combined multi-year 5-minute panel has not yet been written to Drive. The validated 2024 panel is available and was used for Research 040. Missing WTIUSD 2024–2025 does not block the 15-asset panel.


6. **Research 042 — BLS CPI/employment digestion:** completed exploratory on 22 usable 2024 announcements and all 15 panel assets. Continuation, reversal, equal-risk reversal and the expanding multi-input ridge model were all negative after the fixed 4-pip cost. Ridge returned -0.673% at 1x and failed all six gates; see issue #59 and `research/real_bls_event_reaction_2024.md`. The two December releases are absent because the local panel ends on 2024-12-05; no data were imputed.

**Next highest-value work:** repair the matched-control coverage for Research 043 or obtain a comparable session-complete archive, then rerun the frozen confirmation. In parallel, Research 039 remains blocked on a point-in-time, timestamp-verifiable consensus archive; official BLS timestamps alone are available but do not identify the economic surprise.


7. **Research 043 — 2023–2025 pre-FOMC confirmation:** preregistered in [issue #60](https://github.com/HarryWarre/trading-model-ai-lab/issues/60). The 15-asset panel is now built and hash-locked: 224,244 rows, 45/45 source archives SHA-verified, with no interpolation. The event-only checkpoint across 24 FOMC decisions is positive at 0x/1x/2x/4x costs (+4.456%, +4.334%, +4.211%, +3.966%), but the full confirmation is **blocked**, not passed: five matched-control windows violate the frozen 10-minute staleness rule and two events have no valid ±7-day control. Bootstrap P(event return > 0) is 91.17%, below the 95% gate. See the partial results under [results/research043_partial](https://github.com/HarryWarre/trading-model-ai-lab/tree/main/results/research043_partial).

One-run build and confirmation: [open Research 043 in Colab](https://colab.research.google.com/github/HarryWarre/trading-model-ai-lab/blob/main/colab/run_research043_multiyear_confirmation.ipynb). It revalidates the 45 ZIPs, builds the 15-asset wide panel, runs tests, and now preserves an event-only checkpoint if the matched-control gate blocks. After this one-time panel build, routine event strategies can run against the prepared core without rebuilding raw M1 data.


## Research 044 completed — prior same-weekday FOMC controls

Research 043's event-only result was retested against four prior same-weekday controls per event under a design frozen in issue #61 before control performance was computed. The 15-asset 2023–2025 panel passed its SHA/row/time checks; all 24 events obtained four valid historical controls without relaxing the 10-minute quote rule.

At the 4-pip assumption, the event portfolio returned +4.334%, versus +1.400% for the comparable controls. Mean event-minus-control log return was +0.1188% per event, but the circular block-bootstrap probability was only 82.09% and its 95% interval was [-0.1233%, +0.3747%]. The difference was positive in 2023 and 2024, then negative in 2025. Six of seven preregistered gates passed; the 95% inference gate failed, so the decision is rejected/research-only.

The audit also corrected Research 043's cadence label: 24 portfolio event dates contain 96 asset round trips and 192 entry/exit legs. Returns and costs were already calculated at asset level and did not change.

Files: `real_fomc_prior_weekday_controls.py`, `test_real_fomc_prior_weekday_controls.py`, `research/real_fomc_prior_weekday_controls.md`, and `results/research044/`.

Next priority: do not tune the FOMC window. Seek a genuinely later untouched FOMC holdout or preregister an international central-bank replication only where official release timestamps are fully verifiable. Research 039 remains blocked on point-in-time historical consensus data.


## Research 045 — statement-time risk, not a trade

[Research 045 issue #62](https://github.com/HarryWarre/trading-model-ai-lab/issues/62) preregistered an ex-post, non-directional FOMC jump comparison with four past same-clock controls. On the SHA-locked 15-asset panel, 12 session-comparable assets across FX, metals and U.S. indices produced 20/24 eligible meetings (238 asset-events). Mean event-control unsigned jump was +10.4650 bp (10,000 two-event-block resample share positive 99.15%). All preregistered *observed-subset* mechanism gates passed, but only 9/20 meetings were positive, the median was negative, the top three explain 87.63% of the net gain, and four 2023 meetings have no eligible event quotes. This is **research-only evidence about event risk, NOT trading alpha, a 4-pip backtest or proof of consistent jumps**. See [report](https://github.com/HarryWarre/trading-model-ai-lab/blob/main/research/real_fomc_crossfamily_jumps_2023_2025.md), code, tests and `results/research045/`.

Next queue: (1) audit four missing 2023 event windows against independent verified reference feeds without altering the frozen analysis; (2) acquire/hash [SF Fed US Monetary Policy Event-Study Database](https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/) and examine statement versus press-conference shocks, treating revised/full-sample shocks as ex-post unless point-in-time availability is established; (3) continue searching for official, timestamped consensus releases for Research 039, then freeze a genuinely later untouched holdout. Do not tune earlier FOMC drift windows or present event jump as an executable scalp.


## Research 046 — quality gate on Research 045

[Issue #63](https://github.com/HarryWarre/trading-model-ai-lab/issues/63) audits whether the FOMC statement-time sample is representative. Exact quote pairs are complete for only 20/24 events; four consecutive meetings in 2023 have none across the frozen comparable 12-asset subset. Same-clock, same-weekday earlier controls in that period have similarly low availability. The preregistered broad-year completeness requirement (at least 23/24 events) fails. Research 045 is therefore an ex-post observation on available events, **not** a general 2023–2025 or trading-alpha claim. See [public report](https://github.com/HarryWarre/trading-model-ai-lab/blob/main/research/real_fomc_quote_selection_audit_public.md), [aggregate results](https://github.com/HarryWarre/trading-model-ai-lab/tree/main/results/research046) and audit code/tests. Detailed source provenance remains out of the public repository. Next: independent verification of the missing source windows and a later untouched holdout. No imputed price or revised strategy has been used.
