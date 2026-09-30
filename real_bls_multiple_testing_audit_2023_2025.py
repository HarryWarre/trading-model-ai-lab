"""Research 058: joint multiple-testing audit of BLS event-risk findings.

Preregistered in GitHub issue #75 before the three outcome files were joined.
This is a non-trading audit and does not recompute any price-derived outcome.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


RESEARCH = 58
DRAWS = 100_000
SEED = 20260930
MIN_COMMON_EVENTS = 45
ALPHA = 0.05
INPUTS = {
    "h052_full_window_jump": {
        "research": 52,
        "path": "results/research052/research052_event_portfolio.csv",
        "manifest": "results/research052/research052_manifest.json",
        "column": "excess_bps",
        "unit": "bps",
    },
    "h056_cojump_breadth": {
        "research": 56,
        "path": "results/research056/research056_events.csv",
        "manifest": "results/research056/research056_manifest.json",
        "column": "breadth_difference",
        "unit": "fraction",
    },
    "h057_delayed_jump": {
        "research": 57,
        "path": "results/research057/research057_event_portfolio.csv",
        "manifest": "results/research057/research057_manifest.json",
        "column": "delayed_excess_bps",
        "unit": "bps",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_input(root: Path, spec: dict) -> dict:
    path = root / spec["path"]
    manifest_path = root / spec["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded = manifest["artifacts"][path.name]
    actual_hash = sha256(path)
    if actual_hash != recorded["sha256"]:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual_hash} != {recorded['sha256']}")
    if path.stat().st_size != recorded["size_bytes"]:
        raise ValueError(f"size mismatch for {path}")
    return {
        "path": spec["path"],
        "sha256": actual_hash,
        "size_bytes": path.stat().st_size,
        "manifest": spec["manifest"],
        "manifest_sha256": sha256(manifest_path),
    }


def load_family(root: Path) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    frames = []
    provenance = {}
    memberships = []
    for hypothesis, spec in INPUTS.items():
        provenance[hypothesis] = validate_input(root, spec)
        raw = pd.read_csv(root / spec["path"])
        required = {"event_id", "year", "release_timestamp_utc", spec["column"]}
        missing = required - set(raw.columns)
        if missing:
            raise ValueError(f"{spec['path']} missing columns: {sorted(missing)}")
        if raw.event_id.duplicated().any():
            raise ValueError(f"duplicate event_id in {spec['path']}")
        values = pd.to_numeric(raw[spec["column"]], errors="raise")
        if not np.isfinite(values).all():
            raise ValueError(f"non-finite outcome in {spec['path']}")
        frame = raw[["event_id", "year", "release_timestamp_utc"]].copy()
        frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype(int)
        frame["release_timestamp_utc"] = pd.to_datetime(frame["release_timestamp_utc"], utc=True)
        frame[hypothesis] = values.astype(float)
        frames.append(frame)
        memberships.extend({"event_id": event_id, "hypothesis": hypothesis, "included": True}
                           for event_id in frame.event_id)

    common = frames[0]
    for frame in frames[1:]:
        common = common.merge(frame, on=["event_id", "year", "release_timestamp_utc"], how="inner")
    common = common.sort_values(["release_timestamp_utc", "event_id"]).reset_index(drop=True)
    if common.empty:
        raise ValueError("common event intersection is empty")

    common_ids = set(common.event_id)
    exclusions = []
    for hypothesis, spec in INPUTS.items():
        raw = pd.read_csv(root / spec["path"], usecols=["event_id"])
        for event_id in sorted(set(raw.event_id) - common_ids):
            exclusions.append({"hypothesis": hypothesis, "event_id": event_id,
                               "reason": "not_in_three_hypothesis_intersection"})
    return common, provenance, pd.DataFrame(exclusions)


def studentized(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    standard_error = values.std(axis=0, ddof=1) / np.sqrt(values.shape[0])
    if np.any(~np.isfinite(standard_error)) or np.any(standard_error <= 0):
        raise ValueError("studentization requires finite, nonzero standard errors")
    return values.mean(axis=0) / standard_error


def shared_block_signs(n_events: int, draws: int = DRAWS, seed: int = SEED) -> np.ndarray:
    if n_events < 2:
        raise ValueError("at least two events required")
    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(n_events / 2))
    block_signs = rng.choice(np.array([-1.0, 1.0]), size=(draws, blocks))
    return np.repeat(block_signs, 2, axis=1)[:, :n_events]


def randomization_statistics(values: np.ndarray, signs: np.ndarray) -> np.ndarray:
    signed = signs[:, :, None] * values[None, :, :]
    se = signed.std(axis=1, ddof=1) / np.sqrt(values.shape[0])
    means = signed.mean(axis=1)
    if np.any(se <= 0):
        raise ValueError("randomized standard error is zero")
    return means / se


def holm_adjust(raw_p: np.ndarray) -> np.ndarray:
    raw_p = np.asarray(raw_p, dtype=float)
    order = np.argsort(raw_p, kind="stable")
    adjusted = np.empty_like(raw_p)
    running = 0.0
    m = len(raw_p)
    for rank, index in enumerate(order):
        running = max(running, (m - rank) * raw_p[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def romano_wolf(observed: np.ndarray, randomized: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return marginal and stepdown max-T adjusted one-sided p-values."""
    observed = np.asarray(observed, dtype=float)
    order = np.argsort(-observed, kind="stable")
    raw = (1 + (randomized >= observed[None, :]).sum(axis=0)) / (len(randomized) + 1)
    adjusted = np.empty_like(observed)
    running = 0.0
    for rank, index in enumerate(order):
        remaining = order[rank:]
        maxima = randomized[:, remaining].max(axis=1)
        candidate = (1 + np.count_nonzero(maxima >= observed[index])) / (len(randomized) + 1)
        running = max(running, candidate)
        adjusted[index] = min(1.0, running)
    return raw, adjusted


