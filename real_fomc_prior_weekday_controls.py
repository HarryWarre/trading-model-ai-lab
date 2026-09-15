"""Research 044: timing-safe prior-weekday controls for pre-FOMC drift."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ASSETS = ["SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP"]
PIP_SIZE = {asset: 0.1 for asset in ASSETS}
WINDOW = pd.Timedelta(hours=24)
END_LAG = pd.Timedelta(hours=3)
MAX_STALENESS = pd.Timedelta(minutes=10)
VOL_LOOKBACK = pd.Timedelta(days=20)
CONTROL_SCAN_WEEKS = 12
CONTROLS_PER_EVENT = 4
BOOTSTRAPS = 10_000
BLOCK_LENGTH = 2
SEED = 20260915


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_panel(path: Path, manifest_path: Path) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = manifest.get("output", {})
    if output.get("sha256") != sha256(path):
        raise ValueError("panel SHA-256 does not match build manifest")
    if output.get("format") != "wide_close":
        raise ValueError("wide_close panel required")
    if output.get("asset_count", 0) < 15 or output.get("years_requested") != [2023, 2024, 2025]:
        raise ValueError("15-asset 2023-2025 panel required")
    raw = pd.read_csv(path)
    missing = {"timestamp", *ASSETS} - set(raw.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True, errors="raise")
    if raw["timestamp"].duplicated().any() or not raw["timestamp"].is_monotonic_increasing:
        raise ValueError("panel timestamps must be unique and sorted")
    if int(output.get("rows", -1)) != len(raw):
        raise ValueError("panel row count differs from manifest")
    prices = raw.set_index("timestamp")[ASSETS]
    for asset in ASSETS:
        prices[asset] = pd.to_numeric(prices[asset], errors="coerce")
        if prices[asset].dropna().empty or (prices[asset].dropna() <= 0).any():
            raise ValueError(f"invalid prices for {asset}")
    return prices, manifest


def load_events(path: Path) -> pd.DataFrame:
    events = pd.read_csv(path)
    required = {"event_id", "release_timestamp_utc", "source_url"}
    if required - set(events.columns):
        raise ValueError("event provenance columns missing")
    events["release_timestamp_utc"] = pd.to_datetime(events["release_timestamp_utc"], utc=True, errors="raise")
    events = events.sort_values("release_timestamp_utc").reset_index(drop=True)
    counts = events.release_timestamp_utc.dt.year.value_counts().sort_index().to_dict()
    if len(events) != 24 or events.event_id.duplicated().any() or counts != {2023: 8, 2024: 8, 2025: 8}:
        raise ValueError("expected 24 unique events, eight per year")
    local = events.release_timestamp_utc.dt.tz_convert("America/New_York")
    if not ((local.dt.hour == 14) & (local.dt.minute == 0)).all():
        raise ValueError("events must be 14:00 New York")
    if not events.source_url.str.startswith("https://www.federalreserve.gov/newsevents/pressreleases/").all():
        raise ValueError("official Federal Reserve provenance required")
    return events


def last_observed(series: pd.Series, boundary: pd.Timestamp) -> tuple[float, pd.Timestamp]:
    observed = series.loc[:boundary].dropna()
    if observed.empty:
        raise ValueError("no observation before boundary")
    timestamp = observed.index[-1]
    if boundary - timestamp > MAX_STALENESS:
        raise ValueError(f"stale boundary price by {boundary - timestamp}")
    return float(observed.iloc[-1]), timestamp


def pre_event_vol(series: pd.Series, start: pd.Timestamp) -> float:
    x = series.loc[(series.index >= start - VOL_LOOKBACK) & (series.index < start)].dropna()
    if len(x) < 100:
        raise ValueError("insufficient pre-window observations")
    gaps = x.index.to_series().diff()
    returns = np.log(x).diff().loc[gaps <= pd.Timedelta(minutes=10)].dropna()
    vol = float(returns.std(ddof=1))
    if not np.isfinite(vol) or vol <= 0:
        raise ValueError("invalid pre-window volatility")
    return vol


def one_window(prices: pd.DataFrame, window_id: str, release: pd.Timestamp) -> pd.DataFrame:
    end = release - END_LAG
    start = end - WINDOW
    rows = []
    for asset in ASSETS:
        start_price, start_quote = last_observed(prices[asset], start)
        end_price, end_quote = last_observed(prices[asset], end)
        rows.append({
            "window_id": window_id, "release_timestamp_utc": release,
            "window_start": start, "window_end": end, "asset": asset,
            "start_quote": start_quote, "end_quote": end_quote,
            "start_price": start_price, "end_price": end_price,
            "gross_log_return": float(np.log(end_price / start_price)),
            "pre_event_vol": pre_event_vol(prices[asset], start),
        })
    return pd.DataFrame(rows)


def event_windows(prices: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for row in events.itertuples(index=False):
        frame = one_window(prices, row.event_id, row.release_timestamp_utc)
        frame["event_id"] = row.event_id
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def prior_weekday_controls(prices: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_times = list(events.release_timestamp_utc)
    selected, audit = [], []
    for row in events.itertuples(index=False):
        local = row.release_timestamp_utc.tz_convert("America/New_York")
        accepted = 0
        for weeks in range(1, CONTROL_SCAN_WEEKS + 1):
            release = (local - pd.DateOffset(weeks=weeks)).tz_convert("UTC")
            start, end = release - END_LAG - WINDOW, release - END_LAG
            reason = None
            if any(start <= event_time <= end for event_time in event_times):
                reason = "window_contains_fomc_release"
            else:
                try:
                    frame = one_window(prices, f"{row.event_id}_control_w{weeks:02d}", release)
                except ValueError as exc:
                    reason = str(exc)
            if reason is None and accepted < CONTROLS_PER_EVENT:
                accepted += 1
                frame["matched_event_id"] = row.event_id
                frame["control_rank"] = accepted
                frame["weeks_before"] = weeks
                selected.append(frame)
                status = "selected"
            elif reason is None:
                status = "valid_not_selected"
            else:
                status = "rejected"
            audit.append({
                "event_id": row.event_id, "weeks_before": weeks,
                "candidate_release_utc": release, "status": status,
                "reason": reason or "",
            })
        if accepted != CONTROLS_PER_EVENT:
            raise ValueError(f"{row.event_id} has {accepted}, not four, valid prior controls")
    return pd.concat(selected, ignore_index=True), pd.DataFrame(audit)


def aggregate(detail: pd.DataFrame, group_cols: list[str], cost_multiplier: float = 1.0,
              equal_weight: bool = False, omitted_asset: str | None = None) -> pd.DataFrame:
    x = detail.copy()
    if omitted_asset is not None:
        x = x.loc[x.asset != omitted_asset].copy()
    if equal_weight:
        x["weight"] = 1.0 / x.groupby(group_cols)["asset"].transform("count")
    else:
        x["weight"] = x.groupby(group_cols)["pre_event_vol"].transform(
            lambda s: (1.0 / s) / (1.0 / s).sum()
        )
    x["weighted_gross"] = x.weight * x.gross_log_return
    x["cost_1x"] = x.weight * 4.0 * x.asset.map(PIP_SIZE) / x.start_price
    x["net_log_return"] = x.weighted_gross - cost_multiplier * x.cost_1x
    return x.groupby(group_cols, as_index=False).agg(
        release_timestamp_utc=("release_timestamp_utc", "first"),
        gross_log_return=("weighted_gross", "sum"),
        cost_log_return=("cost_1x", lambda s: cost_multiplier * s.sum()),
        net_log_return=("net_log_return", "sum"),
        assets=("asset", "nunique"),
    )


def circular_block_bootstrap(values: np.ndarray) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    n = len(values)
    rng = np.random.default_rng(SEED)
    means = np.empty(BOOTSTRAPS)
    blocks = int(np.ceil(n / BLOCK_LENGTH))
    for draw in range(BOOTSTRAPS):
        starts = rng.integers(0, n, size=blocks)
        sample = np.concatenate([values[(start + np.arange(BLOCK_LENGTH)) % n] for start in starts])[:n]
        means[draw] = sample.mean()
    low, high = np.quantile(means, [0.025, 0.975])
    return float(np.mean(means > 0)), float(low), float(high)


def iid_bootstrap(values: np.ndarray) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(SEED)
    means = rng.choice(values, size=(BOOTSTRAPS, len(values)), replace=True).mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(np.mean(means > 0)), float(low), float(high)


def paired_table(events_detail: pd.DataFrame, controls_detail: pd.DataFrame,
                 omitted_asset: str | None = None, equal_weight: bool = False) -> pd.DataFrame:
    event = aggregate(events_detail, ["event_id"], 1.0, equal_weight, omitted_asset)
    control = aggregate(controls_detail, ["matched_event_id", "window_id"], 1.0,
                        equal_weight, omitted_asset)
    control_mean = control.groupby("matched_event_id").net_log_return.mean()
    out = event.set_index("event_id")[["release_timestamp_utc", "net_log_return"]].rename(
        columns={"net_log_return": "event_net"}
    )
    out["control_mean_net"] = control_mean
    if out.control_mean_net.isna().any():
        raise ValueError("missing paired control mean")
    out["difference"] = out.event_net - out.control_mean_net
    return out.reset_index()


def vix_regimes(paired: pd.DataFrame, vix_path: Path) -> pd.DataFrame:
    vix = pd.read_csv(vix_path)
    if set(vix.columns) != {"observation_date", "VIXCLS"}:
        raise ValueError("unexpected VIX schema")
    vix.observation_date = pd.to_datetime(vix.observation_date, utc=True, errors="raise")
    vix.VIXCLS = pd.to_numeric(vix.VIXCLS, errors="coerce")
    vix = vix.dropna().sort_values("observation_date")
    out = paired.sort_values("release_timestamp_utc").copy()
    out["known_by"] = out.release_timestamp_utc.dt.normalize() - pd.Timedelta(days=1)
    out = pd.merge_asof(out, vix, left_on="known_by", right_on="observation_date", direction="backward")
    if out.VIXCLS.isna().any():
        raise ValueError("missing lagged VIX")
    out["regime"] = np.where(out.VIXCLS > out.VIXCLS.median(), "high_vix", "low_vix")
    return out.groupby("regime", as_index=False).agg(
        events=("event_id", "count"), mean_vix=("VIXCLS", "mean"),
        mean_difference=("difference", "mean"), event_net=("event_net", "sum"),
        control_mean_net=("control_mean_net", "sum"),
    )


def run(panel_path: Path, manifest_path: Path, events_path: Path,
        vix_path: Path, output_dir: Path) -> dict:
    prices, panel_manifest = load_panel(panel_path, manifest_path)
    events = load_events(events_path)
    event_detail = event_windows(prices, events)
    control_detail, audit = prior_weekday_controls(prices, events)
    output_dir.mkdir(parents=True, exist_ok=True)

    cost_rows = []
    for multiplier in (0.0, 1.0, 2.0, 4.0):
        table = aggregate(event_detail, ["event_id"], multiplier)
        cost_rows.append({
            "cost_multiplier": multiplier, "events": len(table),
            "net_return": float(np.expm1(table.net_log_return.sum())),
            "mean_event_log_return": float(table.net_log_return.mean()),
            "positive_events": int((table.net_log_return > 0).sum()),
        })
    costs = pd.DataFrame(cost_rows)
    paired = paired_table(event_detail, control_detail)
    equal_paired = paired_table(event_detail, control_detail, equal_weight=True)
    block_p, block_low, block_high = circular_block_bootstrap(paired.difference.to_numpy())
    iid_p, iid_low, iid_high = iid_bootstrap(paired.difference.to_numpy())

    yearly = paired.assign(year=paired.release_timestamp_utc.dt.year).groupby("year", as_index=False).agg(
        events=("event_id", "count"), mean_difference=("difference", "mean"),
        event_log_return=("event_net", "sum"), control_mean_log_return=("control_mean_net", "sum"),
    )
    loo_rows = []
    for asset in ASSETS:
        table = paired_table(event_detail, control_detail, omitted_asset=asset)
        loo_rows.append({"omitted_asset": asset, "mean_difference": float(table.difference.mean()),
                         "positive_events": int((table.difference > 0).sum())})
    loo = pd.DataFrame(loo_rows)
    phases = paired.assign(phase=np.repeat([1, 2, 3], 8)).groupby("phase", as_index=False).agg(
        events=("event_id", "count"), mean_difference=("difference", "mean"),
        event_log_return=("event_net", "sum"), control_mean_log_return=("control_mean_net", "sum"),
    )
    regimes = vix_regimes(paired, vix_path)
    selected_controls = audit.loc[audit.status == "selected"]
    reuse = selected_controls.candidate_release_utc.value_counts()
    controls_per_event = selected_controls.groupby("event_id").size()
    gates = {
        "all_24_events_have_four_controls": bool(len(controls_per_event) == 24 and (controls_per_event == 4).all()),
        "mean_paired_difference_positive": bool(paired.difference.mean() > 0),
        "block_bootstrap_p_at_least_95pct": bool(block_p >= 0.95),
        "at_least_two_years_positive": bool((yearly.mean_difference > 0).sum() >= 2),
        "all_four_leave_one_out_positive": bool((loo.mean_difference > 0).all()),
        "event_return_positive_1x": bool(costs.loc[costs.cost_multiplier == 1.0, "net_return"].iloc[0] > 0),
        "event_return_positive_2x": bool(costs.loc[costs.cost_multiplier == 2.0, "net_return"].iloc[0] > 0),
    }
    summary = {
        "status": "completed", "panel_assets": int(panel_manifest["output"]["asset_count"]),
        "panel_rows": int(len(prices)), "events": 24, "controls_selected": int(len(selected_controls)),
        "unique_control_windows": int(len(reuse)), "max_control_reuse": int(reuse.max()),
        "portfolio_event_holds": 24, "asset_round_trips": int(len(event_detail)),
        "order_legs": int(2 * len(event_detail)), "costs": cost_rows,
        "mean_event_minus_control_log_return": float(paired.difference.mean()),
        "positive_paired_events": int((paired.difference > 0).sum()),
        "block_bootstrap_p_difference_positive": block_p,
        "block_bootstrap_ci95": [block_low, block_high],
        "iid_bootstrap_p_difference_positive": iid_p, "iid_bootstrap_ci95": [iid_low, iid_high],
        "equal_weight_mean_difference": float(equal_paired.difference.mean()),
        "positive_years": int((yearly.mean_difference > 0).sum()),
        "positive_leave_one_out": int((loo.mean_difference > 0).sum()),
        "gates": gates, "passed_all_gates": bool(all(gates.values())),
        "decision": "mechanism_supported_research_only" if all(gates.values()) else "rejected_research_only",
        "note": "Reused 2023-2025 sample; no untouched-holdout or production claim.",
    }
    event_detail.to_csv(output_dir / "research044_event_detail.csv", index=False)
    control_detail.to_csv(output_dir / "research044_control_detail.csv", index=False)
    audit.to_csv(output_dir / "research044_control_audit.csv", index=False)
    costs.to_csv(output_dir / "research044_costs.csv", index=False)
    paired.to_csv(output_dir / "research044_paired.csv", index=False)
    equal_paired.to_csv(output_dir / "research044_equal_weight.csv", index=False)
    yearly.to_csv(output_dir / "research044_years.csv", index=False)
    loo.to_csv(output_dir / "research044_leave_one_out.csv", index=False)
    phases.to_csv(output_dir / "research044_phases.csv", index=False)
    regimes.to_csv(output_dir / "research044_vix_regimes.csv", index=False)
    (output_dir / "research044_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    result_manifest = {
        "panel": {"sha256": sha256(panel_path), "bytes": panel_path.stat().st_size},
        "panel_manifest": {"sha256": sha256(manifest_path)},
        "events": {"sha256": sha256(events_path)}, "vix": {"sha256": sha256(vix_path)},
        "parameters": {"window_hours": 24, "end_lag_hours": 3, "vol_lookback_days": 20,
                       "max_staleness_minutes": 10, "control_scan_weeks": 12,
                       "controls_per_event": 4, "bootstrap_draws": BOOTSTRAPS,
                       "bootstrap_block_length": BLOCK_LENGTH, "seed": SEED,
                       "cost_multipliers": [0, 1, 2, 4]},
    }
    (output_dir / "research044_manifest.json").write_text(json.dumps(result_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--panel-manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, default=Path("data/fomc_2023_2025_official.csv"))
    parser.add_argument("--vix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.panel, args.panel_manifest, args.events, args.vix, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
