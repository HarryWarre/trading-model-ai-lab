# Research 049 — post-selection audit of the frozen USMPD economic rule

## Decision

**All seven preregistered robustness gates pass, but the rule remains
research-only.** The audit uses the same already-inspected 2023–2025 sample as
Research 048. It strengthens the case for an untouched 2026+ confirmation; it
cannot replace one.

## Mechanism and falsifiable hypothesis

Jarociński and Karadi (2020) show that joint rate and equity reactions can
separate conventional monetary-policy shocks from central-bank information
shocks. Acosta et al. (2025) provide the official USMPD statement windows and
high-frequency changes used by Research 048.

The frozen rule trades only opposite-sign rate/equity statement reactions. It
abstains when both move in the same direction, because that classification is
consistent with an information shock. A hawkish conventional shock buys
USD-base FX and sells USD-quote FX, metals and US equity indices; a dovish shock
reverses those signs. EURJPY remains an abstention.

The preregistered audit hypothesis was that the unchanged rule would remain
positive after every event exclusion and 2x cost, avoid excessive event
concentration, beat the unchanged price-only comparator in an exact paired
sign-flip test, stay positive in both evaluation years and survive every family
exclusion.

Primary sources:

- Jarociński and Karadi (2020), *Deconstructing Monetary Policy Surprises*:
  https://doi.org/10.1257/mac.20180090
- Acosta et al. (2025), *Financial Market Effects of FOMC Communication*:
  https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf
- Official SF Fed USMPD:
  https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/

## Data and timing contract

- Inputs are only hash-locked Research 048 artifacts; this audit does not
  rebuild, alter or impute event returns.
- The evaluation set is the same twelve post-warm-up meetings.
- Entry is exact statement T+20 and exit is exact T+90.
- Positions use inverse pre-event volatility weights.
- Missing quotes fail closed; no price is carried forward.
- The base CFD cost is the frozen 4-pip round trip, with 0x/1x/2x/4x stress.
- The exact paired test enumerates all 2^12 possible sign flips of each event's
  economic-minus-price-only log-return difference.

## Results

| Model | 0x cost | 1x (4 pip) | 2x | 4x | Round trips |
|---|---:|---:|---:|---:|---:|
| Economic rule | +2.0094% | **+1.8015%** | +1.5941% | +1.1805% | 66 |
| Price-only | +0.7711% | +0.3750% | -0.0196% | -0.8041% | 142 |
| Equal-risk long | +0.0078% | -0.3853% | -0.7769% | -1.5554% | 142 |

Additional checks:

- Exact one-sided paired sign-flip p-value versus price-only: **0.00977**.
- All 12 leave-one-event-out totals are positive; the minimum is **+1.0842%**.
- Largest positive event share: **34.73%**, below the locked 60% cap.
- Minimum leave-one-family-out return: **+1.6291%**.
- Minimum leave-one-asset-out return: **+1.7006%**.
- Direction hit rate among 66 active asset trades: **83.33%**.
- Returns remain positive in both 2024 and 2025, as recorded in Research 048.
- The rule makes 66 asset round trips, or 132 entry/exit legs, and abstains for
  six of the twelve evaluation meetings.

## Preregistered gates

| Gate | Result |
|---|:---:|
| Net positive at 1x cost | Pass |
| Net positive at 2x cost | Pass |
| Every event leave-one-out positive | Pass |
| Largest positive event share <= 60% | Pass |
| Exact paired sign-flip p <= 0.05 | Pass |
| Both evaluation years positive | Pass |
| Every family leave-one-out positive | Pass |

Passing these gates addresses concentration and fragility, not post-selection.
The rule was noticed as a baseline after Research 048 outcomes were inspected,
so no production or alpha claim is permitted.

## QA and blocker

- Three independent test functions pass; Python compilation passes.
- Two full runs produce byte-identical Research 049 result directories.
- Every input and output is SHA-256 recorded; any Research 048 artifact change
  fails closed.
- `pytest` is unavailable in the runtime, so the same test functions were
  executed directly.
- The connected Drive folder has no 2026 CFD files. The official HistData web
  route returned HTTP 502 during acquisition. No synthetic, guessed or
  forward-filled 2026 price was substituted.

## Next action

Keep the sign map, T+20/T+90 window, abstention rule, weighting and cost model
unchanged. Acquire a comparable 2026+ CFD panel, hash and validate it, then run
the frozen confirmation exactly once. With only six 2026 FOMC meetings currently
present in USMPD, that confirmation will still be small-sample and must report
event-level leave-one-out results.
