# Roadmap — international CFD universe expansion

## Why change direction

Research 030–033 used four currency proxies because that was the validated data available at the time. The results are useful diagnostics, but a four-currency panel is too narrow for the intended international CFD research program. The next stage therefore expands the universe before adding more model complexity.

## Research 034 target

At least 15 frozen assets:

- 8 FX: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCHF, USDCAD, EURJPY
- 2 metals: XAUUSD, XAGUSD
- 4 equity indices: SPXUSD, NAS100USD, GER40, UK100
- 2 energy contracts: WTIUSD, BRENTUSD

Optional additions require separate source and session validation.

## Data architecture

Each asset needs a coverage and quality record:

1. session boundary and timezone;
2. bid/ask availability or explicit spread scenarios;
3. price and realized volatility;
4. carry, funding, rollover or documented approximation;
5. reference-futures volume/open interest where available;
6. CFTC positioning where eligible;
7. macro and volatility variables with publication-date lags;
8. spread, turnover and liquidity-cost state.

No missing series may be silently replaced by another instrument.

## Model direction

The model forecasts the next comparable holding-period return after costs and is allowed to abstain. It trades only when expected benefit exceeds a locked cost-and-uncertainty buffer. It compares equal-risk, price-only, linear multi-input and fixed nonlinear baselines. Allocation controls volatility, correlation and family concentration.

## Validation gates

- 15 or more assets with per-asset coverage table.
- Untouched post-lock time block.
- Walk-forward and purged validation for overlapping labels.
- 0x, 1x, 2x and 4x cost stress plus slippage/funding stress.
- Leave-one-asset-out and leave-one-family-out tests.
- Regime and phase robustness.
- Bootstrap and multiple-testing adjustment.
- Capacity proxy from spread, volume/open interest and turnover; otherwise explicitly unquantifiable.
- No post-result asset deletion, regime filter or parameter selection.

## Deliverables

Source manifest, coverage QA, point-in-time feature panel, abstention baseline, model code, results, attribution, robustness/capacity tables, tests, research note and updates to issues #13 and #14.

The research status remains research-only unless all preregistered gates pass.
