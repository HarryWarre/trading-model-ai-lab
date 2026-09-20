# Research 048 — official statement surprise and press-conference returns

## Decision

**The expanding Ridge model is rejected / research-only.** It earned a positive
return but failed the preregistered year-stability and inference gates. A simple
economic baseline was stronger and stable in this sample, so it is queued for a
strict later holdout; it is not promoted from the already inspected 2023–2025
sample.

## Paper-driven mechanism

Acosta et al. (2025) define separate high-frequency windows for the FOMC
statement and Chair press conference. Jarociński and Karadi (2020) show that the
joint response of rates and equities helps distinguish a conventional monetary
policy shock from a central-bank information shock.

The test asks whether information complete at statement T+20 predicts returns
from T+20 to T+90. A fixed rate-path surprise is the simple mean of the official
USMPD FF1–FF6 and ED1–ED4/SOFR changes. This avoids full-sample PCA loadings.
The model also receives the official S&P futures statement return, their
interaction, the asset's statement return and lagged volatility/VIX.

Primary sources:

- Acosta et al. (2025), *Financial Market Effects of FOMC Communication*:
  https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf
- SF Fed USMPD: https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/
- Jarociński and Karadi (2020): https://doi.org/10.1257/mac.20180090

## Data and timing

- Official USMPD workbook updated 17 September 2026; 198,422 bytes; SHA-256
  `f02bfcbf80cf597548d4fccb5a80b30cb1f4373a7d50e26fd1def097d43df1aa`.
- The workbook has 279 statement events from 1994-02-04 to 2026-09-16 and
  eight scheduled statement rows in each of 2023, 2024 and 2025.
- CFD input is the validated 15-asset 2023–2025 panel. The tradable test uses
  the 12 assets with preregistered FX, metal and U.S. index family mappings.
- Twenty of 24 meetings meet the exact-quote and family coverage contract.
  The first eight eligible meetings are warm-up; the remaining 12 are evaluated.
- Features end at T+20. Entry is the exact T+20 quote and exit is T+90. Missing
  quotes fail closed; no price is carried forward.
- Cost is a fixed four-pip round trip translated by the locked asset pip table.

## Locked models

1. Price-only continuation.
2. Equal-risk long baseline.
3. Economic baseline: trade only when the statement rate and S&P futures
   reactions have opposite signs (conventional policy classification); abstain
   for same-sign information-shock classifications.
4. Expanding Ridge with alpha 10, eight-event warm-up and no parameter search.
   It abstains unless the forecast exceeds one-times cost plus half the training
   median absolute residual.

## Results

| Model | 0× cost | 1× (4 pip) | 2× | 4× | Round trips |
|---|---:|---:|---:|---:|---:|
| Price-only | +0.7711% | +0.3750% | -0.0196% | -0.8041% | 142 |
| Equal-risk long | +0.0078% | -0.3853% | -0.7769% | -1.5554% | 142 |
| Economic rule | +2.0094% | **+1.8015%** | +1.5941% | +1.1805% | 66 |
| Ridge | +1.4937% | **+1.2715%** | +1.0497% | +0.6076% | 65 |

Ridge details:

- 130 entry/exit legs; 54.23% abstention; 66.15% directional hit rate.
- 2024: +2.1285%; 2025: **-0.8391%**.
- First half: +1.9414%; second half: **-0.6571%**.
- Paired block-bootstrap probability Ridge beats price-only: **69.28%**, below
  the locked 95% gate.
- Every leave-one-family-out and leave-one-asset-out result remains positive.
- The evaluation sample fell entirely above the VIX median learned from warm-up,
  so low/high VIX comparison is not identified.

The preregistered economic baseline is descriptive but notable:

- 2024: +1.2925%; 2025: +0.5026%.
- It trades six of 12 evaluation meetings, with 66 asset round trips.
- Paired block-bootstrap probability it beats price-only: 99.80%.
- All leave-one-family-out and leave-one-asset-out results remain positive.

This baseline was not the primary gated model, and the 2023–2025 sample has
already been inspected. Selecting it now as alpha would be post-selection.

## Gates

| Gate | Result |
|---|:---:|
| Ridge net positive at 1× | Pass |
| Ridge beats price-only with probability at least 95% | **Fail** |
| Ridge positive in both 2024 and 2025 | **Fail** |
| Ridge positive at 2× | Pass |
| All Ridge family leave-one-out positive | Pass |
| At least 16 eligible events and 10 assets | Pass |

## QA and limitations

- Four independent tests pass; compile passes.
- Two full runs produce byte-identical result directories.
- Raw workbook, panel, events, VIX and every output are hash recorded.
- `pytest` is unavailable in the current runtime, so the test functions were
  executed independently in Python.
- USMPD is a current official vintage, not a historical file frozen at each
  event. It contains derived LSEG high-frequency changes.
- No capacity claim is made because depth/ADV are unavailable and not needed
  for this mechanism test.

## Next action

Freeze the economic rule unchanged and test it only on a later untouched CFD
panel. The official USMPD already contains six 2026 meetings, but a comparable
15-asset 2026 CFD panel is not currently present. Do not tune the sign map,
window, threshold or event selection on 2023–2025.
