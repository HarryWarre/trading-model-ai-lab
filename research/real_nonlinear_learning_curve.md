# Research 033 — nonlinear learning-curve audit

## Question

Research 031 used a flexible model on a small panel. This preregistered diagnostic tests whether its ranking quality improves mechanically as the expanding training set grows. It uses the immutable Research 032 predictions and does not refit the model, select a later start date or create a trading gate.

## Results

The first-half mean winner-minus-loser spread was -0.435% per five-session decision. The second half was +0.108%, an improvement of +0.544 percentage points. A fixed-seed stationary bootstrap assigned 99.5% probability to second-half improvement.

Chronological quartiles show spreads of -0.322%, -0.485%, +0.098% and +0.118%. Median rank correlations were -0.316, -0.258, +0.200 and 0.000. Thus the final quartile had a positive spread but did not satisfy the preregistered requirement for positive median rank correlation.

## Decision

The all-pass data-sufficiency explanation is rejected because final-quartile median rank correlation equals zero. There is meaningful partial evidence of learning: both later quartiles have positive spreads and the second half is statistically better than the first under this bootstrap. This evidence is diagnostic, not permission to discard the early sample or trade only after an observed warm-up.

The appropriate next test is a genuinely broader currency panel or a new untouched period, fixed before outcomes are observed. Continuing to increase model complexity on the same four currencies would not resolve identification.

The sample remains reused and small. Bootstrap uses 1,000 fixed-seed draws due worker limits. No liquidity, depth, broker-swap or capacity claim is made.
