# Research 058 — joint multiple-testing audit of BLS event-risk findings

Preregistered before joining outcomes in [GitHub issue #75](https://github.com/HarryWarre/trading-model-ai-lab/issues/75). Completed 2026-09-30.

## Decision

**All 8/8 preregistered gates pass, but the result is non-directional event-risk evidence only. It is not alpha, a trading strategy, or approval for production.**

The three previously reported BLS risk findings all survive 5% family-wise error control on their exact 51-event common intersection. This materially reduces the concern that the Research 052, 056 and 057 conclusions are isolated false positives created by repeatedly testing overlapping BLS samples. It does not resolve the absence of a timestamp-verifiable point-in-time consensus-surprise input, and it does not create a directional forecast.

## Economic/statistical mechanism and primary source

Repeatedly testing related hypotheses on the same or overlapping observations raises the chance of at least one false rejection. Romano and Wolf's studentized stepdown method controls the family-wise error rate while using the joint dependence structure of the statistics rather than treating them as independent.

- Romano, J. P. and Wolf, M. (2005), “Stepwise Multiple Testing as Formalized Data Snooping,” *Econometrica* 73(4), 1237–1282: https://doi.org/10.1111/j.1468-0262.2005.00615.x
- Stanford technical report: https://statistics.stanford.edu/technical-reports/stepwise-multiple-testing-formalized-data-snooping

## Frozen family and model

The family was fixed to three one-sided event-level hypotheses before their outcomes were joined:

1. Research 052 full T−5/T+30 family-balanced event-minus-control jump, `excess_bps`;
2. Research 056 timing-safe cross-family co-jump `breadth_difference`;
3. Research 057 delayed T+5/T+30 family-balanced event-minus-control jump, `delayed_excess_bps`.

For common event t and hypothesis j,

\[
T_j = \frac{\bar{x}_j}{s_j/\sqrt{n}}, \qquad H_{0,j}: E[x_j] \le 0.
\]

The primary inference uses 100,000 deterministic shared-sign wild randomizations with seed 20260930. Adjacent chronological two-event blocks receive one Rademacher sign per draw, and the same signs are applied to all three outcome columns. Romano–Wolf stepdown max-T one-sided p-values are primary; Holm-adjusted shared-sign p-values are the conservative sensitivity check.

This construction assumes sign symmetry of the paired event-minus-control outcomes under the null. Two-event blocks address short serial dependence, but 51 events remain a modest sample and do not substitute for an independent later holdout.

## Frozen inputs and coverage

Only the committed event-level outputs were read; no price outcome was recomputed and no missing event was imputed.

| Input | Events before join | SHA-256 |
|---|---:|---|
| Research 052 event portfolio | 57 | `5200c598f11ec4e927ca70aa60a4ad0d39ae84e67b8310b481f709da4a82edd0` |
| Research 056 timing-safe co-jumps | 51 | `4edebf1717ffe58309503973ba12f5a7bc6a42c0fb664fb4f1b2682cf9ef905e` |
| Research 057 delayed risk | 54 | `4403c5055f91fb823348768abbf6e174068e754f87b4eed3e8cd15ad6c28d921` |

The exact intersection contains 51 events across 2023–2025. Nine source memberships are excluded and exported: six Research 052-only memberships and three Research 057-only memberships absent from Research 056's stricter timing-safe coverage. The Research 056 event set is therefore the binding intersection.

## Results

| Frozen hypothesis | Common-sample mean | Positive events | t statistic | Raw p | Romano–Wolf p | Holm p | Top-five positive share |
|---|---:|---:|---:|---:|---:|---:|---:|
| R052 full-window jump | +19.0252 bp | 40/51 | 6.0656 | 0.000010 | **0.000010** | 0.000030 | 32.01% |
| R056 co-jump breadth | +33.3333 pp | 41/51 | 8.0715 | 0.000010 | **0.000010** | 0.000030 | 22.65% |
| R057 delayed jump | +7.8286 bp | 40/51 | 5.0804 | 0.000030 | **0.000030** | 0.000030 | 31.76% |

The minimum attainable Monte Carlo p-value is 1 / 100,001. The outcomes are materially dependent, which confirms the value of a joint resampling audit: Pearson correlations are +0.7572 between full-window jump and co-jump breadth, +0.3885 between full-window and delayed jump, and +0.2465 between co-jump breadth and delayed jump.

### Leave-one-year-out means

| Omitted year | R052 full-window (bp) | R056 breadth (pp) | R057 delayed (bp) |
|---|---:|---:|---:|
| 2023 | +18.2617 | +33.0163 | +8.0603 |
| 2024 | +16.3048 | +35.4167 | +5.9151 |
| 2025 | +22.7692 | +31.8966 | +9.2426 |

All nine leave-one-year-out means are positive. The five largest positive events contribute 22.65%–32.01%, comfortably below the frozen 60% concentration limit.

## Gate audit

| Gate | Result |
|---|---|
| ≥45 common events and all 2023–2025 years | Pass — 51 events, all three years |
| All three means positive | Pass |
| All Romano–Wolf p-values <0.05 | Pass — maximum 0.000030 |
| All Holm p-values <0.05 | Pass — all 0.000030 |
| Every leave-one-year-out mean positive | Pass — 9/9 |
| Every top-five concentration <60% | Pass — maximum 32.01% |
| Prior hashes match and exclusions exported | Pass |
| Tests, compile and byte-identical rerun | Pass — 6 tests; all artifacts identical |

## Trading, costs and baselines

This audit does not place trades. Positions, round trips, legs, turnover and capacity usage are all zero. P&L is exactly zero at 0×, 1× (4 pip), 2× and 4× costs. The price-only, simple economic and linear forecast comparators remain frozen and reported in Research 052/056/057; none was re-fit or reselected here.

## QA and reproducibility

- All three input hashes match their prior manifests; manifest hashes are also recorded.
- Exact event IDs and all exclusions are exported.
- Six unit tests cover shared block signs, studentization failure, Holm monotonicity, Romano–Wolf dominance over marginal p-values, concentration, and the complete hash-validated run.
- Python compilation passes.
- Two independent 100,000-draw runs generate byte-identical artifacts.
- Earlier result directories are unchanged.

## Limitations and next action

The evidence supports a risk-control conclusion: CPI and Employment Situation releases produce unusually large, broad and persistent cross-asset movement. It still supplies no signed surprise, no directional edge and no production signal. The sample is reused research data, not an untouched later holdout.

The highest-value next action is to obtain either (a) a timestamp-verifiable point-in-time historical consensus archive for CPI and payroll surprises, or (b) a hash-verified 2026/independent later M1 panel. Until then, do not create another BLS window/threshold variation and do not tune the 5- or 30-minute boundaries.
