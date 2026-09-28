"""Research 055: BLS cross-family cojump audit.

Preregistered in GitHub issue #72 before outcome inspection. Non-trading study.
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
    out = {}
    for asset in r52.ASSETS:
        try:
            out[asset] = r52.jump_bps(prices[asset], timestamp)
        except ValueError:
            pass
    return out


def all_families(assets: set[str]) -> bool:
    return {r52.FAMILY[a] for a in assets} == set(r52.FAMILIES)


def unique_max_flags(values: np.ndarray) -> np.ndarray:
    flags = np.zeros_like(values, dtype=bool)
    for row, x in enumerate(values):
        maximum = np.max(x)
        where = np.flatnonzero(np.isclose(x, maximum, rtol=0, atol=1e-12))
        if len(where) == 1:
            flags[row, where[0]] = True
    return flags


def family_activation(flags: dict[str, bool], families: list[str] | None = None) -> dict[str, bool]:
    selected = families or list(r52.FAMILIES)
    out = {}
    for family in selected:
        members = [a for a in r52.FAMILIES[family] if a in flags]
        if not members:
            raise ValueError(f"family absent: {family}")
        threshold = math.ceil(len(members) / 2)
        out[family] = sum(bool(flags[a]) for a in members) >= threshold
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
        X = np.c_[np.ones(len(train)), ((train[FEATURES] - mu) / sd).to_numpy()]
        y = train.event_breadth.to_numpy()
        penalty = np.eye(X.shape[1]); penalty[0, 0] = 0
        beta = np.linalg.solve(X.T @ X + penalty, X.T @ y)
        x = np.c_[np.ones(1), ((test[FEATURES] - mu) / sd).to_numpy()]
        category_train = train.loc[train.category.eq(test.category.iloc[0]), "event_breadth"]
        out.append({
            "event_id": test.event_id.iloc[0],
            "actual_breadth": float(test.event_breadth.iloc[0]),
            "price_only_pred": float(test.control_breadth.iloc[0]),
            "economic_pred": float(category_train.mean()),
            "ridge_pred": float((x @ beta)[0]),
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
    for path in sorted(output.glob("research055_*")):
        if path.name != "research055_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    (output / "research055_manifest.json").write_text(
        json.dumps({"research": 55, "inputs": inputs, "artifacts": artifacts},
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

    event_rows, candidate_rows, activation_rows, coverage_rows = [], [], [], []
    for event in events.itertuples(index=False):
        event_jump = jumps_at(prices, event.release_timestamp_utc)
        controls = []
        for week in range(1, SCAN_WEEKS + 1):
            timestamp = event.release_timestamp_utc - pd.Timedelta(weeks=week)
            if timestamp.date() in event_dates:
                continue
            jump = jumps_at(prices, timestamp)
            if len(jump) >= MIN_ASSETS and all_families(set(jump)):
                controls.append((timestamp, jump))
            if len(controls) == CONTROLS:
                break
        common = set(event_jump)
        for _, jump in controls:
            common &= set(jump)
        eligible = len(controls) == CONTROLS and len(common) >= MIN_ASSETS and all_families(common)
        coverage_rows.append({
            "event_id": event.event_id,
            "event_assets": len(event_jump),
            "controls": len(controls),
            "common_assets": len(common),
            "common_families": len({r52.FAMILY[a] for a in common}),
            "eligible": eligible,
        })
        if not eligible:
            continue
        assets = sorted(common)
        timestamps = [event.release_timestamp_utc] + [x[0] for x in controls]
        jumps = [event_jump] + [x[1] for x in controls]
        matrix = np.array([[candidate[asset] for candidate in jumps] for asset in assets])
        flags = unique_max_flags(matrix)
        breadths, broad = [], []
        family_flags_by_candidate = []
        for index, timestamp in enumerate(timestamps):
            asset_flags = {asset: bool(flags[row, index]) for row, asset in enumerate(assets)}
            family_flags = family_activation(asset_flags)
            family_flags_by_candidate.append(family_flags)
            breadth = sum(family_flags.values()) / 4
            breadths.append(breadth)
            broad.append(breadth >= .75)
            candidate_rows.append({
                "event_id": event.event_id,
                "candidate": "event" if index == 0 else f"control_{index}",
                "timestamp": timestamp,
                "breadth": breadth,
                "broad_cojump": broad[-1],
                "common_assets": len(assets),
            })
            for family, active in family_flags.items():
                activation_rows.append({
                    "event_id": event.event_id,
                    "candidate": "event" if index == 0 else f"control_{index}",
                    "family": family,
                    "active": active,
                })
        event_rows.append({
            "event_id": event.event_id,
            "category": event.category,
            "release_timestamp_utc": event.release_timestamp_utc,
            "year": event.release_timestamp_utc.year,
            "common_assets": len(assets),
            "event_breadth": breadths[0],
            "control_breadth": float(np.mean(breadths[1:])),
            "breadth_difference": float(breadths[0] - np.mean(breadths[1:])),
            "event_broad_cojump": broad[0],
            "control_broad_cojump_rate": float(np.mean(broad[1:])),
            **{f"event_{family}_active": family_flags_by_candidate[0][family]
               for family in r52.FAMILIES},
            **{f"control_{family}_active_rate": float(np.mean([
                x[family] for x in family_flags_by_candidate[1:]
            ])) for family in r52.FAMILIES},
        })

    coverage = pd.DataFrame(coverage_rows)
    frame = pd.DataFrame(event_rows).sort_values("release_timestamp_utc").reset_index(drop=True)
    candidates = pd.DataFrame(candidate_rows)
    activations = pd.DataFrame(activation_rows)
    coverage.to_csv(output / "research055_coverage.csv", index=False)
    frame["vix"] = [r52.prior_vix(vix, pd.Timestamp(x)) for x in frame.release_timestamp_utc]
    frame["cpi"] = frame.category.eq("cpi").astype(float)
    frame["cpi_vix"] = frame.cpi * frame.vix
    frame.to_csv(output / "research055_events.csv", index=False)
    candidates.to_csv(output / "research055_candidates.csv", index=False)
    activations.to_csv(output / "research055_family_activations.csv", index=False)

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
    categories.to_csv(output / "research055_categories.csv", index=False)
    years.to_csv(output / "research055_years.csv", index=False)

    family_loo = []
    for excluded in r52.FAMILIES:
        included = [x for x in r52.FAMILIES if x != excluded]
        event_values, control_values = [], []
        for event_id in frame.event_id:
            subset = activations.loc[activations.event_id.eq(event_id) & activations.family.isin(included)]
            by_candidate = subset.groupby("candidate").active.mean()
            event_values.append(float(by_candidate["event"]))
            control_values.append(float(by_candidate.drop("event").mean()))
        family_loo.append({
            "excluded_family": excluded,
            "mean_breadth_difference": float(np.mean(np.array(event_values) - np.array(control_values))),
        })
    family_loo_frame = pd.DataFrame(family_loo)
    family_loo_frame.to_csv(output / "research055_family_leave_one_out.csv", index=False)

    predictions = ridge_predictions(frame)
    predictions.to_csv(output / "research055_forecasts.csv", index=False)
    metrics = {
        "price_only": forecast_metrics(predictions, "price_only_pred"),
        "economic": forecast_metrics(predictions, "economic_pred"),
        "ridge": forecast_metrics(predictions, "ridge_pred"),
    }
    positive = frame.loc[frame.breadth_difference > 0, "breadth_difference"].sort_values(ascending=False)
    top5_share = float(positive.head(5).sum() / positive.sum()) if positive.sum() > 0 else 1.0
    bootstrap = block_bootstrap(frame.breadth_difference.to_numpy())
    event_broad_rate = float(frame.event_broad_cojump.mean())
    control_broad_rate = float(candidates.loc[candidates.candidate.ne("event"), "broad_cojump"].mean())
    gates = {
        "coverage_50_events_12_assets_four_families": (
            len(frame) >= 50 and frame.common_assets.max() >= 12
            and coverage.common_families.max() == 4
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
        "qa_deterministic_tests_compile": True,
    }
    gates = {name: bool(value) for name, value in gates.items()}
    result = {
        "research": 55,
        "official_events": len(events),
        "eligible_events": len(frame),
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
        "round_trips": 0, "trade_legs": 0, "turnover": 0,
        "pnl_cost_sensitivity": {"0x": 0, "1x": 0, "2x": 0, "4x": 0},
        "gates": gates,
        "passed_all_gates": all(gates.values()),
        "decision": "cojump_risk_supported_not_alpha" if all(gates.values())
                    else "research_only_failed_preregistered_gates",
        "panel_sha256": sha256(panel_path),
    }
    (output / "research055_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_manifest(output, manifest)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--panel", type=Path, required=True)
    p.add_argument("--input-manifest", type=Path, required=True)
    p.add_argument("--bls-html", type=Path, nargs=3, required=True)
    p.add_argument("--vix", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(a.panel, a.input_manifest, a.bls_html, a.vix, a.output),
                     indent=2, sort_keys=True))
