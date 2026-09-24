# Research 052 — BLS CPI/employment cross-asset jump-risk audit

## Decision

**A strong but partial event-risk effect; research-only, not alpha.** On the
largest validated panel, absolute cross-asset movement spanning scheduled BLS
releases exceeded matched ordinary-time controls by **18.04 basis points** on
average. Both release types, all three years, and every leave-one-family-out
portfolio were positive. The result nevertheless failed one of eight locked
gates because only 57 events met the coverage contract versus the required 60.

This study creates no directional signal or trade. P&L, turnover, round trips,
and trade legs are zero at every cost multiplier.

## Mechanism and primary sources

Andersen, Bollerslev, Diebold and Vega (2003), *Micro Effects of Macro
Announcements: Real-Time Price Discovery in Foreign Exchange*, document sharp
price discovery and volatility around scheduled macroeconomic announcements
(https://doi.org/10.1257/000282803321455151).

Release dates and 08:30 Eastern times were parsed only from the official BLS
annual calendars:

- https://www.bls.gov/schedule/2023/home.htm
- https://www.bls.gov/schedule/2024/home.htm
- https://www.bls.gov/schedule/2025/home.htm

The source contains 24 selected events in 2023, 24 in 2024, and 22 in 2025.
The 2025 CPI and Employment Situation calendars each contain 11 releases in the
available period; no omitted month was synthesized.

## Frozen measurement

For each event and asset:

`jump_bps = 10,000 × |log(P[T+30] / P[T−5])|`

The first four valid observations at the same weekday/source-clock time from
the previous 12 weeks form the control mean. Other CPI or Employment Situation
dates are excluded. Exact timestamps are mandatory; missing or nonpositive
prices fail closed. There is no nearest-price lookup, interpolation, or forward
fill.

The event portfolio gives equal weight to FX, metals, equity indices, and
energy, then equal weight within each family. The universe contains all 15 CFD
proxies in the recovered panel.

## Timezone defect and correction

The first coverage run exposed a source-timezone defect before its outcome was
accepted. The multiyear manifest says the raw archives use a fixed EST/UTC−5
clock. Mapping BLS releases with daylight-saving UTC therefore selected the
wrong panel hour in summer.

The correction was recorded in issue #69 before rerunning:

- preserve the official BLS UTC timestamp;
- look up the panel at 08:30 fixed EST, or 13:30 UTC year-round;
- construct controls in the same fixed source clock;
- report the 0/60-minute official-to-panel offset explicitly.

No event, window, family, gate, or result threshold changed.

## Coverage

- Official events: 70.
- Eligible events: **57**.
- Maximum assets per event: 15.
- Eligible split: 29 CPI and 28 Employment Situation.
- Years: 11 events in 2023, 24 in 2024, and 22 in 2025.
- Thirteen early-2023 events failed coverage, mainly because the panel lacked
  four prior matched controls or sufficient exact observations.

The locked minimum was 60 eligible events. This gate failed and remains failed.

## Primary results

| Statistic | Basis points |
|---|---:|
| Mean event jump | 36.28 |
| Mean matched control | 18.24 |
| Mean excess | **+18.04** |
| 95% block-bootstrap interval | +12.86 to +23.84 |

All 10,000 deterministic block-bootstrap samples had positive mean excess.
Forty-five of 57 event portfolios had positive excess.

### By release type

| Type | Events | Event | Control | Excess |
|---|---:|---:|---:|---:|
| CPI | 29 | 36.87 | 17.81 | **+19.06** |
| Employment Situation | 28 | 35.66 | 18.68 | **+16.98** |

### By year

| Year | Events | Excess |
|---|---:|---:|
| 2023 | 11 | +17.11 bp |
| 2024 | 24 | +22.09 bp |
| 2025 | 22 | +14.09 bp |

Every leave-one-family-out result remained positive: +16.32 to +21.19 bp. The
five largest positive events contributed 30.10% of total positive excess,
below the locked 60% concentration limit.

## Forecast comparisons

Forecasts use only prior events after a fixed 12-event warm-up. Target is the
family-balanced absolute event move, not direction.

| Forecast | MAE | Correlation |
|---|---:|---:|
| Price-only matched controls | 20.54 bp | −0.007 |
| Expanding release-type mean | 19.66 bp | −0.115 |
| Expanding Ridge | **19.51 bp** | +0.061 |

The fixed Ridge uses control mean, CPI indicator, prior-day VIX, and CPI×VIX.
It passed the locked MAE gate but its correlation is economically weak; this is
not evidence of a high-quality event-by-event forecast.

## Gates and QA

Seven of eight gates passed. The sole failure was 57 eligible events versus the
required 60. Tests passed for positive aggregate excess, both release types,
all years, every family exclusion, concentration, and forecast MAE.

- Actual recovered-panel SHA-256:
  `18133cc85f5d75263086c83584276a8128d79daa2e9eeb8efdb873944eef117c`.
- The panel has 222,048 rows and ends 2025-12-19 17:15 UTC.
- This hash does not match the older Drive manifest and is explicitly treated
  as a recovered partial panel.
- Three unit tests and Python compilation passed.
- Two complete runs produced byte-identical output artifacts.
- Official BLS HTML, panel, VIX, and outputs are covered by SHA-256 manifests.

## Costs, cadence and interpretation

This is not a strategy. Round trips = 0, trade legs = 0, turnover = 0, and P&L
at 0×/1×/2×/4× the four-pip assumption is identically zero. The result supports
using CPI and employment releases as an intraday risk-control flag. It does not
support a directional position, production model, capacity claim, or alpha.

## Next action

Acquire the manifest-matching full panel or independently rebuild the early
2023 source clock to recover at least three more eligible events without
filling missing prices. Then rerun the unchanged Research 052 specification.
Directional BLS trading remains rejected unless timestamped consensus-surprise
data becomes available.
