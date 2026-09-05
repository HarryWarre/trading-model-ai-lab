# Research 029 — cross-sectional currency momentum, 2024–2025

## Result first

The preregistered hypothesis is rejected. The primary phase produced a positive
net return in both years and survived double cost, but the stationary bootstrap
probability of a positive mean was only 80.58%, below the locked 95% threshold.
The 95% annualized-mean interval was -3.43% to +8.84%.

This is a new hypothesis tested on a sample already used elsewhere in the lab,
not an untouched holdout. It cannot be treated as confirmatory evidence.

## Paper and mechanism

Menkhoff, Sarno, Schmeling and Schrimpf, *Currency Momentum Strategies*, finds
a cross-sectional spread between recent currency winners and losers. The paper
reports behavior consistent with investor underreaction and later overreaction,
while emphasizing that transaction costs absorb part of the spread.

Primary paper and BIS metadata: https://www.bis.org/publ/work366.htm

## Locked model

The narrow available universe is AUD, EUR, GBP and JPY. For each currency, USD
per foreign-currency-unit is used; USDJPY is inverted for signal construction.
At formation session \(t\):

\[
M_{c,t}=\log(S_{c,t}/S_{c,t-21})+
\sum_{d=t-21}^{t-1}(r_{c,d}-r_{USD,d})\Delta_d/365.
\]

The strategy goes long the winner at +0.5 and short the loser at -0.5, holding
for 21 non-overlapping sessions. A signal observed at session-open \(t\) is first
implemented at \(t+1\), preventing same-open execution. JPY currency weight is
mapped with the opposite sign to USDJPY. Interbank-rate observations use the
corrected m+3 availability rule from Research 027.

The primary phase offset is zero. Offsets 0, 5, 10 and 15 were locked before
P&L; their median is reported and no best phase is selected. Cost is 4.4 pip
per unit instrument turnover, with gross exposure fixed at one.

## Preregistered decision table

| Criterion | Result | Pass |
|---|---:|:---:|
| Pooled net return > 0 | +5.46% | yes |
| Both annual returns > 0 | 2024 +2.39%; 2025 +3.00% | yes |
| Positive leave-one-out >= 3/4 | 3/4 | yes |
| Bootstrap P(mean > 0) >= 95% | 80.58% | no |
| Positive at 2x cost | +4.02% | yes |
| Median phase return > 0 | +1.31% | yes |

Any failure rejects the all-pass hypothesis.

## Economics, robustness and concentration

Primary net return was +5.46%, Sharpe 0.573 and maximum drawdown -6.37%.
Before costs, pooled return was +6.93%; the break-even cost multiplier was
4.85 times the locked cost. Annualized turnover was 14.57.

Phase results were +5.46%, -9.74%, +1.53% and +1.10% for offsets 0, 5, 10 and
15. Thus the median remained positive, but one equally preregistered phase was
strongly negative. Currency attribution was AUD -7.20%, EUR +2.06%, GBP -2.32%
and JPY +13.98%. Excluding JPY changed the result to -8.44%; the other three
leave-one-out portfolios were positive. JPY is therefore an important
concentration risk, and is not selected as a standalone model after results.

Lagged q75 VIX attribution was +11.57% in 452 low-VIX sessions and -5.47% in 44
high-VIX sessions. This is descriptive only: the high-VIX sample is small and no
regime gate is introduced.

## Data QA and limitations

HistData M1 BID observations were reconstructed at fixed-EST 17:00 sessions.
The extracted workspace copy of GBPUSD 2024 was discovered to be truncated
mid-row on 22 September after 270,544 lines, while the hash-locked source ZIP
contains 372,107 complete lines through 31 December. The model reads and hashes
the ZIP member directly, excludes the truncated extracted copy, and applies the
same policy to every 2024 currency. Five archive/provenance tests pass.

The four-currency universe is far narrower than the paper's panel. HistData has
only BID, synthetic cost is not an executable spread, and theoretical interbank
carry is not broker swap. FRED files are current-history rather than vintages.
No ask, order-book depth or ADV is available, so capacity cannot be quantified.

## Decision

Status: **rejected / research-only**. The positive primary result is noteworthy
but statistically weak, phase-sensitive and materially concentrated in JPY.
No production candidate is promoted and no horizon, phase, asset or VIX filter
is selected after observing results.
