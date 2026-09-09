# Research 034 — source discovery checkpoint

## Finding

The official HistData site lists the missing target instruments among its historical feeds, including NZD/USD, USD/CAD, USD/CHF, EUR/JPY, XAG/USD, NSX/USD (Nasdaq 100), UKX/GBP (FTSE 100), WTI/USD and BCO/USD (Brent). It offers ordered M1 and tick data, and states that M1 bar prices are based on bid ticks while ask/spread information is available in Generic ASCII tick data.

Sources checked on 2026-09-09:

- HistData instrument and feed list: https://www.histdata.com/
- HistData FAQ and file specification: https://www.histdata.com/f-a-q/
- HistData download flow: https://www.histdata.com/download-free-forex-data/

## Blocker

The download flow requires an interactive format selection and did not expose direct file URLs or hashes through the current research environment. The local workspace therefore still contains only six valid comparable assets for the requested panel. The existence of a feed is not treated as possession or validation of the data.

No model or P&L is run on the missing assets. The next acquisition checkpoint must download the exact M1/tick members, record SHA-256, inspect timestamps/session boundaries, quantify gaps, and decide whether bid-only M1 plus a conservative spread scenario is comparable enough for the locked panel.
