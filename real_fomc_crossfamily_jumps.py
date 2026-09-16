"""Research 045: ex-post FOMC statement jump across CFD families.

This is NOT a strategy: the jump is measured after the release; no trade is
placed on the pre-release price, and no P&L/cost inference is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

FAMILIES = {
    "fx": ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD", "EURJPY"),
    "metal": ("XAUUSD", "XAGUSD"),
    "us_index": ("SPXUSD", "NSXUSD"),
}
ASSETS = tuple(a for group in FAMILIES.values() for a in group)
SCAN_WEEKS = 12
CONTROLS = 4
MIN_ASSETS = 8
MIN_EVENTS = 20
DRAW = 10000
SEED = 20260916


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_data(panel: Path, manifest: Path, events_file: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    output = meta.get("output", {})
    if output.get("sha256") != sha256(panel) or output.get("format") != "wide_close":
        raise ValueError("panel SHA or wide format mismatch")
    if output.get("asset_count", 0) < 15 or output.get("years_requested") != [2023, 2024, 2025]:
        raise ValueError("wrong panel universe/year contract")
    frame = pd.read_csv(panel)
    if set(ASSETS) - set(frame.columns) or "timestamp" not in frame:
        raise ValueError("required assets or timestamp missing")
    if len(frame) != output.get("rows"):
        raise ValueError("panel row count mismatch")
    frame.timestamp = pd.to_datetime(frame.timestamp, utc=True, errors="raise")
    if not frame.timestamp.is_monotonic_increasing or frame.timestamp.duplicated().any():
        raise ValueError("nonunique/unsorted timestamps")
    prices = frame.set_index("timestamp")[list(ASSETS)].apply(pd.to_numeric, errors="coerce")
    if (prices.dropna(how="all") <= 0).any().any():
        raise ValueError("nonpositive market price")
    events = pd.read_csv(events_file)
    if {"event_id", "release_timestamp_utc", "source_url"} - set(events.columns):
        raise ValueError("event provenance missing")
    events.release_timestamp_utc = pd.to_datetime(events.release_timestamp_utc, utc=True, errors="raise")
    events = events.sort_values("release_timestamp_utc").reset_index(drop=True)
    if (len(events) != 24 or events.event_id.duplicated().any()
            or events.release_timestamp_utc.dt.year.value_counts().sort_index().to_dict() != {2023: 8, 2024: 8, 2025: 8}):
        raise ValueError("expected eight official FOMC statements per year")
    local = events.release_timestamp_utc.dt.tz_convert("America/New_York")
    if not ((local.dt.hour == 14) & (local.dt.minute == 0)).all():
        raise ValueError("FOMC release not at 14:00 New York")
    if not events.source_url.str.startswith("https://www.federalreserve.gov/newsevents/pressreleases/").all():
        raise ValueError("event is not documented by official release URL")
    return prices, events, meta


def jump_bps(prices: pd.DataFrame, asset: str, release: pd.Timestamp) -> float:
    """Exact end-labeled bars: 13:55->14:05 local, not an executable return."""
    if release.tzinfo is None:
        raise ValueError("release timestamp must be timezone-aware")
    before = release - pd.Timedelta(minutes=5)
    after = release + pd.Timedelta(minutes=5)
    if before not in prices.index or after not in prices.index:
        raise ValueError("missing exact quote boundary")
    a, b = prices.at[before, asset], prices.at[after, asset]
    if not np.isfinite(a) or not np.isfinite(b) or a <= 0 or b <= 0:
        raise ValueError("missing/nonpositive observed quote")
    return float(1e4 * abs(np.log(b / a)))


def controls_for_asset(prices: pd.DataFrame, events: pd.DataFrame,
                       event_id: str, release: pd.Timestamp, asset: str) -> tuple[list[dict], list[dict]]:
    local = release.tz_convert("America/New_York")
    event_dates = set(events.release_timestamp_utc.dt.tz_convert("America/New_York").dt.date)
    selected, audit = [], []
    for week in range(1, SCAN_WEEKS + 1):
        t = (local - pd.DateOffset(weeks=week)).tz_convert("UTC")
        reason = ""
        value = None
        if t.tz_convert("America/New_York").date() in event_dates:
            reason = "FOMC date"
        else:
            try:
                value = jump_bps(prices, asset, t)
            except ValueError as exc:
                reason = str(exc)
        status = "rejected" if reason else "valid_not_selected"
        if not reason and len(selected) < CONTROLS:
            status = "selected"
            selected.append({"matched_event_id": event_id, "asset": asset,
                             "control_release_utc": t, "weeks_before": week, "jump_bps": value})
        audit.append({"event_id": event_id, "asset": asset, "weeks_before": week,
                      "control_release_utc": t, "status": status, "reason": reason})
    return selected, audit


def block_bootstrap(x: np.ndarray) -> tuple[float, float, float]:
    n = len(x)
    rng = np.random.default_rng(SEED)
    starts = rng.integers(n, size=(DRAW, int(np.ceil(n / 2))))
    idx = np.stack((starts, (starts + 1) % n), axis=-1).reshape(DRAW, -1)[:, :n]
    means = np.asarray(x)[idx].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float((means > 0).mean()), float(lo), float(hi)


def run(panel: Path, manifest: Path, events_file: Path, output_dir: Path) -> dict:
    prices, events, meta = load_data(panel, manifest, events_file)
    asset_family = {asset: family for family, members in FAMILIES.items() for asset in members}
    rows, control_rows, audit_rows = [], [], []
    for event in events.itertuples(index=False):
        for asset in ASSETS:
            selected, audit = controls_for_asset(prices, events, event.event_id,
                                                 event.release_timestamp_utc, asset)
            audit_rows.extend(audit)
            try:
                event_jump = jump_bps(prices, asset, event.release_timestamp_utc)
            except ValueError as exc:
                audit_rows.append({"event_id": event.event_id, "asset": asset,
                                   "weeks_before": 0, "control_release_utc": event.release_timestamp_utc,
                                   "status": "event_rejected", "reason": str(exc)})
                continue
            if len(selected) != CONTROLS:
                audit_rows.append({"event_id": event.event_id, "asset": asset,
                                   "weeks_before": 0, "control_release_utc": event.release_timestamp_utc,
                                   "status": "event_rejected", "reason": f"only {len(selected)} prior controls"})
                continue
            control_rows.extend(selected)
            cmean = float(np.mean([s["jump_bps"] for s in selected]))
            rows.append({"event_id": event.event_id, "release_timestamp_utc": event.release_timestamp_utc,
                         "year": event.release_timestamp_utc.year,
                         "family": asset_family[asset], "asset": asset,
                         "event_jump_bps": event_jump, "control_mean_bps": cmean,
                         "difference_bps": event_jump - cmean})
    eligible = pd.DataFrame(rows)
    audit_df = pd.DataFrame(audit_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Check coverage before reading any primary outcome columns.
    coverage = eligible.groupby("event_id").agg(assets=("asset", "nunique"),
                                                 families=("family", "nunique"))
    coverage = coverage.reindex(events.event_id, fill_value=0).reset_index()
    coverage["primary_eligible"] = (coverage.assets >= MIN_ASSETS) & (coverage.families == 3)
    coverage.to_csv(output_dir / "research045_coverage.csv", index=False)
    eligible.to_csv(output_dir / "research045_asset_events.csv", index=False)
    pd.DataFrame(control_rows).to_csv(output_dir / "research045_selected_controls.csv", index=False)
    audit_df.to_csv(output_dir / "research045_control_audit.csv", index=False)
    if coverage.primary_eligible.sum() < MIN_EVENTS:
        failure = {"status": "blocked_coverage", "eligible_events": int(coverage.primary_eligible.sum()),
                   "minimum_events": MIN_EVENTS, "panel_sha256": sha256(panel)}
        (output_dir / "research045_summary.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
        return failure
    included = eligible.loc[eligible.event_id.isin(coverage.loc[coverage.primary_eligible, "event_id"])].copy()
    fam = included.groupby(["event_id", "release_timestamp_utc", "year", "family"], as_index=False).agg(
        assets=("asset", "count"), event_jump_bps=("event_jump_bps", "mean"),
        control_mean_bps=("control_mean_bps", "mean"), difference_bps=("difference_bps", "mean"))
    events_df = fam.groupby(["event_id", "release_timestamp_utc", "year"], as_index=False).agg(
        families=("family", "count"), assets=("assets", "sum"),
        event_jump_bps=("event_jump_bps", "mean"),
        control_mean_bps=("control_mean_bps", "mean"), difference_bps=("difference_bps", "mean"))
    year = events_df.groupby("year", as_index=False).agg(
        events=("event_id", "count"), mean_difference_bps=("difference_bps", "mean"),
        mean_event_bps=("event_jump_bps", "mean"), mean_control_bps=("control_mean_bps", "mean"))
    families = fam.groupby("family", as_index=False).agg(
        event_families=("event_id", "count"), mean_difference_bps=("difference_bps", "mean"),
        mean_event_bps=("event_jump_bps", "mean"), mean_control_bps=("control_mean_bps", "mean"))
    loo = []
    for excluded in FAMILIES:
        mean = fam.loc[fam.family != excluded].groupby("event_id").difference_bps.mean().mean()
        loo.append({"excluded_family": excluded, "mean_difference_bps": float(mean)})
    loo_df = pd.DataFrame(loo)
    p, ci_lo, ci_hi = block_bootstrap(events_df.difference_bps.to_numpy())
    # Diagnostics below are post-result sensitivity checks, never pass gates.
    excluded = events.loc[~events.event_id.isin(coverage.loc[coverage.primary_eligible, "event_id"]), "event_id"].tolist()
    drop_top3 = events_df.drop(events_df.nlargest(3, "difference_bps").index)
    p_drop3, _, _ = block_bootstrap(drop_top3.difference_bps.to_numpy())
    gates = {"coverage_at_least_20_events": bool(coverage.primary_eligible.sum() >= MIN_EVENTS),
             "mean_difference_positive": bool(events_df.difference_bps.mean() > 0),
             "block_bootstrap_p_at_least_95pct": bool(p >= .95),
             "two_of_three_years_positive": bool((year.mean_difference_bps > 0).sum() >= 2),
             "all_three_families_positive": bool((families.mean_difference_bps > 0).all()),
             "leave_one_family_out_positive": bool((loo_df.mean_difference_bps > 0).all())}
    summary = {"status": "completed", "panel_assets": int(meta["output"]["asset_count"]),
               "analysis_assets": len(ASSETS), "events_total": len(events),
               "eligible_events": int(len(events_df)), "asset_events": int(len(included)),
               "mean_event_jump_bps": float(events_df.event_jump_bps.mean()),
               "mean_control_jump_bps": float(events_df.control_mean_bps.mean()),
               "mean_difference_bps": float(events_df.difference_bps.mean()),
               "positive_event_differences": int((events_df.difference_bps > 0).sum()),
               "median_difference_bps": float(events_df.difference_bps.median()),
               "missing_event_ids": excluded,
               "top3_share_of_total_difference": float(events_df.nlargest(3, "difference_bps").difference_bps.sum() / events_df.difference_bps.sum()),
               "drop_top3_mean_difference_bps": float(drop_top3.difference_bps.mean()),
               "drop_top3_block_bootstrap_p_positive": p_drop3,
               "block_bootstrap_p_positive": p, "block_bootstrap_ci95_bps": [ci_lo, ci_hi],
               "gates": gates, "passed_all_gates": bool(all(gates.values())),
               "decision": "gates_passed_but_coverage_and_outliers_limit_interpretation_research_only" if all(gates.values()) else "risk_mechanism_not_supported_research_only",
               "no_trading_pnl_or_cost_claim": True}
    fam.to_csv(output_dir / "research045_family_events.csv", index=False)
    events_df.to_csv(output_dir / "research045_events.csv", index=False)
    year.to_csv(output_dir / "research045_years.csv", index=False)
    families.to_csv(output_dir / "research045_families.csv", index=False)
    loo_df.to_csv(output_dir / "research045_leave_one_family_out.csv", index=False)
    (output_dir / "research045_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    result_manifest = {"panel": {"sha256": sha256(panel), "bytes": panel.stat().st_size},
                       "panel_manifest": {"sha256": sha256(manifest)},
                       "event_file": {"sha256": sha256(events_file)},
                       "source_manifest": "HistData fixed-EST M1 converted to UTC, 5-minute right-closed/right-labeled; original raw ZIP hashes in panel manifest",
                       "parameters": {"scan_weeks": SCAN_WEEKS, "controls_per_asset": CONTROLS,
                                      "min_assets_per_event": MIN_ASSETS, "min_events": MIN_EVENTS,
                                      "bootstrap_draws": DRAW, "bootstrap_block_events": 2, "seed": SEED}}
    (output_dir / "research045_manifest.json").write_text(json.dumps(result_manifest, indent=2, sort_keys=True) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.panel, args.panel_manifest, args.events, args.output_dir), indent=2, sort_keys=True))
