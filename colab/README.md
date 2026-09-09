# Colab long-runner

Open [run_intraday_research.ipynb](https://colab.research.google.com/github/HarryWarre/trading-model-ai-lab/blob/main/colab/run_intraday_research.ipynb) in Google Colab.

The notebook is a compute runner, not a scheduler. It mounts a persistent Google Drive folder, clones the repository, checks raw-file hashes, and runs restartable stages. Stage markers live in:

`MyDrive/trading-model-ai-lab/checkpoints/`

If Colab disconnects, reopen the notebook and rerun the cells. Completed stages are skipped.

Required Colab setup:

1. Put approved raw M1 files in the Drive data folder.
2. Set `QUANT_RAW_FILES` to the exact paths.
3. Set `QUANT_PREPARE_CMD`, `QUANT_MODEL_CMD`, and `QUANT_ROBUSTNESS_CMD` to committed scripts.
4. Run `validate` before any modeling. A missing file fails closed.
5. Copy compact CSV/Markdown outputs into the repo and commit them after reviewing the runtime manifest.

Do not put tokens in the notebook. If publishing from Colab, use Colab Secrets or authenticate Git locally; never commit credentials. BID-only data still cannot prove broker spread, slippage, or capacity.
