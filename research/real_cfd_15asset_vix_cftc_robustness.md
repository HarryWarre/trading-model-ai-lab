# Research 034 — cost and regime robustness

The fixed 15-asset Ridge + VIX + CFTC result was stress-tested without changing signals or selections.

| Cost | Net return | Sharpe | Max drawdown |
|---|---:|---:|---:|
| 0x | +6.45% | 0.775 | -5.52% |
| 1x locked synthetic cost | -8.62% | -1.110 | -11.28% |
| 2x | -21.55% | -2.912 | -21.47% |
| 4x | -42.19% | -5.934 | -41.96% |

The gross signal is positive, but the profit does not survive the locked synthetic CFD cost assumption. The bootstrap probability of a positive average net return at 1x cost is 11.4%; its annualized 95% interval is -19.39% to +4.32%.

Regime checks also do not support a deployable VIX filter. Low-VIX return was -2.53% over 227 days; high-VIX return was -6.09% over 76 days. The four sequential phases were all negative. No regime threshold is selected after seeing these results.

Conclusion: the model is rejected as a cost-robust CFD alpha candidate. The next valid work is not parameter tuning; it is a different economic mechanism and a later untouched time block.