# Research 032 — nonlinear forecast skill audit

## Question and method

Research 031 lost money. This locked audit asks whether transaction costs and portfolio construction hid a useful forecast, or whether the forecast itself failed. Following the prediction-first evaluation logic in Gu, Kelly and Xiu (RFS 2020), every stored five-session currency forecast is compared with its subsequently realized excess return. The Research 031 model is not refit or changed.

Metrics were registered in issue #45: pooled out-of-sample R2 versus an expanding historical-mean forecast, cross-sectional Spearman rank correlation, realized return of the predicted winner minus predicted loser, annual splits and a fixed-seed stationary bootstrap.

## Results

There are 292 currency forecasts across 73 decisions. Pooled OOS R2 is +3.37%, so the model reduces aggregate squared forecast error modestly. That result does not translate into useful rankings: median decision rank correlation is 0.000, mean realized winner-minus-loser return is -0.150% per five-session decision, and bootstrap P(mean spread > 0) is 17.6% using 1,000 samples with expected block length 10.

Both annual spreads are negative: -0.293% per decision in 2024 and -0.088% in 2025. Median rank correlation is -0.258 in 2024 and 0.000 in 2025.

## Decision

The all-pass forecast-skill hypothesis is rejected. The model shows a small pooled error improvement but fails the economically necessary cross-sectional ranking task. Research 031's loss therefore cannot be attributed only to trading costs. No post-hoc feature, currency or regime selection is made.

The four-currency, two-year reused sample remains small, and the 1,000-draw bootstrap is a disclosed worker-limit reduction from the preferred 5,000 draws. This diagnostic makes no capacity claim.
