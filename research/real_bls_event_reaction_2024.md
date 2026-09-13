# Research 042 — BLS CPI/employment intraday digestion across 15 CFD proxies

## Decision

**Rejected / research-only exploratory.** The expanding multi-input ridge model failed all six preregistered gates. It lost money before costs, lost more after the fixed four-pip round trip, did not beat either frozen price baseline, and was negative in both calendar halves and all four asset families. No threshold, asset, event category, or regime was selected after seeing these results.

The 2024 panel has been used in earlier lab work, so this is not an untouched confirmation sample even if a gate had passed.

## Paper and mechanism

Andersen, Bollerslev, Diebold and Vega (2003), *Micro Effects of Macro Announcements: Real-Time Price Discovery in Foreign Exchange*, documents sharp price discovery and volatility around scheduled macroeconomic announcements (AER, DOI: https://doi.org/10.1257/000282803321455151).

The tested extension is deliberately falsifiable: the first five-minute move after a major BLS announcement may continue while information is digested, or reverse if the first response overshoots. A pooled linear model may improve the choice by conditioning on the size of the first move, pre-event volatility, lagged VIX, release type, and preregistered interactions.

## Preregistered hypothesis and model

The design was recorded in GitHub issue #59 before performance was inspected.

For asset `i` and event `e`, with official release time `t0`:

`r5(i,e) = log(P(i,t0+5m) / P(i,t0))`

`y(i,e) = log(P(i,t0+60m) / P(i,t0+5m))`

Frozen baselines:

- continuation: `sign(r5)`;
- reversal: `-sign(r5)`;
- equal-risk reversal: reversal weighted by inverse pre-event 20-day five-minute volatility.

The primary model is expanding ridge regression with penalty 1.0. Inputs are standardized initial move, pre-event volatility, previous-day VIX, CPI/employment category, category × initial-move, and category × VIX. Training contains only releases strictly earlier than the decision. Trading starts after four prior complete releases. No early prediction is backfilled.

All models enter at the first valid quote at or after `t0+5m` and exit at the first valid quote at or after `t0+60m`. A quote more than ten minutes late fails closed.

## Data and timing

- Events: all twelve CPI and twelve Employment Situation dates in the official [BLS 2024 release calendar](https://www.bls.gov/schedule/2024/home.htm), each at 08:30 `America/New_York`. DST conversion is performed with the named timezone, not a fixed UTC offset.
- Prices: frozen 2024 five-minute panel of 15 international CFD proxies, SHA-256 `e632e54adb79e027e991bb335a917e9a7a30e16c6ddf33b0daecc9ceeae5d05c`.
- VIX: FRED `VIXCLS`, using the last observation strictly before the event date, SHA-256 `d189972fce09597c45f246711881ba8ab35acca9ad52b98027214c42bb01422c`.
- Event file SHA-256: `b94bc7ff54be403f543b7918161eeea3522ffa7b6f65146b32ca84da3a98dbbd`.

The local panel ends at 2024-12-05 04:20 UTC, so the December 6 employment and December 11 CPI releases are absent. They were excluded by the frozen missing-data rule, not replaced. The remaining 22 events produced 327 valid asset-event rows. All 15 assets were represented. Three isolated rows failed closed: UKXGBP on March 8 and November 13, and XAGUSD on November 1.

The common model-comparison period begins after four prior events and contains 18 events.

## Results

| Model | 0× cost | 1× = 4 pip | 2× | 4× | Round trips |
|---|---:|---:|---:|---:|---:|
| Continuation | -0.003% | -0.486% | -0.966% | -1.919% | 265 |
| Reversal | +0.003% | -0.479% | -0.959% | -1.912% | 265 |
| Equal-risk reversal | -0.080% | -0.620% | -1.157% | -2.221% | 265 |
| Expanding ridge | -0.131% | -0.673% | -1.213% | -2.282% | 267 |

At 1× cost, ridge generated 534 entry/exit legs across 18 event windows, about 14.8 round trips per event. Only 2/18 event portfolios were positive. The deterministic 10,000-draw event bootstrap gave `P(mean > 0) = 0.0%`; its 95% interval for mean event log return was `[-0.0566%, -0.0207%]`.

The cost is economically material, but it is not the root failure: ridge was already -0.131% at zero cost. The price-only continuation and reversal rules were essentially flat before cost, indicating no stable one-hour directional digestion effect in this sample.

### Robustness

- First half of the common period: -0.347%; second half: -0.327%.
- CPI events: about -0.194% log contribution; employment events: about -0.481% log contribution.
- Low-VIX half: -0.324%; high-VIX half: -0.351%.
- Family attribution: energy -0.013%, equities -0.086%, FX -0.540%, metals -0.035%.
- Every one of the 15 asset leave-one-out portfolios remained negative.

## Preregistered gates

| Gate | Result |
|---|---|
| Ridge positive at 1× | Fail |
| Ridge beats continuation and reversal | Fail |
| Bootstrap P(mean positive) at least 95% | Fail |
| Both calendar halves non-negative | Fail |
| At least 3/4 families positive | Fail (0/4) |
| Ridge positive at 2× | Fail |

## Interpretation and next action

This rejects a generic strategy that trades the direction of the first five-minute response—or its opposite—after CPI and employment releases. Adding event type, volatility and VIX did not rescue the signal. The likely missing economic input is the *content* of the release: actual value relative to the point-in-time consensus. That input remains blocked because a timestamp-verifiable historical consensus archive has not been acquired. It must not be reconstructed from revised or ambiguously timestamped web pages.

The highest-value confirmation path is to finish the immutable 2023–2025 panel from the 45 raw archives and rerun only frozen hypotheses, or acquire licensed/timestamped consensus data for Research 039. This experiment does not justify live trading.

## Reproduction

Run:

`python real_bls_event_reaction_2024.py --panel data/cfd_intraday_5m_15_2024.csv --events data/bls_major_releases_2024.csv --vix data/fred_VIXCLS.csv --output-dir results/research042`

Then:

`python -m unittest test_real_bls_event_reaction_2024.py`

Four tests cover source/event counts, DST conversion, decision timing, expanding-training chronology, common comparison coverage, cost monotonicity, and deterministic reproduction.
