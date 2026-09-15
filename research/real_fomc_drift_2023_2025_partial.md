# Research 043 — partial event checkpoint

Status: blocked / research-only. This is not a confirmation and not a production signal.

## Mechanism

Lucca and Moench document a recurring positive equity-index return in the hours before scheduled FOMC announcements. The test here asks whether the same pre-announcement effect is visible in a wider CFD-proxy panel.

Primary paper: https://www.newyorkfed.org/research/staff_reports/sr512.html

Event timestamps come from official Federal Reserve release pages and the official FOMC calendar:
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

## Frozen hypothesis and model

For each of 24 scheduled FOMC decisions in 2023–2025:

- hold SPXUSD, NSXUSD, GRXEUR and UKXGBP from 27 hours before the 14:00 New York statement time to 3 hours before it;
- weight assets by inverse volatility measured over the preceding 20 calendar days;
- require boundary quotes no more than 10 minutes stale;
- subtract a fixed 4-pip round-trip CFD cost;
- evaluate 0x, 1x, 2x and 4x cost multipliers;
- compare with matched windows at ±7 calendar days using the same New York wall-clock time.

The full confirmation requires positive results at 1x and 2x cost, non-negative returns in every year, positive leave-one-asset-out portfolios, event bootstrap probability at least 95%, and paired event-minus-control bootstrap probability at least 95%.

2024 overlaps Research 040, so this is a broader replication, not an untouched holdout.

## Data audit

- 15 assets × 3 years.
- 45/45 source archives passed SHA-256 and ZIP/member checks.
- Wide panel: 224,244 timestamps and 15 asset columns.
- No interpolation or forward fill.
- Panel SHA-256: `6b5b91b058ec78c49b95ec48dde207157f18f7dbc4451e0bd1f15b4933a44942`.
- One archive differs from the old manifest: EURUSD 2023 was revalidated and recorded in the immutable revalidation manifest; the original manifest was preserved.

## Event-only checkpoint

The event calculation completed for all 24 FOMC decisions. Each event holds four assets, so the correct cadence is 96 asset round trips and 192 entry/exit order legs. A prior checkpoint incorrectly reported 24/48 by counting portfolio event dates instead of asset positions; this reporting defect did not affect returns or costs.

| Cost | Net return |
|---:|---:|
| 0x | +4.456% |
| 1x / 4 pip | +4.334% |
| 2x | +4.211% |
| 4x | +3.966% |

Yearly 1x net returns:

- 2023: +2.358%
- 2024: +1.785%
- 2025: +0.142%

All four leave-one-asset-out portfolios remained positive:

- omit SPXUSD: +3.874%
- omit NSXUSD: +3.553%
- omit GRXEUR: +5.026%
- omit UKXGBP: +4.941%

The event bootstrap probability of a positive mean was 91.17%, with a 95% bootstrap interval for the mean event log return of [-0.0770%, +0.4365%]. This is below the preregistered 95% gate.

## Blocker

The frozen matched-control rule requires all events to have a valid ±7-day comparison with every boundary quote no more than 10 minutes stale. Five control windows failed that rule:

- FOMC_2023_03_22: both controls unavailable;
- FOMC_2023_05_03: both controls unavailable;
- one control each for FOMC_2023_06_14, FOMC_2023_07_26 and FOMC_2024_12_18.

Therefore the full paired event-minus-control gate is not evaluable. A diagnostic using only the 22 events with at least one available control produced bootstrap probability 76.52%, but it is not the preregistered gate and is not used to claim success.

Decision: keep research-only and blocked. Do not call the positive event-only checkpoint alpha.

## Reproducibility files

- Runner: https://github.com/HarryWarre/trading-model-ai-lab/blob/main/real_fomc_drift_2023_2025.py
- Colab: https://colab.research.google.com/github/HarryWarre/trading-model-ai-lab/blob/main/colab/run_research043_multiyear_confirmation.ipynb
- Partial results: https://github.com/HarryWarre/trading-model-ai-lab/tree/main/results/research043_partial
- Research issue: https://github.com/HarryWarre/trading-model-ai-lab/issues/60

The runner now saves the event-only checkpoint and a blocker file before raising when the matched-control gate cannot be completed.
