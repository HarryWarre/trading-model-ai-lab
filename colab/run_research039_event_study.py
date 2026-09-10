"""Research 039: point-in-time scheduled-news event-study runner.

Run only after news_event_schema.py has accepted the raw event file.  The runner
uses 5-minute prices, waits 15 minutes after a release, trains only on earlier
non-overlapping events, and holds for one hour.  It does not create events,
consensus values, or timestamps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from news_event_schema import load_and_validate_events

ASSET_FAMILY = {
    "AUDUSD": "fx", "EURJPY": "fx", "EURUSD": "fx", "GBPUSD": "fx",
    "NZDUSD": "fx", "USDCAD": "fx", "USDCHF": "fx", "USDJPY": "fx",
    "GRXEUR": "equity", "NSXUSD": "equity", "SPXUSD": "equity",
    "UKXGBP": "equity", "BCOUSD": "commodity", "XAGUSD": "commodity",
    "XAUUSD": "commodity",
}
DECISION_DELAY = pd.Timedelta(minutes=15)
HORIZON = pd.Timedelta(minutes=60)
PURGE = DECISION_DELAY + HORIZON
MIN_TRAIN_EVENTS = 30
COST_BPS = {"fx": 4.0, "equity": 4.0, "commodity": 4.0}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_prices(path: Path) -> pd.DataFrame:
    prices = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
    prices.index = pd.to_datetime(prices.index, utc=True)
    prices = prices.apply(pd.to_numeric, errors="coerce").sort_index()
    missing = set(ASSET_FAMILY) - set(prices.columns)
    if missing:
        raise ValueError(f"Missing frozen assets: {sorted(missing)}")
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("Prices need a unique, increasing UTC timestamp index.")
    return prices.loc[:, list(ASSET_FAMILY)]


def past_standardized_surprise(events: pd.DataFrame) -> pd.Series:
    """Standardize an event only from strictly earlier events in its category."""
    result = pd.Series(np.nan, index=events.index, dtype=float)
    for category, group in events.groupby("category", sort=False):
        prior = []
        for idx, surprise in group["raw_surprise"].items():
            if len(prior) >= 10:
                sd = float(np.std(prior, ddof=1))
                if sd > 0:
                    result.loc[idx] = (surprise - float(np.mean(prior))) / sd
            prior.append(float(surprise))
    return result


def build_event_panel(prices: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    logp = np.log(prices)
    rows = []
    events = events.sort_values("timestamp_utc").copy()
    events["surprise_z"] = past_standardized_surprise(events)
    for event in events.itertuples():
        decision = event.timestamp_utc + DECISION_DELAY
        end = decision + HORIZON
        pre_start = event.timestamp_utc - pd.Timedelta(minutes=60)
        # Exact 5-minute points prevent an accidental next-observation fill.
        required = [pre_start, event.timestamp_utc, decision, end]
        if any(t not in prices.index for t in required):
            continue
        for asset, family in ASSET_FAMILY.items():
            r_pre = float(logp.at[event.timestamp_utc, asset] - logp.at[pre_start, asset])
            r_initial = float(logp.at[decision, asset] - logp.at[event.timestamp_utc, asset])
            realized = float(logp.at[end, asset] - logp.at[decision, asset])
            window = logp.loc[pre_start:event.timestamp_utc, asset].diff().dropna()
            vol = float(window.std())
            if not np.isfinite(vol) or vol <= 0:
                continue
            rows.append({
                "event_id": event.event_id,
                "event_time": event.timestamp_utc,
                "decision_time": decision,
                "end_time": end,
                "category": event.category,
                "asset": asset,
                "family": family,
                "surprise_z": event.surprise_z,
                "pre_return": r_pre / vol,
                "initial_return": r_initial / vol,
                "pre_vol": vol,
                "realized": realized,
            })
    panel = pd.DataFrame(rows)
    if panel.empty:
        raise ValueError("No events align exactly with the 5-minute panel.")
    return panel.sort_values(["event_time", "asset"]).reset_index(drop=True)


def features(frame: pd.DataFrame, use_surprise: bool) -> pd.DataFrame:
    numeric = ["pre_return", "initial_return", "pre_vol"]
    if use_surprise:
        numeric = ["surprise_z"] + numeric
    x = frame[numeric].copy()
    category = pd.get_dummies(frame["category"], prefix="category", dtype=float)
    family = pd.get_dummies(frame["family"], prefix="family", dtype=float)
    return pd.concat([x, category, family], axis=1).astype(float)


def choose_weights(frame: pd.DataFrame, prediction: pd.Series) -> dict[str, float]:
    weights = {a: 0.0 for a in ASSET_FAMILY}
    current = frame.assign(prediction=prediction).dropna(
        subset=["prediction", "pre_vol", "realized"]
    )
    # One long and one short per family prevents a hidden one-way market bet.
    long_names, short_names = [], []
    for family, group in current.groupby("family"):
        if len(group) < 2:
            continue
        ordered = group.sort_values("prediction")
        short_names.append(ordered.iloc[0].asset)
        long_names.append(ordered.iloc[-1].asset)
    if len(long_names) != 3 or len(short_names) != 3:
        return weights
    vol = current.set_index("asset")["pre_vol"]
    for names, sign in ((long_names, 1.0), (short_names, -1.0)):
        inverse = 1 / vol[names].clip(lower=1e-9)
        allocation = .5 * inverse / inverse.sum()
        for asset, value in allocation.items():
            weights[asset] = sign * float(value)
    return weights


def walk_forward(panel: pd.DataFrame) -> pd.DataFrame:
    event_times = panel[["event_id", "event_time"]].drop_duplicates().sort_values("event_time")
    decisions = []
    for event in event_times.itertuples():
        current = panel[panel.event_id == event.event_id].copy()
        train = panel[
            (panel.end_time <= event.event_time - PURGE)
            & panel.surprise_z.notna()
        ].copy()
        if train.event_id.nunique() < MIN_TRAIN_EVENTS:
            continue
        models = {}
        for name, use_surprise in (("news_linear", True), ("price_only", False)):
            x_train = features(train, use_surprise)
            x_current = features(current, use_surprise).reindex(columns=x_train.columns, fill_value=0)
            valid_train = x_train.notna().all(axis=1) & train.realized.notna()
            model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            model.fit(x_train.loc[valid_train], train.loc[valid_train, "realized"] / train.loc[valid_train, "pre_vol"])
            models[name] = pd.Series(
                model.predict(x_current.fillna(0)), index=current.index, dtype=float
            )
        for name, prediction in models.items():
            weights = choose_weights(current, prediction)
            gross = sum(
                weights[a] * float(current.loc[current.asset == a, "realized"].iloc[0])
                for a in ASSET_FAMILY
            )
            # Each event position is opened and liquidated inside the one-hour
            # window. Turnover and cost therefore include both legs.
            turnover = 2 * sum(abs(weights[a]) for a in ASSET_FAMILY)
            cost = sum(
                COST_BPS[ASSET_FAMILY[a]] / 10000 * 2 * abs(weights[a])
                for a in ASSET_FAMILY
            )
            decisions.append({
                "event_id": event.event_id, "event_time": event.event_time,
                "model": name, "gross": gross, "cost_1x": cost,
                "net_1x": gross - cost, "turnover": turnover,
                "traded": int(any(weights.values())),
            })
        # Each position is fully liquidated after its fixed event window.
    if not decisions:
        raise ValueError("Insufficient non-overlapping prior events for walk-forward fit.")
    return pd.DataFrame(decisions)


def summary(decisions: pd.DataFrame) -> dict:
    out = {"models": {}}
    for name, group in decisions.groupby("model"):
        x = group.net_1x
        equity = np.exp(x.cumsum())
        out["models"][name] = {
            "events": int(len(group)),
            "net_return_1x": float(equity.iloc[-1] - 1),
            "gross_return": float(np.exp(group.gross.cumsum()).iloc[-1] - 1),
            "mean_turnover": float(group.turnover.mean()),
            "traded_fraction": float(group.traded.mean()),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    prices = load_prices(args.prices)
    events = load_and_validate_events(args.events, args.start, args.end)
    panel = build_event_panel(prices, events)
    decisions = walk_forward(panel)
    result = summary(decisions)
    result["data"] = {
        "price_sha256": sha256(args.prices),
        "event_sha256": sha256(args.events),
        "assets": len(prices.columns),
        "events_validated": int(events.event_id.nunique()),
        "exploratory_reused_2024": True,
    }
    panel.to_csv(args.output / "research039_event_panel.csv", index=False)
    decisions.to_csv(args.output / "research039_decisions.csv", index=False)
    (args.output / "research039_summary.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
