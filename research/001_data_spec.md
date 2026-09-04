# Research 001 — Point-in-time data specification

## Required grains

- Raw quotes/trades: one row per event or one-minute bar, UTC timestamp.
- Contract metadata: one row per listed futures contract and effective date.
- CFD mapping: one row per broker symbol and effective date.
- Costs: spread, commission, funding and slippage by symbol and effective date.

## Minimum fields

`symbol`, `timestamp_utc`, `open`, `high`, `low`, `close`, `volume`, `bid`, `ask`, `contract`, `expiry`, `currency`, `multiplier`, `tick_size`, `open_interest`, `roll_rule`, `source`, `retrieved_at`.

## Point-in-time rules

1. A contract enters the tradable universe only after its observable listing date.
2. Roll using a pre-declared rule based on volume or open interest; never use future knowledge.
3. Preserve raw prices and create adjusted series as a derived dataset.
4. Align macro/rate features using publication timestamps, not period labels.
5. Store broker costs as effective-dated observations; missing costs must trigger a conservative fallback and QA flag.

## Validation checks

- Monotonic UTC timestamps and no duplicate keys.
- OHLC consistency and non-negative volume.
- Bid <= ask and spread outlier checks.
- Contract expiry/roll continuity.
- Missingness by asset, session and regime.
- Reconciliation of reference price versus broker mid-price.
- Unit and currency consistency.

## Model handoff

The model consumes a clean price panel and returns next-period positions. It must not read execution results, future contract metadata or post-publication revisions when forming a signal.
