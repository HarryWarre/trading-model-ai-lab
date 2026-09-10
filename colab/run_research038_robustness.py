"""Robustness and attribution for Research 038 saved forecasts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research038_residual_intraday import (
    ASSET_FAMILY, choose_weights, family_bps, metrics, stationary_bootstrap_probability,
)


def replay(positions: pd.DataFrame, decisions: pd.DataFrame, model: str,
           excluded: set[str] | None = None) -> pd.Series:
    excluded = excluded or set()
    subset = positions[(positions.model == model) & ~positions.asset.isin(excluded)]
    thresholds = decisions[decisions.model == model].set_index("timestamp").threshold
    previous = {a: 0.0 for a in ASSET_FAMILY}
    values = {}
    grouped = list(subset.groupby("timestamp", sort=True))
    for number, (timestamp, frame) in enumerate(grouped):
        weights = choose_weights(frame, "prediction", float(thresholds.loc[timestamp]))
        gross = sum(weights[a] * float(frame.loc[frame.asset == a, "realized"].iloc[0])
                    for a in weights if weights[a] != 0 and (frame.asset == a).any())
        cost = sum(family_bps(a) * abs(weights[a] - previous[a]) / 10000 for a in weights)
        values[timestamp] = gross - cost
        previous = weights
        next_timestamp = grouped[number + 1][0] if number + 1 < len(grouped) else None
        if next_timestamp is None or next_timestamp - timestamp > pd.Timedelta(hours=1):
            values[timestamp] -= sum(family_bps(a) * abs(w) / 10000
                                     for a, w in previous.items())
            previous = {a: 0.0 for a in ASSET_FAMILY}
    return pd.Series(values, name="net").sort_index()


def family_attribution(positions: pd.DataFrame, model: str) -> pd.DataFrame:
    subset = positions[positions.model == model].sort_values(["timestamp", "asset"])
    previous = {a: 0.0 for a in ASSET_FAMILY}
    rows = []
    grouped = list(subset.groupby("timestamp", sort=True))
    for number, (timestamp, frame) in enumerate(grouped):
        current = frame.set_index("asset").weight.to_dict()
        for family in sorted(set(ASSET_FAMILY.values())):
            members = [a for a, f in ASSET_FAMILY.items() if f == family]
            gross = sum(float(frame.loc[frame.asset == a, "realized"].iloc[0]) * current.get(a, 0)
                        for a in members if (frame.asset == a).any())
            cost = sum(family_bps(a) * abs(current.get(a, 0) - previous[a]) / 10000
                       for a in members)
            next_timestamp = grouped[number + 1][0] if number + 1 < len(grouped) else None
            if next_timestamp is None or next_timestamp - timestamp > pd.Timedelta(hours=1):
                cost += sum(family_bps(a) * abs(current.get(a, 0)) / 10000 for a in members)
            rows.append({"timestamp": timestamp, "family": family, "net": gross - cost})
        previous.update(current)
        if next_timestamp is None or next_timestamp - timestamp > pd.Timedelta(hours=1):
            previous = {a: 0.0 for a in ASSET_FAMILY}
    out = pd.DataFrame(rows)
    return out.groupby("family").net.apply(lambda x: pd.Series(metrics(x))).unstack()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("research038_output"))
    args = parser.parse_args()
    decisions = pd.read_csv(args.input / "research038_decisions.csv", parse_dates=["timestamp"])
    positions = pd.read_csv(args.input / "research038_positions.csv", parse_dates=["timestamp"])

    nonlinear = decisions[decisions.model == "nonlinear"].set_index("timestamp").net
    segment_rows = []
    d = decisions.copy()
    d["month"] = d.timestamp.dt.to_period("M").astype(str)
    d["hour"] = d.timestamp.dt.hour
    for model, group in d.groupby("model"):
        for key, sub in group.groupby("month"):
            segment_rows.append({"model": model, "kind": "month", "segment": key, **metrics(sub.net)})
        for key, sub in group.groupby("hour"):
            segment_rows.append({"model": model, "kind": "hour", "segment": str(key), **metrics(sub.net)})
    pd.DataFrame(segment_rows).to_csv(args.input / "research038_segments.csv", index=False)

    paired = []
    for baseline in ["ridge", "price_only"]:
        base = decisions[decisions.model == baseline].set_index("timestamp").net
        diff = nonlinear.align(base, join="inner")[0] - nonlinear.align(base, join="inner")[1]
        p, ci = stationary_bootstrap_probability(diff.to_numpy())
        paired.append({"comparison": f"nonlinear_minus_{baseline}", "mean_annualized": diff.mean()*252*16,
                       "p_difference_positive": p, "ci_mean_low": ci[0], "ci_mean_high": ci[1]})
    pd.DataFrame(paired).to_csv(args.input / "research038_paired.csv", index=False)

    loo = []
    for asset in ASSET_FAMILY:
        series = replay(positions, decisions, "nonlinear", {asset})
        loo.append({"excluded_asset": asset, **metrics(series)})
    pd.DataFrame(loo).to_csv(args.input / "research038_asset_loo.csv", index=False)
    family_attribution(positions, "nonlinear").reset_index().to_csv(
        args.input / "research038_family_attribution.csv", index=False)

    changes = positions[positions.model == "nonlinear"].pivot(
        index="timestamp", columns="asset", values="weight").fillna(0).diff().abs()
    capacity = {
        "mean_names_changed_per_decision": float((changes > 1e-12).sum(axis=1).mean()),
        "median_names_changed_per_decision": float((changes > 1e-12).sum(axis=1).median()),
        "mean_one_way_turnover": float(decisions.loc[
            decisions.model == "nonlinear", "turnover"].mean()),
        "decisions_per_active_day": float(decisions[decisions.model == "nonlinear"].groupby(
            decisions[decisions.model == "nonlinear"].timestamp.dt.date).size().mean()),
        "live_capacity_quantifiable": False,
        "reason": "BID closes contain no ask, executable depth, broker volume, ADV or slippage curve",
    }
    (args.input / "research038_capacity.json").write_text(json.dumps(capacity, indent=2))
    print(json.dumps({"paired": paired, "capacity": capacity}, indent=2))


if __name__ == "__main__":
    main()
