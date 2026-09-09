"""Fail-closed preparation stage for the Colab intraday runner.

Expected input is one or more CSV files listed in QUANT_RAW_FILES, separated by
semicolons. The stage validates existence, hashes the inputs, checks the
minimum panel shape, and writes a normalized panel plus a manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_paths() -> list[Path]:
    value = os.environ.get("QUANT_RAW_FILES", "")
    paths = [Path(item.strip()) for item in value.split(";") if item.strip()]
    if not paths:
        raise SystemExit("QUANT_RAW_FILES is empty; refusing to run.")
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit(f"Missing raw file(s): {missing}")
    return paths


def choose_column(columns, names):
    lowered = {str(c).lower(): c for c in columns}
    for name in names:
        if name in lowered:
            return lowered[name]
    return None


def main() -> None:
    paths = raw_paths()
    frames = []
    file_manifest = []
    for path in paths:
        frame = pd.read_csv(path)
        if frame.empty:
            raise SystemExit(f"Empty raw file: {path}")
        time_col = choose_column(frame.columns, ["timestamp", "datetime", "date", "time"])
        asset_col = choose_column(frame.columns, ["asset", "symbol", "ticker", "instrument"])
        close_col = choose_column(frame.columns, ["close", "price", "mid", "bidclose"])
        if not all([time_col, asset_col, close_col]):
            raise SystemExit(
                f"{path} must contain time, asset/symbol, and close/price columns; "
                f"found {list(frame.columns)}"
            )
        frame = frame.rename(
            columns={time_col: "timestamp", asset_col: "asset", close_col: "close"}
        )
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        frame["asset"] = frame["asset"].astype(str).str.strip()
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["timestamp", "asset", "close"])
        frames.append(frame[["timestamp", "asset", "close"]])
        file_manifest.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "rows_after_basic_parse": int(len(frame)),
            }
        )

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.drop_duplicates(["timestamp", "asset"]).sort_values(["timestamp", "asset"])
    asset_count = int(panel["asset"].nunique())
    if asset_count < int(os.environ.get("QUANT_MIN_ASSETS", "15")):
        raise SystemExit(
            f"Validated panel has only {asset_count} assets; "
            f"minimum is {os.environ.get('QUANT_MIN_ASSETS', '15')}."
        )
    if len(panel) < int(os.environ.get("QUANT_MIN_ROWS", "10000")):
        raise SystemExit(f"Validated panel has only {len(panel)} rows; refusing to continue.")

    root = Path(os.environ.get("QUANT_DRIVE_ROOT", "/content/drive/MyDrive/trading-model-ai-lab"))
    output = Path(os.environ.get("QUANT_PANEL_OUTPUT", root / "data" / "prepared_intraday_panel.csv"))
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output, index=False)

    manifest = {
        "stage": "prepare",
        "input_files": file_manifest,
        "output": {
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": sha256(output),
            "rows": int(len(panel)),
            "assets": asset_count,
            "min_timestamp": panel["timestamp"].min().isoformat(),
            "max_timestamp": panel["timestamp"].max().isoformat(),
        },
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["output"], indent=2))


if __name__ == "__main__":
    main()