def top_positive_share(values: np.ndarray, count: int = 5) -> float:
    positive = np.asarray(values, dtype=float)
    positive = positive[positive > 0]
    if not len(positive):
        return float("nan")
    return float(np.sort(positive)[-count:].sum() / positive.sum())


def artifact_manifest(output: Path, provenance: dict) -> None:
    artifacts = {}
    for path in sorted(output.glob("research058_*")):
        if path.name != "research058_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    payload = {
        "research": RESEARCH,
        "preregistered_issue": 75,
        "method": {"draws": DRAWS, "seed": SEED, "block_events": 2,
                   "primary_adjustment": "Romano-Wolf stepdown max-T one-sided"},
        "inputs": provenance,
        "artifacts": artifacts,
    }
    (output / "research058_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run(root: Path, output: Path, qa_passed: bool = False) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    common, provenance, exclusions = load_family(root)
    hypotheses = list(INPUTS)
    values = common[hypotheses].to_numpy(dtype=float)
    observed = studentized(values)
    signs = shared_block_signs(len(common))
    randomized = randomization_statistics(values, signs)
    raw_p, rw_p = romano_wolf(observed, randomized)
    holm_p = holm_adjust(raw_p)

    hypothesis_rows = []
    for pos, hypothesis in enumerate(hypotheses):
        vector = values[:, pos]
        hypothesis_rows.append({
            "hypothesis": hypothesis,
            "source_research": INPUTS[hypothesis]["research"],
            "unit": INPUTS[hypothesis]["unit"],
            "events": len(common),
            "mean": float(vector.mean()),
            "standard_error": float(vector.std(ddof=1) / np.sqrt(len(vector))),
            "studentized_t": float(observed[pos]),
            "raw_shared_sign_p": float(raw_p[pos]),
            "romano_wolf_p": float(rw_p[pos]),
            "holm_p": float(holm_p[pos]),
            "top5_positive_share": top_positive_share(vector),
            "positive_events": int((vector > 0).sum()),
        })
    hypothesis_frame = pd.DataFrame(hypothesis_rows)

    year_rows = []
    for omitted in sorted(common.year.unique()):
        retained = common.loc[common.year.ne(omitted)]
        for hypothesis in hypotheses:
            year_rows.append({"omitted_year": int(omitted), "hypothesis": hypothesis,
                              "events": len(retained), "mean": float(retained[hypothesis].mean())})
    year_frame = pd.DataFrame(year_rows)

    dependence_rows = []
    for left in hypotheses:
        for right in hypotheses:
            dependence_rows.append({
                "left": left,
                "right": right,
                "pearson": float(common[left].corr(common[right], method="pearson")),
                "spearman": float(common[left].corr(common[right], method="spearman")),
            })
    dependence_frame = pd.DataFrame(dependence_rows)

    common_export = common.copy()
    common_export["release_timestamp_utc"] = common_export.release_timestamp_utc.map(
        lambda value: value.isoformat()
    )
    common_export.to_csv(output / "research058_common_events.csv", index=False, float_format="%.12g")
    exclusions.to_csv(output / "research058_exclusions.csv", index=False)
    hypothesis_frame.to_csv(output / "research058_hypotheses.csv", index=False, float_format="%.12g")
    year_frame.to_csv(output / "research058_year_leave_out.csv", index=False, float_format="%.12g")
    dependence_frame.to_csv(output / "research058_dependence.csv", index=False, float_format="%.12g")

    years = sorted(int(x) for x in common.year.unique())
    gates = {
        "g1_common_coverage": len(common) >= MIN_COMMON_EVENTS and years == [2023, 2024, 2025],
        "g2_all_means_positive": bool((hypothesis_frame["mean"] > 0).all()),
        "g3_all_romano_wolf_p_lt_005": bool((hypothesis_frame.romano_wolf_p < ALPHA).all()),
        "g4_all_holm_p_lt_005": bool((hypothesis_frame.holm_p < ALPHA).all()),
        "g5_all_leave_one_year_positive": bool((year_frame["mean"] > 0).all()),
        "g6_all_top5_share_lt_060": bool((hypothesis_frame.top5_positive_share < 0.60).all()),
        "g7_input_hashes_and_exclusions_exported": True,
        "g8_tests_compile_byte_identical_rerun": bool(qa_passed),
    }
    summary = {
        "research": RESEARCH,
        "preregistered_issue": 75,
        "decision": "pass_joint_event_risk_evidence_not_alpha" if qa_passed else "pending_external_qa_gate",
        "common_events": len(common),
        "years": years,
        "source_event_counts": {hypothesis: int(pd.read_csv(root / spec["path"]).shape[0])
                                for hypothesis, spec in INPUTS.items()},
        "hypotheses": hypothesis_rows,
        "pairwise_pearson": {
            f"{hypotheses[i]}__{hypotheses[j]}": float(common[hypotheses[i]].corr(common[hypotheses[j]]))
            for i in range(len(hypotheses)) for j in range(i + 1, len(hypotheses))
        },
        "gates": gates,
        "gates_passed_before_external_qa": int(sum(gates.values())),
        "gates_total": len(gates),
        "trades": 0,
        "trade_legs": 0,
        "turnover": 0.0,
        "cost_sensitivity_return": {"0x": 0.0, "1x_4pip": 0.0, "2x_8pip": 0.0, "4x_16pip": 0.0},
        "interpretation": "joint non-directional event-risk evidence only; not alpha or production",
    }
    (output / "research058_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    artifact_manifest(output, provenance)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("results/research058"))
    parser.add_argument("--qa-passed", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.output, qa_passed=args.qa_passed)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
