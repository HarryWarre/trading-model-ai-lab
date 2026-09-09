"""Fail-closed preparation for wide or long intraday CSV panels.

The current Drive file is wide:
timestamp,AUDUSD,EURUSD,...,XAUUSD
This stage also accepts long data with asset/symbol and close/price columns.
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


def normalize(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    if frame.empty:
        raise SystemExit(f"Empty raw file: {path}")
    time_col = choose_column(frame.columns, ["timestamp", "datetime", "date", "time"])
    if time_col is None:
        raise SystemExit(f"{path} has no timestamp column.")

    asset_col = choose_column(frame.columns, ["asset", "symbol", "ticker", "instrument"])
    close_col = choose_column(frame.columns, ["close", "price", "mid", "bidclose"])

    if asset_col is not None and close_col is not None:
        out = frame.rename(
            columns={time_col: "timestamp", asset_col: "asset", close_col: "close"}
        )[["timestamp", "asset", "close"]].copy()
    else:
        # Wide panel: one price column per asset.
        value_cols = [c for c in frame.columns if c != time_col]
        if len(value_cols) < 2:
            raise SystemExit(
                f"{path} is neither a long panel nor a wide multi-asset panel."
            )
        out = frame.rename(columns={time_col: "timestamp"}).melt(
            id_vars=["timestamp"], value_vars=value_cols,
            var_name="asset", value_name="close"
        )

    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["asset"] = out["asset"].astype(str).str.strip()
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    return out.dropna(subset=["timestamp", "asset", "close"])


def main() -> None:
    frames = []
    file_manifest = []
    for path in raw_paths():
        raw = pd.read_csv(path)
        parsed = normalize(raw, path)
        frames.append(parsed)
        file_manifest.append({
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "rows_after_parse": int(len(parsed)),
        })

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.drop_duplicates(["timestamp", "asset"]).sort_values(
        ["timestamp", "asset"]
    )
    asset_count = int(panel["asset"].nunique())
    min_assets = int(os.environ.get("QUANT_MIN_ASSETS", "15"))
    min_rows = int(os.environ.get("QUANT_MIN_ROWS", "10000"))
    if asset_count < min_assets:
        raise SystemExit(f"Validated panel has {asset_count} assets; minimum is {min_assets}.")
    if len(panel) < min_rows:
        raise SystemExit(f"Validated panel has {len(panel)} rows; minimum is {min_rows}.")

    root = Path(os.environ.get(
        "QUANT_DRIVE_ROOT", "/content/drive/MyDrive/trading-model-ai-lab"
    ))
    output = Path(os.environ.get(
        "QUANT_PANEL_OUTPUT", root / "data" / "prepared_intraday_panel.csv"
    ))
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output, index=False)

    manifest = {
        "stage": "prepare",
        "input_files": file_manifest,
        "input_format": "wide_or_long_csv",
        "output": {
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": sha256(output),
            "rows": int(len(panel)),
            "assets": asset_count,
            "asset_names": sorted(panel["asset"].unique().tolist()),
            "timezone": "UTC",
            "min_timestamp": panel["timestamp"].min().isoformat(),
            "max_timestamp": panel["timestamp"].max().isoformat(),
        },
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["output"], indent=2))


if __name__ == "__main__":
    main()
