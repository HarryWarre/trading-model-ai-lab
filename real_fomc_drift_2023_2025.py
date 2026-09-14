"""Research 043: frozen 2023-2025 pre-FOMC drift confirmation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from real_fomc_drift_2024 import (
    ASSETS, PIP_SIZE, WINDOW, END_LAG, MAX_STALENESS, VOL_LOOKBACK,
    BOOTSTRAPS, SEED, aggregate_events, bootstrap_probability,
    event_windows, leave_one_out, one_window, sha256, vix_regimes,
)


def load_panel(path: Path, manifest_path: Path) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = manifest.get("output", {})
    expected_sha = output.get("sha256")
    if not expected_sha or sha256(path) != expected_sha:
        raise ValueError("panel SHA-256 does not match its build manifest")
    if output.get("format") != "wide_close":
        raise ValueError("Research 043 requires a wide_close panel")
    if output.get("asset_count", 0) < 15:
        raise ValueError("panel manifest has fewer than 15 assets")
    if output.get("years_requested") != [2023, 2024, 2025]:
        raise ValueError("panel manifest year coverage mismatch")

    prices = pd.read_csv(path)
    missing = {"timestamp", *ASSETS} - set(prices.columns)
    if missing:
        raise ValueError(f"panel missing required columns: {sorted(missing)}")
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], utc=True, errors="raise")
    if prices["timestamp"].duplicated().any():
        raise ValueError("duplicate panel timestamps")
    prices = prices.set_index("timestamp").sort_index()[ASSETS]
    for asset in ASSETS:
        prices[asset] = pd.to_numeric(prices[asset], errors="coerce")
        if prices[asset].dropna().empty or (prices[asset].dropna() <= 0).any():
            raise ValueError(f"invalid prices for {asset}")
    return prices, manifest


def load_events(path: Path) -> pd.DataFrame:
    events = pd.read_csv(path)
    required = {"event_id", "release_timestamp_utc", "release_timezone",
                "release_time_local", "source_url"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"event file missing columns: {sorted(missing)}")
    events["release_timestamp_utc"] = pd.to_datetime(
        events["release_timestamp_utc"], utc=True, errors="raise"
    )
    if len(events) != 24 or events["event_id"].duplicated().any():
        raise ValueError("expected 24 unique 2023-2025 FOMC events")
    if events["release_timestamp_utc"].dt.year.value_counts().sort_index().to_dict() != {
        2023: 8, 2024: 8, 2025: 8
    }:
        raise ValueError("expected eight events in each year")
    local = events["release_timestamp_utc"].dt.tz_convert("America/New_York")
    if not (local.dt.hour == 14).all():
        raise ValueError("FOMC statement time is not 14:00 New York")
    if not events["source_url"].str.startswith(
        "https://www.federalreserve.gov/newsevents/pressreleases/"
    ).all():
        raise ValueError("all events need official Federal Reserve provenance")
    return events.sort_values("release_timestamp_utc").reset_index(drop=True)


def placebo_windows_multiyear(prices: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    event_times = list(events["release_timestamp_utc"])
    frames = []
    for row in events.itertuples(index=False):
        for offset in (-7, 7):
            local_release = row.release_timestamp_utc.tz_convert("America/New_York")
            release = (local_release + pd.DateOffset(days=offset)).tz_convert("UTC")
            candidate_start = release - END_LAG - WINDOW
            candidate_end = release - END_LAG
            if any(candidate_start <= timestamp <= candidate_end for timestamp in event_times):
                continue
            try:
                frame = one_window(
                    prices, f"{row.event_id}_placebo_{offset:+d}d", release
                )
            except ValueError as exc:
                if "stale boundary price" in str(exc) or "no observation" in str(exc):
                    continue
                raise
            frame["matched_event_id"] = row.event_id
            frames.append(frame)
    if not frames:
        raise ValueError("no valid matched placebo windows")
    out = pd.concat(frames, ignore_index=True)
    missing = set(events["event_id"]) - set(out["matched_event_id"])
    if missing:
        raise ValueError(f"events without a valid matched placebo: {sorted(missing)}")
    return out


def run(
    panel_path: Path, panel_manifest_path: Path, events_path: Path,
    vix_path: Path, output_dir: Path,
) -> dict:
    prices, panel_manifest = load_panel(panel_path, panel_manifest_path)
    events = load_events(events_path)
    detail = event_windows(prices, events)
    placebos = placebo_windows_multiyear(prices, events)
    output_dir.mkdir(parents=True, exist_ok=True)

    cost_rows = []
    event_tables = {}
    for multiplier in (0.0, 1.0, 2.0, 4.0):
        table = aggregate_events(detail, multiplier)
        event_tables[multiplier] = table
        cost_rows.append({
            "cost_multiplier": multiplier,
            "events": int(len(table)),
            "net_return": float(np.expm1(table["net_log_return"].sum())),
            "mean_event_log_return": float(table["net_log_return"].mean()),
            "median_event_log_return": float(table["net_log_return"].median()),
            "positive_events": int((table["net_log_return"] > 0).sum()),
        })
    costs = pd.DataFrame(cost_rows)
    costs.to_csv(output_dir / "research043_costs.csv", index=False)
    event_1x = event_tables[1.0]
    event_1x.to_csv(output_dir / "research043_events.csv", index=False)

    yearly = event_1x.assign(
        year=event_1x["release_timestamp_utc"].dt.year
    ).groupby("year", as_index=False).agg(
        events=("event_id", "count"),
        total_log_return=("net_log_return", "sum"),
        positive_events=("net_log_return", lambda x: int((x > 0).sum())),
    )
    yearly["net_return"] = np.expm1(yearly["total_log_return"])
    yearly.to_csv(output_dir / "research043_years.csv", index=False)

    loo = leave_one_out(detail, cost_multiplier=1.0)
    loo.to_csv(output_dir / "research043_leave_one_out.csv", index=False)

    placebo_event = aggregate_events(placebos, 1.0)
    placebo_event["matched_event_id"] = placebo_event["event_id"].str.extract(
        r"(FOMC_\d{4}_\d{2}_\d{2})"
    )[0]
    placebo_mean = placebo_event.groupby("matched_event_id")["net_log_return"].mean()
    paired = event_1x.set_index("event_id")["net_log_return"].to_frame("event_net")
    paired["placebo_net"] = placebo_mean
    if paired["placebo_net"].isna().any():
        raise ValueError("missing paired placebo return")
    paired["difference"] = paired["event_net"] - paired["placebo_net"]
    paired.reset_index().to_csv(output_dir / "research043_paired.csv", index=False)

    p_positive, ci_low, ci_high = bootstrap_probability(
        event_1x["net_log_return"].to_numpy()
    )
    p_difference, diff_low, diff_high = bootstrap_probability(
        paired["difference"].to_numpy()
    )
    regimes, vix_sha = vix_regimes(event_1x, vix_path)
    regimes.to_csv(output_dir / "research043_vix_regimes.csv", index=False)

    gates = {
        "pooled_1x_positive": bool(costs.loc[costs.cost_multiplier == 1.0, "net_return"].iloc[0] > 0),
        "pooled_2x_positive": bool(costs.loc[costs.cost_multiplier == 2.0, "net_return"].iloc[0] > 0),
        "all_three_years_nonnegative": bool((yearly["net_return"] >= 0).all()),
        "all_four_leave_one_out_positive": bool((loo["net_return"] > 0).all()),
        "bootstrap_p_positive_at_least_95pct": bool(p_positive >= 0.95),
        "paired_bootstrap_at_least_95pct": bool(p_difference >= 0.95),
    }
    summary = {
        "panel_sha256": sha256(panel_path),
        "panel_manifest_sha256": sha256(panel_manifest_path),
        "events_sha256": sha256(events_path),
        "vix_sha256": vix_sha,
        "panel_rows": int(len(prices)),
        "panel_assets": int(panel_manifest["output"]["asset_count"]),
        "events": int(len(event_1x)),
        "round_trips": int(len(detail)),
        "trade_legs": int(2 * len(detail)),
        "net_return_0x": float(costs.loc[costs.cost_multiplier == 0.0, "net_return"].iloc[0]),
        "net_return_1x": float(costs.loc[costs.cost_multiplier == 1.0, "net_return"].iloc[0]),
        "net_return_2x": float(costs.loc[costs.cost_multiplier == 2.0, "net_return"].iloc[0]),
        "net_return_4x": float(costs.loc[costs.cost_multiplier == 4.0, "net_return"].iloc[0]),
        "positive_events": int((event_1x["net_log_return"] > 0).sum()),
        "bootstrap_p_mean_positive": p_positive,
        "bootstrap_mean_ci95": [ci_low, ci_high],
        "bootstrap_p_event_gt_placebo": p_difference,
        "bootstrap_difference_ci95": [diff_low, diff_high],
        "mean_event_minus_placebo_log_return": float(paired["difference"].mean()),
        "yearly_net_returns": {
            str(int(row.year)): float(row.net_return)
            for row in yearly.itertuples(index=False)
        },
        "positive_leave_one_out": int((loo["net_return"] > 0).sum()),
        "gates": gates,
        "passed_all_gates": bool(all(gates.values())),
        "decision": "research_only_broader_replication_pass" if all(gates.values())
                    else "rejected_research_only",
        "note": "2024 overlaps Research 040; this is not an untouched holdout.",
    }
    (output_dir / "research043_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "panel": {"path": str(panel_path), "sha256": sha256(panel_path)},
        "panel_manifest": {
            "path": str(panel_manifest_path), "sha256": sha256(panel_manifest_path)
        },
        "events": {"path": str(events_path), "sha256": sha256(events_path)},
        "vix": {"path": str(vix_path), "sha256": vix_sha},
        "parameters": {
            "window_hours": 24, "end_lag_hours": 3,
            "max_staleness_minutes": int(MAX_STALENESS.total_seconds() / 60),
            "vol_lookback_days": int(VOL_LOOKBACK.days),
            "cost_multipliers": [0, 1, 2, 4],
            "bootstrap_draws": BOOTSTRAPS, "seed": SEED,
        },
    }
    (output_dir / "research043_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, default=Path("data/fomc_2023_2025_official.csv"))
    parser.add_argument("--vix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(
        args.panel, args.panel_manifest, args.events, args.vix, args.output_dir
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
