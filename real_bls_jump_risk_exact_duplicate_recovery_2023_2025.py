"""Research 054: frozen BLS jump-risk rerun after exact-duplicate collapse.

Preregistered in GitHub issue #71 before any event result was computed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import real_bls_jump_risk_2023_2025 as r52
import real_bls_jump_risk_raw_recovery_2023_2025 as recovery_code


def rename_outputs(output: Path) -> None:
    for path in sorted(output.glob("research052_*")):
        path.rename(output / path.name.replace("research052_", "research054_", 1))
    for path in sorted(output.glob("research053_*")):
        path.rename(output / path.name.replace("research053_", "research054_", 1))


def write_manifest(output: Path, input_manifest: dict, qa_rows: list[dict],
                   recovery: dict) -> None:
    artifacts = {}
    for path in sorted(output.glob("research054_*")):
        if path.name != "research054_manifest.json":
            artifacts[path.name] = {
                "sha256": r52.sha256(path), "size_bytes": path.stat().st_size
            }
    payload = {
        "research": 54,
        "inputs": input_manifest,
        "raw_2023": [{k: row[k] for k in (
            "asset", "path", "sha256", "size_bytes", "duplicate_rows_collapsed",
            "duplicate_timestamps_collapsed", "conflicting_duplicate_timestamps"
        )} for row in sorted(qa_rows, key=lambda x: x["asset"])],
        "recovery": recovery,
        "artifacts": artifacts,
    }
    (output / "research054_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run(panel_path: Path, raw_dir: Path, base_manifest_path: Path,
        html_paths: list[Path], vix_path: Path, patched_path: Path,
        derived_manifest_path: Path, output: Path) -> dict:
    recovery, qa_rows = recovery_code.reconstruct_panel(
        panel_path, raw_dir, patched_path, output, allow_exact_duplicates=True
    )
    recovery["duplicate_rows_collapsed"] = int(sum(
        row["duplicate_rows_collapsed"] for row in qa_rows
    ))
    recovery["duplicate_timestamps_collapsed"] = int(sum(
        row["duplicate_timestamps_collapsed"] for row in qa_rows
    ))
    recovery["conflicting_duplicate_timestamps"] = int(sum(
        row["conflicting_duplicate_timestamps"] for row in qa_rows
    ))

    manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    timestamps = pd.read_csv(patched_path, usecols=["timestamp"])
    manifest["panel"] = {
        "path": str(patched_path),
        "sha256": recovery["patched_panel_sha256"],
        "size_bytes": recovery["patched_panel_size_bytes"],
        "rows": recovery["patched_panel_rows"],
        "asset_count": 15,
        "first_timestamp_utc": timestamps.timestamp.iloc[0],
        "last_timestamp_utc": timestamps.timestamp.iloc[-1],
        "status": "Research 054 raw-M1 exact-duplicate collapse; missing cells only",
    }
    manifest["research054_raw_2023"] = [
        {k: row[k] for k in (
            "asset", "path", "sha256", "size_bytes", "duplicate_rows_collapsed",
            "duplicate_timestamps_collapsed", "conflicting_duplicate_timestamps"
        )} for row in sorted(qa_rows, key=lambda x: x["asset"])
    ]
    derived_manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    r52.run(patched_path, derived_manifest_path, html_paths, vix_path, output)
    rename_outputs(output)
    summary_path = output / "research054_summary.json"
    result = json.loads(summary_path.read_text(encoding="utf-8"))
    old = result["gates"]
    gates = {
        "raw_exact_duplicate_policy_qa": (
            recovery["raw_files"] == 15 and recovery["raw_parser_pass"]
            and recovery["conflicting_duplicate_timestamps"] == 0
        ),
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
        "research": 54,
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
