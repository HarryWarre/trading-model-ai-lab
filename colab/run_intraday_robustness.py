"""Run the committed intraday robustness checks.

The stage is explicit and fail-closed: it never labels a run complete when no
robustness implementation has been supplied.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def main() -> None:
    command = os.environ.get("QUANT_INTRADAY_ROBUSTNESS_CMD", "").strip()
    if command:
        print("Running QUANT_INTRADAY_ROBUSTNESS_CMD:", command)
        subprocess.run(command, shell=True, check=True)
        return

    script = Path(
        os.environ.get("QUANT_INTRADAY_ROBUSTNESS", "real_intraday_15asset_robustness.py")
    )
    if not script.exists():
        raise SystemExit(
            "No intraday robustness checks are configured. Set "
            "QUANT_INTRADAY_ROBUSTNESS_CMD or commit the robustness script."
        )
    subprocess.run(["python", str(script)], check=True)


if __name__ == "__main__":
    main()
