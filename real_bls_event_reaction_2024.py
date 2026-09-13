"""Research 042: timing-safe BLS CPI/employment reaction on 15 CFD proxies."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ASSETS = ["AUDUSD", "BCOUSD", "EURJPY", "EURUSD", "GBPUSD", "GRXEUR",
          "NSXUSD", "NZDUSD", "SPXUSD", "UKXGBP", "USDCAD", "USDCHF",
          "USDJPY", "XAGUSD", "XAUUSD"]
PIP = {a: (0.01 if a in {"USDJPY", "EURJPY"} else 0.0001) for a in ASSETS}
PIP.update({"XAUUSD": 0.01, "XAGUSD": 0.001, "BCOUSD": 0.01,
            "SPXUSD": 0.1, "NSXUSD": 0.1, "GRXEUR": 0.1, "UKXGBP": 0.1})
FAMILY = {a: ("equity" if a in {"SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP"}
              else "metal" if a in {"XAUUSD", "XAGUSD"}
              else "energy" if a == "BCOUSD" else "fx") for a in ASSETS}
PANEL_SHA = "e632e54adb79e027e991bb335a917e9a7a30e16c6ddf33b0daecc9ceeae5d05c"
SEED = 42042


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_panel(path: Path) -> pd.DataFrame:
    if sha256(path) != PANEL_SHA:
        raise ValueError("panel SHA-256 mismatch")
    x = pd.read_csv(path)
    if not {"timestamp", *ASSETS}.issubset(x.columns):
        raise ValueError("panel schema mismatch")
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True, errors="raise")
    if x["timestamp"].duplicated().any():
        raise ValueError("duplicate timestamps")
    x = x.set_index("timestamp").sort_index()[ASSETS]
    for asset in ASSETS:
        x[asset] = pd.to_numeric(x[asset], errors="coerce")
    return x


def load_events(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path, dtype=str)
    required = {"event_id", "category", "release_date_local", "release_time_local",
                "release_timezone", "source_url"}
    if not required.issubset(x.columns) or len(x) != 24 or x.event_id.duplicated().any():
        raise ValueError("event schema/count mismatch")
    if set(x.category) != {"cpi", "employment"} or (x.groupby("category").size() != 12).any():
        raise ValueError("event category mismatch")
    if not (x.release_timezone == "America/New_York").all():
        raise ValueError("event timezone mismatch")
    if not x.source_url.str.startswith("https://www.bls.gov/").all():
        raise ValueError("unverified event source")
    local = pd.to_datetime(x.release_date_local + " " + x.release_time_local, errors="raise")
    x["release_timestamp_utc"] = local.dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    return x.sort_values("release_timestamp_utc").reset_index(drop=True)


def quote(series: pd.Series, timestamp: pd.Timestamp) -> tuple[float, pd.Timestamp]:
    z = series.loc[timestamp:].dropna()
    if z.empty or z.index[0] - timestamp > pd.Timedelta(minutes=10):
        raise ValueError("stale or missing quote")
    return float(z.iloc[0]), z.index[0]


def prevol(series: pd.Series, timestamp: pd.Timestamp) -> float:
    z = series.loc[(series.index >= timestamp - pd.Timedelta(days=20)) &
                   (series.index < timestamp)].dropna()
    returns = np.log(z).diff().dropna()
    returns = returns.loc[returns.index.to_series().diff() <= pd.Timedelta(minutes=10)]
    if len(returns) < 100:
        raise ValueError("insufficient volatility history")
    vol = float(returns.std(ddof=1))
    if not np.isfinite(vol) or vol <= 0:
        raise ValueError("invalid volatility")
    return vol


def load_vix(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path)
    x["observation_date"] = pd.to_datetime(x.observation_date, utc=True, errors="raise")
    x["VIXCLS"] = pd.to_numeric(x.VIXCLS, errors="coerce")
    return x.dropna().sort_values("observation_date")


def lagged_vix(vix: pd.DataFrame, timestamp: pd.Timestamp) -> float:
    prior = vix.loc[vix.observation_date < timestamp.normalize()]
    if prior.empty:
        raise ValueError("missing lagged VIX")
    return float(prior.iloc[-1].VIXCLS)


def build_rows(prices: pd.DataFrame, events: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for event in events.itertuples(index=False):
        t0 = event.release_timestamp_utc
        t1 = t0 + pd.Timedelta(minutes=5)
        tend = t0 + pd.Timedelta(minutes=60)
        vix_value = lagged_vix(vix, t0)
        for asset in ASSETS:
            try:
                p0, q0 = quote(prices[asset], t0)
                p1, q1 = quote(prices[asset], t1)
                pend, qend = quote(prices[asset], tend)
                vol = prevol(prices[asset], t0)
            except ValueError:
                continue
            rows.append({
                "event_id": event.event_id, "category": event.category,
                "release_timestamp_utc": t0, "asset": asset, "family": FAMILY[asset],
                "p0": p0, "p1": p1, "pend": pend, "q0": q0, "q1": q1, "qend": qend,
                "initial_log_return": float(np.log(p1 / p0)),
                "future_log_return": float(np.log(pend / p1)),
                "pre_event_vol": vol, "vix": vix_value,
            })
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("no valid event/asset rows")
    return out


def ridge_signals(rows: pd.DataFrame) -> pd.Series:
    """Expanding ridge; no signal until four prior complete release timestamps exist."""
    signals = pd.Series(0.0, index=rows.index)
    for timestamp, group in rows.groupby("release_timestamp_utc", sort=True):
        train = rows.loc[rows.release_timestamp_utc < timestamp].copy()
        if train.release_timestamp_utc.nunique() < 4:
            continue
        train["initial_z"] = train.initial_log_return / train.pre_event_vol
        group = group.copy()
        group["initial_z"] = group.initial_log_return / group.pre_event_vol
        train["cpi"] = (train.category == "cpi").astype(float)
        group["cpi"] = (group.category == "cpi").astype(float)
        train["initial_cpi"] = train.initial_z * train.cpi
        group["initial_cpi"] = group.initial_z * group.cpi
        train["vix_cpi"] = train.vix * train.cpi
        group["vix_cpi"] = group.vix * group.cpi
        cols = ["initial_z", "pre_event_vol", "vix", "cpi", "initial_cpi", "vix_cpi"]
        mu = train[cols].mean()
        sd = train[cols].std(ddof=0).replace(0, 1.0)
        X = ((train[cols] - mu) / sd).to_numpy()
        y = train.future_log_return.to_numpy()
        X = np.c_[np.ones(len(X)), X]
        penalty = np.eye(X.shape[1]); penalty[0, 0] = 0.0
        beta = np.linalg.solve(X.T @ X + penalty, X.T @ y)
        Xnew = np.c_[np.ones(len(group)), ((group[cols] - mu) / sd).to_numpy()]
        signals.loc[group.index] = np.sign(Xnew @ beta)
    return signals


def make_strategy(rows: pd.DataFrame, kind: str) -> pd.DataFrame:
    x = rows.copy()
    if kind == "continuation":
        x["signal"] = np.sign(x.initial_log_return)
        x["scale"] = 1.0
    elif kind in {"reversal", "equal_risk_reversal"}:
        x["signal"] = -np.sign(x.initial_log_return)
        x["scale"] = 1.0 if kind == "reversal" else 1.0 / x.pre_event_vol
    elif kind == "expanding_ridge":
        x["signal"] = ridge_signals(x)
        x["scale"] = 1.0 / x.pre_event_vol
    else:
        raise ValueError("unknown strategy")
    x = x.loc[x.signal != 0].copy()
    x["weight"] = x.groupby("event_id").scale.transform(lambda z: z / z.sum())
    x["gross"] = x.weight * x.signal * x.future_log_return
    x["cost_1x"] = x.weight * 4.0 * x.asset.map(PIP) / x.p1
    return x


def common_ridge_subset(rows: pd.DataFrame) -> pd.DataFrame:
    ordered = rows[["event_id", "release_timestamp_utc"]].drop_duplicates().sort_values("release_timestamp_utc")
    valid_ids = set(ordered.iloc[4:].event_id)
    return rows.loc[rows.event_id.isin(valid_ids)].copy()


def event_returns(strategy: pd.DataFrame, multiplier: float) -> pd.DataFrame:
    return (strategy.assign(net=strategy.gross - multiplier * strategy.cost_1x)
            .groupby(["event_id", "release_timestamp_utc", "category"], as_index=False)
            .agg(net=("net", "sum"), gross=("gross", "sum"), cost_1x=("cost_1x", "sum"),
                 trades=("asset", "count"), vix=("vix", "first")))


def bootstrap_probability(values: np.ndarray, draws: int = 10000) -> tuple[float, list[float]]:
    rng = np.random.default_rng(SEED)
    boot = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    return float((boot > 0).mean()), [float(np.quantile(boot, .025)), float(np.quantile(boot, .975))]


def summarize(strategy: pd.DataFrame, multiplier: float) -> tuple[dict, pd.DataFrame]:
    events = event_returns(strategy, multiplier)
    probability, interval = bootstrap_probability(events.net.to_numpy())
    return {
        "events": int(len(events)), "round_trips": int(len(strategy)),
        "trade_legs": int(2 * len(strategy)), "net_return": float(np.expm1(events.net.sum())),
        "mean_event_log_return": float(events.net.mean()),
        "positive_events": int((events.net > 0).sum()),
        "bootstrap_p_mean_positive": probability, "bootstrap_ci95_mean": interval,
    }, events


def diagnostics(strategy: pd.DataFrame, output: Path, prefix: str) -> dict:
    base_events = event_returns(strategy, 1.0)
    midpoint = base_events.release_timestamp_utc.sort_values().iloc[len(base_events) // 2]
    halves = []
    for label, mask in (("first", base_events.release_timestamp_utc < midpoint),
                        ("second", base_events.release_timestamp_utc >= midpoint)):
        z = base_events.loc[mask]
        halves.append({"half": label, "events": len(z), "net_return": float(np.expm1(z.net.sum()))})
    pd.DataFrame(halves).to_csv(output / f"{prefix}_halves.csv", index=False)

    family = []
    for fam in sorted(strategy.family.unique()):
        z = strategy.loc[strategy.family == fam]
        e = event_returns(z, 1.0)
        family.append({"family": fam, "assets": z.asset.nunique(), "events": len(e),
                       "net_return": float(np.expm1(e.net.sum()))})
    pd.DataFrame(family).to_csv(output / f"{prefix}_families.csv", index=False)

    leave = []
    for asset in sorted(strategy.asset.unique()):
        z = strategy.loc[strategy.asset != asset]
        e = event_returns(z, 1.0)
        leave.append({"omitted_asset": asset, "assets_remaining": z.asset.nunique(),
                      "net_return": float(np.expm1(e.net.sum()))})
    pd.DataFrame(leave).to_csv(output / f"{prefix}_asset_leave_one_out.csv", index=False)

    threshold = float(base_events.vix.median())
    regimes = []
    for label, mask in (("low_vix", base_events.vix <= threshold), ("high_vix", base_events.vix > threshold)):
        z = base_events.loc[mask]
        regimes.append({"regime": label, "events": len(z), "net_return": float(np.expm1(z.net.sum()))})
    pd.DataFrame(regimes).to_csv(output / f"{prefix}_vix_regimes.csv", index=False)
    return {"positive_families": int(sum(row["net_return"] > 0 for row in family)),
            "both_halves_nonnegative": bool(all(row["net_return"] >= 0 for row in halves))}


def run(panel_path: Path, event_path: Path, vix_path: Path, output: Path) -> dict:
    prices = load_panel(panel_path)
    events = load_events(event_path)
    vix = load_vix(vix_path)
    rows = build_rows(prices, events, vix)
    output.mkdir(parents=True, exist_ok=True)
    rows.to_csv(output / "research042_rows.csv", index=False)

    common = common_ridge_subset(rows)
    models = {}
    strategies = {}
    for kind in ("continuation", "reversal", "equal_risk_reversal", "expanding_ridge"):
        source = rows if kind == "expanding_ridge" else common
        strategy = make_strategy(source, kind)
        strategies[kind] = strategy
        costs = []
        for multiplier in (0.0, 1.0, 2.0, 4.0):
            summary, event_table = summarize(strategy, multiplier)
            event_table.to_csv(output / f"research042_{kind}_events_{int(multiplier)}x.csv", index=False)
            summary["cost_multiplier"] = multiplier
            costs.append(summary)
        pd.DataFrame(costs).to_csv(output / f"research042_{kind}_costs.csv", index=False)
        models[kind] = costs

    ridge_diag = diagnostics(strategies["expanding_ridge"], output, "research042_expanding_ridge")
    ridge_1x = models["expanding_ridge"][1]
    benchmark_1x = [models["continuation"][1]["net_return"], models["reversal"][1]["net_return"]]
    gates = {
        "ridge_positive_1x": ridge_1x["net_return"] > 0,
        "ridge_beats_continuation_and_reversal": ridge_1x["net_return"] > max(benchmark_1x),
        "bootstrap_at_least_95pct": ridge_1x["bootstrap_p_mean_positive"] >= .95,
        "both_halves_nonnegative": ridge_diag["both_halves_nonnegative"],
        "at_least_3_of_4_families_positive": ridge_diag["positive_families"] >= 3,
        "ridge_positive_2x": models["expanding_ridge"][2]["net_return"] > 0,
    }
    summary = {
        "panel_sha256": sha256(panel_path), "events_sha256": sha256(event_path),
        "vix_sha256": sha256(vix_path), "panel_assets": len(ASSETS),
        "usable_assets": int(rows.asset.nunique()), "official_events": len(events),
        "usable_events": int(rows.event_id.nunique()), "valid_rows": len(rows),
        "common_comparison_events": int(common.event_id.nunique()),
        "models": models, "gates": gates, "passed_all_gates": all(gates.values()),
        "decision": "research_only_exploratory_rejected" if not all(gates.values()) else "research_only_exploratory_passed",
        "note": "2024 was used in prior research and is not an untouched holdout",
    }
    (output / "research042_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--vix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.panel, args.events, args.vix, args.output_dir), indent=2))
