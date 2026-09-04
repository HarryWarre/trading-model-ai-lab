# Research 001 — Replication protocol

## Stage A: academic benchmark

Replicate the published monthly TSMOM construction before testing any intraday extension.

For instrument s at month t:

`TSMOM_return(s,t+1) = sign(r(s,t-12:t)) * (target_vol / sigma(s,t)) * r(s,t:t+1)`

where the signal uses the instrument's own trailing 12-month excess return, `sigma` is an ex-ante volatility estimate, and target volatility is pre-registered. Aggregate instruments within asset class and then across classes using equal risk or equal weight variants.

## Stage B: attribution

Decompose futures total return into:

`futures return = spot return + roll yield + residual pricing/settlement effects`

Report TSMOM performance separately for the spot-like component, roll component and total return. This prevents a signal from being credited to information diffusion when it is actually driven by futures curve shape or hedging pressure.

## Stage C: intraday-to-swing extension

Only after Stage A passes, test horizons `{4h, 1d, 3d, 5d, 10d, 20d}`. Keep the model family fixed and vary only the sampling/forecast horizon according to a pre-registered grid.

Required comparisons:

- raw directional state vs volatility-normalized state
- constant volatility scaling vs dynamic scaling
- independent asset scaling vs covariance-aware portfolio scaling
- with and without volatility floor
- with and without regime filter

## Statistical tests

- Mean return and Newey-West t-statistic for overlapping returns.
- Block bootstrap confidence intervals.
- Reality-check or multiple-testing adjustment across the pre-registered grid.
- Placebo labels from time-block permutation.
- Cross-asset correlation and leave-one-class-out tests.
- Subperiod results including crisis, recovery and low-volatility periods.

## Execution tests

- One-bar execution lag.
- Bid/ask and slippage scenarios.
- Funding and rollover by effective date.
- Contract multiplier, tick size and currency conversion.
- Capacity proxy using volume/open interest and participation limits.

## Failure criteria

Reject the hypothesis for deployment if the result disappears after costs, exists only in one asset class, depends on one parameter point, fails placebo controls, or collapses under adjacent timeframes and leave-one-class-out tests.
