"""Run the committed intraday model or an explicitly supplied command.

This adapter deliberately does not invent a model. Configure
QUANT_INTRADAY_MODEL_CMD with a reproducible command, or place the committed
model script named by QUANT_INTRADAY_MODEL in the repository.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


def main() -> None:
    command = os.environ.get("QUANT_INTRADAY_MODEL_CMD", "").strip()
    if command:
        print("Running QUANT_INTRADAY_MODEL_CMD:", command)
        subprocess.run(command, shell=True, check=True)
        return

    script = Path(os.environ.get("QUANT_INTRADAY_MODEL", "real_intraday_15asset_scalp.py"))
    if not script.exists():
        raise SystemExit(
            "No intraday model is configured. Set QUANT_INTRADAY_MODEL_CMD or "
            f"commit {script} before running the model stage."
        )
    subprocess.run(["python", str(script)], check=True)


if __name__ == "__main__":
    main()
