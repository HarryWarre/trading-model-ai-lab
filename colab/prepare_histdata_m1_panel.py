"""Build a fail-closed 5-minute panel from HistData M1 ZIP archives.

Research 039 uses this stage before any event model.  HistData's documented
timestamps are fixed EST (not DST-adjusted), therefore naive source times are
localized to UTC-5 and emitted as UTC.  The script never fills missing minutes
or silently replaces an unavailable asset.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

FROZEN_UNIVERSE = (
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD",
    "EURJPY", "XAUUSD", "XAGUSD", "SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP",
    "WTIUSD", "BCOUSD",
)
SOURCE_TIMEZONE = "Etc/GMT+5"  # Fixed EST: UTC-5, as documented by HistData.
REQUIRED_COLUMNS = ("timestamp", "asset", "close")


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def archive_path(raw_dir: Path, asset: str, year: int) -> Path:
    return raw_dir / f"histdata_{asset}_M1_{year}.zip"


def load_archive(path: Path, asset: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.read_bytes()[:4] != b"PK\x03\x04":
        raise ValueError(f"{path} is not a ZIP archive")
    with ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{path} must contain exactly one CSV member, found {members}")
        if archive.testzip():
            raise ValueError(f"{path} contains a corrupt member")
        with archive.open(members[0]) as handle:
            raw = pd.read_csv(
                handle,
                sep=";",
                header=None,
                usecols=[0, 4],
                names=["source_timestamp", "close"],
                dtype={"source_timestamp": "string"},
                low_memory=False,
            )
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    raw["timestamp"] = pd.to_datetime(
        raw["source_timestamp"].str.strip(),
        format="%Y%m%d %H%M%S",
        errors="coerce",
    )
    if raw["timestamp"].isna().all():
        # A few source members omit seconds; accept the known M1 alternative only.
        raw["timestamp"] = pd.to_datetime(
            raw["source_timestamp"].str.strip(),
            format="%Y%m%d %H%M",
            errors="coerce",
        )
    raw = raw.dropna(subset=["timestamp", "close"])
    if raw.empty:
        raise ValueError(f"{path} has no parseable timestamp/close rows")
    raw["timestamp"] = raw["timestamp"].dt.tz_localize(
        SOURCE_TIMEZONE, ambiguous="raise", nonexistent="raise"
    ).dt.tz_convert("UTC")
    raw["asset"] = asset
    if raw.duplicated("timestamp").any():
        raise ValueError(f"{path} contains duplicate M1 timestamps")
    return raw.loc[:, list(REQUIRED_COLUMNS)].sort_values("timestamp")


def resample_5m(m1: pd.DataFrame) -> pd.DataFrame:
    asset = m1["asset"].iloc[0]
    out = (
        m1.set_index("timestamp")["close"]
        .resample("5min", label="right", closed="right")
        .last()
        .dropna()
        .rename("close")
        .to_frame()
    )
    out["asset"] = asset
    return out.reset_index().loc[:, list(REQUIRED_COLUMNS)]


def build_panel(raw_dir: Path, years: list[int], assets: list[str]) -> tuple[pd.DataFrame, list[dict]]:
    frames: list[pd.DataFrame] = []
    coverage: list[dict] = []
    for asset in assets:
        for year in years:
            path = archive_path(raw_dir, asset, year)
            m1 = load_archive(path, asset)
            panel = resample_5m(m1)
            if panel.empty:
                raise ValueError(f"{path} produced no 5-minute bars")
            actual_years = set(panel["timestamp"].dt.year)
            if year not in actual_years:
                raise ValueError(f"{path} has no UTC bars in requested year {year}")
            frames.append(panel)
            coverage.append({
                "asset": asset,
                "year": year,
                "archive": str(path),
                "sha256": digest(path),
                "m1_rows": int(len(m1)),
                "bars_5m": int(len(panel)),
                "start_utc": panel["timestamp"].min().isoformat(),
                "end_utc": panel["timestamp"].max().isoformat(),
                "missing_values_introduced": 0,
                "source_timezone": "fixed_EST_UTC_minus_5",
            })
    long = pd.concat(frames, ignore_index=True)
    if long.duplicated(["timestamp", "asset"]).any():
        raise ValueError("duplicate 5-minute asset/timestamp rows after concatenation")
    return long.sort_values(["timestamp", "asset"]).reset_index(drop=True), coverage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--years", default="2023,2024,2025")
    parser.add_argument("--assets", default=",".join(x for x in FROZEN_UNIVERSE if x != "WTIUSD"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-assets", type=int, default=15)
    args = parser.parse_args()

    years = [int(x) for x in args.years.split(",") if x.strip()]
    assets = [x.strip().upper() for x in args.assets.split(",") if x.strip()]
    if len(set(assets)) != len(assets):
        raise SystemExit("Duplicate assets requested.")
    unknown = sorted(set(assets) - set(FROZEN_UNIVERSE))
    if unknown:
        raise SystemExit(f"Unknown frozen-universe assets: {unknown}")
    if len(assets) < args.min_assets:
        raise SystemExit(f"Requested {len(assets)} assets below min-assets {args.min_assets}.")

    panel, coverage = build_panel(args.raw_dir, years, assets)
    if panel["asset"].nunique() < args.min_assets:
        raise SystemExit("Panel failed minimum asset count after validation.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)

    manifest = {
        "stage": "research039_histdata_m1_to_5m",
        "output": {
            "path": str(args.output),
            "sha256": digest(args.output),
            "rows": int(len(panel)),
            "assets": sorted(panel["asset"].unique().tolist()),
            "years_requested": years,
            "timezone": "UTC",
            "missing_data_rule": "No interpolation; only observed last M1 close per 5-minute bin.",
        },
        "coverage": coverage,
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    coverage_path = args.output.with_name(args.output.stem + "_coverage.csv")
    with coverage_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=coverage[0].keys())
        writer.writeheader()
        writer.writerows(coverage)
    print(json.dumps({"output": manifest["output"], "coverage_file": str(coverage_path)}, indent=2))


if __name__ == "__main__":
    main()
