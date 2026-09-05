# Research 022 — CFTC speculative-pressure holdout

## Decision

The preregistered hypothesis is rejected. On the untouched 2024 HistData
holdout, the six-asset market-neutral positioning portfolio returned -3.29%
net with Sharpe -0.594. Only one of six leave-one-asset-out portfolios was
positive and the stationary-bootstrap probability of a positive mean was
28.14%, far below the locked 95% threshold.

This model is not a broad international-CFD alpha candidate. No contract,
ranking, lookback, or sign was changed after observing the result.

## Literature and mechanism

De Roon, Nijman and Veld (2000), *Hedging Pressure Effects in Futures
Markets*, predicts compensation to non-market participants who absorb net
hedging demand. Fan, Li and Zhang (2020), *Speculative Pressure*, reports that
net speculative demand contains cross-asset return information after several
standard controls. These are risk-transfer/informed-demand mechanisms, not a
technical-indicator combination.

Primary sources:

- De Roon, Nijman & Veld: https://repository.tilburguniversity.edu/bitstreams/81b4685f-66fa-4fe8-9c51-da6e3e5dcfdf/download
- Fan, Li & Zhang: https://openaccess.city.ac.uk/id/eprint/23283/1/FINAL_JFM__Accepted_27Nov2019_SSRN.pdf
- CFTC historical archives: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
- CFTC report taxonomy: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm

## Preregistered model

For asset i and Tuesday report t:

    SP[i,t] = (speculative_long[i,t] - speculative_short[i,t]) / OI[i,t]

TFF Leveraged Funds are used for EUR, JPY, GBP, AUD and E-mini S&P 500.
Disaggregated Managed Money is used for COMEX gold. USDJPY reverses the JPY
futures sign because the CFD quote is JPY per USD while the futures exposure
is USD per JPY.

An expanding z-score uses only observations through report t, with at least
52 prior/current weekly observations. At each Friday release, the strategy
ranks all six assets, buys the top two and sells the bottom two. Each active
leg has absolute weight 0.25, giving gross exposure 1 and net exposure 0.

## Leakage controls and data

- Contract mappings and thresholds were written to issue #35 before opening
  the 2024 strategy result.
- Tuesday positions are treated as available only on Friday (Tuesday + three
  calendar days), consistent with the COT publication schedule.
- Execution begins at the first reconstructed fixed-EST 17:00 session after
  release; returns are measured open to next open.
- The CFTC futures-only archives cover 2010–2024 and every ZIP is SHA-256 and
  byte-size locked. The selected six series each contain 626 weekly reports
  from 2013-01-08 through 2024-12-31; 575 have valid expanding z-scores.
- Prices are the six 2024 HistData M1 BID feeds already hash-locked in
  Research 020/021. There are 258 common reconstructed sessions.
- The 2024 model changed target ranking 19 times.

Contract mappings:

| CFD proxy | CFTC report | Contract code |
|---|---|---|
| EURUSD | TFF, Leveraged Funds | 099741 |
| USDJPY | TFF, Leveraged Funds, reversed sign | 097741 |
| GBPUSD | TFF, Leveraged Funds | 096742 |
| AUDUSD | TFF, Leveraged Funds | 232741 |
| SPXUSD | TFF, Leveraged Funds | 13874A |
| XAUUSD | Disaggregated, Managed Money | 088691 |

## Holdout result

| Gross return | Net return | Sharpe | Max drawdown | Turnover/year |
|---:|---:|---:|---:|---:|
| -2.72% | -3.29% | -0.594 | -5.80% | 11.23x |

The locked stressed costs are 4.4 pips for FX and 10 bps for gold/S&P per unit
turnover. They produce 0.588% log-return drag. Since gross return is already
negative, transaction costs are not the main explanation for failure.

Asset-level net attribution:

| Asset | Net return | Sharpe |
|---|---:|---:|
| EURUSD | -0.52% | -0.865 |
| USDJPY | -1.01% | -0.501 |
| GBPUSD | -1.31% | -0.933 |
| AUDUSD | +0.43% | +0.281 |
| XAUUSD | +3.17% | +0.827 |
| SPXUSD | -3.96% | -1.313 |

Only excluding SPXUSD makes a leave-one-out portfolio positive (+4.23%,
Sharpe 0.828). Selecting that exclusion after observing the result would be
data mining, so it is retained only as attribution.

## Robustness and regimes

| Cost multiplier vs locked | Net return | Sharpe |
|---:|---:|---:|
| 0x | -2.72% | -0.490 |
| 0.5x | -3.00% | -0.542 |
| 1x | -3.29% | -0.594 |
| 2x | -3.86% | -0.697 |

Point-in-time regime attribution uses the lagged 20-session SPXUSD return and
does not gate positions. The strategy is negative in both states: -2.93%
(Sharpe -0.688) when trailing SPX is up and -0.51% (Sharpe -0.550) when it is
down. The down-state sample has only 41 observations and is descriptive.

The 5,000-sample stationary bootstrap uses expected block length 10 sessions.
Probability of positive mean is 28.14%; the annualized mean 95% interval is
[-14.18%, +7.96%].

## Assumptions and capacity

HistData is BID-only. Synthetic costs do not include financing, overnight
swap, futures roll carry, taxes, or nonlinear market impact. COT aggregates
exchange positions and cannot establish whether the same information is
available or priced identically in a broker CFD.

Capacity is not estimated: COT open interest is not executable CFD depth, and
the BID bars do not provide ask quotes, order-book depth, or reliable ADV for
market impact. Inventing a capacity number would be misleading.

## Reproduction

    python download_cftc_positioning.py
    python real_cftc_speculative_pressure.py

`test_real_cftc_speculative_pressure.py` checks market neutrality/gross
exposure, the three-day publication lag, all six mappings, the untouched 2024
window, robustness outputs, and bootstrap bounds.
