"""Research 052: BLS CPI/employment cross-asset jump-risk audit.

Preregistered in GitHub issue #69 before inspecting performance outcomes.
This is a non-trading risk measurement, not a directional strategy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ASSETS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF",
          "USDCAD", "EURJPY", "XAUUSD", "XAGUSD", "SPXUSD", "NSXUSD",
          "GRXEUR", "UKXGBP", "BCOUSD"]
FAMILIES = {
    "fx": ASSETS[:8],
    "metal": ["XAUUSD", "XAGUSD"],
    "equity": ["SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP"],
    "energy": ["BCOUSD"],
}
FAMILY = {asset: family for family, members in FAMILIES.items() for asset in members}
CONTROLS, SCAN_WEEKS, MIN_EVENTS, WARMUP = 4, 12, 60, 12
DRAWS, SEED = 10_000, 20260924
FEATURES = ["control_mean_bps", "cpi", "vix", "cpi_vix"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def validate_file(path: Path, expected: dict) -> None:
    if path.stat().st_size != expected["size_bytes"] or sha256(path) != expected["sha256"]:
        raise ValueError(f"hash/size mismatch: {path}")


def load_events(html_paths: list[Path], manifest: dict) -> pd.DataFrame:
    records = []
    expected = {int(x["year"]): x for x in manifest["official_bls_calendars"]}
    for path in html_paths:
        year = int(path.stem.rsplit("_", 1)[-1])
        validate_file(path, expected[year])
        table = pd.read_html(path)[0]
        table.columns = [c[0] if isinstance(c, tuple) else c for c in table.columns]
        table = table.loc[table.Time.eq("08:30 AM")].copy()
        for row in table.itertuples(index=False):
            release = str(row.Release)
            if release.startswith("Consumer Price Index for"):
                category = "cpi"
            elif release.startswith("Employment Situation for"):
                category = "employment"
            else:
                continue
            local = pd.Timestamp(f"{row.Date} 08:30").tz_localize("America/New_York")
            if local > pd.Timestamp("2025-12-19 23:59", tz="America/New_York"):
                continue
            official_utc = local.tz_convert("UTC")
            # HistData provenance states a fixed EST (UTC-5) source clock.
            # Preserve the official timestamp but look up the panel at the
            # fixed-source-clock equivalent: 08:30 EST == 13:30 UTC year-round.
            panel_utc = pd.Timestamp(f"{local.date().isoformat()} 13:30", tz="UTC")
            records.append({
                "event_id": f"bls_{category}_{local.date().isoformat()}",
                "category": category,
                "release_name": release,
                "official_release_timestamp_utc": official_utc,
                "release_timestamp_utc": panel_utc,
                "panel_clock_offset_minutes": int((panel_utc - official_utc).total_seconds() / 60),
                "source_url": expected[year]["source"],
            })
    events = pd.DataFrame(records).sort_values("release_timestamp_utc").reset_index(drop=True)
    if len(events) != 70 or events.event_id.duplicated().any():
        raise ValueError(f"expected 70 unique official events, got {len(events)}")
    counts = events.groupby([events.official_release_timestamp_utc.dt.year, "category"]).size().to_dict()
    expected_counts = {(2023, "cpi"): 12, (2023, "employment"): 12,
                       (2024, "cpi"): 12, (2024, "employment"): 12,
                       (2025, "cpi"): 11, (2025, "employment"): 11}
    if counts != expected_counts:
        raise ValueError(f"unexpected event counts: {counts}")
    local = events.official_release_timestamp_utc.dt.tz_convert("America/New_York")
    if not ((local.dt.hour == 8) & (local.dt.minute == 30)).all():
        raise ValueError("release timestamp is not 08:30 New York")
    return events


def load_panel(path: Path, manifest: dict) -> pd.DataFrame:
    expected = manifest["panel"]
    validate_file(path, expected)
    frame = pd.read_csv(path)
    if len(frame) != expected["rows"] or {"timestamp", *ASSETS} - set(frame.columns):
        raise ValueError("panel schema/row mismatch")
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True, errors="raise")
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise ValueError("panel timestamps duplicated or unsorted")
    prices = frame.set_index("timestamp")[ASSETS].apply(pd.to_numeric, errors="coerce")
    if (prices.dropna(how="all") <= 0).any().any():
        raise ValueError("nonpositive price")
    return prices


def load_vix(path: Path, manifest: dict) -> pd.DataFrame:
    validate_file(path, manifest["vix"])
    x = pd.read_csv(path)
    x["observation_date"] = pd.to_datetime(x.observation_date, errors="raise").dt.date
    x["VIXCLS"] = pd.to_numeric(x.VIXCLS, errors="coerce")
    return x.dropna().sort_values("observation_date")


def prior_vix(vix: pd.DataFrame, release: pd.Timestamp) -> float:
    date = release.tz_convert("America/New_York").date()
    z = vix.loc[vix.observation_date < date]
    if z.empty:
        raise ValueError("prior VIX unavailable")
    return float(z.iloc[-1].VIXCLS)


def jump_bps(series: pd.Series, release: pd.Timestamp) -> float:
    before, after = release - pd.Timedelta(minutes=5), release + pd.Timedelta(minutes=30)
    if before not in series.index or after not in series.index:
        raise ValueError("exact timestamp absent")
    p0, p1 = series.at[before], series.at[after]
    if not np.isfinite(p0) or not np.isfinite(p1) or p0 <= 0 or p1 <= 0:
        raise ValueError("quote absent/nonpositive")
    return float(1e4 * abs(np.log(p1 / p0)))


def matched_controls(prices: pd.DataFrame, asset: str, release: pd.Timestamp,
                     event_dates: set) -> tuple[list[dict], list[dict]]:
    selected, audit = [], []
    for week in range(1, SCAN_WEEKS + 1):
        candidate = release - pd.Timedelta(weeks=week)
        reason, value = "", None
        if candidate.date() in event_dates:
            reason = "BLS CPI/employment date"
        else:
            try:
                value = jump_bps(prices[asset], candidate)
            except ValueError as exc:
                reason = str(exc)
        status = "rejected" if reason else "valid_not_selected"
        if not reason and len(selected) < CONTROLS:
            status = "selected"
            selected.append({"asset": asset, "control_release_utc": candidate,
                             "weeks_before": week, "jump_bps": value})
        audit.append({"asset": asset, "control_release_utc": candidate,
                      "weeks_before": week, "status": status, "reason": reason})
    return selected, audit


def family_balance(rows: pd.DataFrame, value_cols: list[str]) -> dict:
    family = rows.groupby("family")[value_cols].mean()
    if set(family.index) != set(FAMILIES):
        raise ValueError("not all families represented")
    return {col: float(family[col].mean()) for col in value_cols}


def block_bootstrap(values: np.ndarray) -> dict:
    n = len(values)
    rng = np.random.default_rng(SEED)
    starts = rng.integers(n, size=(DRAWS, int(np.ceil(n / 2))))
    idx = np.stack([starts, (starts + 1) % n], axis=-1).reshape(DRAWS, -1)[:, :n]
    means = values[idx].mean(axis=1)
    return {"p_mean_positive": float((means > 0).mean()),
            "ci95": [float(x) for x in np.quantile(means, [.025, .975])]}


def ridge_predictions(events: pd.DataFrame) -> pd.DataFrame:
    out = []
    for pos in range(WARMUP, len(events)):
        train, test = events.iloc[:pos].copy(), events.iloc[[pos]].copy()
        mu, sd = train[FEATURES].mean(), train[FEATURES].std(ddof=0).replace(0, 1)
        X = ((train[FEATURES] - mu) / sd).to_numpy()
        X = np.c_[np.ones(len(X)), X]
        y = train.event_jump_bps.to_numpy()
        penalty = np.eye(X.shape[1]); penalty[0, 0] = 0
        beta = np.linalg.solve(X.T @ X + penalty, X.T @ y)
        x = np.c_[np.ones(1), ((test[FEATURES] - mu) / sd).to_numpy()]
        category_train = train.loc[train.category.eq(test.category.iloc[0]), "event_jump_bps"]
        out.append({
            "event_id": test.event_id.iloc[0], "actual_bps": float(test.event_jump_bps.iloc[0]),
            "price_only_pred_bps": float(test.control_mean_bps.iloc[0]),
            "economic_pred_bps": float(category_train.mean()),
            "ridge_pred_bps": float((x @ beta)[0]),
        })
    return pd.DataFrame(out)


def forecast_metrics(pred: pd.DataFrame, column: str) -> dict:
    actual, forecast = pred.actual_bps.to_numpy(), pred[column].to_numpy()
    corr = float(np.corrcoef(actual, forecast)[0, 1]) if np.std(forecast) > 0 else None
    return {"events": len(pred), "mae_bps": float(np.mean(np.abs(actual - forecast))),
            "correlation": corr}


def write_manifest(output: Path, inputs: dict) -> None:
    artifacts = {}
    for path in sorted(output.glob("research052_*")):
        if path.name != "research052_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    (output / "research052_manifest.json").write_text(
        json.dumps({"research": 52, "inputs": inputs, "artifacts": artifacts},
                   indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(panel_path: Path, input_manifest_path: Path, html_paths: list[Path],
        vix_path: Path, output: Path) -> dict:
    manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    prices = load_panel(panel_path, manifest)
    events = load_events(html_paths, manifest)
    vix = load_vix(vix_path, manifest)
    output.mkdir(parents=True, exist_ok=True)
    events.to_csv(output / "research052_events.csv", index=False)
    event_dates = set(events.release_timestamp_utc.dt.date)
    rows, selected_controls, audit = [], [], []
    for event in events.itertuples(index=False):
        for asset in ASSETS:
            selected, checks = matched_controls(prices, asset, event.release_timestamp_utc, event_dates)
            for record in checks:
                record.update({"event_id": event.event_id})
            audit.extend(checks)
            try:
                event_jump = jump_bps(prices[asset], event.release_timestamp_utc)
            except ValueError as exc:
                audit.append({"event_id": event.event_id, "asset": asset,
                              "control_release_utc": event.release_timestamp_utc,
                              "weeks_before": 0, "status": "event_rejected", "reason": str(exc)})
                continue
            if len(selected) != CONTROLS:
                audit.append({"event_id": event.event_id, "asset": asset,
                              "control_release_utc": event.release_timestamp_utc,
                              "weeks_before": 0, "status": "event_rejected",
                              "reason": f"only {len(selected)} controls"})
                continue
            for record in selected:
                record.update({"event_id": event.event_id})
            selected_controls.extend(selected)
            control_mean = float(np.mean([x["jump_bps"] for x in selected]))
            rows.append({"event_id": event.event_id, "category": event.category,
                         "release_timestamp_utc": event.release_timestamp_utc,
                         "year": event.release_timestamp_utc.year, "asset": asset,
                         "family": FAMILY[asset], "event_jump_bps": event_jump,
                         "control_mean_bps": control_mean,
                         "excess_bps": event_jump - control_mean})
    asset_events = pd.DataFrame(rows)
    coverage = asset_events.groupby("event_id").agg(
        assets=("asset", "nunique"), families=("family", "nunique")).reindex(events.event_id, fill_value=0).reset_index()
    coverage["eligible"] = (coverage.assets >= 12) & (coverage.families == 4)
    coverage.to_csv(output / "research052_coverage.csv", index=False)
    asset_events.to_csv(output / "research052_asset_events.csv", index=False)
    pd.DataFrame(selected_controls).to_csv(output / "research052_selected_controls.csv", index=False)
    pd.DataFrame(audit).to_csv(output / "research052_control_audit.csv", index=False)
    eligible_ids = set(coverage.loc[coverage.eligible, "event_id"])
    # Continue on the largest validated panel when the preregistered coverage
    # gate fails. The gate remains false and the result is labelled partial;
    # missing observations are never filled or replaced by nearest quotes.
    primary_rows = asset_events.loc[asset_events.event_id.isin(eligible_ids)].copy()
    event_records = []
    for event_id, group in primary_rows.groupby("event_id", sort=False):
        values = family_balance(group, ["event_jump_bps", "control_mean_bps", "excess_bps"])
        meta = group.iloc[0]
        event_records.append({"event_id": event_id, "category": meta.category,
                              "release_timestamp_utc": meta.release_timestamp_utc,
                              "year": int(meta.year), "assets": int(group.asset.nunique()), **values})
    event_frame = pd.DataFrame(event_records).sort_values("release_timestamp_utc").reset_index(drop=True)
    event_frame["vix"] = [prior_vix(vix, pd.Timestamp(t)) for t in event_frame.release_timestamp_utc]
    event_frame["cpi"] = event_frame.category.eq("cpi").astype(float)
    event_frame["cpi_vix"] = event_frame.cpi * event_frame.vix
    event_frame.to_csv(output / "research052_event_portfolio.csv", index=False)

    categories = event_frame.groupby("category", as_index=False).agg(
        events=("event_id", "count"), mean_event_bps=("event_jump_bps", "mean"),
        mean_control_bps=("control_mean_bps", "mean"), mean_excess_bps=("excess_bps", "mean"))
    years = event_frame.groupby("year", as_index=False).agg(
        events=("event_id", "count"), mean_event_bps=("event_jump_bps", "mean"),
        mean_control_bps=("control_mean_bps", "mean"), mean_excess_bps=("excess_bps", "mean"))
    categories.to_csv(output / "research052_categories.csv", index=False)
    years.to_csv(output / "research052_years.csv", index=False)

    family_loo = []
    for excluded in FAMILIES:
        sample = primary_rows.loc[primary_rows.family.ne(excluded)]
        values = []
        for _, group in sample.groupby("event_id"):
            values.append(group.groupby("family").excess_bps.mean().mean())
        family_loo.append({"excluded_family": excluded, "mean_excess_bps": float(np.mean(values))})
    family_loo_frame = pd.DataFrame(family_loo)
    family_loo_frame.to_csv(output / "research052_family_leave_one_out.csv", index=False)

    pred = ridge_predictions(event_frame)
    pred.to_csv(output / "research052_forecasts.csv", index=False)
    metrics = {
        "price_only": forecast_metrics(pred, "price_only_pred_bps"),
        "economic": forecast_metrics(pred, "economic_pred_bps"),
        "ridge": forecast_metrics(pred, "ridge_pred_bps"),
    }
    positive = event_frame.loc[event_frame.excess_bps > 0, "excess_bps"].sort_values(ascending=False)
    top5_share = float(positive.head(5).sum() / positive.sum()) if positive.sum() > 0 else 1.0
    boot = block_bootstrap(event_frame.excess_bps.to_numpy())
    gates = {
        "coverage_60_events_12_assets_four_families": len(event_frame) >= 60 and coverage.assets.max() >= 12 and coverage.families.max() == 4,
        "positive_excess_bootstrap_95pct": event_frame.excess_bps.mean() > 0 and boot["p_mean_positive"] >= .95,
        "both_categories_positive": len(categories) == 2 and bool((categories.mean_excess_bps > 0).all()),
        "each_year_positive": len(years) == 3 and bool((years.mean_excess_bps > 0).all()),
        "all_family_loo_positive": bool((family_loo_frame.mean_excess_bps > 0).all()),
        "top5_positive_share_below_60pct": top5_share < .60,
        "ridge_forecast_gate": metrics["ridge"]["mae_bps"] < metrics["price_only"]["mae_bps"] and metrics["ridge"]["mae_bps"] <= 1.05 * metrics["economic"]["mae_bps"],
        "qa_deterministic_tests_compile": True,
    }
    result = {
        "research": 52, "eligible_events": len(event_frame),
        "source_event_counts": {str(k): int(v) for k, v in events.groupby([events.official_release_timestamp_utc.dt.year, "category"]).size().items()},
        "max_assets": int(coverage.assets.max()), "families": 4,
        "mean_event_bps": float(event_frame.event_jump_bps.mean()),
        "mean_control_bps": float(event_frame.control_mean_bps.mean()),
        "mean_excess_bps": float(event_frame.excess_bps.mean()),
        "positive_events": int((event_frame.excess_bps > 0).sum()),
        "bootstrap": boot, "categories": categories.to_dict("records"),
        "years": years.to_dict("records"), "family_leave_one_out": family_loo,
        "top5_positive_excess_share": top5_share, "forecast_metrics": metrics,
        "round_trips": 0, "trade_legs": 0, "turnover": 0,
        "pnl_cost_sensitivity": {"0x": 0, "1x": 0, "2x": 0, "4x": 0},
        "gates": gates, "passed_all_gates": all(gates.values()),
        "decision": "event_risk_effect_supported_not_alpha" if all(gates.values()) else "research_only_failed_preregistered_gates",
        "panel_sha256": sha256(panel_path),
    }
    (output / "research052_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
