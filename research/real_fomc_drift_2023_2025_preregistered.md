# Research 043 — 2023–2025 pre-FOMC drift confirmation

## Current decision

**Preregistered and implementation-complete; performance not run.** No return, bootstrap, or alpha claim is made in this note. The combined 15-asset panel does not yet exist in Drive, and the currently selected execution environment is unavailable. The end-to-end Colab runner is ready to build and test it in one invocation.

Issue: https://github.com/HarryWarre/trading-model-ai-lab/issues/60

## Paper and frozen mechanism

This is a broader replication of Research 040 using the pre-FOMC announcement-drift mechanism in Lucca and Moench, *The Pre-FOMC Announcement Drift*: https://www.newyorkfed.org/research/staff_reports/sr512.html.

For each of the 24 scheduled decisions in 2023–2025, the model buys four equity-index CFD proxies for the same common-market window locked in Research 040: from 27 hours before the 14:00 New York statement to three hours before it. Weights are inverse pre-event volatility. The test uses 0x/1x/2x/4x of the fixed four-pip round trip and matched ±7-day controls.

All six pass gates were published in issue #60 before the 2023–2025 panel or performance was inspected.

## Official events

The new event file contains eight decisions for each of 2023, 2024 and 2025. Dates come from the Federal Reserve meeting calendar and each row links to the official statement. The event loader independently requires 24 unique rows and checks that every UTC timestamp converts to 14:00 `America/New_York`.

Primary calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

## Drive/raw-data audit

Connected Drive currently contains:

- 45 primary ZIPs: 15 assets × 2023–2025;
- one additional WTIUSD 2023 ZIP, while WTIUSD 2024–2025 remain blocked and outside the primary panel;
- the original 48-row acquisition manifest;
- no combined `histdata_m1_5m_15_2023_2025.csv`.

A metadata comparison found one raw-file change after the original manifest:

| Asset/year | Original bytes | Current Drive bytes |
|---|---:|---:|
| EURUSD 2023 | 2,919,186 | 2,800,380 |

The other 44 primary ZIP byte sizes match the acquisition manifest. Size equality is not treated as hash equality; all 45 files must be streamed and hashed before use.

## Defects found and fixed

### 1. Panel/model schema mismatch

The old builder wrote long rows: `timestamp, asset, close`. Existing research runners expect one `timestamp` column plus one column per asset. The builder now creates a deterministic `wide_close` panel with 15 ordered asset columns. Missing observations remain NaN; there is no forward fill or interpolation.

### 2. Manifest was not enforced

The old builder calculated archive hashes for the output report but did not require them to equal the acquisition manifest before reading prices. It now rejects:

- missing asset-year rows;
- duplicate rows;
- blocked/unverified status;
- byte-size differences;
- SHA-256 differences;
- corrupt ZIPs;
- unexpected members.

### 3. Original manifest no longer describes every current file

The original manifest is never overwritten. A separate revalidation stage checks ZIP integrity, streams every file through SHA-256, and writes:

- `histdata_multiyear_manifest_revalidated.csv`;
- `histdata_multiyear_manifest_revalidated.summary.json`;
- old and new hash/byte values plus `changed_from_original`.

The panel builder accepts only this newly verified manifest.

### 4. Manual multi-step workflow

A new one-run notebook performs:

1. Drive mount and repository update;
2. 45-file ZIP/hash revalidation;
3. tests;
4. wide-panel construction;
5. coverage and SHA validation;
6. frozen Research 043 execution;
7. result persistence to Drive.

Notebook: `colab/run_research043_multiyear_confirmation.ipynb`.

## Files

- `colab/revalidate_histdata_manifest.py`
- `colab/prepare_histdata_m1_panel.py`
- `data/fomc_2023_2025_official.csv`
- `real_fomc_drift_2023_2025.py`
- `test_revalidate_histdata_manifest.py`
- `test_prepare_histdata_m1_panel.py`
- `test_real_fomc_drift_2023_2025.py`
- `colab/run_research043_multiyear_confirmation.ipynb`

## Remaining blocker

The code could not be executed in this workday because no active compute environment was available and the connected DigitalOcean account has no existing droplet. Creating a paid machine was not assumed. The Drive connector can verify metadata and fetch small text files, but it does not expose the 100+ MB of private ZIP bytes to the local runtime for computation.

Therefore no performance metric has been produced. The next valid state transition is execution of the one-run notebook; after `DONE_RESEARCH043`, the automation can inspect Drive results and publish the exact decision without another model-build step.
