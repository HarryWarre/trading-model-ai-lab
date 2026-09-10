"""Research 038: leakage-resistant residual intraday CFD model.

The script consumes the hash-locked wide 5-minute panel and a FRED VIX CSV.
It evaluates a nonlinear model and two fixed baselines with expanding,
purged walk-forward training. 2024 is explicitly an exploratory sample.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


SEED = 38038
HORIZON_BARS = 12
ENTRY_LAG_BARS = 1
MIN_TRAIN_DAYS = 60
REFIT_DAYS = 21
DECISION_HOURS = tuple(range(8, 24))
ASSET_FAMILY = {
    "AUDUSD": "fx", "EURJPY": "fx", "EURUSD": "fx", "GBPUSD": "fx",
    "NZDUSD": "fx", "USDCAD": "fx", "USDCHF": "fx", "USDJPY": "fx",
    "GRXEUR": "equity", "NSXUSD": "equity", "SPXUSD": "equity",
    "UKXGBP": "equity", "BCOUSD": "commodity", "XAGUSD": "commodity",
    "XAUUSD": "commodity",
}
FEATURES = [
    "z_r5", "z_r30", "z_r120", "z_same_clock", "vol60", "vol120",
    "family_r30", "breadth", "dispersion", "hour_sin", "hour_cos",
    "vix_lag1", "vix_change_lag1",
]
PRICE_FEATURES = ["z_r5", "z_r30", "z_r120", "z_same_clock", "vol60", "vol120"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def family_bps(asset: str) -> float:
    family = ASSET_FAMILY[asset]
    return {"fx": 1.0, "equity": 2.0, "commodity": 2.0}[family]


def load_prices(path: Path) -> pd.DataFrame:
    prices = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    prices.index = pd.to_datetime(prices.index, utc=True)
    prices = prices.apply(pd.to_numeric, errors="coerce").sort_index()
    missing = set(ASSET_FAMILY) - set(prices.columns)
    if missing:
        raise ValueError(f"Missing frozen assets: {sorted(missing)}")
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("Timestamp index must be unique and sorted")
    return prices[list(ASSET_FAMILY)]


def load_lagged_vix(path: Path, index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    raw = pd.read_csv(path)
    raw["observation_date"] = pd.to_datetime(raw["observation_date"], utc=True)
    daily = pd.Series(pd.to_numeric(raw["VIXCLS"], errors="coerce").to_numpy(),
                      index=raw["observation_date"]).dropna().sort_index()
    lagged = daily.shift(1)
    changed = daily.diff().shift(1)
    dates = pd.DatetimeIndex(index.normalize())
    level = lagged.reindex(dates, method="ffill").set_axis(index)
    delta = changed.reindex(dates, method="ffill").set_axis(index)
    return level, delta


def make_dataset(prices: pd.DataFrame, vix_path: Path) -> pd.DataFrame:
    logp = np.log(prices)
    r5 = logp.diff()
    vol60 = r5.rolling(12, min_periods=10).std()
    vol120 = r5.rolling(24, min_periods=20).std()
    r30 = logp.diff(6)
    r120 = logp.diff(24)
    # Trade at t+5m and exit at t+65m. This makes adjacent hourly holdings non-overlapping.
    forward = logp.shift(-(ENTRY_LAG_BARS + HORIZON_BARS)) - logp.shift(-ENTRY_LAG_BARS)
    same_clock = forward.shift(288)
    vix, vix_change = load_lagged_vix(vix_path, prices.index)
    breadth = r5.gt(0).sum(axis=1) / r5.notna().sum(axis=1).replace(0, np.nan)
    dispersion = r5.std(axis=1)

    family_forward = pd.DataFrame(index=prices.index)
    family_r30 = pd.DataFrame(index=prices.index)
    for family in sorted(set(ASSET_FAMILY.values())):
        members = [a for a, f in ASSET_FAMILY.items() if f == family]
        family_forward[family] = forward[members].median(axis=1, skipna=True)
        family_r30[family] = r30[members].median(axis=1, skipna=True)

    rows = []
    for asset in prices.columns:
        sigma = vol120[asset].replace(0, np.nan)
        family = ASSET_FAMILY[asset]
        f = pd.DataFrame(index=prices.index)
        f["z_r5"] = r5[asset] / sigma
        f["z_r30"] = r30[asset] / (sigma * np.sqrt(6))
        f["z_r120"] = r120[asset] / (sigma * np.sqrt(24))
        f["z_same_clock"] = same_clock[asset] / (sigma * np.sqrt(HORIZON_BARS))
        f["vol60"] = vol60[asset]
        f["vol120"] = sigma
        f["family_r30"] = family_r30[family] / (sigma * np.sqrt(6))
        f["breadth"] = breadth
        f["dispersion"] = dispersion
        f["hour_sin"] = np.sin(2 * np.pi * f.index.hour / 24)
        f["hour_cos"] = np.cos(2 * np.pi * f.index.hour / 24)
        f["vix_lag1"] = vix
        f["vix_change_lag1"] = vix_change
        f["realized"] = forward[asset]
        f["target"] = (forward[asset] - family_forward[family]) / (sigma * np.sqrt(HORIZON_BARS))
        f["asset"] = asset
        f["family"] = family
        rows.append(f.reset_index(names="timestamp"))
    data = pd.concat(rows, ignore_index=True)
    data = data[(data.timestamp.dt.weekday < 5) & data.timestamp.dt.hour.isin(DECISION_HOURS)
                & (data.timestamp.dt.minute == 0)]
    for col in FEATURES + ["target"]:
        data[col] = data[col].replace([np.inf, -np.inf], np.nan)
    data[["z_r5", "z_r30", "z_r120", "z_same_clock", "family_r30", "target"]] = (
        data[["z_r5", "z_r30", "z_r120", "z_same_clock", "family_r30", "target"]].clip(-10, 10)
    )
    return data.sort_values(["timestamp", "asset"]).reset_index(drop=True)


def choose_weights(frame: pd.DataFrame, pred_col: str, threshold: float) -> dict[str, float]:
    weights = {a: 0.0 for a in ASSET_FAMILY}
    valid = frame.dropna(subset=[pred_col, "vol120", "realized"]).copy()
    if len(valid) < 10 or valid[pred_col].max() - valid[pred_col].min() < threshold:
        return weights

    # One long and one short in every family removes broad FX/equity/commodity
    # direction and enforces the preregistered two-position family cap.
    longs, shorts = [], []
    for family in sorted(valid.family.unique()):
        family_rows = valid[valid.family == family].sort_values(pred_col)
        if len(family_rows) < 2:
            continue
        shorts.append(str(family_rows.iloc[0].asset))
        longs.append(str(family_rows.iloc[-1].asset))
    if len(longs) < 3 or len(shorts) < 3:
        return weights
    vols = valid.set_index("asset")["vol120"]
    for names, sign in [(longs, 1.0), (shorts, -1.0)]:
        inv = 1 / vols[names].clip(lower=1e-8)
        side_weights = 0.5 * inv / inv.sum()
        for asset, value in side_weights.items():
            weights[asset] = sign * float(value)
    return weights


def train_spread_threshold(model, train: pd.DataFrame, cols: list[str]) -> float:
    recent_days = sorted(train.timestamp.dt.normalize().unique())[-60:]
    sample = train[train.timestamp.dt.normalize().isin(recent_days)].copy()
    sample["p"] = model.predict(sample[cols])
    spread = sample.groupby("timestamp")["p"].agg(lambda x: x.max() - x.min())
    return float(spread.median())


def metrics(values: pd.Series) -> dict:
    x = pd.Series(values).dropna()
    equity = np.exp(x.cumsum())
    sd = x.std()
    return {
        "n": int(len(x)), "total_return": float(equity.iloc[-1] - 1),
        "annualized_mean": float(x.mean() * 252 * 16),
        "sharpe": float(x.mean() / sd * np.sqrt(252 * 16)) if sd > 0 else None,
        "max_drawdown": float((equity / equity.cummax() - 1).min()),
    }


def run_walk_forward(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    timestamps = sorted(data.timestamp.unique())
    dates = sorted(data.timestamp.dt.normalize().unique())
    date_number = {d: i for i, d in enumerate(dates)}
    specs = {
        "nonlinear": (HistGradientBoostingRegressor(max_iter=50, max_depth=2,
            learning_rate=.05, l2_regularization=1., random_state=SEED), FEATURES),
        "ridge": (make_pipeline(StandardScaler(), Ridge(alpha=10.0)), FEATURES),
        "price_only": (make_pipeline(StandardScaler(), Ridge(alpha=10.0)), PRICE_FEATURES),
    }
    fitted: dict[str, object] = {}
    thresholds: dict[str, float] = {}
    previous = {name: {a: 0.0 for a in ASSET_FAMILY} for name in specs}
    last_fit_day = -10_000
    decisions, positions = [], []

    for timestamp_number, timestamp in enumerate(timestamps):
        timestamp = pd.Timestamp(timestamp)
        day_idx = date_number[timestamp.normalize()]
        if day_idx < MIN_TRAIN_DAYS:
            continue
        if not fitted or day_idx - last_fit_day >= REFIT_DAYS:
            cutoff = timestamp - pd.Timedelta(minutes=5 * (ENTRY_LAG_BARS + HORIZON_BARS))
            train = data[data.timestamp <= cutoff].dropna(subset=FEATURES + ["target"])
            if train.timestamp.dt.normalize().nunique() < MIN_TRAIN_DAYS:
                continue
            for name, (model, cols) in specs.items():
                model.fit(train[cols], train.target)
                fitted[name] = model
                thresholds[name] = train_spread_threshold(model, train, cols)
            last_fit_day = day_idx

        current = data[data.timestamp == timestamp].copy()
        if len(current) < 10:
            continue
        for name, (_, cols) in specs.items():
            current[name] = np.nan
            predictable = current[cols].notna().all(axis=1)
            if predictable.sum() < 10:
                continue
            current.loc[predictable, name] = fitted[name].predict(current.loc[predictable, cols])
            weights = choose_weights(current, name, thresholds[name])
            gross = sum(weights[a] * float(current.loc[current.asset == a, "realized"].iloc[0])
                        for a in weights if weights[a] != 0)
            turnover = sum(abs(weights[a] - previous[name][a]) for a in weights)
            cost = sum(family_bps(a) * abs(weights[a] - previous[name][a]) / 10000
                       for a in weights)
            decisions.append({"timestamp": timestamp, "model": name, "gross": gross,
                              "cost": cost, "net": gross - cost, "turnover": turnover,
                              "abstained": int(turnover == 0 and all(v == 0 for v in weights.values())),
                              "threshold": thresholds[name]})
            for row in current.itertuples():
                positions.append({"timestamp": timestamp, "model": name, "asset": row.asset,
                                  "family": row.family, "prediction": getattr(row, name),
                                  "target": row.target, "realized": row.realized,
                                  "weight": weights[row.asset], "vol120": row.vol120})
            previous[name] = weights

        # The strategy is intraday. Close all surviving positions before an
        # overnight/weekend/data gap, then reopen explicitly on the next day.
        next_timestamp = (pd.Timestamp(timestamps[timestamp_number + 1])
                          if timestamp_number + 1 < len(timestamps) else None)
        if next_timestamp is None or next_timestamp - timestamp > pd.Timedelta(hours=1):
            for name in specs:
                model_rows = [i for i in range(len(decisions) - 1, -1, -1)
                              if decisions[i]["model"] == name]
                if not model_rows:
                    continue
                idx = model_rows[0]
                liquidation = sum(family_bps(a) * abs(w) / 10000
                                  for a, w in previous[name].items())
                decisions[idx]["cost"] += liquidation
                decisions[idx]["net"] -= liquidation
                decisions[idx]["turnover"] += sum(abs(w) for w in previous[name].values())
                previous[name] = {a: 0.0 for a in ASSET_FAMILY}

    out = pd.DataFrame(decisions)
    return out, pd.DataFrame(positions)


def stationary_bootstrap_probability(x: np.ndarray, samples: int = 2000,
                                     block: int = 16) -> tuple[float, list[float]]:
    rng = np.random.default_rng(SEED)
    n = len(x)
    means = np.empty(samples)
    for b in range(samples):
        idx = np.empty(n, dtype=int)
        idx[0] = rng.integers(n)
        for j in range(1, n):
            idx[j] = rng.integers(n) if rng.random() < 1 / block else (idx[j-1] + 1) % n
        means[b] = x[idx].mean()
    return float((means > 0).mean()), [float(v) for v in np.quantile(means, [.025, .975])]


def summarize(decisions: pd.DataFrame, positions: pd.DataFrame) -> dict:
    summary: dict[str, object] = {"models": {}, "cost_stress": [], "segments": []}
    for name, group in decisions.groupby("model"):
        m = metrics(group.net)
        prob, ci = stationary_bootstrap_probability(group.net.to_numpy())
        rank_ic = positions[positions.model == name].groupby("timestamp").apply(
            lambda x: x.prediction.corr(x.target, method="spearman"), include_groups=False).median()
        summary["models"][name] = {**m, "bootstrap_p_positive": prob,
            "bootstrap_ci_mean": ci, "median_rank_ic": float(rank_ic),
            "mean_turnover": float(group.turnover.mean()),
            "active_fraction": float((group.turnover > 0).mean())}
        for multiple in [0, 1, 2, 4]:
            summary["cost_stress"].append({"model": name, "multiple": multiple,
                **metrics(group.gross - multiple * group.cost)})
        midpoint = group.timestamp.min() + (group.timestamp.max() - group.timestamp.min()) / 2
        for label, mask in [("first_half", group.timestamp <= midpoint),
                            ("second_half", group.timestamp > midpoint)]:
            summary["segments"].append({"model": name, "segment": label,
                                       **metrics(group.loc[mask, "net"])})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--vix", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("research038_output"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    prices = load_prices(args.prices)
    data = make_dataset(prices, args.vix)
    decisions, positions = run_walk_forward(data)
    summary = summarize(decisions, positions)
    summary["data"] = {"price_sha256": sha256(args.prices), "vix_sha256": sha256(args.vix),
                       "assets": len(prices.columns), "first": str(prices.index.min()),
                       "last": str(prices.index.max()), "exploratory_reused_2024": True}
    decisions.to_csv(args.output / "research038_decisions.csv", index=False)
    positions.to_csv(args.output / "research038_positions.csv", index=False)
    (args.output / "research038_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
