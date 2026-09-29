# Research 057 — BLS delayed volatility after initial price discovery

## Decision

The preregistered audit supports persistent non-directional event risk from T+5 through T+30 after scheduled US CPI and Employment Situation releases. All eight gates pass on the observable 2023–2025 panel. This is **not a directional signal, trading strategy or alpha claim**. The study creates zero positions, turnover and P&L at 0×, 1×, 2× and 4× the fixed four-pip cost convention.

## Mechanism and hypothesis

Andersen, Bollerslev, Diebold and Vega (2003) document rapid price discovery and strong volatility responses to macro announcements. Andersen and Bollerslev (1998) model announcement effects together with intraday volatility persistence. Research 057 asks whether elevated risk remains after the first five minutes rather than repeating Research 042's rejected directional continuation/reversal strategy.

For each asset and official BLS release at T:

- immediate move: `10,000 × abs(log(P[T+5] / P[T−5]))`;
- delayed move: `10,000 × abs(log(P[T+30] / P[T+5]))`.

The intervals share only the T+5 price boundary, not a return. Four controls are selected from exact same-clock dates one to twelve weeks before the event, excluding CPI and employment dates. Missing/nonpositive exact quotes fail closed. The primary portfolio weights the four families equally and assets equally within each family.

The initial co-jump feature is also timing-safe: every event is compared only with four earlier non-event anchors for the immediate T−5 to T+5 interval. The implementation explicitly avoids reading T+30 when constructing this feature.

## Data and coverage

- 70 official releases: 35 CPI and 35 Employment Situation dates from the official 2023–2025 BLS calendars.
- 15-asset recovered five-minute panel, SHA-256 `18133cc85f5d75263086c83584276a8128d79daa2e9eeb8efdb873944eef117c`.
- 54 events passed fail-closed coverage checks, with 14–15 assets and all four families.
- No interpolation, nearest quote, forward fill or synthetic value.

## Primary results

| Metric | Event | Matched controls | Difference |
|---|---:|---:|---:|
| Delayed T+5 to T+30 move | 23.0750 bp | 15.3466 bp | **+7.7284 bp** |

Forty-two of 54 events had positive delayed excess. The deterministic two-event moving-block bootstrap gave a 100.00% probability of positive mean excess and a 95% interval of **+4.8570 to +10.6999 bp**.

| Segment | Events | Delayed excess |
|---|---:|---:|
| CPI | 28 | +8.5882 bp |
| Employment Situation | 26 | +6.8025 bp |
| 2023 | 8 | +5.8199 bp |
| 2024 | 24 | +9.9814 bp |
| 2025 | 22 | +5.9647 bp |

Every family leave-one-out remained positive: +8.3739 bp excluding FX, +6.5935 excluding metals, +8.1062 excluding equity indices and +7.8401 excluding energy. The five largest positive events contributed 30.19% of total positive excess, below the 60% gate.

The rank correlation between immediate and delayed event movement was +0.3822, satisfying the preregistered positive-association gate.

## Forecast comparators

After a fixed 12-event warm-up, every fit used earlier eligible events only.

| Model | Events | MAE | Correlation |
|---|---:|---:|---:|
| Price-only matched-control mean | 42 | 9.8636 bp | +0.0851 |
| Economic release-type mean | 42 | **8.1896 bp** | −0.0602 |
| Ridge multi-input | 42 | 8.2641 bp | +0.0690 |

Ridge beat price-only, remained within 5% of the economic baseline and had positive correlation, so the locked forecast gate passed. The correlation is nevertheless economically weak; the regression must not be presented as a strong event-level predictor.

## Descriptive robustness outside the decision gates

The effect was positive in both chronological halves (+9.9363 and +5.5205 bp). It was also positive with prior VIX below 20 (+8.1501 bp across 44 events) and VIX at least 20 (+5.8729 bp across 10 events). These diagnostics were added after the locked decision specification and are not promotion gates.

## QA

- Eight standard-library tests passed, including exact boundary separation, missing-boundary failure, official event counts and confirmation that the initial feature never requires T+30.
- Python compilation passed.
- Two full executions produced all artifacts byte-for-byte identically.
- Inputs and outputs are SHA-256 manifested.
- The first technical checkpoint required T+30 for an initial-feature anchor. It was preserved separately and corrected because it was stricter than the preregistered T−5/T+5 definition; corrected outcomes were unchanged.

## Interpretation and next action

BLS event-risk controls should not be assumed to expire after the first five minutes: unsigned movement remains elevated through minute 30 across both release types, all years and all family omissions. This does not identify direction or expected trading profit. The highest-value next directional test remains blocked on a point-in-time, timestamp-verifiable consensus-surprise archive or a genuinely independent later panel. No thresholds or windows should be retuned on these outcomes.

