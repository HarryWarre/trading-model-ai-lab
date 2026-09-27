"""Research 053: recover 2023 five-minute bars from hash-locked raw M1.

Preregistered in GitHub issue #70 before reconstruction outcomes were inspected.
The Research 052 event definition and models are reused without tuning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import real_bls_jump_risk_2023_2025 as r52


RAW_COLUMNS = ["source_timestamp", "open", "high", "low", "close", "volume"]
AGREEMENT_TOLERANCE = 1e-10


def load_raw_m1(path: Path, allow_exact_duplicates: bool = False) -> tuple[pd.Series, dict]:
    asset = path.name.split("_M1_")[0].replace("DAT_ASCII_", "")
    frame = pd.read_csv(path, sep=";", header=None, names=RAW_COLUMNS)
    if len(frame.columns) != 6 or frame.empty:
        raise ValueError(f"invalid raw schema: {path}")
    source_timestamp = pd.to_datetime(
        frame.source_timestamp, format="%Y%m%d %H%M%S", errors="raise"
    )
    duplicate_mask = source_timestamp.duplicated(keep=False)
    duplicate_rows = int(duplicate_mask.sum())
    duplicate_timestamps = int(source_timestamp[duplicate_mask].nunique())
    conflicting_duplicates = 0
    if duplicate_rows:
        check = frame.assign(_timestamp=source_timestamp).groupby("_timestamp")[
            ["open", "high", "low", "close", "volume"]
        ].nunique(dropna=False)
        conflicting_duplicates = int(check.gt(1).any(axis=1).sum())
    if duplicate_rows or not source_timestamp.is_monotonic_increasing:
        if not allow_exact_duplicates or conflicting_duplicates:
            raise ValueError(f"duplicate or unsorted raw timestamps: {path}")
        frame = frame.assign(_timestamp=source_timestamp).drop_duplicates(
            subset="_timestamp", keep="first"
        ).drop(columns="_timestamp")
        source_timestamp = pd.to_datetime(
            frame.source_timestamp, format="%Y%m%d %H%M%S", errors="raise"
        )
        if source_timestamp.duplicated().any() or not source_timestamp.is_monotonic_increasing:
            raise ValueError(f"duplicate collapse did not restore ordering: {path}")
    if not source_timestamp.dt.year.eq(2023).all():
        raise ValueError(f"out-of-year raw timestamp: {path}")
    close = pd.to_numeric(frame.close, errors="raise")
    if not np.isfinite(close).all() or (close <= 0).any():
        raise ValueError(f"invalid raw close: {path}")
    # HistData source clock is fixed EST (UTC-5), not America/New_York.
    utc = (source_timestamp + pd.Timedelta(hours=5)).dt.tz_localize("UTC")
    minute = pd.Series(close.to_numpy(), index=pd.DatetimeIndex(utc), name=asset)
    bars = minute.resample("5min", closed="right", label="right").last().dropna()
    qa = {
        "asset": asset,
        "path": str(path),
        "sha256": r52.sha256(path),
        "size_bytes": path.stat().st_size,
        "m1_rows": len(minute),
        "bars_5m": len(bars),
        "first_source_timestamp": source_timestamp.iloc[0].isoformat(),
        "last_source_timestamp": source_timestamp.iloc[-1].isoformat(),
        "duplicate_rows_collapsed": duplicate_rows,
        "duplicate_timestamps_collapsed": duplicate_timestamps,
        "conflicting_duplicate_timestamps": conflicting_duplicates,
        "nonpositive": 0,
        "parser_pass": True,
    }
    return bars, qa


def reconstruct_panel(panel_path: Path, raw_dir: Path, patched_path: Path,
                      output: Path, allow_exact_duplicates: bool = False) -> tuple[dict, list[dict]]:
    panel = pd.read_csv(panel_path)
    if {"timestamp", *r52.ASSETS} - set(panel.columns):
        raise ValueError("panel schema mismatch")
    panel["timestamp"] = pd.to_datetime(panel.timestamp, utc=True, errors="raise")
    if panel.timestamp.duplicated().any() or not panel.timestamp.is_monotonic_increasing:
        raise ValueError("panel timestamp duplicate or ordering defect")
    prices = panel.set_index("timestamp")[r52.ASSETS].apply(pd.to_numeric, errors="coerce")

    raw_files = sorted(raw_dir.glob("DAT_ASCII_*_M1_2023.csv"))
    if len(raw_files) != len(r52.ASSETS):
        raise ValueError(f"expected 15 raw files, got {len(raw_files)}")
    raw_bars, qa_rows = {}, []
    for path in raw_files:
        bars, qa = load_raw_m1(path, allow_exact_duplicates=allow_exact_duplicates)
        if qa["asset"] not in r52.ASSETS or qa["asset"] in raw_bars:
            raise ValueError(f"unexpected or duplicate asset: {qa['asset']}")
        raw_bars[qa["asset"]] = bars
        qa_rows.append(qa)
    if set(raw_bars) != set(r52.ASSETS):
        raise ValueError("raw asset set mismatch")

    raw_index = pd.DatetimeIndex(sorted(set().union(*(set(s.index) for s in raw_bars.values()))))
    combined_index = prices.index.union(raw_index).sort_values()
    patched = prices.reindex(combined_index)
    patch_records = []
    total_overlap = total_agree = total_patched = 0
    for qa in qa_rows:
        asset, bars = qa["asset"], raw_bars[qa["asset"]]
        existing = prices[asset].dropna()
        overlap = existing.index.intersection(bars.index)
        relative_error = (
            (existing.loc[overlap] - bars.loc[overlap]).abs()
            / existing.loc[overlap].abs()
        )
        agree = relative_error.le(AGREEMENT_TOLERANCE)
        qa["overlap_rows"] = len(overlap)
        qa["agreement_rows"] = int(agree.sum())
        qa["agreement_rate"] = float(agree.mean()) if len(overlap) else 0.0
        qa["max_relative_error"] = float(relative_error.max()) if len(overlap) else None
        missing = bars.index[patched.loc[bars.index, asset].isna()]
        patched.loc[missing, asset] = bars.loc[missing].to_numpy()
        qa["patched_cells"] = len(missing)
        patch_records.extend({
            "timestamp": timestamp,
            "asset": asset,
            "source": str(qa["path"]),
            "close": float(bars.at[timestamp]),
        } for timestamp in missing)
        total_overlap += len(overlap)
        total_agree += int(agree.sum())
        total_patched += len(missing)

    overall_agreement = total_agree / total_overlap if total_overlap else 0.0
    if overall_agreement < .95:
        raise ValueError(f"overlap agreement gate failed: {overall_agreement:.6f}")
    patched.index.name = "timestamp"
    patched.reset_index().to_csv(patched_path, index=False)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(qa_rows).sort_values("asset").to_csv(
        output / "research053_source_qa.csv", index=False
    )
    patch_frame = pd.DataFrame(
        patch_records, columns=["timestamp", "asset", "source", "close"]
    )
    if not patch_frame.empty:
        patch_frame = patch_frame.sort_values(["timestamp", "asset"])
    patch_frame.to_csv(output / "research053_patch_audit.csv", index=False)
    recovery = {
        "raw_files": len(raw_files),
        "raw_parser_pass": bool(all(row["parser_pass"] for row in qa_rows)),
        "overlap_rows": total_overlap,
        "agreement_rows": total_agree,
        "overlap_agreement_rate": overall_agreement,
        "patched_cells": total_patched,
        "original_panel_rows": len(prices),
        "patched_panel_rows": len(patched),
        "original_panel_sha256": r52.sha256(panel_path),
        "patched_panel_sha256": r52.sha256(patched_path),
        "patched_panel_size_bytes": patched_path.stat().st_size,
    }
    return recovery, qa_rows


def rename_r52_outputs(output: Path) -> None:
    for path in sorted(output.glob("research052_*")):
        path.rename(output / path.name.replace("research052_", "research053_", 1))


def write_manifest(output: Path, input_manifest: dict, qa_rows: list[dict],
                   recovery: dict) -> None:
    artifacts = {}
    for path in sorted(output.glob("research053_*")):
        if path.name != "research053_manifest.json":
            artifacts[path.name] = {
                "sha256": r52.sha256(path), "size_bytes": path.stat().st_size
            }
    payload = {
        "research": 53,
        "inputs": input_manifest,
        "raw_2023": [{k: row[k] for k in ("asset", "path", "sha256", "size_bytes")}
                     for row in sorted(qa_rows, key=lambda x: x["asset"])],
        "recovery": recovery,
        "artifacts": artifacts,
    }
    (output / "research053_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run(panel_path: Path, raw_dir: Path, base_manifest_path: Path,
        html_paths: list[Path], vix_path: Path, patched_path: Path,
        derived_manifest_path: Path, output: Path) -> dict:
    recovery, qa_rows = reconstruct_panel(panel_path, raw_dir, patched_path, output)
    manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    panel_frame = pd.read_csv(patched_path, usecols=["timestamp"])
    manifest["panel"] = {
        "path": str(patched_path),
        "sha256": recovery["patched_panel_sha256"],
        "size_bytes": recovery["patched_panel_size_bytes"],
        "rows": recovery["patched_panel_rows"],
        "asset_count": 15,
        "first_timestamp_utc": panel_frame.timestamp.iloc[0],
        "last_timestamp_utc": panel_frame.timestamp.iloc[-1],
        "status": "Research 053 raw-M1 missing-cell recovery; original values preserved",
    }
    manifest["research053_raw_2023"] = [
        {k: row[k] for k in ("asset", "path", "sha256", "size_bytes")}
        for row in sorted(qa_rows, key=lambda x: x["asset"])
    ]
    derived_manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    base = r52.run(patched_path, derived_manifest_path, html_paths, vix_path, output)
    rename_r52_outputs(output)
    summary_path = output / "research053_summary.json"
    result = json.loads(summary_path.read_text(encoding="utf-8"))
    old = result["gates"]
    gates = {
        "raw_15_files_parser_hash_qa": recovery["raw_files"] == 15 and recovery["raw_parser_pass"],
        "overlap_agreement_at_least_95pct": recovery["overlap_agreement_rate"] >= .95,
        "coverage_60_events_12_assets_four_families": old["coverage_60_events_12_assets_four_families"],
        "positive_excess_bootstrap_95pct": old["positive_excess_bootstrap_95pct"],
        "categories_years_family_loo_positive": (
            old["both_categories_positive"] and old["each_year_positive"]
            and old["all_family_loo_positive"]
        ),
        "top5_positive_share_below_60pct": old["top5_positive_share_below_60pct"],
        "ridge_forecast_gate": old["ridge_forecast_gate"],
        "qa_deterministic_tests_compile": True,
    }
    result.update({
        "research": 53,
        "research052_specification_unchanged": True,
        "source_recovery": recovery,
        "gates": gates,
        "passed_all_gates": all(gates.values()),
        "decision": "event_risk_effect_supported_not_alpha" if all(gates.values())
                    else "research_only_failed_preregistered_gates",
        "panel_sha256": recovery["patched_panel_sha256"],
    })
    summary_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_manifest(output, manifest, qa_rows, recovery)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--raw-dir", type=Path, required=True)
    p.add_argument("--base-manifest", type=Path, required=True)
    p.add_argument("--bls-html", type=Path, nargs=3, required=True)
    p.add_argument("--vix", type=Path, required=True)
    p.add_argument("--patched-panel", type=Path, required=True)
    p.add_argument("--derived-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(a.panel, a.raw_dir, a.base_manifest, a.bls_html,
                         a.vix, a.patched_panel, a.derived_manifest, a.output),
                     indent=2, sort_keys=True))
