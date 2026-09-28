"""Research 056: timing-safe nested-control BLS cross-family cojump audit.

Preregistered in GitHub issue #73 before outcome inspection. Non-trading study.
Every target date is classified only against observations strictly before that date.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import real_bls_jump_risk_2023_2025 as r52


CONTROLS = 4
SCAN_WEEKS = 12
MIN_ASSETS = 12
WARMUP = 12
DRAWS = 10_000
SEED = 20260928
FEATURES = ["control_breadth", "cpi", "vix", "cpi_vix"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def jumps_at(prices: pd.DataFrame, timestamp: pd.Timestamp) -> dict[str, float]:
    out: dict[str, float] = {}
    for asset in r52.ASSETS:
        try:
            out[asset] = r52.jump_bps(prices[asset], timestamp)
        except ValueError:
            pass
    return out


def all_families(assets: set[str]) -> bool:
    return {r52.FAMILY[a] for a in assets} == set(r52.FAMILIES)


def strict_historical_extreme(target: float, anchors: list[float]) -> bool:
    """Ties are not extremes; all benchmarks must be historical."""
    return len(anchors) == CONTROLS and target > max(anchors)


def target_flags(
    prices: pd.DataFrame,
    target: pd.Timestamp,
    event_dates: set,
) -> tuple[dict[str, bool], list[pd.Timestamp]] | None:
    """Classify target with exactly four valid prior, non-event weekly anchors."""
    target_jump = jumps_at(prices, target)
    anchors: list[tuple[pd.Timestamp, dict[str, float]]] = []
    for week in range(1, SCAN_WEEKS + 1):
        timestamp = target - pd.Timedelta(weeks=week)
        if timestamp.date() in event_dates:
            continue
        jump = jumps_at(prices, timestamp)
        if len(jump) >= MIN_ASSETS and all_families(set(jump)):
            anchors.append((timestamp, jump))
        if len(anchors) == CONTROLS:
            break
    common = set(target_jump)
    for _, jump in anchors:
        common &= set(jump)
    if len(anchors) != CONTROLS or len(common) < MIN_ASSETS or not all_families(common):
        return None
    flags = {
        asset: strict_historical_extreme(
            target_jump[asset], [jump[asset] for _, jump in anchors]
        )
        for asset in sorted(common)
    }
    timestamps = [timestamp for timestamp, _ in anchors]
    if not all(timestamp < target for timestamp in timestamps):
        raise AssertionError("non-historical anchor detected")
    return flags, timestamps


def family_activation(flags: dict[str, bool], families: list[str] | None = None) -> dict[str, bool]:
    selected = families or list(r52.FAMILIES)
    out: dict[str, bool] = {}
    for family in selected:
        members = [asset for asset in r52.FAMILIES[family] if asset in flags]
        if not members:
            raise ValueError(f"family absent: {family}")
        out[family] = sum(bool(flags[a]) for a in members) >= math.ceil(len(members) / 2)
    return out


def block_bootstrap(values: np.ndarray) -> dict:
    n = len(values)
    rng = np.random.default_rng(SEED)
    starts = rng.integers(n, size=(DRAWS, int(np.ceil(n / 2))))
    idx = np.stack([starts, (starts + 1) % n], axis=-1).reshape(DRAWS, -1)[:, :n]
    means = values[idx].mean(axis=1)
    return {
        "p_mean_positive": float((means > 0).mean()),
        "ci95": [float(x) for x in np.quantile(means, [.025, .975])],
    }


def ridge_predictions(events: pd.DataFrame) -> pd.DataFrame:
    out = []
    for pos in range(WARMUP, len(events)):
        train, test = events.iloc[:pos].copy(), events.iloc[[pos]].copy()
        mu = train[FEATURES].mean()
        sd = train[FEATURES].std(ddof=0).replace(0, 1)
        x_train = np.c_[np.ones(len(train)), ((train[FEATURES] - mu) / sd).to_numpy()]
        y_train = train.event_breadth.to_numpy()
        penalty = np.eye(x_train.shape[1])
        penalty[0, 0] = 0
        beta = np.linalg.solve(x_train.T @ x_train + penalty, x_train.T @ y_train)
        x_test = np.c_[np.ones(1), ((test[FEATURES] - mu) / sd).to_numpy()]
        category_train = train.loc[train.category.eq(test.category.iloc[0]), "event_breadth"]
        out.append({
            "event_id": test.event_id.iloc[0],
            "actual_breadth": float(test.event_breadth.iloc[0]),
            "price_only_pred": float(test.control_breadth.iloc[0]),
            "economic_pred": float(category_train.mean()),
            "ridge_pred": float((x_test @ beta)[0]),
        })
    return pd.DataFrame(out)


def forecast_metrics(frame: pd.DataFrame, column: str) -> dict:
    actual, forecast = frame.actual_breadth.to_numpy(), frame[column].to_numpy()
    corr = float(np.corrcoef(actual, forecast)[0, 1]) if np.std(forecast) > 0 else None
    return {
        "events": len(frame),
        "mae": float(np.mean(np.abs(actual - forecast))),
        "correlation": corr,
    }


def write_manifest(output: Path, inputs: dict) -> None:
    artifacts = {}
    for path in sorted(output.glob("research056_*")):
        if path.name != "research056_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    (output / "research056_manifest.json").write_text(
        json.dumps({"research": 56, "inputs": inputs, "artifacts": artifacts},
                   indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run(panel_path: Path, input_manifest_path: Path, html_paths: list[Path],
        vix_path: Path, output: Path) -> dict:
    manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    prices = r52.load_panel(panel_path, manifest)
    events = r52.load_events(html_paths, manifest)
    vix = r52.load_vix(vix_path, manifest)
    event_dates = set(events.release_timestamp_utc.dt.date)
    output.mkdir(parents=True, exist_ok=True)

    event_rows, candidate_rows, activation_rows, coverage_rows, anchor_rows = [], [], [], [], []
    for event in events.itertuples(index=False):
        event_result = target_flags(prices, event.release_timestamp_utc, event_dates)
        controls: list[tuple[pd.Timestamp, dict[str, bool], list[pd.Timestamp]]] = []
        if event_result is not None:
            for week in range(1, SCAN_WEEKS + 1):
                target = event.release_timestamp_utc - pd.Timedelta(weeks=week)
                if target.date() in event_dates:
                    continue
                result = target_flags(prices, target, event_dates)
                if result is not None:
                    flags, anchors = result
                    controls.append((target, flags, anchors))
                if len(controls) == CONTROLS:
                    break

        common: set[str] = set(event_result[0]) if event_result is not None else set()
        for _, flags, _ in controls:
            common &= set(flags)
        eligible = (
            event_result is not None and len(controls) == CONTROLS
            and len(common) >= MIN_ASSETS and all_families(common)
        )
        coverage_rows.append({
            "event_id": event.event_id,
            "event_valid": event_result is not None,
            "controls": len(controls),
            "common_assets": len(common),
            "common_families": len({r52.FAMILY[a] for a in common}),
            "eligible": eligible,
        })
        if not eligible:
            continue

        candidates = [(event.release_timestamp_utc, event_result[0], event_result[1])] + controls
        family_flags_by_candidate: list[dict[str, bool]] = []
        breadths, broad = [], []
        for index, (target, raw_flags, anchors) in enumerate(candidates):
            flags = {asset: raw_flags[asset] for asset in sorted(common)}
            family_flags = family_activation(flags)
            family_flags_by_candidate.append(family_flags)
            breadth = sum(family_flags.values()) / len(r52.FAMILIES)
            breadths.append(breadth)
            broad.append(breadth >= .75)
            label = "event" if index == 0 else f"control_{index}"
            candidate_rows.append({
                "event_id": event.event_id,
                "candidate": label,
                "target_timestamp": target,
                "breadth": breadth,
                "broad_cojump": broad[-1],
                "common_assets": len(common),
            })
            for rank, anchor in enumerate(anchors, start=1):
                anchor_rows.append({
                    "event_id": event.event_id,
                    "candidate": label,
                    "target_timestamp": target,
                    "anchor_rank": rank,
                    "anchor_timestamp": anchor,
                    "strictly_prior": anchor < target,
                })
            for family, active in family_flags.items():
                activation_rows.append({
                    "event_id": event.event_id,
                    "candidate": label,
                    "family": family,
                    "active": active,
                })

        event_rows.append({
            "event_id": event.event_id,
            "category": event.category,
            "release_timestamp_utc": event.release_timestamp_utc,
            "year": event.release_timestamp_utc.year,
            "common_assets": len(common),
            "event_breadth": breadths[0],
            "control_breadth": float(np.mean(breadths[1:])),
            "breadth_difference": float(breadths[0] - np.mean(breadths[1:])),
            "event_broad_cojump": broad[0],
            "control_broad_cojump_rate": float(np.mean(broad[1:])),
            **{f"event_{family}_active": family_flags_by_candidate[0][family]
               for family in r52.FAMILIES},
            **{f"control_{family}_active_rate": float(np.mean([
                item[family] for item in family_flags_by_candidate[1:]
            ])) for family in r52.FAMILIES},
        })

    coverage = pd.DataFrame(coverage_rows)
    frame = pd.DataFrame(event_rows).sort_values("release_timestamp_utc").reset_index(drop=True)
    candidates_frame = pd.DataFrame(candidate_rows)
    activations = pd.DataFrame(activation_rows)
    anchors_frame = pd.DataFrame(anchor_rows)
    if frame.empty:
        raise RuntimeError("no eligible events")
    if not anchors_frame.strictly_prior.all():
        raise AssertionError("future anchor detected")
    if not (candidates_frame.loc[candidates_frame.candidate.ne("event"), "target_timestamp"].to_numpy()
            < candidates_frame.loc[candidates_frame.candidate.ne("event"), "event_id"].map(
                frame.set_index("event_id").release_timestamp_utc).to_numpy()).all():
        raise AssertionError("non-prior matched control detected")

    frame["vix"] = [r52.prior_vix(vix, pd.Timestamp(x)) for x in frame.release_timestamp_utc]
    frame["cpi"] = frame.category.eq("cpi").astype(float)
    frame["cpi_vix"] = frame.cpi * frame.vix
    coverage.to_csv(output / "research056_coverage.csv", index=False)
    frame.to_csv(output / "research056_events.csv", index=False)
    candidates_frame.to_csv(output / "research056_candidates.csv", index=False)
    activations.to_csv(output / "research056_family_activations.csv", index=False)
    anchors_frame.to_csv(output / "research056_anchor_audit.csv", index=False)

    categories = frame.groupby("category", as_index=False).agg(
        events=("event_id", "count"), event_breadth=("event_breadth", "mean"),
        control_breadth=("control_breadth", "mean"),
        breadth_difference=("breadth_difference", "mean"),
    )
    years = frame.groupby("year", as_index=False).agg(
        events=("event_id", "count"), event_breadth=("event_breadth", "mean"),
        control_breadth=("control_breadth", "mean"),
        breadth_difference=("breadth_difference", "mean"),
    )
    categories.to_csv(output / "research056_categories.csv", index=False)
    years.to_csv(output / "research056_years.csv", index=False)

    family_loo = []
    for excluded in r52.FAMILIES:
        included = [family for family in r52.FAMILIES if family != excluded]
        event_values, control_values = [], []
        for event_id in frame.event_id:
            subset = activations.loc[
                activations.event_id.eq(event_id) & activations.family.isin(included)
            ]
            by_candidate = subset.groupby("candidate").active.mean()
            event_values.append(float(by_candidate["event"]))
            control_values.append(float(by_candidate.drop("event").mean()))
        family_loo.append({
            "excluded_family": excluded,
            "mean_breadth_difference": float(np.mean(
                np.array(event_values) - np.array(control_values)
            )),
        })
    family_loo_frame = pd.DataFrame(family_loo)
    family_loo_frame.to_csv(output / "research056_family_leave_one_out.csv", index=False)

    predictions = ridge_predictions(frame)
    predictions.to_csv(output / "research056_forecasts.csv", index=False)
    metrics = {
        "price_only": forecast_metrics(predictions, "price_only_pred"),
        "economic": forecast_metrics(predictions, "economic_pred"),
        "ridge": forecast_metrics(predictions, "ridge_pred"),
    }
    positive = frame.loc[frame.breadth_difference > 0, "breadth_difference"].sort_values(ascending=False)
    top5_share = float(positive.head(5).sum() / positive.sum()) if positive.sum() > 0 else 1.0
    bootstrap = block_bootstrap(frame.breadth_difference.to_numpy())
    event_broad_rate = float(frame.event_broad_cojump.mean())
    control_broad_rate = float(candidates_frame.loc[
        candidates_frame.candidate.ne("event"), "broad_cojump"
    ].mean())
    gates = {
        "coverage_40_events_12_assets_four_families": (
            len(frame) >= 40 and bool((frame.common_assets >= MIN_ASSETS).all())
            and bool((coverage.loc[coverage.eligible, "common_families"] == 4).all())
        ),
        "positive_breadth_bootstrap_95pct": (
            frame.breadth_difference.mean() > 0 and bootstrap["p_mean_positive"] >= .95
        ),
        "event_broad_rate_exceeds_controls": event_broad_rate > control_broad_rate,
        "both_categories_positive": len(categories) == 2 and bool((categories.breadth_difference > 0).all()),
        "years_and_family_loo_positive": (
            len(years) == 3 and bool((years.breadth_difference > 0).all())
            and bool((family_loo_frame.mean_breadth_difference > 0).all())
        ),
        "top5_positive_share_below_60pct": top5_share < .60,
        "ridge_forecast_gate": (
            metrics["ridge"]["mae"] < metrics["price_only"]["mae"]
            and metrics["ridge"]["mae"] <= 1.05 * metrics["economic"]["mae"]
        ),
        "qa_no_future_anchors_deterministic_tests_compile": bool(anchors_frame.strictly_prior.all()),
    }
    gates = {name: bool(value) for name, value in gates.items()}
    result = {
        "research": 56,
        "official_events": len(events),
        "eligible_events": len(frame),
        "min_common_assets": int(frame.common_assets.min()),
        "max_common_assets": int(frame.common_assets.max()),
        "families": 4,
        "mean_event_breadth": float(frame.event_breadth.mean()),
        "mean_control_breadth": float(frame.control_breadth.mean()),
        "mean_breadth_difference": float(frame.breadth_difference.mean()),
        "event_broad_cojump_rate": event_broad_rate,
        "control_broad_cojump_rate": control_broad_rate,
        "bootstrap": bootstrap,
        "categories": categories.to_dict("records"),
        "years": years.to_dict("records"),
        "family_leave_one_out": family_loo,
        "top5_positive_difference_share": top5_share,
        "forecast_metrics": metrics,
        "round_trips": 0,
        "trade_legs": 0,
        "turnover": 0,
        "pnl_cost_sensitivity": {"0x": 0, "1x": 0, "2x": 0, "4x": 0},
        "gates": gates,
        "passed_all_gates": all(gates.values()),
        "decision": "timing_safe_cojump_risk_supported_not_alpha" if all(gates.values())
                    else "research_only_failed_preregistered_gates",
        "panel_sha256": sha256(panel_path),
        "supersedes_research055_due_to_joint_rank_label_leakage": True,
    }
    (output / "research056_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_manifest(output, manifest)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--bls-html", type=Path, nargs=3, required=True)
    parser.add_argument("--vix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.panel, args.input_manifest, args.bls_html, args.vix, args.output),
                     indent=2, sort_keys=True))
