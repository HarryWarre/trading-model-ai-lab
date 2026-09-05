# Research 027 — conservative monthly-rate availability audit

## Decision

The prior documentation overstated the lag implemented in Research 023.
`MonthBegin(2)` maps a January observation to March 1, so only February has
fully elapsed. The conservative implementation required by the stated
two-full-calendar-month rule is `MonthBegin(3)`, mapping January to April 1.

Re-running all affected models with m+3 changes returns only slightly and does
not change any research decision. Research 023, 025 and 026 remain rejected.

## Why observation dates are insufficient

FRED's ordinary CSV is current-history data. FRED documents vintage dates and
real-time periods separately for retrieving observations as they existed at a
historical date:

- https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- https://fred.stlouisfed.org/docs/api/fred/

The five OECD interbank-rate series are monthly reference-period observations.
For example, the US series is described here:

- https://fred.stlouisfed.org/series/IR3TIB01USM156N

Without vintage snapshots or exact release timestamps, shifting by m+3 is a
conservative approximation. It does not prove the true publication date, but
it enforces the stated requirement that two entire calendar months pass.

## Economic mechanism and frozen audit

The carry mechanism remains the interest-differential/UIP risk premium in
Lustig, Roussanov and Verdelhan and Burnside et al. No economic or trading
parameter changes. The audit only changes rate availability:

\[
\text{old effective date}(m)=m+2\text{ month begins},\qquad
\text{corrected effective date}(m)=m+3\text{ month begins}.
\]

Prices, sessions, positions, costs, REER horizon, currency ranks, leave-one-out
rules and bootstrap settings remain fixed. The affected tests are:

- Research 023 carry on 2025;
- Research 025 REER value on 2025, where rates affect carry accrual only;
- Research 026 REER value on 2024, where rates affect carry accrual only.

## Return impact

| Model | Historical m+2 | Corrected m+3 | Difference | Corrected Sharpe |
|---|---:|---:|---:|---:|
| Carry 2025 | -3.7847% | -3.7570% | +0.0277 pp | -0.472 |
| REER value 2025 | +0.9789% | +0.9698% | -0.0090 pp | 0.259 |
| REER value 2024 | -7.4249% | -7.4528% | -0.0279 pp | -1.984 |

All daily returns change slightly because theoretical carry accrues every day,
but the maximum absolute daily change is only 0.22 basis points. Carry targets
change on 0 of 259 target rows; rate ordering is unchanged.

## Corrected locked decisions

| Model | Net positive | Positive leave-one-out | Bootstrap P(mean > 0) | 2x cost positive | Supported |
|---|:---:|---:|---:|:---:|:---:|
| Carry 2025 | no | 0/4 | 30.04% | n/a | **no** |
| REER value 2025 | yes | 2/4 | 61.44% | yes | **no** |
| REER value 2024 | no | 0/4 | 4.98% | no | **no** |

No corrected model meets its original support criteria. The correction cannot
promote a model because the macro inputs remain non-vintage.

## QA

- A synthetic January observation is first available in April under m+3.
- The corrected score panel equals the old values shifted exactly one calendar
  month.
- Both 2024 and 2025 price samples have complete corrected rate coverage.
- Four tests pass.
- Independent result assertions pass.
- A deterministic rerun reproduces the aggregate CSV checksum.

## Cost, regime and capacity interpretation

The correction does not alter spot returns or transaction costs. It changes
only the rate used for theoretical daily financing and, potentially, carry
ranking; the latter did not change in these samples. Existing cost, regime and
capacity conclusions therefore remain intact.

Capacity is still unquantifiable because HistData lacks ask, broker swap, order
book, depth and CFD ADV. The m+3 interbank-rate accrual is still not a broker
swap quote.

## Conclusion

Research 023's wording should be read as corrected by this audit: its published
m+2 result used one complete intervening month, while m+3 implements two full
calendar months. The numerical error is immaterial here, but recording it is
necessary for leakage-resistant reproducibility. All three affected model
decisions remain rejected.
