# Research 050 — USMPD policy/information-shock identification audit

## Decision

**The broad 1994–2026 identification claim fails one preregistered data gate.**
The fixed classifier is strongly identified wherever its ten-contract input is
available, including all six 2026 meetings, but scheduled-event coverage is
88.89%, below the locked 90% requirement. The shortfall is concentrated in the
early sample: 1994–1996 have no row with the required eight contracts and 1997
has only three.

This is a mechanism and data-availability audit. It calculates no CFD return,
Sharpe ratio or trading P&L and cannot establish alpha.

## Research mechanism

Jarociński and Karadi (2020) distinguish conventional monetary-policy shocks
from central-bank information shocks using joint high-frequency rate and equity
responses. Acosta et al. (2025) provide the official US Monetary Policy
Event-Study Database (USMPD) and event-window definitions.

The Research 048/049 economic rule uses the same idea:

- rate and S&P futures moves with opposite signs: conventional policy shock;
- rate and S&P futures moves with the same sign: information shock;
- missing or zero products: unclassified.

Primary sources:

- Jarociński and Karadi (2020), *Deconstructing Monetary Policy Surprises*:
  https://doi.org/10.1257/mac.20180090
- Acosta et al. (2025), *Financial Market Effects of FOMC Communication*:
  https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf
- Official SF Fed USMPD:
  https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/

## Frozen model and data

For statement event t:

`q_t = mean(FF1..FF6, ED1..ED4)` when at least eight contracts exist.

`s_t = SPFUT / 100`, and `c_t = q_t * s_t`.

- `c_t < 0`: conventional;
- `c_t > 0`: information;
- otherwise unclassified.

The official workbook was updated 17 September 2026 and is locked at SHA-256
`f02bfcbf80cf597548d4fccb5a80b30cb1f4373a7d50e26fd1def097d43df1aa`.
No PCA, threshold search, event deletion or revised sign rule was used.

## Results

The workbook contains 279 statement rows: 261 scheduled and 18 unscheduled.
Among scheduled meetings, 232/261 have valid q and S&P futures inputs; three
valid zero-product rows remain unclassified. The 229 classified rows contain:

- 148 conventional shocks;
- 81 information shocks;
- conventional share **64.63%**;
- exact one-sided binomial p-value **0.00000564** against a 50% share.

| Regime | Rows | Valid | Coverage | Conventional share | Median q×S&P product |
|---|---:|---:|---:|---:|---:|
| 1994–2007 | 112 | 83 | 74.11% | 65.85% | −0.000022 |
| 2008–2019 | 96 | 96 | 100.00% | 67.02% | −0.000007 |
| 2020–2026 | 53 | 53 | 100.00% | 58.49% | −0.000004 |

The leave-one-year-out conventional majority remains true after excluding each
year separately.

## Untouched 2026 classification availability

All six 2026 scheduled meetings have ten rate contracts and valid S&P futures
responses:

| Date | Rate-path surprise | S&P futures | Classification |
|---|---:|---:|---|
| 2026-01-28 | +0.00350 | −0.0179% | Conventional |
| 2026-03-18 | −0.00525 | −0.0749% | Information |
| 2026-04-29 | +0.01225 | −0.1188% | Conventional |
| 2026-06-17 | +0.05750 | −0.3228% | Conventional |
| 2026-07-29 | −0.06300 | +0.1281% | Conventional |
| 2026-09-16 | +0.040625 | +0.0394% | Information |

Therefore a future frozen CFD confirmation would trade four meetings and
abstain on two. These labels are now fixed before any 2026 CFD return is seen.

## Preregistered gates

| Gate | Result |
|---|:---:|
| Scheduled coverage at least 90% | **Fail — 88.89%** |
| Overall conventional majority, exact p <= 0.05 | Pass |
| Every regime conventional share >=35% | Pass |
| Every regime median product negative | Pass |
| 2026 has >=2 conventional and >=4 valid events | Pass |
| Every leave-one-year-out sample keeps conventional majority | Pass |

The coverage gate is not relaxed after seeing the result. The correct inference
is narrower: the fixed ten-contract classifier is not available across the
entire 1994–2026 history, but it is fully available from 2008 onward and for all
six 2026 meetings.

## Reproducibility and acquisition status

- Three independent tests pass and Python compilation passes.
- Two complete runs produce seven byte-identical artifacts.
- Workbook, input manifest and every output are SHA-256 locked.
- Drive contains no `M1_2026` files.
- A public Dukascopy endpoint returned HTTP 200, but no file bytes completed in
  this runtime. The failed transfer was not treated as data.
- No synthetic price, nearest quote, interpolation or forward fill replaced the
  missing 2026 CFD panel.

## Next action

The 2026 labels and four tradable dates are now frozen. Acquire a comparable
intraday panel for those dates, validate source/session/timezone compatibility,
then run the unchanged Research 048/049 sign map and T+20/T+90 window. With only
four active meetings, report event-level results and leave-one-event-out; do not
claim production alpha even if all returns are positive.
