# Research 047 — FOMC statement-to-press-conference continuation versus reversal

Preregistered in [issue #64](https://github.com/HarryWarre/trading-model-ai-lab/issues/64) before performance inspection. [Acosta, Ajello, Bauer, Loria and Miranda-Agrippino (2026)](https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf) defines a statement window from ten minutes before to twenty minutes after the FOMC statement and a press-conference window from ten minutes before to sixty minutes after the press conference starts. The paper reports that press-conference *policy surprises* have often counteracted statement-induced rate-expectation changes since the March 2022 liftoff. That does not mechanically imply reversal in CFD price returns, so continuation versus reversal is tested rather than assumed. The paper also states press conferences have followed every scheduled meeting since 2019.

## Frozen model

For asset i and meeting e at official statement time T, statement return s=ln[P(T+20)/P(T−10)] and press-conference return p=ln[P(T+90)/P(T+20)]. Exact 5-minute closes are mandatory; no nearest-quote substitution. The analysis uses the previously hash-locked 2023–2025 panel and the same 12 comparable assets: eight FX, two metals and two US indices. Four 2023 meetings already identified as unavailable in Research 046 remain missing; they are not backfilled. An event needs at least eight assets and all three families.

Four models were declared: continuation sign(s); paper-mechanism reversal −sign(s); unconditional long; and an expanding ridge. Ridge inputs are own statement return divided by prior 20-day 5-minute volatility, leave-self-out family statement response, equal-family global statement response, log pre-volatility, last VIX observation strictly before the event day, and statement×VIX interaction. Target is p divided by pre-volatility. Scaling and coefficients use earlier meetings only. Ridge alpha=10, first eight eligible events are training-only, and every later event is held out in full. Ridge abstains unless predicted raw return exceeds four-pip round-trip cost plus half the prior-training residual median absolute error. Active assets are inverse-volatility weighted to gross exposure one.

Pip values were frozen by instrument convention; 4-pip round-trip is stressed at 0x/1x/2x/4x. Entry is the observed T+20 close and exit T+90. The strategy can make at most one round trip per asset per meeting; this is event trading, not a scalp-frequency strategy. Capacity is unquantifiable from BID OHLC and is not needed to reject/retain this research-only model.

## Results

Twenty of 24 meetings are eligible. The first eight are warm-up, leaving **12 fully event-held-out evaluations** (four in 2024 and eight in 2025; 142 possible asset-events).

| Model | 0x cost | 1x (4 pip) | 2x | 4x |
|---|---:|---:|---:|---:|
| Continuation | +0.7711% | +0.3750% | −0.0196% | −0.8041% |
| Reversal | −0.7652% | −1.1553% | −1.5438% | −2.3163% |
| Long | +0.0078% | −0.3853% | −0.7769% | −1.5554% |
| Expanding ridge | +1.9629% | **+1.7987%** | +1.6347% | +1.3076% |

Ridge executed 43 round trips (86 entry/exit legs), abstained on 69.72% of possible asset-events and made no trade at four of 12 meetings. Direction hit rate among actual trades was 69.77%. Six event portfolios were positive. The two-event-block bootstrap fraction with positive ridge mean is 88.62%, with interval crossing zero. Against the strongest baseline (continuation), the paired resample fraction that ridge's mean improvement is positive is **79.65%**, below the preregistered 95%; its interval also crosses zero.

Stability fails: 2024 evaluation return is +2.2440%, while 2025 is **−0.4356%**. First and second halves are +1.6804% and +0.1163%, showing strong decay. The warm-up-fixed VIX split puts every evaluation event in the high-VIX bucket, so it provides no high/low comparison and is explicitly non-informative. Every asset and family leave-one-out portfolio stays positive. XAGUSD contributes +0.9418% log and NSXUSD +0.5624%, but removing either still leaves total simple return positive (+1.0483% and +2.5136%, respectively).

## Decision

Five of seven gates pass: net positive at 1x and 2x, better than all three baselines, every family leave-one-out positive, and enough evaluation events. Two decisive gates fail: both years are not positive, and paired bootstrap support versus the strongest baseline is only 79.65% rather than 95%. The paper-inspired simple reversal baseline is strongly negative; the paper's result concerns policy-surprise factors, not necessarily raw CFD returns.

**Research-only / rejected as alpha.** The positive ridge result is worth recording because it survived 4x fixed spread and every leave-one-out, but it is neither stable across years nor statistically reliable versus continuation. The sample has been used repeatedly by the lab and no later untouched holdout exists. Do not tune ridge strength, abstention threshold, features, or event windows on these outcomes. A valid next test needs either the timing-audited SF Fed policy-surprise data or future untouched meetings.

Reproduce with:

`python real_fomc_statement_pressconference_2023_2025.py --panel histdata_m1_5m_15_2023_2025_recovered.csv --manifest histdata_m1_5m_15_2023_2025.manifest.json --events data/fomc_2023_2025_official.csv --vix data/fred_VIXCLS.csv --output results/research047`

The complete output directory was reproduced byte-for-byte. Four stdlib tests and Python compilation pass. Results include event coverage, model trade ledgers, each cost level, asset/family leave-one-out, asset attribution, years, phases, VIX attribution, input hashes and frozen-gate decision.
