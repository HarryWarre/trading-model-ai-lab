# Research 001 — Data source map

| Research role | Preferred source | Use | Limitation |
|---|---|---|---|
| Contract-level futures prices | CME DataMine | Settlement, OHLC, volume/open interest and contract history | Access/licensing and mainly exchange data, not broker CFD quotes |
| TSMOM benchmark | AQR TSMOM Factors | Monthly benchmark comparison from 1985 across 58 instruments | Factor data is not intraday and is not a raw execution feed |
| Positioning | CFTC COT | Weekly trader positioning and hedging-pressure covariates | Report date differs from release date; align by release timestamp |
| Funding/rates | FRED Treasury series | Risk-free and rate-regime controls | US-centric and daily/low frequency |
| CFD execution calibration | Broker export | Spread, funding, margin, trading sessions and symbol mapping | Broker-specific; should not be generalized across brokers |

## Acquisition order

1. Download AQR benchmark data for a high-level replication check.
2. Acquire contract-level futures data for the selected asset classes.
3. Build point-in-time continuous series with a pre-declared roll rule.
4. Add CFTC/FRED covariates only with release-date alignment.
5. Calibrate synthetic CFD execution from broker exports.

## Evidence rule

Benchmark factor data can validate broad direction and implementation, but it cannot validate intraday execution. A model is not eligible for deployment claims until it passes on contract-level data with explicit costs and roll treatment.
