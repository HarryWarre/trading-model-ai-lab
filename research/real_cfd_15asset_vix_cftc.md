# Research 034 — VIX plus CFTC positioning

The fixed 15-asset daily panel was extended with weekly CFTC speculative-pressure data for eight assets: EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF and XAUUSD. TFF data was used for FX and disaggregated data for gold. The positioning observation was released three days after the CFTC report date; only the released value was carried forward.

The Ridge model retained all previous price, volatility, breadth and VIX features and added the signed expanding z-score of speculative pressure. It was fitted only on earlier five-day decisions.

| Model | Net return | Sharpe | Max drawdown | Bootstrap P(mean > 0) |
|---|---:|---:|---:|---:|
| Ridge + VIX | -8.98% | -1.136 | -11.19% | 10.5% |
| Ridge + VIX + CFTC | -8.62% | -1.110 | -11.28% | 11.3% |

The positioning input improved the point estimate only slightly and did not produce a positive or statistically credible result. This is a preliminary 2024 run, not an untouched confirmation holdout. CFTC positioning is futures positioning, not directly executable CFD depth or broker flow, so it does not provide a capacity estimate.
