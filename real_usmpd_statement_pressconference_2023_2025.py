"""Research 048: timing-safe USMPD statement surprise -> press conference return.

Preregistered in GitHub issue #65 before CFD outcomes were inspected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from real_fomc_crossfamily_jumps import ASSETS, FAMILIES, load_data, sha256
from real_fomc_statement_pressconference_2023_2025 import load_vix, prior_vix


RATE_COLUMNS = [f"FF{i}" for i in range(1, 7)] + [f"ED{i}" for i in range(1, 5)]
FEATURES = [
    "statement_z", "rate_surprise", "sp_future", "rate_x_sp",
    "log_prevol", "vix", "statement_vix", "is_fx", "is_metal",
    "rate_x_fx", "rate_x_metal", "sp_x_fx", "sp_x_metal",
]
PIP = {a: (0.01 if a in {"USDJPY", "EURJPY"} else 0.0001) for a in ASSETS}
PIP.update({"XAUUSD": 0.01, "XAGUSD": 0.001, "SPXUSD": 0.1, "NSXUSD": 0.1})
ALPHA, WARMUP, DRAWS, SEED = 10.0, 8, 10_000, 20260920


def validate_usmpd(workbook: Path, manifest: Path) -> pd.DataFrame:
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    if sha256(workbook) != meta.get("sha256") or workbook.stat().st_size != meta.get("size_bytes"):
        raise ValueError("USMPD hash/size mismatch")
    if meta.get("source_updated") != "2026-09-17":
        raise ValueError("unexpected USMPD vintage")
    x = pd.read_excel(workbook, sheet_name="Statements")
    required = {"Date", "date_time", "SPFUT", *RATE_COLUMNS}
    if required - set(x.columns):
        raise ValueError("USMPD statement schema mismatch")
    x["Date"] = pd.to_datetime(x["Date"], errors="raise").dt.normalize()
    x["date_time"] = pd.to_datetime(x["date_time"], errors="raise")
    if x["Date"].duplicated().any() or x["Date"].max() < pd.Timestamp("2026-09-16"):
        raise ValueError("USMPD dates stale or duplicated")
    for c in RATE_COLUMNS + ["SPFUT"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["rate_contracts"] = x[RATE_COLUMNS].notna().sum(axis=1)
    x["rate_surprise"] = x[RATE_COLUMNS].mean(axis=1, skipna=True)
    x.loc[x.rate_contracts < 8, "rate_surprise"] = np.nan
    return x[["Date", "date_time", "rate_contracts", "rate_surprise", "SPFUT"]]


def exact(prices: pd.DataFrame, asset: str, timestamp: pd.Timestamp) -> float:
    if timestamp not in prices.index:
        raise ValueError("timestamp absent")
    value = prices.at[timestamp, asset]
    if not np.isfinite(value) or value <= 0:
        raise ValueError("quote absent")
    return float(value)


def prevol(prices: pd.DataFrame, asset: str, timestamp: pd.Timestamp) -> float:
    z = prices.loc[(prices.index >= timestamp - pd.Timedelta(days=20)) &
                   (prices.index < timestamp), asset].dropna()
    r = np.log(z).diff().dropna()
    r = r.loc[r.index.to_series().diff() <= pd.Timedelta(minutes=10)]
    if len(r) < 500:
        raise ValueError("insufficient prevol")
    value = float(r.std(ddof=1))
    if not np.isfinite(value) or value <= 0:
        raise ValueError("invalid prevol")
    return value


def build_rows(prices: pd.DataFrame, events: pd.DataFrame, usmpd: pd.DataFrame,
               vix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    family = {a: f for f, members in FAMILIES.items() for a in members}
    source = usmpd.set_index("Date")
    out, coverage = [], []
    for event in events.itertuples(index=False):
        release = event.release_timestamp_utc
        local_date = release.tz_convert("America/New_York").tz_localize(None).normalize()
        if local_date not in source.index:
            coverage.append({"event_id": event.event_id, "year": release.year,
                             "assets": 0, "families": 0, "eligible": False,
                             "reason": "USMPD date absent"})
            continue
        shock = source.loc[local_date]
        if not np.isfinite(shock.rate_surprise) or not np.isfinite(shock.SPFUT):
            coverage.append({"event_id": event.event_id, "year": release.year,
                             "assets": 0, "families": 0, "eligible": False,
                             "reason": "USMPD surprise absent"})
            continue
        # USMPD statement information is complete only at T+20; every feature
        # below is either known then or lagged. The target starts at that boundary.
        tmp = []
        for asset in ASSETS:
            try:
                p0 = exact(prices, asset, release - pd.Timedelta(minutes=10))
                p1 = exact(prices, asset, release + pd.Timedelta(minutes=20))
                p2 = exact(prices, asset, release + pd.Timedelta(minutes=90))
                vol = prevol(prices, asset, release)
                lag_vix = prior_vix(vix, release)
            except ValueError:
                continue
            tmp.append({
                "event_id": event.event_id, "release_timestamp_utc": release,
                "year": release.year, "asset": asset, "family": family[asset],
                "statement_return": float(np.log(p1 / p0)),
                "press_return": float(np.log(p2 / p1)), "entry_price": p1,
                "prevol": vol, "vix": lag_vix,
                "rate_surprise": float(shock.rate_surprise),
                "sp_future": float(shock.SPFUT) / 100.0,
                "rate_contracts": int(shock.rate_contracts),
                "cost_1x": 4 * PIP[asset] / p1,
            })
        families = len({r["family"] for r in tmp})
        eligible = len(tmp) >= 10 and families == 3
        coverage.append({"event_id": event.event_id, "year": release.year,
                         "assets": len(tmp), "families": families,
                         "eligible": eligible, "reason": "" if eligible else "CFD coverage"})
        if eligible:
            out.extend(tmp)
    x, cov = pd.DataFrame(out), pd.DataFrame(coverage)
    if cov.eligible.sum() < 16:
        raise ValueError("fewer than 16 eligible events")
    x["statement_z"] = x.statement_return / x.prevol
    x["rate_x_sp"] = x.rate_surprise * x.sp_future
    x["log_prevol"] = np.log(x.prevol)
    x["statement_vix"] = x.statement_z * x.vix
    x["is_fx"] = (x.family == "fx").astype(float)
    x["is_metal"] = (x.family == "metal").astype(float)
    x["rate_x_fx"] = x.rate_surprise * x.is_fx
    x["rate_x_metal"] = x.rate_surprise * x.is_metal
    x["sp_x_fx"] = x.sp_future * x.is_fx
    x["sp_x_metal"] = x.sp_future * x.is_metal
    x["target_z"] = x.press_return / x.prevol
    if not np.isfinite(x[FEATURES + ["target_z"]].to_numpy()).all():
        raise ValueError("nonfinite model matrix")
    return x, cov


def ridge_fit(train: pd.DataFrame):
    mu = train[FEATURES].mean()
    sd = train[FEATURES].std(ddof=0).replace(0, 1)
    X = ((train[FEATURES] - mu) / sd).to_numpy()
    X = np.c_[np.ones(len(X)), X]
    y = train.target_z.to_numpy()
    penalty = np.eye(X.shape[1]) * ALPHA
    penalty[0, 0] = 0
    beta = np.linalg.solve(X.T @ X + penalty, X.T @ y)
    residual = y - X @ beta
    return mu, sd, beta, float(np.median(np.abs(residual)))


def ridge_signals(x: pd.DataFrame, order: list[str]) -> pd.Series:
    signal = pd.Series(0.0, index=x.index)
    for pos, event_id in enumerate(order):
        if pos < WARMUP:
            continue
        test = x[x.event_id == event_id]
        cutoff = test.release_timestamp_utc.iloc[0]
        train = x[x.release_timestamp_utc < cutoff]
        if train.event_id.nunique() < WARMUP:
            raise ValueError("walk-forward leakage")
        mu, sd, beta, mad = ridge_fit(train)
        X = ((test[FEATURES] - mu) / sd).to_numpy()
        pred_z = np.c_[np.ones(len(X)), X] @ beta
        raw = pred_z * test.prevol.to_numpy()
        threshold = test.cost_1x.to_numpy() + 0.5 * mad * test.prevol.to_numpy()
        signal.loc[test.index] = np.where(np.abs(raw) > threshold, np.sign(raw), 0)
    return signal


def economic_signal(row: pd.Series) -> float:
    # Same-sign rate/equity movements are information shocks and abstain.
    if row.rate_surprise == 0 or row.sp_future == 0 or row.rate_surprise * row.sp_future >= 0:
        return 0.0
    hawkish = float(np.sign(row.rate_surprise))
    if row.asset in {"USDJPY", "USDCHF", "USDCAD"}:
        return hawkish
    if row.asset in {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}:
        return -hawkish
    if row.asset == "EURJPY":
        return 0.0
    return -hawkish  # metals and U.S. equity indexes


def strategy_rows(x: pd.DataFrame, kind: str, order: list[str]) -> pd.DataFrame:
    z = x[x.event_id.isin(order[WARMUP:])].copy()
    if kind == "price_only":
        z["signal"] = np.sign(z.statement_return)
    elif kind == "economic":
        z["signal"] = z.apply(economic_signal, axis=1)
    elif kind == "long":
        z["signal"] = 1.0
    elif kind == "ridge":
        z["signal"] = ridge_signals(x, order).reindex(z.index)
    else:
        raise ValueError(kind)
    z = z[z.signal != 0].copy()
    z["invvol"] = 1 / z.prevol
    z["weight"] = z.groupby("event_id").invvol.transform(lambda q: q / q.sum())
    z["gross"] = z.weight * z.signal * z.press_return
    z["cost"] = z.weight * z.cost_1x
    return z


def event_returns(z: pd.DataFrame, multiplier: float, all_events: list[str]) -> pd.DataFrame:
    e = z.assign(net=z.gross - multiplier * z.cost).groupby("event_id", as_index=False).agg(
        gross=("gross", "sum"), cost_1x=("cost", "sum"), net=("net", "sum"),
        round_trips=("asset", "count"))
    return pd.DataFrame({"event_id": all_events}).merge(e, on="event_id", how="left").fillna(0)


def block_probability(values: np.ndarray) -> tuple[float, list[float]]:
    n = len(values)
    rng = np.random.default_rng(SEED)
    starts = rng.integers(n, size=(DRAWS, int(np.ceil(n / 2))))
    idx = np.stack([starts, (starts + 1) % n], axis=-1).reshape(DRAWS, -1)[:, :n]
    means = values[idx].mean(axis=1)
    return float((means > 0).mean()), [float(v) for v in np.quantile(means, [.025, .975])]


def summary(e: pd.DataFrame) -> dict:
    probability, ci = block_probability(e.net.to_numpy())
    return {"events": len(e), "round_trips": int(e.round_trips.sum()),
            "trade_legs": int(2 * e.round_trips.sum()),
            "gross_return": float(np.expm1(e.gross.sum())),
            "net_return": float(np.expm1(e.net.sum())),
            "positive_events": int((e.net > 0).sum()),
            "block_p_mean_positive": probability, "block_ci95_mean_log": ci}


def run(panel: Path, panel_manifest: Path, events_file: Path, vix_file: Path,
        workbook: Path, usmpd_manifest: Path, output: Path) -> dict:
    prices, events, _ = load_data(panel, panel_manifest, events_file)
    usmpd = validate_usmpd(workbook, usmpd_manifest)
    vix = load_vix(vix_file)
    x, coverage = build_rows(prices, events, usmpd, vix)
    order = coverage.loc[coverage.eligible, "event_id"].tolist()
    evaluation = order[WARMUP:]
    output.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(output / "research048_coverage.csv", index=False)
    x.to_csv(output / "research048_rows.csv", index=False)
    models, tables = {}, {}
    for kind in ("price_only", "economic", "long", "ridge"):
        trades = strategy_rows(x, kind, order)
        trades.to_csv(output / f"research048_{kind}_trades.csv", index=False)
        costs = []
        for multiplier in (0, 1, 2, 4):
            e = event_returns(trades, multiplier, evaluation)
            e.to_csv(output / f"research048_{kind}_events_{multiplier}x.csv", index=False)
            costs.append({"cost_multiplier": multiplier, **summary(e)})
            if multiplier == 1:
                tables[kind] = e
        models[kind] = costs

    paired = tables["ridge"].net.to_numpy() - tables["price_only"].net.to_numpy()
    paired_p, paired_ci = block_probability(paired)
    ridge = strategy_rows(x, "ridge", order)
    family_loo = []
    for family in sorted(FAMILIES):
        q = ridge[ridge.family != family].copy()
        q["weight"] = q.groupby("event_id").invvol.transform(lambda v: v / v.sum())
        q["gross"] = q.weight * q.signal * q.press_return
        q["cost"] = q.weight * q.cost_1x
        e = event_returns(q, 1, evaluation)
        family_loo.append({"excluded_family": family,
                           "net_return": float(np.expm1(e.net.sum()))})
    loo = pd.DataFrame(family_loo)
    loo.to_csv(output / "research048_ridge_family_leave_one_out.csv", index=False)

    asset_loo = []
    for asset in ASSETS:
        q = ridge[ridge.asset != asset].copy()
        q["weight"] = q.groupby("event_id").invvol.transform(lambda v: v / v.sum())
        q["gross"] = q.weight * q.signal * q.press_return
        q["cost"] = q.weight * q.cost_1x
        e = event_returns(q, 1, evaluation)
        asset_loo.append({"excluded_asset": asset,
                          "net_return": float(np.expm1(e.net.sum()))})
    asset_loo_frame = pd.DataFrame(asset_loo)
    asset_loo_frame.to_csv(output / "research048_ridge_asset_leave_one_out.csv", index=False)

    event_meta = x[["event_id", "year"]].drop_duplicates("event_id")
    primary = tables["ridge"].merge(event_meta, on="event_id", how="left")
    years = primary.groupby("year", as_index=False).net.sum()
    years["net_return"] = np.expm1(years.net)
    years.to_csv(output / "research048_ridge_years.csv", index=False)
    primary["phase"] = np.where(np.arange(len(primary)) < len(primary) / 2, "first", "second")
    warm_vix = x[x.event_id.isin(order[:WARMUP])].drop_duplicates("event_id").vix.median()
    event_vix = x[["event_id", "vix"]].drop_duplicates("event_id")
    primary = primary.merge(event_vix, on="event_id", how="left")
    primary["vix_regime"] = np.where(primary.vix > warm_vix, "high", "low")
    phases = primary.groupby("phase", as_index=False).net.sum()
    phases["net_return"] = np.expm1(phases.net)
    regimes = primary.groupby("vix_regime", as_index=False).net.sum()
    regimes["net_return"] = np.expm1(regimes.net)
    phases.to_csv(output / "research048_ridge_phases.csv", index=False)
    regimes.to_csv(output / "research048_ridge_vix_regimes.csv", index=False)

    # The economic rule was preregistered as a baseline. Persist its time
    # stability rather than promoting it based on the observed total return.
    economic_primary = tables["economic"].merge(event_meta, on="event_id", how="left")
    economic_years = economic_primary.groupby("year", as_index=False).net.sum()
    economic_years["net_return"] = np.expm1(economic_years.net)
    economic_years.to_csv(output / "research048_economic_years.csv", index=False)
    economic_paired = tables["economic"].net.to_numpy() - tables["price_only"].net.to_numpy()
    economic_paired_p, economic_paired_ci = block_probability(economic_paired)
    economic = strategy_rows(x, "economic", order)
    economic_family_loo = []
    for family in sorted(FAMILIES):
        q = economic[economic.family != family].copy()
        q["weight"] = q.groupby("event_id").invvol.transform(lambda v: v / v.sum())
        q["gross"] = q.weight * q.signal * q.press_return
        q["cost"] = q.weight * q.cost_1x
        e = event_returns(q, 1, evaluation)
        economic_family_loo.append({"excluded_family": family,
                                    "net_return": float(np.expm1(e.net.sum()))})
    economic_loo = pd.DataFrame(economic_family_loo)
    economic_loo.to_csv(output / "research048_economic_family_leave_one_out.csv", index=False)
    economic_asset_loo = []
    for asset in ASSETS:
        q = economic[economic.asset != asset].copy()
        q["weight"] = q.groupby("event_id").invvol.transform(lambda v: v / v.sum())
        q["gross"] = q.weight * q.signal * q.press_return
        q["cost"] = q.weight * q.cost_1x
        e = event_returns(q, 1, evaluation)
        economic_asset_loo.append({"excluded_asset": asset,
                                   "net_return": float(np.expm1(e.net.sum()))})
    economic_asset_loo_frame = pd.DataFrame(economic_asset_loo)
    economic_asset_loo_frame.to_csv(output / "research048_economic_asset_leave_one_out.csv", index=False)

    m1 = next(v for v in models["ridge"] if v["cost_multiplier"] == 1)
    m2 = next(v for v in models["ridge"] if v["cost_multiplier"] == 2)
    gates = {
        "ridge_net_1x_positive": m1["net_return"] > 0,
        "ridge_beats_price_only_p_at_least_95pct": paired_p >= .95,
        "ridge_2024_and_2025_positive": set(years.year) == {2024, 2025} and bool((years.net > 0).all()),
        "ridge_net_2x_positive": m2["net_return"] > 0,
        "all_family_loo_positive": bool((loo.net_return > 0).all()),
        "coverage_at_least_16_events_10_assets": len(order) >= 16 and int(coverage.assets.max()) >= 10,
    }
    possible = len(x[x.event_id.isin(evaluation)])
    result = {
        "panel_sha256": sha256(panel), "panel_manifest_sha256": sha256(panel_manifest),
        "events_sha256": sha256(events_file), "vix_sha256": sha256(vix_file),
        "usmpd_sha256": sha256(workbook), "usmpd_manifest_sha256": sha256(usmpd_manifest),
        "eligible_events": len(order), "warmup_events": WARMUP,
        "evaluation_events": len(evaluation), "models": models,
        "paired_ridge_minus_price_only_block_p": paired_p,
        "paired_ci95_mean_log": paired_ci, "gates": gates,
        "passed_all_gates": all(gates.values()),
        "ridge_active_round_trips": int(len(ridge)),
        "ridge_trade_legs": int(2 * len(ridge)),
        "ridge_abstention_rate": float(1 - len(ridge) / possible),
        "ridge_direction_hit_rate": float((ridge.signal * ridge.press_return > 0).mean()) if len(ridge) else None,
        "all_ridge_asset_loo_positive": bool((asset_loo_frame.net_return > 0).all()),
        "economic_minus_price_only_block_p": economic_paired_p,
        "economic_minus_price_only_ci95_mean_log": economic_paired_ci,
        "economic_all_years_positive": bool((economic_years.net > 0).all()),
        "economic_all_family_loo_positive": bool((economic_loo.net_return > 0).all()),
        "economic_all_asset_loo_positive": bool((economic_asset_loo_frame.net_return > 0).all()),
        "economic_active_round_trips": int(len(economic)),
        "economic_zero_trade_events": int((tables["economic"].round_trips == 0).sum()),
        "fixed_roundtrip_cost_pips": 4,
        "decision": "research_candidate_requires_untouched_holdout" if all(gates.values())
                    else "rejected_research_only_failed_preregistered_gates",
    }
    (output / "research048_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    artifacts = {}
    for path in sorted(output.glob("research048_*")):
        if path.name != "research048_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    output_manifest = {
        "research": 48,
        "source_updated": "2026-09-17",
        "inputs": {
            "panel": sha256(panel), "panel_manifest": sha256(panel_manifest),
            "events": sha256(events_file), "vix": sha256(vix_file),
            "usmpd": sha256(workbook), "usmpd_manifest": sha256(usmpd_manifest),
        },
        "artifacts": artifacts,
    }
    (output / "research048_manifest.json").write_text(
        json.dumps(output_manifest, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("panel", "panel-manifest", "events", "vix", "workbook", "usmpd-manifest", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(a.panel, a.panel_manifest, a.events, a.vix,
                         a.workbook, a.usmpd_manifest, a.output), indent=2, sort_keys=True))
