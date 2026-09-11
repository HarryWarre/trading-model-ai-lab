"""Research 040: preregistered pre-FOMC drift replication on 2024 CFD proxies."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ASSETS = ["SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP"]
PIP_SIZE = {"SPXUSD": 0.1, "NSXUSD": 0.1, "GRXEUR": 0.1, "UKXGBP": 0.1}
EXPECTED_PANEL_SHA256 = "6f8f6995527e429dc60fd9dc372bae21ad458698c88a70a46f3e46aa27c9f8ef"
WINDOW = pd.Timedelta(hours=24)
END_LAG = pd.Timedelta(hours=3)
MAX_STALENESS = pd.Timedelta(minutes=10)
VOL_LOOKBACK = pd.Timedelta(days=20)
BOOTSTRAPS = 10_000
SEED = 20260911


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_panel(path: Path, verify_hash: bool = True) -> pd.DataFrame:
    if verify_hash and sha256(path) != EXPECTED_PANEL_SHA256:
        raise ValueError("panel SHA-256 does not match frozen manifest")
    prices = pd.read_csv(path)
    missing = set(["timestamp", *ASSETS]) - set(prices.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], utc=True, errors="raise")
    if prices["timestamp"].duplicated().any():
        raise ValueError("duplicate timestamps")
    prices = prices.set_index("timestamp").sort_index()[ASSETS]
    for col in ASSETS:
        prices[col] = pd.to_numeric(prices[col], errors="coerce")
        if (prices[col].dropna() <= 0).any():
            raise ValueError(f"non-positive prices for {col}")
    return prices


def load_events(path: Path) -> pd.DataFrame:
    events = pd.read_csv(path)
    required = {"event_id", "release_timestamp_utc", "release_timezone", "source_url"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"event file missing columns: {sorted(missing)}")
    events["release_timestamp_utc"] = pd.to_datetime(
        events["release_timestamp_utc"], utc=True, errors="raise"
    )
    if len(events) != 8 or events["event_id"].duplicated().any():
        raise ValueError("expected eight unique scheduled 2024 FOMC events")
    if not events["source_url"].str.startswith("https://www.federalreserve.gov/").all():
        raise ValueError("all events need official Federal Reserve provenance")
    return events.sort_values("release_timestamp_utc").reset_index(drop=True)


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
        raise ValueError("insufficient pre-event observations")
    frame = x.to_frame("price")
    gaps = frame.index.to_series().diff()
    returns = np.log(frame["price"]).diff().loc[gaps <= pd.Timedelta(minutes=10)].dropna()
    vol = float(returns.std(ddof=1))
    if not np.isfinite(vol) or vol <= 0:
        raise ValueError("invalid pre-event volatility")
    return vol


def one_window(prices: pd.DataFrame, event_id: str, release: pd.Timestamp) -> pd.DataFrame:
    end = release - END_LAG
    start = end - WINDOW
    rows = []
    for asset in ASSETS:
        start_price, start_quote = last_observed(prices[asset], start)
        end_price, end_quote = last_observed(prices[asset], end)
        vol = pre_event_vol(prices[asset], start)
        rows.append({
            "event_id": event_id,
            "release_timestamp_utc": release,
            "window_start": start,
            "window_end": end,
            "asset": asset,
            "start_quote": start_quote,
            "end_quote": end_quote,
            "start_price": start_price,
            "end_price": end_price,
            "gross_log_return": float(np.log(end_price / start_price)),
            "pre_event_vol": vol,
        })
    out = pd.DataFrame(rows)
    inv = 1.0 / out["pre_event_vol"]
    out["weight"] = inv / inv.sum()
    out["cost_1x"] = out["weight"] * 4.0 * out["asset"].map(PIP_SIZE) / out["start_price"]
    return out


def event_windows(prices: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    frames = [
        one_window(prices, row.event_id, row.release_timestamp_utc)
        for row in events.itertuples(index=False)
    ]
    return pd.concat(frames, ignore_index=True)


def placebo_windows(prices: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    event_times = list(events["release_timestamp_utc"])
    frames = []
    for row in events.itertuples(index=False):
        for offset in (-7, 7):
            # Preserve the official 2 p.m. New York wall-clock time across DST.
            local_release = row.release_timestamp_utc.tz_convert("America/New_York")
            release = (local_release + pd.DateOffset(days=offset)).tz_convert("UTC")
            candidate_start = release - WINDOW
            candidate_end = release - END_LAG
            if any(candidate_start <= t <= candidate_end for t in event_times):
                continue
            try:
                frame = one_window(prices, f"{row.event_id}_placebo_{offset:+d}d", release)
            except ValueError as exc:
                # Holidays and shortened sessions can make a matched control
                # non-comparable. Fail closed for that control; never relax staleness.
                if "stale boundary price" in str(exc) or "no observation" in str(exc):
                    continue
                raise
            frame["matched_event_id"] = row.event_id
            frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    covered = set(out["matched_event_id"])
    missing = set(events["event_id"]) - covered
    if missing:
        raise ValueError(f"events without a valid matched placebo: {sorted(missing)}")
    return out


def aggregate_events(detail: pd.DataFrame, cost_multiplier: float) -> pd.DataFrame:
    x = detail.copy()
    x["weighted_gross"] = x["weight"] * x["gross_log_return"]
    x["weighted_net"] = x["weighted_gross"] - cost_multiplier * x["cost_1x"]
    return x.groupby("event_id", as_index=False).agg(
        release_timestamp_utc=("release_timestamp_utc", "first"),
        gross_log_return=("weighted_gross", "sum"),
        cost_log_return=("cost_1x", lambda s: cost_multiplier * s.sum()),
        net_log_return=("weighted_net", "sum"),
        assets=("asset", "nunique"),
    )


def bootstrap_probability(values: np.ndarray, *, positive: bool = True) -> tuple[float, float, float]:
    rng = np.random.default_rng(SEED)
    draws = rng.choice(values, size=(BOOTSTRAPS, len(values)), replace=True).mean(axis=1)
    probability = float(np.mean(draws > 0 if positive else draws < 0))
    low, high = np.quantile(draws, [0.025, 0.975])
    return probability, float(low), float(high)


def leave_one_out(detail: pd.DataFrame, cost_multiplier: float = 1.0) -> pd.DataFrame:
    rows = []
    for omitted in ASSETS:
        x = detail.loc[detail["asset"] != omitted].copy()
        x["weight_loo"] = x.groupby("event_id")["pre_event_vol"].transform(
            lambda s: (1.0 / s) / (1.0 / s).sum()
        )
        x["net"] = x["weight_loo"] * x["gross_log_return"] - (
            cost_multiplier * x["weight_loo"] * 4.0
            * x["asset"].map(PIP_SIZE) / x["start_price"]
        )
        event_net = x.groupby("event_id")["net"].sum()
        rows.append({
            "omitted_asset": omitted,
            "events": int(len(event_net)),
            "net_return": float(np.expm1(event_net.sum())),
            "median_event_log_return": float(event_net.median()),
            "positive_events": int((event_net > 0).sum()),
        })
    return pd.DataFrame(rows)


def vix_regimes(event_table: pd.DataFrame, vix_path: Path) -> tuple[pd.DataFrame, str]:
    vix = pd.read_csv(vix_path)
    if set(vix.columns) != {"observation_date", "VIXCLS"}:
        raise ValueError("unexpected VIX schema")
    vix["observation_date"] = pd.to_datetime(vix["observation_date"], utc=True, errors="raise")
    vix["VIXCLS"] = pd.to_numeric(vix["VIXCLS"], errors="coerce")
    vix = vix.dropna().sort_values("observation_date")
    events = event_table.copy().sort_values("release_timestamp_utc")
    events["known_by"] = events["release_timestamp_utc"].dt.normalize() - pd.Timedelta(days=1)
    events = pd.merge_asof(
        events, vix, left_on="known_by", right_on="observation_date", direction="backward"
    )
    if events["VIXCLS"].isna().any():
        raise ValueError("missing lagged VIX regime")
    threshold = float(events["VIXCLS"].median())
    events["regime"] = np.where(events["VIXCLS"] > threshold, "high_vix", "low_vix")
    summary = events.groupby("regime", as_index=False).agg(
        events=("event_id", "count"), mean_vix=("VIXCLS", "mean"),
        mean_event_log_return=("net_log_return", "mean"), total_log_return=("net_log_return", "sum"),
    )
    summary["net_return"] = np.expm1(summary["total_log_return"])
    return summary, sha256(vix_path)


def run(panel_path: Path, events_path: Path, vix_path: Path, output_dir: Path) -> dict:
    prices = load_panel(panel_path)
    events = load_events(events_path)
    detail = event_windows(prices, events)
    placebos = placebo_windows(prices, events)
    output_dir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(output_dir / "real_fomc_drift_2024_detail.csv", index=False)
    placebos.to_csv(output_dir / "real_fomc_drift_2024_placebos.csv", index=False)

    cost_rows = []
    event_tables = {}
    for mult in (0.0, 1.0, 2.0, 4.0):
        table = aggregate_events(detail, mult)
        event_tables[mult] = table
        total = float(np.expm1(table["net_log_return"].sum()))
        cost_rows.append({
            "cost_multiplier": mult,
            "events": len(table),
            "net_return": total,
            "mean_event_log_return": float(table["net_log_return"].mean()),
            "median_event_log_return": float(table["net_log_return"].median()),
            "positive_events": int((table["net_log_return"] > 0).sum()),
        })
    pd.DataFrame(cost_rows).to_csv(output_dir / "real_fomc_drift_2024_costs.csv", index=False)
    event_1x = event_tables[1.0]
    event_1x.to_csv(output_dir / "real_fomc_drift_2024_events.csv", index=False)

    asset = detail.assign(net=lambda x: x["gross_log_return"] - 4.0 * x["asset"].map(PIP_SIZE) / x["start_price"])
    asset_summary = asset.groupby("asset", as_index=False).agg(
        events=("event_id", "nunique"), gross_log_return=("gross_log_return", "sum"), net_log_return=("net", "sum")
    )
    asset_summary["net_return"] = np.expm1(asset_summary["net_log_return"])
    asset_summary.to_csv(output_dir / "real_fomc_drift_2024_assets.csv", index=False)
    loo = leave_one_out(detail)
    loo.to_csv(output_dir / "real_fomc_drift_2024_leave_one_out.csv", index=False)

    placebo_event = aggregate_events(placebos, 1.0)
    placebo_event["matched_event_id"] = placebo_event["event_id"].str.extract(r"(FOMC_2024_\d\d_\d\d)")[0]
    placebo_mean = placebo_event.groupby("matched_event_id")["net_log_return"].mean()
    paired = event_1x.set_index("event_id")["net_log_return"].to_frame("event_net")
    paired["placebo_net"] = placebo_mean
    paired["difference"] = paired["event_net"] - paired["placebo_net"]
    paired.reset_index().to_csv(output_dir / "real_fomc_drift_2024_paired.csv", index=False)

    p_pos, ci_low, ci_high = bootstrap_probability(event_1x["net_log_return"].to_numpy())
    p_diff, diff_low, diff_high = bootstrap_probability(paired["difference"].to_numpy())
    first = float(np.expm1(event_1x.iloc[:4]["net_log_return"].sum()))
    second = float(np.expm1(event_1x.iloc[4:]["net_log_return"].sum()))
    regimes, vix_hash = vix_regimes(event_1x, vix_path)
    regimes.to_csv(output_dir / "real_fomc_drift_2024_regimes.csv", index=False)
    summary = {
        "panel_sha256": sha256(panel_path),
        "events_sha256": sha256(events_path),
        "events": 8,
        "assets": 4,
        "panel_assets": 15,
        "net_return_1x": float(np.expm1(event_1x["net_log_return"].sum())),
        "net_return_2x": float(np.expm1(event_tables[2.0]["net_log_return"].sum())),
        "median_event_net_log_return": float(event_1x["net_log_return"].median()),
        "positive_events": int((event_1x["net_log_return"] > 0).sum()),
        "positive_assets": int((asset_summary["net_return"] > 0).sum()),
        "positive_leave_one_out": int((loo["net_return"] > 0).sum()),
        "first_half_net_return": first,
        "second_half_net_return": second,
        "bootstrap_p_mean_positive": p_pos,
        "bootstrap_mean_ci95": [ci_low, ci_high],
        "mean_event_minus_placebo_log_return": float(paired["difference"].mean()),
        "bootstrap_p_event_gt_placebo": p_diff,
        "bootstrap_difference_ci95": [diff_low, diff_high],
        "trade_count": int(len(detail) * 2),
        "round_trips": int(len(detail)),
        "vix_sha256": vix_hash,
        "decision": "pass" if all([
            np.expm1(event_1x["net_log_return"].sum()) > 0,
            event_1x["net_log_return"].median() > 0,
            (asset_summary["net_return"] > 0).sum() >= 3,
            first >= 0,
            second >= 0,
            p_pos >= 0.95,
            np.expm1(event_tables[2.0]["net_log_return"].sum()) >= 0,
            paired["difference"].mean() > 0,
            p_diff >= 0.95,
        ]) else "reject_research_only",
    }
    with (output_dir / "real_fomc_drift_2024_summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    manifest = {
        "panel": {"path": str(panel_path), "bytes": panel_path.stat().st_size, "sha256": sha256(panel_path)},
        "events": {"path": str(events_path), "bytes": events_path.stat().st_size, "sha256": sha256(events_path)},
        "vix": {"path": str(vix_path), "bytes": vix_path.stat().st_size, "sha256": vix_hash},
        "parameters": {"window_hours": 24, "end_lag_hours": 3, "max_staleness_minutes": 10, "bootstrap_draws": BOOTSTRAPS, "seed": SEED},
    }
    with (output_dir / "real_fomc_drift_2024_manifest.json").open("w") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--events", type=Path, default=Path("data/fomc_2024_official.csv"))
    parser.add_argument("--vix", type=Path, default=Path("data/fred_VIXCLS.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(run(args.panel, args.events, args.vix, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
