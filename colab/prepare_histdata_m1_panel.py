"""Build a fail-closed wide 5-minute panel from HistData M1 ZIP archives.

HistData timestamps are fixed EST (not DST-adjusted). Naive source times are
localized to UTC-5 and emitted as UTC. Raw archives must match the acquisition
manifest byte-for-byte. Missing prices remain missing; nothing is interpolated.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

FROZEN_UNIVERSE = (
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD",
    "EURJPY", "XAUUSD", "XAGUSD", "SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP",
    "WTIUSD", "BCOUSD",
)
SOURCE_TIMEZONE = "Etc/GMT+5"
REQUIRED_COLUMNS = ("timestamp", "asset", "close")
VALID_ARCHIVE_STATUS = {"downloaded", "existing_verified"}


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def archive_path(raw_dir: Path, asset: str, year: int) -> Path:
    return raw_dir / f"histdata_{asset}_M1_{year}.zip"


def validate_download_manifest(
    manifest_path: Path, raw_dir: Path, assets: list[str], years: list[int]
) -> dict[tuple[str, int], str]:
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = pd.read_csv(manifest_path)
    required = {"asset", "year", "status", "sha256", "bytes"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"download manifest missing columns: {sorted(missing)}")
    manifest["asset"] = manifest["asset"].astype(str).str.upper()
    manifest["year"] = pd.to_numeric(manifest["year"], errors="raise").astype(int)
    wanted = {(asset, year) for asset in assets for year in years}
    selected = manifest[
        manifest.apply(lambda row: (row["asset"], row["year"]) in wanted, axis=1)
    ].copy()
    if selected.duplicated(["asset", "year"]).any():
        raise ValueError("duplicate asset/year rows in download manifest")
    present = set(zip(selected["asset"], selected["year"]))
    if present != wanted:
        raise ValueError(f"manifest coverage mismatch; missing={sorted(wanted - present)}")
    invalid = selected.loc[~selected["status"].isin(VALID_ARCHIVE_STATUS)]
    if not invalid.empty:
        pairs = list(zip(invalid["asset"], invalid["year"], invalid["status"]))
        raise ValueError(f"unverified archive status: {pairs}")

    verified: dict[tuple[str, int], str] = {}
    for row in selected.itertuples(index=False):
        path = archive_path(raw_dir, row.asset, int(row.year))
        if not path.exists():
            raise FileNotFoundError(path)
        actual_size = path.stat().st_size
        expected_size = int(row.bytes)
        if actual_size != expected_size:
            raise ValueError(f"archive byte-size mismatch: {path}")
        actual_sha = digest(path)
        if actual_sha != str(row.sha256):
            raise ValueError(f"archive SHA-256 mismatch: {path}")
        verified[(row.asset, int(row.year))] = actual_sha
    return verified


def load_archive(path: Path, asset: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("rb") as handle:
        if handle.read(4) != b"PK\x03\x04":
            raise ValueError(f"{path} is not a ZIP archive")
    with ZipFile(path) as archive:
        members = [name for name in archive.namelist()
                   if name.lower().endswith((".csv", ".txt"))]
        if len(members) != 1:
            raise ValueError(f"{path} must contain exactly one data member, found {members}")
        corrupt = archive.testzip()
        if corrupt:
            raise ValueError(f"{path} contains corrupt member {corrupt}")
        with archive.open(members[0]) as handle:
            raw = pd.read_csv(
                handle, sep=";", header=None, usecols=[0, 4],
                names=["source_timestamp", "close"],
                dtype={"source_timestamp": "string"}, low_memory=False,
            )
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    source = raw["source_timestamp"].str.strip()
    raw["timestamp"] = pd.to_datetime(
        source, format="%Y%m%d %H%M%S", errors="coerce"
    )
    if raw["timestamp"].isna().all():
        raw["timestamp"] = pd.to_datetime(
            source, format="%Y%m%d %H%M", errors="coerce"
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
        .last().dropna().rename("close").to_frame()
    )
    out["asset"] = asset
    return out.reset_index().loc[:, list(REQUIRED_COLUMNS)]


def to_wide_panel(long: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    if long.duplicated(["timestamp", "asset"]).any():
        raise ValueError("duplicate 5-minute asset/timestamp rows")
    wide = (
        long.pivot(index="timestamp", columns="asset", values="close")
        .reindex(columns=assets).sort_index()
    )
    if list(wide.columns) != assets or wide.columns.isna().any():
        raise ValueError("wide panel asset schema mismatch")
    if any(wide[asset].notna().sum() == 0 for asset in assets):
        raise ValueError("wide panel contains an empty asset")
    wide.columns.name = None
    return wide.reset_index()


def build_panel(
    raw_dir: Path, years: list[int], assets: list[str],
    verified: dict[tuple[str, int], str],
) -> tuple[pd.DataFrame, list[dict]]:
    frames: list[pd.DataFrame] = []
    coverage: list[dict] = []
    for asset in assets:
        for year in years:
            path = archive_path(raw_dir, asset, year)
            if (asset, year) not in verified:
                raise ValueError(f"archive was not manifest-verified: {asset} {year}")
            m1 = load_archive(path, asset)
            bars = resample_5m(m1)
            if bars.empty or year not in set(bars["timestamp"].dt.year):
                raise ValueError(f"{path} produced no UTC bars in requested year {year}")
            frames.append(bars)
            coverage.append({
                "asset": asset, "year": year, "archive": str(path),
                "sha256": verified[(asset, year)], "m1_rows": int(len(m1)),
                "bars_5m": int(len(bars)),
                "start_utc": bars["timestamp"].min().isoformat(),
                "end_utc": bars["timestamp"].max().isoformat(),
                "missing_values_introduced": 0,
                "source_timezone": "fixed_EST_UTC_minus_5",
            })
    long = pd.concat(frames, ignore_index=True).sort_values(["timestamp", "asset"])
    return to_wide_panel(long, assets), coverage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--download-manifest", type=Path, required=True)
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

    verified = validate_download_manifest(
        args.download_manifest, args.raw_dir, assets, years
    )
    panel, coverage = build_panel(args.raw_dir, years, assets, verified)
    if len(panel.columns) - 1 < args.min_assets:
        raise SystemExit("Panel failed minimum asset count after validation.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)
    observed = {asset: int(panel[asset].notna().sum()) for asset in assets}
    manifest = {
        "stage": "research043_histdata_m1_to_wide_5m",
        "download_manifest": {
            "path": str(args.download_manifest),
            "sha256": digest(args.download_manifest),
        },
        "output": {
            "path": str(args.output), "sha256": digest(args.output),
            "rows": int(len(panel)), "columns": list(panel.columns),
            "assets": assets, "asset_count": len(assets),
            "years_requested": years, "timezone": "UTC",
            "format": "wide_close", "observed_values_by_asset": observed,
            "missing_data_rule": "No interpolation or forward fill; NaN means no observed quote.",
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
    print(json.dumps({
        "output": manifest["output"],
        "coverage_file": str(coverage_path),
        "manifest_file": str(manifest_path),
    }, indent=2))


if __name__ == "__main__":
    main()
