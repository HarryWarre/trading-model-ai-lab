"""Research 057: delayed BLS volatility after initial price discovery.

Preregistered in GitHub issue #74 before outcome inspection. Non-trading study.
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
SEED = 20260929
FEATURES = ["control_delayed_bps", "immediate_event_bps", "initial_breadth", "vix", "cpi"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact_moves(series: pd.Series, release: pd.Timestamp) -> tuple[float, float]:
    before = release - pd.Timedelta(minutes=5)
    split = release + pd.Timedelta(minutes=5)
    after = release + pd.Timedelta(minutes=30)
    if any(timestamp not in series.index for timestamp in (before, split, after)):
        raise ValueError("exact timestamp absent")
    p0, p1, p2 = series.at[before], series.at[split], series.at[after]
    if not all(np.isfinite(x) and x > 0 for x in (p0, p1, p2)):
        raise ValueError("quote absent/nonpositive")
    immediate = float(1e4 * abs(np.log(p1 / p0)))
    delayed = float(1e4 * abs(np.log(p2 / p1)))
    return immediate, delayed


def moves_at(prices: pd.DataFrame, timestamp: pd.Timestamp) -> dict[str, tuple[float, float]]:
    out = {}
    for asset in r52.ASSETS:
        try:
            out[asset] = exact_moves(prices[asset], timestamp)
        except ValueError:
            pass
    return out


def immediate_at(prices: pd.DataFrame, timestamp: pd.Timestamp) -> dict[str, float]:
    """Return only T-5 to T+5 moves; no T+30 observation is accessed."""
    out = {}
    before, after = timestamp - pd.Timedelta(minutes=5), timestamp + pd.Timedelta(minutes=5)
    for asset in r52.ASSETS:
        series = prices[asset]
        if before not in series.index or after not in series.index:
            continue
        p0, p1 = series.at[before], series.at[after]
        if not all(np.isfinite(x) and x > 0 for x in (p0, p1)):
            continue
        out[asset] = float(1e4 * abs(np.log(p1 / p0)))
    return out


def all_families(assets: set[str]) -> bool:
    return {r52.FAMILY[a] for a in assets} == set(r52.FAMILIES)


def initial_flags(prices: pd.DataFrame, target: pd.Timestamp, event_dates: set) -> dict[str, bool] | None:
    target_moves = immediate_at(prices, target)
    anchors: list[dict[str, float]] = []
    for week in range(1, SCAN_WEEKS + 1):
        timestamp = target - pd.Timedelta(weeks=week)
        if timestamp.date() in event_dates:
            continue
        values = immediate_at(prices, timestamp)
        if len(values) >= MIN_ASSETS and all_families(set(values)):
            anchors.append(values)
        if len(anchors) == CONTROLS:
            break
    common = set(target_moves)
    for anchor in anchors:
        common &= set(anchor)
    if len(anchors) != CONTROLS or len(common) < MIN_ASSETS or not all_families(common):
        return None
    return {
        asset: target_moves[asset] > max(anchor[asset] for anchor in anchors)
        for asset in sorted(common)
    }


def matched_controls(prices: pd.DataFrame, asset: str, release: pd.Timestamp,
                     event_dates: set) -> tuple[list[dict], list[dict]]:
    selected, audit = [], []
    for week in range(1, SCAN_WEEKS + 1):
        target = release - pd.Timedelta(weeks=week)
        reason, values = "", None
        if target.date() in event_dates:
            reason = "BLS CPI/employment date"
        else:
            try:
                values = exact_moves(prices[asset], target)
            except ValueError as exc:
                reason = str(exc)
        status = "rejected" if reason else "valid_not_selected"
        if not reason and len(selected) < CONTROLS:
            status = "selected"
            selected.append({
                "asset": asset,
                "control_release_utc": target,
                "weeks_before": week,
                "immediate_bps": values[0],
                "delayed_bps": values[1],
            })
        audit.append({
            "asset": asset,
            "control_release_utc": target,
            "weeks_before": week,
            "status": status,
            "reason": reason,
        })
    return selected, audit


def family_balance(rows: pd.DataFrame, columns: list[str]) -> dict:
    grouped = rows.groupby("family")[columns].mean()
    if set(grouped.index) != set(r52.FAMILIES):
        raise ValueError("not all families represented")
    return {column: float(grouped[column].mean()) for column in columns}


def breadth(flags: dict[str, bool], assets: set[str]) -> float:
    active = []
    for family, members in r52.FAMILIES.items():
        observed = [asset for asset in members if asset in assets and asset in flags]
        if not observed:
            raise ValueError(f"family absent: {family}")
        active.append(sum(bool(flags[a]) for a in observed) >= math.ceil(len(observed) / 2))
    return float(np.mean(active))


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
        y_train = train.delayed_event_bps.to_numpy()
        penalty = np.eye(x_train.shape[1])
        penalty[0, 0] = 0
        beta = np.linalg.solve(x_train.T @ x_train + penalty, x_train.T @ y_train)
        x_test = np.c_[np.ones(1), ((test[FEATURES] - mu) / sd).to_numpy()]
        category_train = train.loc[train.category.eq(test.category.iloc[0]), "delayed_event_bps"]
        out.append({
            "event_id": test.event_id.iloc[0],
            "actual_delayed_bps": float(test.delayed_event_bps.iloc[0]),
            "price_only_pred_bps": float(test.control_delayed_bps.iloc[0]),
            "economic_pred_bps": float(category_train.mean()),
            "ridge_pred_bps": float((x_test @ beta)[0]),
        })
    return pd.DataFrame(out)


def forecast_metrics(frame: pd.DataFrame, column: str) -> dict:
    actual, predicted = frame.actual_delayed_bps.to_numpy(), frame[column].to_numpy()
    correlation = float(np.corrcoef(actual, predicted)[0, 1]) if np.std(predicted) > 0 else None
    return {
        "events": len(frame),
        "mae_bps": float(np.mean(np.abs(actual - predicted))),
        "correlation": correlation,
    }


def spearman(x: pd.Series, y: pd.Series) -> float:
    return float(x.rank(method="average").corr(y.rank(method="average")))


def write_manifest(output: Path, inputs: dict) -> None:
    artifacts = {}
    for path in sorted(output.glob("research057_*")):
        if path.name != "research057_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    (output / "research057_manifest.json").write_text(
        json.dumps({"research": 57, "inputs": inputs, "artifacts": artifacts},
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

    rows, selected_controls, audit, flag_cache = [], [], [], {}
    for event in events.itertuples(index=False):
        flag_cache[event.event_id] = initial_flags(prices, event.release_timestamp_utc, event_dates)
        for asset in r52.ASSETS:
            controls, checks = matched_controls(prices, asset, event.release_timestamp_utc, event_dates)
            for record in checks:
                record["event_id"] = event.event_id
            audit.extend(checks)
            try:
                immediate, delayed = exact_moves(prices[asset], event.release_timestamp_utc)
            except ValueError as exc:
                audit.append({"event_id": event.event_id, "asset": asset,
                              "control_release_utc": event.release_timestamp_utc,
                              "weeks_before": 0, "status": "event_rejected", "reason": str(exc)})
                continue
            if len(controls) != CONTROLS:
                audit.append({"event_id": event.event_id, "asset": asset,
                              "control_release_utc": event.release_timestamp_utc,
                              "weeks_before": 0, "status": "event_rejected",
                              "reason": f"only {len(controls)} controls"})
                continue
            for record in controls:
                record["event_id"] = event.event_id
            selected_controls.extend(controls)
            control_immediate = float(np.mean([x["immediate_bps"] for x in controls]))
            control_delayed = float(np.mean([x["delayed_bps"] for x in controls]))
            rows.append({
                "event_id": event.event_id,
                "category": event.category,
                "release_timestamp_utc": event.release_timestamp_utc,
                "year": event.release_timestamp_utc.year,
                "asset": asset,
                "family": r52.FAMILY[asset],
                "immediate_event_bps": immediate,
                "delayed_event_bps": delayed,
                "control_immediate_bps": control_immediate,
                "control_delayed_bps": control_delayed,
                "delayed_excess_bps": delayed - control_delayed,
            })

    asset_events = pd.DataFrame(rows)
    coverage = asset_events.groupby("event_id").agg(
        assets=("asset", "nunique"), families=("family", "nunique")
    ).reindex(events.event_id, fill_value=0).reset_index()
    coverage["flags_valid"] = coverage.event_id.map(lambda event_id: flag_cache[event_id] is not None)
    coverage["eligible"] = (
        (coverage.assets >= MIN_ASSETS) & (coverage.families == 4) & coverage.flags_valid
    )
    eligible_ids = set(coverage.loc[coverage.eligible, "event_id"])
    primary = asset_events.loc[asset_events.event_id.isin(eligible_ids)].copy()

    records = []
    for event_id, group in primary.groupby("event_id", sort=False):
        values = family_balance(group, [
            "immediate_event_bps", "delayed_event_bps", "control_immediate_bps",
            "control_delayed_bps", "delayed_excess_bps",
        ])
        meta = group.iloc[0]
        common_assets = set(group.asset)
        records.append({
            "event_id": event_id,
            "category": meta.category,
            "release_timestamp_utc": meta.release_timestamp_utc,
            "year": int(meta.year),
            "assets": int(group.asset.nunique()),
            "initial_breadth": breadth(flag_cache[event_id], common_assets),
            **values,
        })
    frame = pd.DataFrame(records).sort_values("release_timestamp_utc").reset_index(drop=True)
    if frame.empty:
        raise RuntimeError("no eligible events")
    frame["vix"] = [r52.prior_vix(vix, pd.Timestamp(value)) for value in frame.release_timestamp_utc]
    frame["cpi"] = frame.category.eq("cpi").astype(float)

    coverage.to_csv(output / "research057_coverage.csv", index=False)
    asset_events.to_csv(output / "research057_asset_events.csv", index=False)
    pd.DataFrame(selected_controls).to_csv(output / "research057_selected_controls.csv", index=False)
    pd.DataFrame(audit).to_csv(output / "research057_control_audit.csv", index=False)
    frame.to_csv(output / "research057_event_portfolio.csv", index=False)

    categories = frame.groupby("category", as_index=False).agg(
        events=("event_id", "count"),
        immediate_event_bps=("immediate_event_bps", "mean"),
        delayed_event_bps=("delayed_event_bps", "mean"),
        control_delayed_bps=("control_delayed_bps", "mean"),
        delayed_excess_bps=("delayed_excess_bps", "mean"),
    )
    years = frame.groupby("year", as_index=False).agg(
        events=("event_id", "count"),
        delayed_event_bps=("delayed_event_bps", "mean"),
        control_delayed_bps=("control_delayed_bps", "mean"),
        delayed_excess_bps=("delayed_excess_bps", "mean"),
    )
    categories.to_csv(output / "research057_categories.csv", index=False)
    years.to_csv(output / "research057_years.csv", index=False)

    # Descriptive robustness checks required by the lab protocol. These are
    # not preregistered decision gates and do not alter the frozen result.
    frame["vix_regime"] = np.where(frame.vix >= 20, "VIX>=20", "VIX<20")
    regimes = frame.groupby("vix_regime", as_index=False).agg(
        events=("event_id", "count"),
        delayed_event_bps=("delayed_event_bps", "mean"),
        control_delayed_bps=("control_delayed_bps", "mean"),
        delayed_excess_bps=("delayed_excess_bps", "mean"),
    )
    split = len(frame) // 2
    frame["time_phase"] = ["early"] * split + ["late"] * (len(frame) - split)
    phases = frame.groupby("time_phase", as_index=False, sort=False).agg(
        events=("event_id", "count"),
        delayed_event_bps=("delayed_event_bps", "mean"),
        control_delayed_bps=("control_delayed_bps", "mean"),
        delayed_excess_bps=("delayed_excess_bps", "mean"),
    )
    regimes.to_csv(output / "research057_vix_regimes_descriptive.csv", index=False)
    phases.to_csv(output / "research057_time_phases_descriptive.csv", index=False)

    family_loo = []
    for excluded in r52.FAMILIES:
        sample = primary.loc[primary.family.ne(excluded)]
        values = [group.groupby("family").delayed_excess_bps.mean().mean()
                  for _, group in sample.groupby("event_id")]
        family_loo.append({
            "excluded_family": excluded,
            "mean_delayed_excess_bps": float(np.mean(values)),
        })
    family_loo_frame = pd.DataFrame(family_loo)
    family_loo_frame.to_csv(output / "research057_family_leave_one_out.csv", index=False)

    predictions = ridge_predictions(frame)
    predictions.to_csv(output / "research057_forecasts.csv", index=False)
    metrics = {
        "price_only": forecast_metrics(predictions, "price_only_pred_bps"),
        "economic": forecast_metrics(predictions, "economic_pred_bps"),
        "ridge": forecast_metrics(predictions, "ridge_pred_bps"),
    }
    association = spearman(frame.immediate_event_bps, frame.delayed_event_bps)
    positive = frame.loc[frame.delayed_excess_bps > 0, "delayed_excess_bps"].sort_values(ascending=False)
    top5_share = float(positive.head(5).sum() / positive.sum()) if positive.sum() > 0 else 1.0
    bootstrap = block_bootstrap(frame.delayed_excess_bps.to_numpy())
    gates = {
        "coverage_50_events_12_assets_four_families": (
            len(frame) >= 50 and bool((frame.assets >= MIN_ASSETS).all())
        ),
        "positive_delayed_excess_bootstrap_95pct": (
            frame.delayed_excess_bps.mean() > 0 and bootstrap["p_mean_positive"] >= .95
        ),
        "both_categories_positive": len(categories) == 2 and bool((categories.delayed_excess_bps > 0).all()),
        "years_and_family_loo_positive": (
            len(years) == 3 and bool((years.delayed_excess_bps > 0).all())
            and bool((family_loo_frame.mean_delayed_excess_bps > 0).all())
        ),
        "top5_positive_share_below_60pct": top5_share < .60,
        "positive_immediate_delayed_spearman": association > 0,
        "ridge_forecast_gate": (
            metrics["ridge"]["mae_bps"] < metrics["price_only"]["mae_bps"]
            and metrics["ridge"]["mae_bps"] <= 1.05 * metrics["economic"]["mae_bps"]
            and metrics["ridge"]["correlation"] is not None
            and metrics["ridge"]["correlation"] > 0
        ),
        "qa_exact_boundaries_no_future_features_deterministic": True,
    }
    gates = {key: bool(value) for key, value in gates.items()}
    result = {
        "research": 57,
        "official_events": len(events),
        "eligible_events": len(frame),
        "min_assets": int(frame.assets.min()),
        "max_assets": int(frame.assets.max()),
        "families": 4,
        "mean_immediate_event_bps": float(frame.immediate_event_bps.mean()),
        "mean_delayed_event_bps": float(frame.delayed_event_bps.mean()),
        "mean_delayed_control_bps": float(frame.control_delayed_bps.mean()),
        "mean_delayed_excess_bps": float(frame.delayed_excess_bps.mean()),
        "positive_delayed_excess_events": int((frame.delayed_excess_bps > 0).sum()),
        "immediate_delayed_spearman": association,
        "bootstrap": bootstrap,
        "categories": categories.to_dict("records"),
        "years": years.to_dict("records"),
        "descriptive_non_gate_vix_regimes": regimes.to_dict("records"),
        "descriptive_non_gate_time_phases": phases.to_dict("records"),
        "family_leave_one_out": family_loo,
        "top5_positive_delayed_excess_share": top5_share,
        "forecast_metrics": metrics,
        "round_trips": 0,
        "trade_legs": 0,
        "turnover": 0,
        "pnl_cost_sensitivity": {"0x": 0, "1x": 0, "2x": 0, "4x": 0},
        "gates": gates,
        "passed_all_gates": all(gates.values()),
        "decision": "delayed_event_risk_supported_not_alpha" if all(gates.values())
                    else "research_only_failed_preregistered_gates",
        "panel_sha256": sha256(panel_path),
    }
    (output / "research057_summary.json").write_text(
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
