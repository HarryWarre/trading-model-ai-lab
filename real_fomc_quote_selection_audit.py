"""Research 046: fail-closed audit of FOMC event-time quote availability."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from real_fomc_crossfamily_jumps import ASSETS, FAMILIES, load_data, sha256

def inspect(prices: pd.DataFrame, asset: str, t: pd.Timestamp) -> dict:
    """Exact 5m boundaries and nearest real quote within one hour."""
    b, a = t-pd.Timedelta(minutes=5), t+pd.Timedelta(minutes=5)
    valid = prices[asset].dropna()
    valid = valid[valid > 0]
    left = valid.loc[t-pd.Timedelta(minutes=60):b]
    right = valid.loc[a:t+pd.Timedelta(minutes=60)]
    return {"before_present": b in valid.index, "after_present": a in valid.index,
            "both_present": b in valid.index and a in valid.index,
            "last_before_utc": left.index.max().isoformat() if not left.empty else "",
            "first_after_utc": right.index.min().isoformat() if not right.empty else "",
            "before_gap_minutes": (b-left.index.max()).total_seconds()/60 if not left.empty else None,
            "after_gap_minutes": (right.index.min()-a).total_seconds()/60 if not right.empty else None}

def previous_controls(events: pd.DataFrame, t: pd.Timestamp) -> list[pd.Timestamp]:
    local = t.tz_convert("America/New_York")
    event_days = set(events.release_timestamp_utc.dt.tz_convert("America/New_York").dt.date)
    candidates = []
    for week in range(1, 13):
        other = local - pd.DateOffset(weeks=week)
        if other.date() not in event_days:
            candidates.append(other.tz_convert("UTC"))
            if len(candidates) == 4:
                break
    if len(candidates) != 4:
        raise ValueError("too few prior same-clock non-FOMC dates")
    return candidates

def run(panel: Path, manifest: Path, events_file: Path, prior_file: Path, output: Path) -> dict:
    prices, events, _ = load_data(panel, manifest, events_file)
    previous = json.loads((prior_file.parent/"research045_manifest.json").read_text())
    if previous["panel"]["sha256"] != sha256(panel) or previous["event_file"]["sha256"] != sha256(events_file):
        raise ValueError("Research 045 source identity differs")
    prior = pd.read_csv(prior_file)
    if prior.event_id.duplicated().any() or len(prior) != 20 or not np.isfinite(prior.difference_bps).all():
        raise ValueError("Research 045 outcome contract changed")
    family = {asset: name for name, members in FAMILIES.items() for asset in members}
    erows, crows = [], []
    for e in events.itertuples(index=False):
        times = previous_controls(events, e.release_timestamp_utc)
        for asset in ASSETS:
            key = {"event_id": e.event_id, "year": e.release_timestamp_utc.year, "asset": asset, "family": family[asset]}
            erows.append({**key, "time_utc": e.release_timestamp_utc.isoformat(),
                          **inspect(prices, asset, e.release_timestamp_utc)})
            for rank, t in enumerate(times, 1):
                crows.append({**key, "control_rank": rank, "time_utc": t.isoformat(), **inspect(prices, asset, t)})
    observed, controls = pd.DataFrame(erows), pd.DataFrame(crows)
    by_event = observed.groupby("event_id", as_index=False).agg(
        year=("year", "first"), assets_present=("both_present", "sum"))
    f = observed.loc[observed.both_present].groupby("event_id").family.nunique()
    by_event["families_present"] = by_event.event_id.map(f).fillna(0).astype(int)
    by_event["eligible"] = (by_event.assets_present >= 8) & (by_event.families_present == 3)
    # Post-result descriptive check: are controls around rejected events also absent?
    control_rates = controls.groupby("event_id").both_present.mean()
    by_event["prior_four_control_availability"] = by_event.event_id.map(control_rates)
    missing = by_event.loc[~by_event.eligible, "event_id"].tolist()
    if sorted(missing) != sorted(set(events.event_id)-set(prior.event_id)):
        raise ValueError("eligibility changed from Research 045")
    by_family = observed.groupby("family", as_index=False).agg(event_total=("both_present", "size"),
                                                                 event_present=("both_present", "sum"))
    c = controls.groupby("family").both_present.agg(["size", "sum"])
    by_family["control_total"] = by_family.family.map(c["size"])
    by_family["control_present"] = by_family.family.map(c["sum"])
    by_family["event_availability"] = by_family.event_present/by_family.event_total
    by_family["control_availability"] = by_family.control_present/by_family.control_total
    by_family["absolute_gap_pp"] = 100*(by_family.event_availability-by_family.control_availability).abs()
    years = observed.groupby("year", as_index=False).agg(total=("both_present", "size"),
                                                          present=("both_present", "sum"))
    years["availability"] = years.present/years.total
    year_family = observed.groupby(["year", "family"], as_index=False).agg(
        event_total=("both_present", "size"), event_present=("both_present", "sum"))
    cy = controls.groupby(["year", "family"]).both_present.agg(["size", "sum"]).reset_index()
    year_family = year_family.merge(cy, on=["year", "family"], validate="one_to_one")
    year_family["event_availability"] = year_family.event_present/year_family.event_total
    year_family["control_availability"] = year_family["sum"]/year_family["size"]
    d = prior.difference_bps.to_numpy()
    assert len(events)-len(d) == 4
    gates = {"at_least_23_of_24_events": bool(by_event.eligible.sum() >= 23),
             "every_family_gap_at_most_5pp": bool((by_family.absolute_gap_pp <= 5).all())}
    result = {"panel_sha256": sha256(panel), "panel_manifest_sha256": sha256(manifest),
              "events_sha256": sha256(events_file), "prior_outcomes_sha256": sha256(prior_file),
              "events": len(events), "eligible_events": int(by_event.eligible.sum()),
              "missing_event_ids": missing, "asset_event_rows": len(observed),
              "control_asset_rows": len(controls), "gates": gates,
              "broad_year_completeness_pass": all(gates.values()),
              "observed_20_mean_bps": float(d.mean()),
              "24_event_mean_if_missing_zero_bps": float(d.sum()/len(events)),
              "24_event_mean_if_missing_equal_observed_min_bps": float((d.sum()+4*d.min())/len(events)),
              "missing_each_to_make_full_mean_zero_bps": float(-d.sum()/4),
              "observed_event_min_bps": float(d.min()),
              "no_imputed_prices_or_pnl": True}
    output.mkdir(parents=True, exist_ok=True)
    for name, table in {"asset_events": observed, "paired_controls": controls,
                        "events": by_event, "families": by_family, "years": years,
                        "year_family": year_family}.items():
        table.to_csv(output/f"research046_{name}.csv", index=False)
    (output/"research046_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    return result

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for arg in ("panel", "manifest", "events", "prior-events", "output"):
        p.add_argument("--"+arg, type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(a.panel,a.manifest,a.events,a.prior_events,a.output), indent=2, sort_keys=True))
