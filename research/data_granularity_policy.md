# Data granularity policy

## Default

OHLC or OHLCV bars are sufficient for the primary research program because the intended holding period is several hours to several days.

Accepted research bars:

- 5-minute and 15-minute for intraday/swing execution studies.
- 1-hour and 4-hour for lower-turnover swing models.
- Daily and monthly for academic replication and macro/factor research.

## Required OHLC fields

`symbol`, `timestamp_utc`, `open`, `high`, `low`, `close`.

Preferred additions:

`volume`, `bid`, `ask`, `open_interest`, `contract`, `expiry`, `currency`, `multiplier`, `source`, `retrieved_at`.

## Tick data is optional

Tick data is not required for the core model. It is only needed when studying:

- microstructure or order-flow hypotheses;
- sub-minute execution;
- spread dynamics and precise slippage;
- stop-loss/limit-order fill behavior;
- quote-to-trade latency.

When bid/ask is unavailable, the backtest must use a pre-registered conservative spread/slippage assumption and label the result as synthetic execution.

## OHLC caveat

OHLC bars cannot determine the order of intrabar high/low events. Stop and target logic must therefore use conservative fill rules or a lower timeframe for execution reconstruction. No strategy may claim tick-level execution accuracy from OHLC alone.
