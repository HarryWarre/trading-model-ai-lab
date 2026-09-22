"""Research 050: identification audit for USMPD policy/information shocks.

Preregistered in GitHub issue #67 before classification outcomes were inspected.
This is a mechanism/data audit, not a trading backtest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


RATE_COLUMNS = [f"FF{i}" for i in range(1, 7)] + [f"ED{i}" for i in range(1, 5)]
EXPECTED_WORKBOOK_SHA = "f02bfcbf80cf597548d4fccb5a80b30cb1f4373a7d50e26fd1def097d43df1aa"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def exact_binomial_greater(k: int, n: int) -> float:
    if not (0 <= k <= n) or n <= 0:
        raise ValueError("invalid binomial counts")
    return float(sum(math.comb(n, j) for j in range(k, n + 1)) / (2 ** n))


def classify(product: float) -> str:
    if not np.isfinite(product) or product == 0:
        return "unclassified"
    return "conventional" if product < 0 else "information"


def regime(year: int) -> str:
    if year <= 2007:
        return "1994-2007"
    if year <= 2019:
        return "2008-2019"
    return "2020-2026"


def load_statements(workbook: Path, manifest_path: Path) -> pd.DataFrame:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = sha256(workbook)
    if digest != EXPECTED_WORKBOOK_SHA or digest != manifest.get("sha256"):
        raise ValueError("USMPD workbook hash mismatch")
    if workbook.stat().st_size != manifest.get("size_bytes"):
        raise ValueError("USMPD workbook size mismatch")
    if manifest.get("source_updated") != "2026-09-17":
        raise ValueError("unexpected USMPD vintage")

    x = pd.read_excel(workbook, sheet_name="Statements")
    required = {"Date", "date_time", "Unscheduled", "SPFUT", *RATE_COLUMNS}
    if required - set(x):
        raise ValueError(f"statement schema mismatch: {sorted(required - set(x))}")
    x["Date"] = pd.to_datetime(x.Date, errors="raise").dt.normalize()
    x["date_time"] = pd.to_datetime(x.date_time, errors="raise")
    if x.Date.duplicated().any() or not x.Date.is_monotonic_increasing:
        raise ValueError("statement dates duplicated or unordered")
    if x.Date.min() > pd.Timestamp("1994-02-04") or x.Date.max() != pd.Timestamp("2026-09-16"):
        raise ValueError("unexpected statement coverage")
    for c in RATE_COLUMNS + ["SPFUT", "Unscheduled"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["scheduled"] = x.Unscheduled.fillna(0).eq(0)
    x["rate_contracts"] = x[RATE_COLUMNS].notna().sum(axis=1)
    x["rate_surprise"] = x[RATE_COLUMNS].mean(axis=1, skipna=True)
    x.loc[x.rate_contracts < 8, "rate_surprise"] = np.nan
    x["sp_future"] = x.SPFUT / 100.0
    x["valid"] = np.isfinite(x.rate_surprise) & np.isfinite(x.sp_future)
    x["product"] = x.rate_surprise * x.sp_future
    x["classification"] = x["product"].map(classify)
    x.loc[~x.valid, "classification"] = "unclassified"
    x["year"] = x.Date.dt.year
    x["regime"] = x.year.map(regime)
    return x[["Date", "date_time", "year", "regime", "scheduled", "rate_contracts",
              "rate_surprise", "sp_future", "product", "valid", "classification"]]


def summarize_group(x: pd.DataFrame, name: str) -> dict:
    valid = x[x.valid].copy()
    classified = valid[valid.classification != "unclassified"]
    conventional = int((classified.classification == "conventional").sum())
    information = int((classified.classification == "information").sum())
    n = conventional + information
    return {
        "group": name,
        "rows": int(len(x)),
        "valid": int(x.valid.sum()),
        "coverage": float(x.valid.mean()) if len(x) else None,
        "classified": n,
        "conventional": conventional,
        "information": information,
        "conventional_share": float(conventional / n) if n else None,
        "median_product": float(classified["product"].median()) if n else None,
    }


def run(workbook: Path, input_manifest: Path, output: Path) -> dict:
    x = load_statements(workbook, input_manifest)
    scheduled = x[x.scheduled].copy()
    output.mkdir(parents=True, exist_ok=True)
    x.to_csv(output / "research050_event_detail.csv", index=False)

    regimes = pd.DataFrame([
        summarize_group(group, name) for name, group in scheduled.groupby("regime", sort=False)
    ])
    regimes.to_csv(output / "research050_regimes.csv", index=False)
    years = pd.DataFrame([
        summarize_group(group, str(year)) for year, group in scheduled.groupby("year", sort=True)
    ])
    years.to_csv(output / "research050_years.csv", index=False)
    current = scheduled[scheduled.year == 2026].copy()
    current.to_csv(output / "research050_2026_events.csv", index=False)

    overall = summarize_group(scheduled, "scheduled_all")
    valid_classified = scheduled[(scheduled.valid) & (scheduled.classification != "unclassified")]
    k = int((valid_classified.classification == "conventional").sum())
    n = int(len(valid_classified))
    binomial_p = exact_binomial_greater(k, n)

    loo = []
    for year in sorted(scheduled.year.unique()):
        q = valid_classified[valid_classified.year != year]
        conventional = int((q.classification == "conventional").sum())
        information = int((q.classification == "information").sum())
        loo.append({
            "excluded_year": int(year), "conventional": conventional,
            "information": information, "conventional_majority": conventional > information,
        })
    loo_frame = pd.DataFrame(loo)
    loo_frame.to_csv(output / "research050_year_leave_one_out.csv", index=False)

    current_valid = current[current.valid & (current.classification != "unclassified")]
    current_conventional = int((current_valid.classification == "conventional").sum())
    gates = {
        "scheduled_coverage_at_least_90pct": bool(overall["coverage"] >= .90),
        "overall_conventional_majority_exact_p_at_most_5pct": bool(k > n / 2 and binomial_p <= .05),
        "every_regime_conventional_share_at_least_35pct": bool((regimes.conventional_share >= .35).all()),
        "every_regime_median_product_negative": bool((regimes.median_product < 0).all()),
        "2026_at_least_2_conventional_and_4_valid": bool(current_conventional >= 2 and len(current_valid) >= 4),
        "all_leave_one_year_out_conventional_majority": bool(loo_frame.conventional_majority.all()),
    }
    result = {
        "research": 50,
        "workbook_sha256": sha256(workbook),
        "input_manifest_sha256": sha256(input_manifest),
        "source_updated": "2026-09-17",
        "statement_rows": int(len(x)),
        "scheduled_rows": int(len(scheduled)),
        "unscheduled_rows": int((~x.scheduled).sum()),
        "scheduled_valid_rows": int(scheduled.valid.sum()),
        "scheduled_coverage": overall["coverage"],
        "scheduled_conventional": k,
        "scheduled_information": int(n - k),
        "scheduled_conventional_share": float(k / n),
        "exact_binomial_p_conventional_share_gt_50pct": binomial_p,
        "events_2026": int(len(current)),
        "valid_events_2026": int(len(current_valid)),
        "conventional_events_2026": current_conventional,
        "information_events_2026": int((current_valid.classification == "information").sum()),
        "gates": gates,
        "passed_all_gates": bool(all(gates.values())),
        "decision": "mechanism_identified_requires_cfd_holdout" if all(gates.values())
                    else "mechanism_audit_failed_one_or_more_gates",
        "trading_pnl_computed": False,
    }
    (output / "research050_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    artifacts = {}
    for path in sorted(output.glob("research050_*")):
        if path.name != "research050_manifest.json":
            artifacts[path.name] = {"sha256": sha256(path), "size_bytes": path.stat().st_size}
    manifest = {
        "research": 50,
        "inputs": {"workbook": sha256(workbook), "manifest": sha256(input_manifest)},
        "artifacts": artifacts,
    }
    (output / "research050_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.workbook, args.input_manifest, args.output), indent=2, sort_keys=True))
