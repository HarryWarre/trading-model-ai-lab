# Research 016 — selection-adjusted reality check

## Outcome

The apparent advantage of adjustment speed 0.10 in Research 015 is not
statistically distinguishable from selecting the best of three alternatives by
chance. The global null that no partial speed improves on full adjustment is
not rejected at any preregistered stationary-bootstrap block length.

## Why this test is needed

Research 015 reported all speeds, but speed 0.10 had the highest 2020 net
return. Treating that maximum as an ordinary single-model result would ignore
that three partial speeds were compared. White's Reality Check addresses
repeated model search; Hansen's SPA framework motivates studentizing performance
differences; Politis and Romano's stationary bootstrap retains serial dependence.

- White (2000), *A Reality Check for Data Snooping*:
  https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152
- Hansen (2005), *A Test for Superior Predictive Ability*:
  https://www.tandfonline.com/doi/abs/10.1198/073500105000000063
- Politis and Romano (1994), *The Stationary Bootstrap*:
  https://www.tandfonline.com/doi/abs/10.1080/01621459.1994.10476870

## Preregistered statistic

At 2x observed FXCM spread, for each partial speed `m` in `{0.50, 0.25,
0.10}`:

`d(m,t) = net_return(m,t) - net_return(full,t)`

The test statistic is:

`max_m sqrt(T) * mean(d_m) / sd(d_m)`

The null distribution is generated from centered paired differentials. Every
model uses the same stationary-bootstrap index path, preserving cross-model
dependence. The design uses 5,000 resamples, seed 20260904, primary expected
block length 10 sessions, and sensitivity lengths 5 and 20.

The global null could be rejected only if the one-sided selection-adjusted
p-value was below 0.05 for all three block lengths.

## Results

| Expected block | Observed max t | Adjusted p-value | Reject 5% |
|---:|---:|---:|:---:|
| 5 | 0.359 | 0.5001 | No |
| 10 | 0.359 | 0.4883 | No |
| 20 | 0.359 | 0.4717 | No |

At the primary 10-session block length, annualized paired mean-log-return
differences and 95% bootstrap intervals are:

| Partial speed | Mean difference | 95% interval |
|---:|---:|---:|
| 0.50 | -0.83% | [-3.41%, +1.59%] |
| 0.25 | -1.02% | [-5.62%, +3.35%] |
| 0.10 | +1.17% | [-4.77%, +7.10%] |

All intervals cross zero. Speed 0.10 has a positive point estimate but low
studentized evidence (`t = 0.359`) and a wide uncertainty interval.

## QA

- Daily net return paths exactly reconcile to every 2x-spread total return in
  Research 015 to numerical tolerance `1e-12`.
- Stationary-bootstrap paths are circular, bounded and deterministic by seed.
- Three block lengths, three models and all numeric outputs are complete and
  finite.
- An initial QA run caught invalid annualization caused by applying the
  pre-holdout estimator to the already sliced 2020 panel. The final code derives
  308 sessions/year only from the full archive's 2017–2019 rows.

## Interpretation and limitations

The result does not prove that speed 0.10 has no economic value. It shows that
the one-year sample cannot distinguish its selected advantage from noise after
accounting for the three-speed search.

- There are only 305 paired daily observations from one crisis year.
- The model set includes only three partial speeds; prior research choices are
  not fully captured by this local correction.
- Stationary bootstrap assumes the holdout series is sufficiently stationary,
  an imperfect approximation across the 2020 shock.
- Financing and unobserved slippage remain outside the PnL.

## Decision

Do not promote speed 0.10 and do not tune another speed on 2020. Partial
adjustment remains a cost-control component. A future speed must be locked
before acquiring a genuinely new post-2020 broker holdout.

## Reproduction

`python real_fxcm_reality_check.py`

Outputs:

- `real_fxcm_reality_check_global.csv`
- `real_fxcm_reality_check_models.csv`
- `real_fxcm_reality_check_decision.csv`

QA tests are in `test_real_fxcm_reality_check.py`.
