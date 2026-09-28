# Research 056 — timing-safe BLS cross-family co-jump audit

## Decision

The corrected audit supports a cross-family jump-risk effect around scheduled US CPI and Employment Situation releases, but it is **not a trading strategy or alpha claim**. All eight preregistered gates passed on the observable 2023–2025 panel. The study makes no trades and reports zero turnover and zero P&L at 0×, 1×, 2× and 4× the fixed 4-pip cost.

## Mechanism and preregistered hypothesis

Lahaye, Laurent and Neely (2011) report that macro announcements are associated with international jumps and co-jumps. The falsifiable hypothesis here is that scheduled BLS releases create more simultaneous extreme moves across FX, metals, equity indices and energy than comparable ordinary dates at the same UTC clock time.

For each target date `t`, the absolute T−5 to T+30 minute return of each asset is compared only with four valid non-BLS observations from 1–12 weeks before `t`. An asset is extreme only if its target jump is strictly greater than all four historical anchors. A family is active when at least half its observed assets are extreme. Breadth is the active-family count divided by four; a broad co-jump requires at least three active families.

Each BLS event is compared with four prior non-BLS target dates. Crucially, each matched target has its own nested historical anchors. All anchors are strictly earlier than their own target and all controls are earlier than the event. No filling or nearest-price substitution is allowed.

Preregistered gates required at least 40 eligible events with 12 assets and all four families; positive event-minus-control breadth with at least 95% block-bootstrap probability; a higher broad co-jump rate at events; positive effects for both release types, every year and every family leave-one-out; top-five concentration below 60%; a fixed expanding Ridge forecast gate; and deterministic QA with explicit no-future-anchor tests.

## Data

- 70 official BLS releases: 35 CPI and 35 Employment Situation dates from official 2023, 2024 and 2025 calendars.
- Recovered 15-asset, five-minute panel with 222,048 timestamps.
- Panel SHA-256: `18133cc85f5d75263086c83584276a8128d79daa2e9eeb8efdb873944eef117c`.
- 51 events passed fail-closed coverage checks; each retained event had 14–15 common assets and all four families.
- Prior-day VIX was used only by the preregistered expanding Ridge comparator.

## Results

| Metric | Event | Matched controls | Difference |
|---|---:|---:|---:|
| Mean active-family breadth | 55.88% | 22.55% | **+33.33 pp** |
| Broad co-jump rate (≥3 families) | 43.14% | 6.37% | **+36.76 pp** |

The moving-block bootstrap probability that mean breadth difference is positive was 100.00%; its 95% interval was +25.25 to +41.18 percentage points.

| Segment | Events | Breadth difference |
|---|---:|---:|
| CPI | 26 | +36.54 pp |
| Employment Situation | 25 | +30.00 pp |
| 2023 | 5 | +36.25 pp |
| 2024 | 24 | +30.99 pp |
| 2025 | 22 | +35.23 pp |

Family leave-one-out differences remained positive: +28.10 pp excluding FX, +36.60 pp excluding metals, +27.61 pp excluding equity indices and +41.01 pp excluding energy. The five largest positive events contributed 22.65% of all positive event differences, below the 60% gate.

## Forecast comparators

After a fixed 12-event warm-up, all forecasts were expanding and used prior events only.

| Model | Events | MAE | Correlation |
|---|---:|---:|---:|
| Price-only prior-control breadth | 39 | 0.3606 | −0.0731 |
| Economic release-type mean | 39 | **0.2449** | −0.0398 |
| Ridge multi-input | 39 | 0.2567 | −0.1547 |

Ridge beat price-only and remained within 5% of the economic baseline MAE, so the preregistered forecast gate passed. Its negative correlation is weak evidence against interpreting the regression as a useful continuous forecasting model; the primary result is the non-trading co-jump risk comparison.

## QA and reproducibility

- Seven standard-library unit tests passed, including tie rejection, exact boundaries, official event counts, strictly historical anchors and invariance of an earlier control label to a later event.
- Python compilation passed.
- Two complete executions generated all artifacts byte-for-byte identically.
- The manifest records SHA-256 hashes for every input and result artifact.
- Research 055's joint-rank output is explicitly invalidated and preserved only as a defect checkpoint.

## Interpretation and next action

Scheduled BLS releases are a robust risk regime in this panel: simultaneous extreme moves are much more common than on matched ordinary dates. This can justify event-risk controls, but it does not establish direction, tradability or positive expected P&L. A future trading hypothesis requires timing-safe consensus surprises or another economically justified directional input with verifiable availability timestamps. The restored 2023 coverage remains incomplete, so no imputation is permitted.

