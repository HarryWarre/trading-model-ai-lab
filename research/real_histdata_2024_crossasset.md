# Research 021 — fresh cross-asset HistData panel

## Decision

The pre-registered five-asset confirmatory test is not fully evaluable because
HistData exposed no valid 2024 M1 download token for WTIUSD. No replacement was
introduced after registration.

The four available fresh assets nevertheless provide a clear negative result:
GBPUSD, AUDUSD, XAUUSD and SPXUSD produce -3.15% net return, Sharpe -0.671 and
-0.26% gross return. All four leave-one-out portfolios are also negative. The
available evidence therefore rejects broad cross-asset generalization even
before considering the missing WTI observation.

## Paper mechanism and falsifiable hypothesis

Moskowitz, Ooi and Pedersen (2012) report time-series momentum across equity
indexes, currencies and commodities. If the 20-session signal captures broad
return persistence rather than favorable outcomes in EURUSD/USDJPY, a fresh
cross-asset sleeve should remain profitable after conservative trading costs
and after removing any one instrument.

Issue #34 froze the universe, model and decision rule before performance was
calculated. The registered fresh assets were GBPUSD, AUDUSD, XAUUSD, WTIUSD and
SPXUSD. EURUSD and USDJPY were retained only as previously inspected controls.

## Data and provenance

- Source: HistData Generic ASCII M1 BID OHLC, calendar 2024.
- HistData documents fixed EST timestamps without daylight-saving adjustment.
- Volume is zero/unusable, so sessions are screened by observed minute count.
- ZIP and extracted CSV SHA-256 values are locked in the downloader and model.
- Available: EURUSD, USDJPY, GBPUSD, AUDUSD, XAUUSD, SPXUSD.
- Blocked: WTIUSD; its 2024 ASCII M1 page returned an empty token during this
  iteration.
- No synthetic prices or substituted WTI observations are used.

Identical duplicate timestamps were found and removed: 60 each in USDJPY,
GBPUSD, AUDUSD, XAUUSD and SPXUSD; none in EURUSD. Conflicting duplicates would
stop the run. Each asset forms its signal on its own valid session history;
asset returns are aligned only after signal construction, avoiding distortion
of a currency lookback by missing index sessions.

## Model

Daily OHLC is reconstructed at fixed 17:00 EST. Sessions require at least 1,000
observed minute bars.

\[
s_{i,t}=\operatorname{sign}\left(\log(C_{i,t}/C_{i,t-20})\right),
\qquad
w^*_{i,t}=\operatorname{clip}\left(s_{i,t}\frac{0.10}{\hat\sigma_{i,t}},-1,1\right).
\]

The target is delayed one session and earns the next open-to-open return. Costs
are charged on absolute turnover:

- FX: 4.4 pips.
- XAUUSD: 10 bps.
- SPXUSD: 10 bps.
- Registered WTIUSD assumption: 20 bps, not applied because data is blocked.

These are 2x stress extensions of prior lab assumptions. Financing, executable
spreads and market impact are unavailable.

## Results

Common investable dates are 2024-01-30 through 2024-12-29, 236 observations.

| Portfolio | Assets | Gross return | Net return | Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| Fresh available | 4 | -0.26% | -3.15% | -0.671 | -7.83% |
| All available | 6 | +1.01% | -1.36% | -0.341 | -4.73% |

Standalone attribution:

| Asset | Net return | Sharpe | Max DD |
|---|---:|---:|---:|
| EURUSD — control | +1.70% | 0.303 | -4.60% |
| USDJPY — control | +2.93% | 0.330 | -5.54% |
| GBPUSD — fresh | -2.54% | -0.435 | -5.27% |
| AUDUSD — fresh | -6.36% | -0.820 | -16.15% |
| XAUUSD — fresh | -5.10% | -0.522 | -15.11% |
| SPXUSD — fresh | +1.61% | 0.165 | -9.88% |

Only one of four available fresh assets is positive. The fresh sleeve is
negative even before costs, so transaction-cost tuning cannot rescue the
economic hypothesis.

## Concentration and statistical checks

All four fresh leave-one-out portfolios are negative:

| Excluded | Net return | Sharpe |
|---|---:|---:|
| GBPUSD | -3.35% | -0.619 |
| AUDUSD | -2.05% | -0.385 |
| XAUUSD | -2.49% | -0.486 |
| SPXUSD | -4.68% | -0.916 |

A deterministic 5,000-sample stationary bootstrap with expected block length
20 sessions gives:

- Probability fresh-four mean is positive: 24.22%.
- 95% annualized-mean CI: [-13.22%, +6.81%].

The negative outcome is not caused by one asset, although the confidence
interval remains wide because only one year is available.

## Pre-registered decision

- Registered fresh data available: 4/5; confirmatory test not fully evaluable.
- Fresh available portfolio positive and Sharpe >0.5: fail.
- At least 3/5 fresh assets positive: fail; only 1/4 observed is positive.
- All available portfolio positive: fail.
- At least 4/5 fresh leave-one-out portfolios positive: fail; 0/4 observed.
- Bootstrap probability >=95%: fail; 24.22%.

Overall hypothesis: **not supported**. Missing WTI does not create a favorable
interpretation because every evaluable performance condition fails.

## QA and limitations

- File hashes, schema, OHLC invariants and duplicate identity are checked.
- Session counts are 260 for the four FX pairs, 259 for XAUUSD and 258 for
  SPXUSD before warm-up/alignment.
- Execution uses a one-session lag; deterministic warm-up is excluded.
- Costs are non-negative and tested in both pip and basis-point units.
- HistData is BID-only and gives no usable volume. Capacity is therefore not
  estimated.
- SPXUSD and XAUUSD are reference feeds/proxies, not executable CFD contracts.
- The same 2024 sample must not be used to select a different subset or
  lookback.

## Next step

The two-pair result from Research 020 does not generalize to the available
fresh cross-asset panel. Further iterations should stop treating this exact
20-session specification as a broad CFD alpha candidate. A new research branch
should begin from a different documented economic mechanism—preferably carry,
term structure or positioning—and acquire the required futures/forward data
before model implementation.

## References

- Moskowitz, Ooi and Pedersen (2012), *Time Series Momentum*.
- Politis and Romano (1994), *The Stationary Bootstrap*.
- HistData, *Data Files: Detailed Specification* and FAQ.
- Philippe Remy, *FX-1-Minute-Data*.
