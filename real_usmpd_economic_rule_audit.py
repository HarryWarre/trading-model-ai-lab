"""Research 049: post-selection audit of the frozen Research 048 economic rule.

Preregistered in GitHub issue #66 before these robustness outputs were inspected.
This script consumes only hash-locked Research 048 artifacts; it never rebuilds
or changes the underlying event returns.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = {
    "research048_economic_trades.csv",
    "research048_price_only_trades.csv",
    "research048_long_trades.csv",
    "research048_economic_events_0x.csv",
    "research048_economic_events_1x.csv",
    "research048_economic_events_2x.csv",
    "research048_economic_events_4x.csv",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_inputs(source: Path) -> dict:
    manifest_path = source / "research048_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("research") != 48:
        raise ValueError("not a Research 048 manifest")
    artifacts = manifest.get("artifacts", {})
    missing = REQUIRED - set(artifacts)
    if missing:
        raise ValueError(f"manifest lacks required artifacts: {sorted(missing)}")
    for name in sorted(REQUIRED):
        path = source / name
        meta = artifacts[name]
        if not path.is_file():
            raise ValueError(f"missing artifact: {name}")
        if sha256(path) != meta.get("sha256") or path.stat().st_size != meta.get("size_bytes"):
            raise ValueError(f"hash/size mismatch: {name}")
    return manifest


def event_table(trades: pd.DataFrame, events: list[str], multiplier: float) -> pd.DataFrame:
    needed = {"event_id", "asset", "family", "year", "invvol", "signal", "press_return", "cost_1x"}
    if needed - set(trades):
        raise ValueError(f"trade schema mismatch: {sorted(needed - set(trades))}")
    z = trades.copy()
    if z.empty:
        grouped = pd.DataFrame(columns=["event_id", "gross", "cost_1x", "net", "round_trips"])
    else:
        z["weight"] = z.groupby("event_id").invvol.transform(lambda v: v / v.sum())
        z["gross"] = z.weight * z.signal * z.press_return
        z["cost"] = z.weight * z.cost_1x
        z["net"] = z.gross - multiplier * z.cost
        grouped = z.groupby("event_id", as_index=False).agg(
            gross=("gross", "sum"), cost_1x=("cost", "sum"),
            net=("net", "sum"), round_trips=("asset", "count"),
        )
    return pd.DataFrame({"event_id": events}).merge(grouped, on="event_id", how="left").fillna(0)


def exact_sign_flip_p(differences: np.ndarray) -> float:
    """One-sided exact randomization P(mean >= observed mean), including ties."""
    values = np.asarray(differences, dtype=float)
    observed = float(values.mean())
    totals = []
    for signs in itertools.product((-1.0, 1.0), repeat=len(values)):
        totals.append(float(np.mean(values * np.asarray(signs))))
    return float(np.mean(np.asarray(totals) >= observed - 1e-15))


def cumulative_return(values: pd.Series | np.ndarray) -> float:
    return float(np.expm1(np.asarray(values, dtype=float).sum()))


def run(source: Path, output: Path) -> dict:
    source_manifest = validate_inputs(source)
    economic = pd.read_csv(source / "research048_economic_trades.csv")
    price = pd.read_csv(source / "research048_price_only_trades.csv")
    long = pd.read_csv(source / "research048_long_trades.csv")
    frozen = pd.read_csv(source / "research048_economic_events_1x.csv")
    events = frozen.event_id.astype(str).tolist()
    if len(events) != 12 or len(set(events)) != 12:
        raise ValueError("expected exactly twelve unique frozen evaluation events")

    output.mkdir(parents=True, exist_ok=True)
    cost_rows, event_tables = [], {}
    for kind, trades in (("economic", economic), ("price_only", price), ("long", long)):
        for multiplier in (0, 1, 2, 4):
            table = event_table(trades, events, multiplier)
            event_tables[(kind, multiplier)] = table
            table.to_csv(output / f"research049_{kind}_events_{multiplier}x.csv", index=False)
            cost_rows.append({
                "model": kind, "cost_multiplier": multiplier,
                "net_return": cumulative_return(table.net),
                "gross_return": cumulative_return(table.gross),
                "round_trips": int(table.round_trips.sum()),
                "positive_events": int((table.net > 0).sum()),
            })
    costs = pd.DataFrame(cost_rows)
    costs.to_csv(output / "research049_costs.csv", index=False)

    econ_1x = event_tables[("economic", 1)].copy()
    price_1x = event_tables[("price_only", 1)].copy()
    econ_1x["price_only_net"] = price_1x.net
    econ_1x["difference"] = econ_1x.net - price_1x.net
    event_year = pd.concat([economic[["event_id", "year"]], price[["event_id", "year"]]])
    event_year = event_year.drop_duplicates("event_id")
    econ_1x = econ_1x.merge(event_year, on="event_id", how="left", validate="one_to_one")
    if econ_1x.year.isna().any():
        raise ValueError("event year unavailable")
    econ_1x.to_csv(output / "research049_event_detail.csv", index=False)

    loo_event = []
    for excluded in events:
        q = econ_1x[econ_1x.event_id != excluded]
        loo_event.append({"excluded_event": excluded, "net_return": cumulative_return(q.net)})
    loo_event = pd.DataFrame(loo_event)
    loo_event.to_csv(output / "research049_event_leave_one_out.csv", index=False)

    def exclusion_table(column: str) -> pd.DataFrame:
        rows = []
        for excluded in sorted(economic[column].unique()):
            q = economic[economic[column] != excluded]
            e = event_table(q, events, 1)
            rows.append({f"excluded_{column}": excluded, "net_return": cumulative_return(e.net)})
        return pd.DataFrame(rows)

    family_loo = exclusion_table("family")
    asset_loo = exclusion_table("asset")
    family_loo.to_csv(output / "research049_family_leave_one_out.csv", index=False)
    asset_loo.to_csv(output / "research049_asset_leave_one_out.csv", index=False)

    years = econ_1x.groupby("year", as_index=False).net.sum()
    years["net_return"] = np.expm1(years.net)
    years.to_csv(output / "research049_years.csv", index=False)

    positive = econ_1x.net.clip(lower=0)
    concentration = float(positive.max() / positive.sum()) if positive.sum() > 0 else 1.0
    sign_p = exact_sign_flip_p(econ_1x.difference.to_numpy())
    active = economic.copy()
    hit = float((active.signal * active.press_return > 0).mean()) if len(active) else None
    cost_1x = costs[(costs.model == "economic") & (costs.cost_multiplier == 1)].iloc[0]
    cost_2x = costs[(costs.model == "economic") & (costs.cost_multiplier == 2)].iloc[0]
    gates = {
        "economic_net_1x_positive": bool(cost_1x.net_return > 0),
        "economic_net_2x_positive": bool(cost_2x.net_return > 0),
        "all_event_leave_one_out_positive": bool((loo_event.net_return > 0).all()),
        "largest_positive_event_share_at_most_60pct": bool(concentration <= .60),
        "exact_sign_flip_p_at_most_5pct": bool(sign_p <= .05),
        "all_years_positive": bool(len(years) == 2 and (years.net_return > 0).all()),
        "all_family_leave_one_out_positive": bool((family_loo.net_return > 0).all()),
    }
    result = {
        "research": 49,
        "source_research048_manifest_sha256": sha256(source / "research048_manifest.json"),
        "source_input_hashes": source_manifest.get("inputs", {}),
        "evaluation_events": len(events),
        "economic_net_1x": float(cost_1x.net_return),
        "economic_net_2x": float(cost_2x.net_return),
        "economic_round_trips": int(cost_1x.round_trips),
        "economic_trade_legs": int(2 * cost_1x.round_trips),
        "economic_direction_hit_rate": hit,
        "largest_positive_event_share": concentration,
        "exact_paired_sign_flip_p_economic_beats_price_only": sign_p,
        "minimum_event_leave_one_out_return": float(loo_event.net_return.min()),
        "minimum_family_leave_one_out_return": float(family_loo.net_return.min()),
        "minimum_asset_leave_one_out_return": float(asset_loo.net_return.min()),
        "gates": gates,
        "passed_all_gates": bool(all(gates.values())),
        "decision": "research_only_same_inspected_sample",
        "untouched_2026_confirmation_available": False,
    }
    (output / "research049_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    artifacts = {}
    for path in sorted(output.glob("research049_*")):
        if path.name != "research049_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    manifest = {"research": 49, "source": result["source_research048_manifest_sha256"], "artifacts": artifacts}
    (output / "research049_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), indent=2, sort_keys=True))
