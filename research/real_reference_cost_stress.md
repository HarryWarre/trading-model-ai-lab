# Research 010 — transaction-cost stress and capacity blocker

## Literature mechanism

Gârleanu & Pedersen (2013) show that predictable-return strategies should
trade partially toward a moving target when transaction costs are material.
This makes cost robustness a model requirement rather than a cosmetic
backtest adjustment. Baltas & Kosowski also document that higher trading
frequency produces substantially higher trend-strategy turnover and costs.

## Falsifiable test

All six fixed S&P 500/WTI variants are evaluated from 2016 through 2019 under
0.5x, 1x, 2x and 4x the declared base costs. Base assumptions are 5 bps per
unit turnover for SP500 and 10 bps for WTI. A candidate is cost-robust only if
net return remains positive at 2x and performance does not depend entirely on
one year. Break-even cost multiplier is calculated without selecting a new
parameter.

## Capacity limitation

The S&P 500 reference file has unusable/zero volume and the EIA WTI spot
series has no tradable contract volume. Therefore ADV participation, market
impact and capital capacity cannot be estimated. The repository records this
as a blocker rather than inventing a capacity number. Continuous futures or
broker volume/contract specifications are required.

## Reproduction

```bash
python real_reference_cost_stress.py
pytest -q test_real_reference_cost_stress.py
```

## Findings

| Model | Lookback | Net at 1x | Net at 2x | Net at 4x | Break-even multiplier |
|---|---:|---:|---:|---:|---:|
| continuous | 5 | +4.80% | -10.63% | -35.01% | 1.29x |
| continuous | 10 | +10.65% | +0.23% | -17.76% | 2.02x |
| continuous | 20 | +8.04% | +1.33% | -10.88% | 2.21x |
| sparse | 5 | -0.43% | -7.38% | -19.86% | 0.94x |
| sparse | 10 | +2.04% | -1.64% | -8.62% | 1.55x |
| sparse | 20 | +16.60% | +14.44% | +10.25% | 9.23x |

Only continuous-10, continuous-20 and sparse-20 remain positive at 2x base
cost. At 4x, sparse-20 is the only positive configuration, with net Sharpe
0.32 and 3/4 positive years. Its robustness comes from low turnover rather
than leverage. This strengthens its status as a research candidate, but does
not resolve proxy-data or model-selection bias.
