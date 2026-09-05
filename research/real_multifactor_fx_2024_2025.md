# Research 030 — multi-input FX panel forecast

## Mechanism and preregistration

The experiment asks whether four economically distinct inputs jointly forecast currency returns better than price momentum alone: 21-session momentum, corrected m+3 interest-rate differentials, lagged 60-month BIS REER value, and lagged VIX stress interactions. A pooled expanding-window ridge model with fixed penalty 10 and currency fixed effects predicts the next five-session currency excess return. Features are standardized only on past training data. The top prediction receives +0.5 and the bottom -0.5 from the next session for five sessions.

The design was registered in issue #43 before complete P&L. HistData 2024–2025 is a reused research sample, not an untouched holdout. Synthetic transaction cost is 4.4 pip on entry and exit.

## Results

The full model produced -7.53% net return, annualized mean -5.40%, Sharpe -1.188, and maximum drawdown -12.17% over 365 active sessions. Fixed-seed stationary bootstrap with 1,000 draws gave P(mean > 0) = 8.3%. The paired probability that the full model beats the locked price-only baseline was 49.9%, providing no evidence of improvement.

Both calendar slices were negative: 2024 -6.45% and 2025 -1.15%. Low-VIX sessions lost 11.62%; high-VIX sessions gained 4.64%, but the latter contains only 44 sessions and is descriptive. No post-hoc VIX gate is created.

## Decision and limitations

The preregistered hypothesis is rejected. More inputs and a more complex estimator did not create a robust edge. The result does not show that macro data are useless; it shows that this exact data timing, feature definition, linear interaction model, and four-currency sample failed.

The sample has only four currencies and two previously used years. Prices are BID-only; rates are theoretical, macro series are current-history, and broker swaps, ask prices, depth and ADV are absent. Capacity cannot be quantified. The worker limit required 1,000 rather than 5,000 bootstrap draws, which is disclosed and fixed-seed reproducible.
