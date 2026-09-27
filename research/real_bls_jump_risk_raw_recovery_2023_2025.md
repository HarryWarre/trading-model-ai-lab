# Research 053/054 — raw-M1 recovery audit for BLS jump risk

## Decision

Research 053 failed closed before performance calculation because 14 of the 15
raw 2023 HistData M1 files contain duplicate timestamps. Its strict gate
prohibited any duplicate, so issue #70 is a completed source-audit failure.

Research 054 was separately preregistered in issue #71 before any event result
was computed. It allowed only full-row-identical duplicates to be collapsed.
All 839 duplicated timestamps (1,678 rows) had identical OHLCV values; there
were zero conflicting duplicates. Nevertheless, direct reconstruction added
**zero** missing panel cells. The 925,143 raw/panel overlapping closes agreed
exactly. The 57-event Research 052 result therefore remains unchanged and the
locked 60-event coverage gate still fails.

Research 054 passes seven of eight preregistered gates. It is **research-only
evidence of announcement-time jump risk, not alpha or a trading strategy**.

## Mechanism and falsifiable hypothesis

Andersen, Bollerslev, Diebold and Vega (2003) document discrete price discovery
and volatility around scheduled macroeconomic announcements. Research 052
found larger unsigned moves around official CPI and Employment Situation
releases than matched ordinary-time controls, but only 57 events met the frozen
coverage rule. Research 053/054 tested whether the missing early-2023 coverage
was caused by a prepared-panel defect.

The falsifiable data hypothesis was that reconstruction from the original M1
files would add enough exact bars to produce at least 60 eligible events. It
was rejected: no missing cell could be recovered from those source files.

Primary paper: <https://doi.org/10.1257/000282803321455151>

Official event calendars:

- <https://www.bls.gov/schedule/2023/home.htm>
- <https://www.bls.gov/schedule/2024/home.htm>
- <https://www.bls.gov/schedule/2025/home.htm>

## Frozen reconstruction

- Fifteen raw 2023 M1 CSV files were downloaded from the connected research
  folder and individually SHA-256 locked.
- Schema: `YYYYMMDD HHMMSS;open;high;low;close;volume`.
- Source clock: documented fixed EST, converted to UTC by adding five hours.
- Five-minute bars: last M1 close, `closed=right`, `label=right`.
- Existing non-null panel values could not be replaced.
- Only exact missing timestamps/cells could be added.
- No nearest quote, interpolation, forward fill or synthetic price.
- The Research 052 event window, controls, aggregation, models, bootstrap and
  thresholds were unchanged.

## Source QA

| Check | Result |
|---|---:|
| Raw files | 15 |
| Raw M1 rows after duplicate collapse | 4,508,996 |
| Duplicate rows collapsed | 1,678 |
| Duplicate timestamps collapsed | 839 |
| Conflicting duplicate timestamps | 0 |
| Raw/panel overlapping closes | 925,143 |
| Exact agreement | 100.0000% |
| Cells added to panel | 0 |
| Original panel rows | 222,048 |
| Reconstructed panel rows | 222,048 |

GRXEUR contained no duplicate timestamps. Fourteen other assets contained a
single repeated block on 2023-10-29: 60 timestamps per asset, except USDCAD
with 59. The duplicate rows were identical, so the Research 054 policy could
collapse them deterministically. Research 053 did not permit this and remains
failed rather than being retroactively amended.

The rebuilt CSV has a different byte hash because timestamps were serialized
in a normalized format, but no cell value or row was added or replaced.

## Unchanged Research 052 results

| Statistic | Result |
|---|---:|
| Official releases | 70 |
| Eligible events | 57 |
| Mean event jump | 36.2754 bp |
| Mean matched-control jump | 18.2368 bp |
| Mean excess | **+18.0386 bp** |
| Bootstrap P(mean excess > 0) | 100.00% |
| 95% interval | [+12.8611, +23.8426] bp |
| Positive events | 45/57 |
| Top-five positive-excess share | 30.0969% |

Category excess remains +19.0584 bp for CPI and +16.9824 bp for employment.
Annual excess remains +17.1059 bp in 2023, +22.0857 bp in 2024 and +14.0900
bp in 2025. Every leave-one-family-out result is positive; the minimum is
+16.3206 bp.

## Forecast comparators

The 45 post-warm-up events are unchanged:

| Comparator | MAE | Correlation |
|---|---:|---:|
| Price-only matched-control mean | 20.5371 bp | -0.0066 |
| Simple economic event-type mean | 19.6602 bp | -0.1145 |
| Expanding Ridge | 19.5110 bp | +0.0608 |

Ridge passes the relative-MAE gate but its correlation is weak. This does not
support a directional forecast or trade.

## Gates and trading interpretation

Seven of eight Research 054 gates pass. The only failure is unchanged:
57 eligible events are below the frozen minimum of 60. Thirteen 2023 releases
remain ineligible, primarily because exact event/control coverage is
insufficient; January and early-February controls also require 2022 data not in
the frozen source set.

The study takes no positions. Round trips, trade legs, turnover and P&L are
zero under 0x, 1x (four-pip), 2x and 4x costs. Capacity is not applicable.

## Reproducibility

- Eight direct unit tests pass.
- Python compilation passes.
- Two complete Research 054 runs produce fourteen byte-identical artifacts.
- Summary SHA-256:
  `b677b84ea615f41cb62217385a00b6e70f9731bbee18885a17fa743273b38b63`.
- Output manifest SHA-256:
  `d074e3c2bd8e7a550956c9856bf7ffa53e1ae2c9b02f820ec629d5daf042292f`.

## Next action

Do not tune the event window or reduce the coverage threshold. A valid coverage
extension requires hash-verified 2022 M1 data and/or an independently sourced
later period, followed by another frozen confirmation. Research 052/054 may be
used for event-risk limits but not for directional trading or alpha claims.
