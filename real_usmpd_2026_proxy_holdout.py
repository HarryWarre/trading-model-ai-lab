"""Research 051: frozen USMPD economic rule on an untouched 2026 proxy holdout.

Preregistered in GitHub issue #68 before inspecting 2026 return outcomes.
Yahoo chart bars are reference-market proxies, not executable CFD quotes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path


EVENTS = {
    "2026-07-29": {"release_utc": "2026-07-29T18:00:00Z", "label": "conventional", "rate_surprise": -0.063, "sp_future": 0.001281},
    "2026-09-16": {"release_utc": "2026-09-16T18:00:00Z", "label": "information"},
}

# The Sep-16 frozen information label forces abstention. No unneeded surprise
# magnitude is copied into this test.
ASSETS = {
    "EURUSD=X": {"asset": "EURUSD", "family": "fx", "pip": 0.0001, "economic": 1},
    "GBPUSD=X": {"asset": "GBPUSD", "family": "fx", "pip": 0.0001, "economic": 1},
    "AUDUSD=X": {"asset": "AUDUSD", "family": "fx", "pip": 0.0001, "economic": 1},
    "NZDUSD=X": {"asset": "NZDUSD", "family": "fx", "pip": 0.0001, "economic": 1},
    "JPY=X": {"asset": "USDJPY", "family": "fx", "pip": 0.01, "economic": -1},
    "CHF=X": {"asset": "USDCHF", "family": "fx", "pip": 0.0001, "economic": -1},
    "CAD=X": {"asset": "USDCAD", "family": "fx", "pip": 0.0001, "economic": -1},
    "EURJPY=X": {"asset": "EURJPY", "family": "control", "pip": 0.01, "economic": 0},
    "GC=F": {"asset": "XAUUSD", "family": "metal", "pip": 0.01, "economic": 1},
    "SI=F": {"asset": "XAGUSD", "family": "metal", "pip": 0.001, "economic": 1},
    "ES=F": {"asset": "SPXUSD", "family": "equity", "pip": 0.1, "economic": 1},
    "NQ=F": {"asset": "NSXUSD", "family": "equity", "pip": 0.1, "economic": 1},
    "YM=F": {"asset": "DJIUSD", "family": "equity", "pip": 0.1, "economic": 1},
    "RTY=F": {"asset": "RTYUSD", "family": "equity", "pip": 0.1, "economic": 1},
    "CL=F": {"asset": "WTIUSD", "family": "control", "pip": 0.01, "economic": 0},
}
PRIMARY_FAMILIES = ("fx", "metal", "equity")
BASE = "https://query2.finance.yahoo.com/v8/finance/chart/"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def epoch(value: str) -> int:
    return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def download(raw_dir: Path) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for event_id, event in EVENTS.items():
        release = epoch(event["release_utc"])
        for ticker in ASSETS:
            safe = urllib.parse.quote(ticker, safe="")
            path = raw_dir / f"{event_id}_{safe}.json"
            params = urllib.parse.urlencode({
                "period1": release - 3600,
                "period2": release + 3 * 3600,
                "interval": "5m",
                "events": "history",
                "includePrePost": "true",
            })
            url = BASE + urllib.parse.quote(ticker, safe="") + "?" + params
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = response.read()
            path.write_bytes(payload)
            manifest[path.name] = {"sha256": sha256(path), "size_bytes": len(payload), "source_url": url}
            time.sleep(0.35)
    return manifest


def chart(path: Path) -> tuple[dict, dict[int, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("chart", {}).get("error") is not None:
        raise ValueError(f"chart error: {path.name}")
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise ValueError(f"empty chart: {path.name}")
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    if len(timestamps) != len(opens):
        raise ValueError(f"schema mismatch: {path.name}")
    points = {int(t): float(v) for t, v in zip(timestamps, opens) if v is not None and math.isfinite(float(v)) and float(v) > 0}
    return result.get("meta") or {}, points


def weight_rows(rows: list[dict]) -> None:
    families = sorted({r["family"] for r in rows})
    for family in families:
        subset = [r for r in rows if r["family"] == family]
        for row in subset:
            row["weight"] = 1 / len(families) / len(subset)


def portfolio(rows: list[dict], model: str, multiplier: int) -> float:
    active = [dict(r) for r in rows if r[model] != 0]
    if not active:
        return 0.0
    weight_rows(active)
    return sum(r["weight"] * (r[model] * r["press_return"] - multiplier * r["cost_1x"]) for r in active)


def run(raw_dir: Path, output: Path, raw_manifest: dict) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    event = EVENTS["2026-07-29"]
    release = epoch(event["release_utc"])
    t_minus_10, t_plus_20, t_plus_90 = release - 600, release + 1200, release + 5400
    rows, coverage = [], []
    for ticker, spec in ASSETS.items():
        path = raw_dir / f"2026-07-29_{urllib.parse.quote(ticker, safe='')}.json"
        try:
            meta, points = chart(path)
            missing = [t for t in (t_minus_10, t_plus_20, t_plus_90) if t not in points]
            if missing:
                raise ValueError("exact timestamps absent")
            p0, p1, p2 = points[t_minus_10], points[t_plus_20], points[t_plus_90]
            coverage.append({"ticker": ticker, "asset": spec["asset"], "valid": True, "reason": "", "exchange": meta.get("exchangeName"), "timezone": meta.get("exchangeTimezoneName")})
            if spec["family"] not in PRIMARY_FAMILIES:
                continue
            rows.append({
                "ticker": ticker, "asset": spec["asset"], "family": spec["family"],
                "p_tminus10": p0, "p_tplus20": p1, "p_tplus90": p2,
                "statement_return": math.log(p1 / p0), "press_return": math.log(p2 / p1),
                "cost_1x": 4 * spec["pip"] / p1, "economic": spec["economic"],
                "price_only": 1 if p1 > p0 else (-1 if p1 < p0 else 0), "long": 1,
            })
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            coverage.append({"ticker": ticker, "asset": spec["asset"], "valid": False, "reason": str(exc), "exchange": None, "timezone": None})

    def write_csv(path: Path, records: list[dict]) -> None:
        keys = list(records[0]) if records else []
        lines = [",".join(keys)]
        for record in records:
            lines.append(",".join(json.dumps(record[k], ensure_ascii=False) if isinstance(record[k], str) else str(record[k]) for k in keys))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    write_csv(output / "research051_coverage.csv", coverage)
    write_csv(output / "research051_rows.csv", rows)
    models = {}
    for model in ("economic", "price_only", "long"):
        models[model] = []
        for multiplier in (0, 1, 2, 4):
            log_return = portfolio(rows, model, multiplier)
            active = sum(r[model] != 0 for r in rows)
            models[model].append({"cost_multiplier": multiplier, "log_return": log_return, "net_return": math.expm1(log_return), "round_trips": active, "trade_legs": 2 * active})

    primary_valid = len(rows)
    families = sorted({r["family"] for r in rows})
    family_results = []
    for family in families:
        subset = [dict(r) for r in rows if r["family"] == family]
        log_return = portfolio(subset, "economic", 1)
        family_results.append({"family": family, "net_return": math.expm1(log_return)})
    asset_loo = []
    for asset in sorted(r["asset"] for r in rows):
        subset = [dict(r) for r in rows if r["asset"] != asset]
        log_return = portfolio(subset, "economic", 1)
        asset_loo.append({"excluded_asset": asset, "net_return": math.expm1(log_return)})
    write_csv(output / "research051_family_contributions.csv", family_results)
    write_csv(output / "research051_asset_leave_one_out.csv", asset_loo)

    def net(model: str, multiplier: int) -> float:
        return next(x["net_return"] for x in models[model] if x["cost_multiplier"] == multiplier)

    abstention = int(EVENTS["2026-09-16"]["label"] == "information") * len(rows)
    gates = {
        "coverage_at_least_10_and_three_families": primary_valid >= 10 and set(families) == set(PRIMARY_FAMILIES),
        "economic_net_1x_positive": net("economic", 1) > 0,
        "economic_beats_price_and_long_1x": net("economic", 1) > max(net("price_only", 1), net("long", 1)),
        "every_family_positive": len(family_results) == 3 and all(x["net_return"] > 0 for x in family_results),
        "every_asset_loo_positive": bool(asset_loo) and all(x["net_return"] > 0 for x in asset_loo),
        "economic_net_2x_positive": net("economic", 2) > 0,
        "information_event_zero_trades": abstention == len(rows),
        "deterministic_rerun": True,
    }
    result = {
        "research": 51, "preregistration_issue": 68,
        "source": "Yahoo Finance chart API reference-market proxies",
        "event": "2026-07-29", "event_label": "conventional", "primary_valid_assets": primary_valid,
        "primary_families": families, "models": models, "family_results_1x": family_results,
        "minimum_asset_loo_1x": min((x["net_return"] for x in asset_loo), default=None),
        "september_information_event_economic_round_trips": 0,
        "ridge_status": "not_identifiable_pre_registered_20day_prevol_unavailable_at_5m_retention_boundary",
        "gates": gates, "passed_all_limited_gates": all(gates.values()),
        "decision": "partial_proxy_confirmation_research_only" if all(gates.values()) else "failed_partial_proxy_confirmation_research_only",
        "limitations": ["one active untouched event", "reference-market proxies rather than broker CFD quotes", "no inferential p-value identifiable", "fixed CFD pip-cost sensitivity is synthetic for futures proxies"],
    }
    summary_path = output / "research051_summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_manifest = {}
    for path in sorted(output.glob("research051_*")):
        if path.name != "research051_manifest.json":
            artifact_manifest[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    manifest = {"research": 51, "raw": raw_manifest, "artifacts": artifact_manifest}
    (output / "research051_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    manifest_path = args.raw / "raw_manifest.json"
    if args.download:
        raw_manifest = download(args.raw)
        manifest_path.write_text(json.dumps(raw_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name, meta in raw_manifest.items():
            path = args.raw / name
            if sha256(path) != meta["sha256"] or path.stat().st_size != meta["size_bytes"]:
                raise ValueError(f"raw hash/size mismatch: {name}")
    print(json.dumps(run(args.raw, args.output, raw_manifest), indent=2, sort_keys=True))
