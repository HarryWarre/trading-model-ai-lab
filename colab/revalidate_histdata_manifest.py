"""Revalidate HistData archives without overwriting the acquisition manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

DEFAULT_ASSETS = [
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD",
    "EURJPY", "XAUUSD", "XAGUSD", "SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP",
    "BCOUSD",
]
VALID_STATUS = {"downloaded", "existing_verified"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def revalidate(
    original_path: Path, raw_dir: Path, output_path: Path,
    assets: list[str], years: list[int],
) -> dict:
    original = pd.read_csv(original_path)
    required = {"asset", "year", "status", "sha256", "bytes"}
    missing = required - set(original.columns)
    if missing:
        raise ValueError(f"original manifest missing columns: {sorted(missing)}")
    original["asset"] = original["asset"].astype(str).str.upper()
    original["year"] = pd.to_numeric(original["year"], errors="raise").astype(int)
    wanted = {(asset, year) for asset in assets for year in years}
    selected = original[
        original.apply(lambda row: (row.asset, row.year) in wanted, axis=1)
    ].copy()
    if selected.duplicated(["asset", "year"]).any():
        raise ValueError("duplicate requested asset/year")
    found = set(zip(selected.asset, selected.year))
    if found != wanted:
        raise ValueError(f"original manifest coverage mismatch: {sorted(wanted - found)}")
    if not selected.status.isin(VALID_STATUS).all():
        bad = selected.loc[~selected.status.isin(VALID_STATUS), ["asset", "year", "status"]]
        raise ValueError(f"unverified original rows: {bad.to_dict('records')}")

    rows = []
    for row in selected.sort_values(["asset", "year"]).itertuples(index=False):
        path = raw_dir / f"histdata_{row.asset}_M1_{int(row.year)}.zip"
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("rb") as handle:
            if handle.read(4) != b"PK\x03\x04":
                raise ValueError(f"not a ZIP archive: {path}")
        with ZipFile(path) as archive:
            data_members = [
                name for name in archive.namelist()
                if name.lower().endswith((".csv", ".txt"))
            ]
            if len(data_members) != 1:
                raise ValueError(f"unexpected ZIP members in {path}: {data_members}")
            corrupt = archive.testzip()
            if corrupt:
                raise ValueError(f"corrupt ZIP member {corrupt} in {path}")
        actual_sha = digest(path)
        actual_bytes = path.stat().st_size
        rows.append({
            "asset": row.asset, "year": int(row.year),
            "status": "existing_verified", "archive": str(path),
            "sha256": actual_sha, "bytes": actual_bytes, "error": "",
            "original_sha256": str(row.sha256),
            "original_bytes": int(row.bytes),
            "changed_from_original": bool(
                actual_sha != str(row.sha256) or actual_bytes != int(row.bytes)
            ),
        })

    output = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    changed = output.loc[output.changed_from_original]
    summary = {
        "original_manifest": str(original_path),
        "original_manifest_sha256": digest(original_path),
        "revalidated_manifest": str(output_path),
        "revalidated_manifest_sha256": digest(output_path),
        "assets": len(assets), "years": years, "rows": len(output),
        "changed_rows": int(len(changed)),
        "changed_asset_years": [
            {"asset": row.asset, "year": int(row.year),
             "original_sha256": row.original_sha256, "sha256": row.sha256,
             "original_bytes": int(row.original_bytes), "bytes": int(row.bytes)}
            for row in changed.itertuples(index=False)
        ],
    }
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assets", default=",".join(DEFAULT_ASSETS))
    parser.add_argument("--years", default="2023,2024,2025")
    args = parser.parse_args()
    assets = [item.strip().upper() for item in args.assets.split(",") if item.strip()]
    years = [int(item) for item in args.years.split(",") if item.strip()]
    if len(set(assets)) != len(assets):
        raise SystemExit("duplicate assets")
    result = revalidate(args.original, args.raw_dir, args.output, assets, years)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
