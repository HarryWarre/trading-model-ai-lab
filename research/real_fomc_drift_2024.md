# Research 040 — pre-FOMC drift across international equity CFD proxies

## Decision

**Rejected / research-only.** The 2024 replication has a positive sign, but it fails the preregistered statistical and matched-control gates. It is not an alpha or production claim.

## Paper and mechanism

Lucca and Moench, *The Pre-FOMC Announcement Drift*, American Economic Review 105(2), 2015, documents unusually high U.S. equity returns during the 24 hours before scheduled FOMC announcements. Primary research page: https://www.newyorkfed.org/research/staff_reports/sr512.html.

The proposed mechanism is that risk-bearing and uncertainty change before a known central-bank decision. This study tests the timing pattern, not an indicator combination.

Official 2024 event dates come from the Federal Reserve meeting calendar and each statement page: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm. All eight pages state a 2:00 p.m. EST/EDT release time.

## Preregistered hypothesis

An inverse-volatility portfolio of SPXUSD, NSXUSD, GRXEUR and UKXGBP should earn positive net returns in a common 24-hour pre-FOMC window, remain positive at doubled cost, be positive in both halves of 2024 and in at least three assets, and beat matched non-event windows with at least 95% bootstrap probability. All gates were required.

## Timing-safe model

For event e and asset i:

- the common international window ends three hours before the official FOMC release and starts exactly 24 hours earlier;
- each boundary uses only the last observed quote at or before that boundary;
- a quote more than 10 minutes stale rejects the window;
- volatility is estimated only from observed 5-minute returns in the preceding 20 calendar days;
- weights are proportional to inverse volatility and sum to one;
- fixed round-trip cost is 4 index pips per asset at 1x, with 0x/1x/2x/4x sensitivity.

The initial T-5-minute design was rejected before P&L because German and U.K. proxies were already closed. The common T-3-hour design and DST-safe placebo matching were recorded in issue #57 before performance was inspected.

Matched controls are the same New York wall-clock window seven days before and after each event. Stale holiday/short-session controls are rejected; every event must retain at least one valid control.

## Data quality

- Frozen panel: 15 assets, 5-minute UTC, 105,120 timestamps in 2024.
- Panel SHA-256: 6f8f6995527e429dc60fd9dc372bae21ad458698c88a70a46f3e46aa27c9f8ef.
- Eight official FOMC timestamps; event-file SHA-256: 991875afeea3029cd8a9d812685577d39c51220ef76c9cbd62bd454a5c22a552.
- VIX is lagged to the latest observation strictly before the event date and used only for descriptive regime attribution.
- No missing quote is forward-filled across an event boundary.
- 13 valid matched-control windows remained.
- Deterministic rerun reproduced all 10 result files byte for byte.

## Results

| Check | Result | Gate |
|---|---:|:---:|
| Net return, 1x cost | +1.260% | pass |
| Net return, 2x cost | +1.225% | pass |
| Net return, 4x cost | +1.154% | descriptive |
| Positive events | 6/8 | descriptive |
| Median event return | +0.483% log | pass |
| Positive assets | 4/4 | pass |
| Positive leave-one-asset-out portfolios | 4/4 | robust |
| First four events | +1.112% | pass |
| Last four events | +0.146% | pass |
| Bootstrap P(mean > 0) | 65.28% | **fail** |
| Mean event minus matched control | +0.112% log/event | sign pass |
| Bootstrap P(event > matched control) | 57.48% | **fail** |

The 95% bootstrap interval for mean event return is -0.808% to +0.938% log per event. The interval for event-minus-control is -1.179% to +1.284%. Both include zero by a wide margin.

Asset net returns were positive: GRXEUR +3.108%, NSXUSD +2.152%, SPXUSD +0.760%, and UKXGBP +0.451%. These are stand-alone attribution sums and must not be added because the portfolio is inverse-volatility weighted.

The low-VIX half earned +1.112%; the high-VIX half earned +0.146%. With four events in each group this is descriptive only and is not a trading filter.

## Trading cadence and costs

There were 32 asset-level round trips, or 64 entry/exit trade legs, across eight events. This is an event strategy, not a scalping model; its low cadence is intentional. Costs are not the reason for rejection: the result stays positive at 4x cost, while statistical evidence and matched controls remain weak.

## Limitations

- Only eight 2024 events are available.
- The 2024 panel has already been used by the lab, so this is exploratory rather than untouched.
- The primary paper studies U.S. equities up to the announcement. The international common-session window ends three hours earlier to avoid comparing live U.S. prices with closed European markets.
- The 4-pip mapping for index CFDs is a declared synthetic assumption, not broker execution data.
- A fitted linear or nonlinear event model is not estimated from eight observations; doing so would be severe overfitting.
- Capacity is not estimated because depth/volume is not a research bottleneck for this hypothesis.

## Next action

Research 039 remains the higher-value target: scheduled inflation, employment, growth and central-bank surprises with verified actual, point-in-time consensus and UTC release timestamps. The 2023-2025 15-asset raw archive is complete for 45 asset-years, but the combined prepared panel is still missing. After the panel is built, Research 040 can be replicated over 24 FOMC events; Research 039 still requires a defensible historical consensus source.
