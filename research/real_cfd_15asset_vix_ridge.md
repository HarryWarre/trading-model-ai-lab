# Research 034 — 15-asset VIX multi-input result

The expanded 15-asset panel was tested with an expanding Ridge forecast. At each five-day decision, the model used each asset's 20-day return, 20-day volatility, return/volatility ratio, five-day cross-asset breadth, VIX level, five-day VIX change, and the interaction between asset momentum and VIX change. The target was the next five-day log return. The model was fit only on earlier decisions.

Synthetic costs were unchanged from the fixed baseline: 4.4-pip equivalent for FX, 15 bp for gold/index assets, and 25 bp for silver/Brent.

| Model | Net return | Sharpe | Max drawdown | Bootstrap P(mean > 0) |
|---|---:|---:|---:|---:|
| Price-only | -18.98% | -2.383 | -19.81% | 0.2% |
| Risk-adjusted price | -13.37% | -2.022 | -13.69% | 0.9% |
| Ridge + VIX multi-input | -8.98% | -1.136 | -11.19% | 10.5% |

The multi-input model improved the point estimate by 4.39 percentage points versus the risk-adjusted baseline and reduced drawdown, but the result remained negative. It is not an alpha candidate. This is a preliminary 2024 test, not an untouched confirmation holdout. VIX came from FRED's VIXCLS daily series and was forward-filled only after aligning dates; no future value was used at the decision timestamp.

The next research step is to add time-available carry/rates and positioning inputs, then rerun against these fixed baselines with cost stress, leave-one-family-out and an untouched time block.
