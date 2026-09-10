# Research 038 — leakage-resistant residual intraday CFD model

Status: **rejected / exploratory only**. The 2024 panel has already been used by the lab, so this is not an untouched confirmation test.

## Question and mechanism

Research 037 mixed CFDs with very different volatility and common family exposure. It also began trading with less than one day of training history and allowed the final one-hour target of some training rows to cross the decision time. Research 038 asks whether a correctly purged model can rank *asset-specific* next-hour moves after removing the simultaneous FX, equity-index, or commodity family move.

Heston, Korajczyk and Sadka find cross-sectional continuation at recurring intraday clock times, while sub-hour reversals can reflect temporary liquidity imbalance. Gu, Kelly and Xiu show why nonlinear interactions among momentum and volatility variables can matter for expected-return measurement. Moreira and Muir motivate scaling risk down when volatility is high.

Primary sources:

- Heston, Korajczyk & Sadka, *Intraday Patterns in the Cross-section of Stock Returns*: https://arxiv.org/abs/1005.3535
- Gu, Kelly & Xiu, *Empirical Asset Pricing via Machine Learning*: https://www.nber.org/papers/w25398
- Moreira & Muir, *Volatility-Managed Portfolios*: https://www.nber.org/papers/w22208

## Frozen model

For asset `i` at decision `t`, the target is

`y(i,t) = [r(i,t+5m→t+65m) - median_family(r(t+5m→t+65m))] / [sigma(i,t) sqrt(12)]`.

Inputs are volatility-scaled 5-, 30-, and 120-minute returns; the return at the same clock time one day earlier; 60- and 120-minute volatility; lagged family return; market breadth and dispersion; time of day; and prior-day VIX level/change. The nonlinear model is a fixed shallow histogram gradient booster. Ridge and price-only Ridge are fixed baselines.

The model waits for 60 completed weekdays, removes all training observations whose target has not ended before the decision, refits every 21 weekdays, and uses only data available at the decision. Each portfolio holds one long and one short in each of FX, equity indices, and commodities, with inverse-volatility weights and gross exposure 1x. It abstains when prediction spread is below the expanding training median. Positions are closed before overnight or data gaps.

## Data

- 15 CFD proxies, five-minute UTC closes, 2024-01-01 to 2024-12-31.
- Price SHA-256: `6f8f6995527e429dc60fd9dc372bae21ad458698c88a70a46f3e46aa27c9f8ef`.
- VIX SHA-256: `6b2cd4028784f69ae160250c3c10dbce88150e125f5fdc18f0c8d43ae557d5a3`.
- BID-only closes; no ask, executable depth, broker volume, financing series, or measured slippage.

## Results

| Model | Gross return | Net return | Median rank correlation | Bootstrap P(net mean > 0) |
|---|---:|---:|---:|---:|
| Nonlinear multi-input | -0.90% | -23.19% | -0.0072 | 0.0% |
| Ridge multi-input | -1.24% | -24.45% | -0.0022 | 0.0% |
| Price-only Ridge | -1.09% | -24.07% | -0.0107 | 0.0% |

Nonlinear cost stress: 0x `-0.90%`, 1x `-23.19%`, 2x `-40.46%`, 4x `-64.23%`. Both half-samples are negative at main cost (`-13.54%` and `-11.16%`). All ten evaluated months are negative after cost. All 15 asset leave-one-out portfolios are negative, ranging from `-23.65%` to `-17.46%`. FX, equity-index, and commodity contributions are all negative.

The nonlinear model's annualized mean is 3.56 percentage points above Ridge and 2.49 points above price-only, but paired stationary-bootstrap probabilities are only 70.5% and 65.1%; both 95% intervals cross zero. These are not reliable wins.

## Trading cadence and capacity

There are 1,881 evaluated hourly decision slots after the 60-day warm-up. The source supplies 9.41 usable slots per active day on average. The model changes positions on 76.4% of evaluated slots, about 7.2 portfolio rebalances per active day; six names change at the median rebalance. Mean one-way turnover is about 0.92 per evaluated slot after including day-end liquidation.

Live capacity cannot be quantified: BID closes provide no ask, depth, executable volume, ADV, or slippage curve. High turnover makes this missing information especially important.

## Decision

The preregistered hypothesis fails every core return criterion. Residualization and volatility comparability reduce the gross loss relative to Research 037, but the median rank correlation remains approximately zero. The central problem is therefore weak ranking information, not merely model complexity. No asset, hour, month, or inverted signal is selected after seeing the result.

The next clean confirmation requires a new time period and richer execution inputs. Any future model should first demonstrate positive, stable rank information before paying to trade it.
