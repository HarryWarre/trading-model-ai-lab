# Two-tier research execution

The lab uses two execution tiers.

## Tier A — lightweight autonomous run

Codex can run this tier directly:

- source and manifest checks;
- schema, timestamp and timezone validation;
- compilation and unit tests;
- small-sample smoke tests;
- feature availability and missing-data reports;
- deterministic checks;
- audit of prior results;
- research-note and issue updates.

These tasks must finish within the available local run budget and must never be reported as a completed heavy backtest.

## Tier B — heavy Colab run

Colab is used for:

- M1 or 5-minute data;
- 15+ assets;
- walk-forward retraining;
- large bootstrap and multiple-testing checks;
- cost, capacity and regime stress;
- model comparisons that need long CPU time.

The notebook is [colab/run_intraday_research.ipynb](../colab/run_intraday_research.ipynb). It stores data, hashes, logs and checkpoints in Drive. Each stage is restartable.

## Handoff contract

A heavy run is considered complete only when Colab produces:

1. a raw-file SHA-256 manifest;
2. a validated panel manifest with asset count, timestamps and timezone;
3. model and baseline result CSVs;
4. robustness and cost-stress CSVs;
5. a research note containing the exact commit and run configuration.

The next lightweight run then reads those compact outputs, checks their hashes and updates GitHub. If any artifact is missing, the status remains **waiting-for-Colab**; no performance claim is made.

## Cost and execution rule

The default model is not changed merely to make Tier A fast. Tier A is a gate and audit layer. Tier B is where the registered heavy experiment runs.
