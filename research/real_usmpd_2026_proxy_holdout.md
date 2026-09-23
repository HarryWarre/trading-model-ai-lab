# Research 051 — untouched 2026 USMPD economic-rule proxy holdout

## Decision

**Failed partial confirmation; research-only.** The frozen economic rule made
`+0.1022%` after the fixed 4-pip round-trip convention on the untouched
2026-07-29 event, but it failed two preregistered gates: it did not beat the
price-only comparator and the U.S. equity family contribution was negative.
No window, sign map, asset, or threshold was changed after observing returns.

This is one active event on public reference-market proxies, not executable
broker CFD data. It cannot establish alpha even if every limited gate passes.

## Primary evidence and mechanism

Jarociński and Karadi (2020), *Deconstructing Monetary Policy Surprises*, use
the joint high-frequency sign of rate and equity surprises to distinguish
conventional policy shocks from central-bank information shocks
(https://doi.org/10.1257/mac.20180090). Statement-window inputs and frozen
2026 labels come from the official SF Fed US Monetary Policy Event-Study
Database (https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/).

Research 050 froze 2026-07-29 as conventional and 2026-09-16 as information
before 2026 tradable prices were available. The rule therefore traded only
July 29 and abstained on September 16.

## Timing-safe model

- Public Yahoo Finance five-minute chart JSON, captured and SHA-256 locked.
- Exact interval opens at statement T+20 (14:20 New York) and T+90 (15:30).
- Price-only comparator uses the exact T-10 to T+20 move.
- No nearest-price lookup, interpolation, or forward fill.
- Equal weight across FX, metals, and U.S. equity families, then equal weight
  within each available family.
- Dovish conventional mapping: long USD-quote FX, metals, and equity proxies;
  short USD-base FX; abstain EURJPY and oil controls.
- Costs: 0x/1x/2x/4x the fixed four-pip CFD round-trip convention.

The preregistered linear Ridge comparator was not identifiable. A direct source
probe returned `Unprocessable Entity`: five-minute data for the required
20-day pre-event volatility window was outside Yahoo's 60-day retention range.
It is reported as unavailable, not assigned a zero return.

## Coverage and results

All 13 primary proxies had exact T-10, T+20, and T+90 observations across all
three families. EURJPY and oil were frozen controls and not part of the primary
portfolio.

| Model | 0x | 1x (4 pip) | 2x | 4x |
|---|---:|---:|---:|---:|
| Economic rule | +0.1192% | +0.1022% | +0.0851% | +0.0510% |
| Price-only continuation | +0.1535% | +0.1365% | +0.1194% | +0.0853% |
| Equal-risk always long | +0.0625% | +0.0454% | +0.0284% | -0.0057% |

Each active model made 13 round trips / 26 entry-exit legs on July 29. The
economic rule made zero trades on the frozen September information-shock event.

Economic-rule family contributions at 1x cost:

| Family | Net return |
|---|---:|
| FX | +0.1839% |
| Metals | +0.2901% |
| U.S. equity | **-0.1669%** |

Every leave-one-asset-out economic portfolio remained positive; the minimum
was `+0.0828%`. This is descriptive only because there is one active event and
no event-level p-value is identifiable.

## Preregistered gates

Six of eight limited gates passed. Failed gates:

1. economic rule did not exceed price-only at 1x cost (`+0.1022%` versus
   `+0.1365%`);
2. not every family was positive because U.S. equity returned `-0.1669%`.

Passed: coverage, positive 1x return, positive 2x return, all asset LOO
positive, information-event abstention, and deterministic rerun.

## QA and limitations

- Raw responses and source URLs are hash-locked in the raw manifest.
- Two runs from the same raw files produced byte-identical artifacts.
- Python compilation and three unit tests passed.
- Yahoo futures/FX are reference proxies; the synthetic CFD pip convention is
  a sensitivity calculation, not an execution-cost claim.
- One active untouched event is insufficient for inference or production use.
- The issue preregistration says `10/14` in one gate while the frozen primary
  universe contains 13 assets after excluding two controls. The threshold was
  not altered; actual coverage was 13 primary assets and three families.

## Next action

Keep the economic rule frozen but downgraded after this failed partial
confirmation. Do not remove equity or switch to price-only based on one event.
Acquire comparable broker/CFD 2026 data or wait for additional untouched
conventional events; then rerun the unchanged rule with event-level inference.
