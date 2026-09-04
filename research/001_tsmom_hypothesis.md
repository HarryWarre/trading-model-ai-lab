# Research 001 — Time-Series Momentum as a Cross-Asset State Model

## Status

Hypothesis design and literature review. No market-valid performance claim yet.

## Literature

Moskowitz, Ooi and Pedersen (2012) document time-series momentum across 58 liquid equity-index, currency, commodity and bond futures, with persistence over 1–12 months and partial reversal at longer horizons. The proposed interpretation is delayed reaction/under-reaction followed by over-reaction.

The project will treat this as a replication target, not as proof that the effect survives modern CFD execution costs. The intraday-to-swing extension is an empirical question.

## Economic mechanism

Information may diffuse gradually, while heterogeneous participants and risk-management flows create persistence. The model should therefore predict continuation conditional on a sufficiently persistent directional state, while reducing exposure when volatility and reversal risk rise.

## Falsifiable hypotheses

H1: A signed, volatility-normalized trend state predicts positive next-horizon excess returns across multiple asset classes after realistic costs.

H2: The effect is stronger when directional persistence is high and weaker during rapid reversal/high-volatility transitions.

H3: Portfolio-level volatility targeting improves comparability but may create timing/left-tail effects; a volatility floor and exposure cap must be tested rather than assumed beneficial.

H4: Any apparent edge at a single timeframe or asset is insufficient; the effect must survive adjacent timeframes, subperiods, cost shocks and leave-one-asset-class-out tests.

## Model specification

For asset i and horizon h:

1. Compute log return r(i,t,h) = log(P(i,t) / P(i,t-h)).
2. Estimate ex-ante volatility sigma(i,t) from an expanding/rolling window ending at t.
3. Define the directional state s(i,t) = sign(r(i,t,h)) only when |r(i,t,h)| / sigma(i,t) exceeds a pre-registered threshold; otherwise s(i,t)=0.
4. Raw exposure e(i,t) = s(i,t) / max(sigma(i,t), sigma_floor).
5. Normalize across assets to a portfolio risk target using a covariance estimator fitted only on data available at t.
6. Execute at t+1 with bid/ask, slippage, commission, funding and rollover costs.

The first implementation should compare h in {4h, 1d, 3d, 5d, 10d, 20d} and several volatility estimators, with parameters selected on training data only.

## Identification and validation

- Point-in-time continuous futures with explicit contract rolls.
- Separate signal timeframe from execution timeframe.
- Purged walk-forward splits with embargo at least equal to the forecast horizon.
- Pre-register the parameter grid before viewing OOS results.
- Report pooled, per-asset, per-class and leave-one-class-out results.
- Include placebo tests using sign-shuffled or time-block-shuffled returns.
- Report net returns under base, conservative and stress costs.

## Required data

- Intraday trades/quotes or OHLCV with bid/ask proxy.
- Individual futures contracts, expiry, volume, open interest and roll calendar.
- Contract multiplier, tick size, currency and settlement.
- Broker CFD symbol mapping, spread, funding, margin and trading sessions.
- Risk-free/funding reference rates where required.

## Success gate

Proceed only if the model shows a positive and economically meaningful OOS contribution after costs, with stable behavior across timeframes and asset classes. Otherwise document the failure and revise the economic mechanism rather than optimizing parameters.

## Primary references

- Moskowitz, Ooi & Pedersen (2012): https://www.sciencedirect.com/science/article/pii/S0304405X11002613
- Working paper: https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- AQR updated factor data: https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Factors-Monthly
- Fan, Li & Liu (2018), risk-adjusted momentum comparison: https://mpra.ub.uni-muenchen.de/83510/1/MPRA_paper_83510.pdf
