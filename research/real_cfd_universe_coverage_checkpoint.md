# Research 034 — coverage checkpoint

## Objective

The roadmap requires at least 15 international CFD proxies before fitting a new multi-asset model. This checkpoint audits the requested 16-asset universe against local files and fails closed when a source is absent or malformed.

## Result

Six of sixteen requested assets have valid local HistData-style M1 files:

- EURUSD
- GBPUSD
- AUDUSD
- USDJPY
- XAUUSD
- SPXUSD

Ten are blocked for the target panel: NZDUSD, USDCHF, USDCAD, EURJPY, XAGUSD, NAS100USD, GER40, UK100, WTIUSD and BRENTUSD.

The workspace does contain some older FXCM files for selected indices and energy instruments, but they are not silently mixed into the 2024–2025 HistData panel because their source, session definition, coverage and quote/cost fields are not comparable. No 15-asset P&L, model result or capacity claim is produced.

Every available file is recorded with SHA-256 in `real_cfd_universe_coverage.csv`. The validator has two tests and is fail-closed.

## Decision

Research 034 is blocked before model fitting until a comparable source supplies at least 15 assets, or until a separately preregistered mixed-source design defines how source, session and cost differences are handled. The next safe step is data acquisition and cross-source QA, not parameter optimization.
