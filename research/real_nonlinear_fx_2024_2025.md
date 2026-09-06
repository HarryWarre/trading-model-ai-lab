# Research 031 — nonlinear multi-input FX forecast

## Mechanism

Gu, Kelly and Xiu (RFS 2020) show that nonlinear interactions can improve expected-return prediction in large equity panels. This experiment tests transfer to a much smaller four-currency CFD proxy panel. It is not a direct replication of their equity result.

The locked model is gradient boosting with 50 depth-2 trees, learning rate 0.05 and fixed seed. Inputs, five-session target, expanding training, one-session execution lag and synthetic 4.4-pip entry/exit cost are identical to Research 030. No parameter search was performed.

## Results

The nonlinear model returned -11.77% net over 365 active sessions, with annualized mean -8.64%, Sharpe -1.820 and maximum drawdown -13.94%. Fixed-seed stationary bootstrap with 1,000 samples gave P(mean > 0) = 2.8%.

Both years were negative: 2024 -4.15% and 2025 -7.94%. Relative to the locked Ridge model, the nonlinear model reduced annualized mean return by 3.24 percentage points. Paired bootstrap P(nonlinear beats Ridge) was 24.4%.

## Decision

The all-pass hypothesis is rejected by pooled return, both annual slices, bootstrap confidence and the paired comparison. Cost stress, phase offsets and leave-one-out refits are not used to rescue a model that already fails the primary gates. The nonlinear model is not a candidate.

## Limitations

This is a reused 2024–2025 sample with only four currencies. Tree methods are data-hungry, so the small panel is a severe limitation. HistData is BID-only; rates and costs are synthetic; broker swaps, ask prices, depth and ADV are unavailable. Capacity cannot be quantified. The worker limit required 1,000 instead of 5,000 bootstrap samples, disclosed here.
