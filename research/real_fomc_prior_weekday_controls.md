# Research 044 — prior same-weekday controls for pre-FOMC drift

Status: completed / rejected / research-only. This is not an untouched holdout and not a production signal.

## Question and mechanism

Lucca and Moench document unusually positive U.S. equity returns in the hours before scheduled Federal Open Market Committee announcements. The economic claim is stronger than “stocks happened to rise”: if the return is linked to the scheduled Fed event, the same frozen window should beat ordinary windows on the same weekday and at the same New York clock time.

Primary paper: https://www.newyorkfed.org/research/staff_reports/sr512.html

The 24 statement timestamps come from official Federal Reserve release pages and the official calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

## Preregistered design

The design was frozen in issue #61 before the new control returns were computed.

- Data: hash-locked 15-asset, 5-minute CFD-proxy panel for 2023–2025.
- Event assets: SPXUSD, NSXUSD, GRXEUR and UKXGBP.
- Event holding window: T−27 hours to T−3 hours relative to the 14:00 New York statement.
- Weights: inverse volatility from the preceding 20 calendar days.
- Price boundary rule: last observation may be at most 10 minutes stale.
- Cost: fixed 4-pip round trip; stress at 0×, 1×, 2× and 4×.
- Controls: scan the preceding 12 same weekdays at 14:00 New York, exclude windows containing another FOMC statement, and select the four most recent valid windows. No later controls are allowed.
- Main value for event e: its 1× net return minus the mean 1× net return of its four controls.
- Main inference: 10,000-draw circular moving-block bootstrap, block length two events, fixed seed 20260915.

The event-specific hypothesis required all seven gates: complete control coverage, positive mean difference, bootstrap probability at least 95%, at least two positive years, all four leave-one-asset-out differences positive, and event-only returns positive at both 1× and 2× cost.

## Data quality and reproducibility

- Panel SHA-256: `6b5b91b058ec78c49b95ec48dde207157f18f7dbc4451e0bd1f15b4933a44942`.
- Panel-manifest SHA-256: `cabb1aad9a8533121d123f762fac19454a41e744ba254c9a1c8a9d0a84a51db7`.
- 224,244 unique sorted timestamps and 15 asset columns.
- Coverage: 2023-01-01 22:00 UTC through 2025-12-31 22:00 UTC.
- Missing rows remain missing; no interpolation or forward fill was used. Missingness reflects different market sessions and source gaps, so every trade boundary was checked independently.
- All 24 events obtained four controls: 96 selected control windows, 92 unique windows, maximum reuse two.
- The scanner audited 288 candidates: 96 selected, 151 valid but unused, and 41 rejected. Rejections were retained with exact reasons.
- Identical reruns produced byte-identical result files.
- Compilation and three independent assertions passed. `pytest` was unavailable in this runtime; a four-test pytest file is committed for the repository/Colab environment.

## Results

### Event-only return and costs

| Cost multiplier | Net return | Positive events |
|---:|---:|---:|
| 0× | +4.456% | 15/24 |
| 1× (4 pips) | +4.334% | 15/24 |
| 2× | +4.211% | 15/24 |
| 4× | +3.966% | 15/24 |

There were 24 portfolio event holds, 96 asset round trips and 192 entry/exit order legs. This corrects Research 043's checkpoint count; its return and cost calculations were already asset-level and did not change.

### Event versus prior same-weekday controls

| Measure | Result |
|---|---:|
| Mean event-minus-control log return per event | +0.1188% |
| Compounded event return, 1× | +4.334% |
| Compounded comparable control return | +1.400% |
| Compounded event-minus-control difference | +2.893% |
| Positive paired events | 11/24 |
| Block-bootstrap P(mean difference > 0) | 82.09% |
| Block-bootstrap 95% interval | [−0.1233%, +0.3747%] |
| IID-bootstrap sensitivity | 77.66% |
| Equal-weight mean difference | +0.1227% per event |

The mean difference has the expected sign, but the uncertainty interval includes zero and the main probability is below the frozen 95% gate.

### Time and robustness checks

| Year | Event return | Control return | Mean difference per event |
|---:|---:|---:|---:|
| 2023 | +2.358% | −0.196% | +0.3158% |
| 2024 | +1.785% | −0.296% | +0.2582% |
| 2025 | +0.142% | +1.900% | −0.2174% |

All four leave-one-asset-out mean differences remained positive, from +0.0896% to +0.1807% per event. The difference was positive in both VIX halves, but smaller in high VIX (+0.0690%) than low VIX (+0.1687%). These are robustness descriptions, not filters.

## Gate decision

Six of seven gates passed. The failed gate was the main block-bootstrap probability: 82.09% versus the required 95%.

Decision: reject as a validated event-specific trading signal; retain as research-only evidence. The positive 2023–2024 result does not persist in 2025, and 2024 was already used by Research 040. No production or alpha claim is allowed.

## What this changes

The earlier matched-control coverage blocker is resolved without weakening the 10-minute quote rule. The remaining problem is statistical and temporal stability, not transaction cost or missing control data. The next honest test is a genuinely later, untouched set of FOMC events or a separately preregistered international central-bank replication with official timestamps; changing the window or selecting 2023–2024 would be post-result tuning.

## Reproducibility files

- Runner: `real_fomc_prior_weekday_controls.py`
- Tests: `test_real_fomc_prior_weekday_controls.py`
- Results and manifests: `results/research044/`
- Preregistration and decision: issue #61
