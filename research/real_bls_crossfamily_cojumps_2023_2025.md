# Research 055 — invalidated joint-rank BLS co-jump audit

## Status

**Invalid because of target leakage. Do not use the reported metrics as evidence.**

This experiment was preregistered in issue #72 and attempted to identify cross-family co-jumps around 70 official US CPI and Employment Situation releases in 2023–2025. It was motivated by Lahaye, Laurent and Neely (2011), who document links between macro announcements and international jump/co-jump behavior.

The implementation ranked each asset's event-day jump jointly against the event and four prior matched dates. That definition makes every matched-date label depend on the later event-day observation. Consequently, the price-only control and Ridge forecast received information that was unavailable on the control date. The resulting 8/8 mechanical gate pass, including the unusually strong Ridge result, is invalid.

The raw outputs are preserved under `results/research055/` for auditability. They must not be promoted, combined with valid evidence, or used to tune Research 056. The corrected design was independently preregistered in issue #73 before its outputs were inspected.

## Defect correction

Research 056 classifies every target date only against four observations strictly earlier than that target date. Its ordinary matched dates receive their own nested historical anchors, so no later BLS event can alter an earlier control label. Ties fail closed.

## Decision

Research 055 is **invalidated**, not merely a failed model. It supplies no alpha, risk, or forecasting evidence.

