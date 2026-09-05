# Research 028 — current-account currency premium: blocked before P&L

## Research question and mechanism

Della Corte, Riddiough and Sarno, *Currency Premia and Global Imbalances*, link
currency premia to countries' external balance sheets: net-debtor countries need
to compensate international investors for financing negative external
imbalances, especially because debtor currencies can depreciate in bad states.
This iteration preregistered a deliberately simpler flow proxy using annual
current-account balance as a percentage of GDP. It is not a replication of the
paper's full net-foreign-asset and liability-composition factor.

Primary paper: https://openaccess.city.ac.uk/id/eprint/13287/

Official indicator definition and source:
https://data.worldbank.org/indicator/BN.CAB.XOKA.GD.ZS

## Preregistered hypothesis and model

For currency \(c\) and source year \(y\),

\[
I_{c,y}=CA_{c,y}/GDP_{c,y},\qquad S_{c,y}=-I_{c,y}.
\]

Rank AUD, EUR, GBP, JPY and USD by \(S\). Long the two largest debtor scores,
short the two largest creditor scores and hold the median currency flat. Gross
currency exposure is one. Observation year \(y\) becomes usable only on 1 July
of \(y+2\), and orders would execute at the next fixed-EST 17:00 session open.
The intended OOS test was HistData 2024–2025 with corrected m+3 theoretical
carry, 4.4 pip cost per unit turnover, 0x/1x/2x cost stress, annual and asset
attribution, leave-one-out without re-ranking, a locked q75 VIX regime split,
and 5,000 stationary-bootstrap samples with expected block length 10.

All five preregistered currencies were required. Any missing cell had to stop
the test before price returns were loaded or P&L was calculated.

## Data audit and blocker

The official World Development Indicators archive downloaded on 5 September
2026 reports a source update date of 13 July 2026. SHA-256:
`5f20b759b6f56162d9d733df58803aaef8ec47a10c13db257c74f23d9172e83f`.
The archive contains an `EMU` / Euro area row, but every annual value for this
indicator is blank. Australia, the United Kingdom, Japan and the United States
have observations for the required 2022 and 2023 source years.

Therefore the preregistered five-currency rank cannot be formed. The pipeline
fails closed, writes only a coverage table and blocker summary, and calculates
no market return, transaction cost, bootstrap statistic or performance claim.
No euro-country proxy, interpolation, four-currency redesign or mixed-source
replacement was introduced after seeing the source coverage.

## Decision and limitations

Status: **blocked before P&L; hypothesis untested**. This is not a negative
backtest result. The sub-issue should remain a reproducible data-blocker record.
A later iteration may preregister a new design using a single comparable source
with complete point-in-time coverage, but it must be a new hypothesis rather
than an amendment informed by returns.

Even with complete annual data, WDI is current-history rather than vintage and
the July y+2 rule is only a conservative availability assumption. HistData is
BID-only, theoretical carry is not broker swap, and capacity cannot be
quantified without executable ask, depth and ADV data.
