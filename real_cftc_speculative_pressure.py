"""Preregistered 2024 CFTC speculative-pressure CFD-proxy holdout."""
from hashlib import sha256
from io import StringIO
from pathlib import Path
import csv
import zipfile

import numpy as np
import pandas as pd

from real_histdata_2024_crossasset import (
    AVAILABLE_ASSETS, ASSET_COSTS, CSV_SHA256, FILES, load_m1, reconstruct_daily,
)
from real_histdata_2024_confirmation import stationary_indices


TFF_CODES = {
    "EURUSD": "099741", "USDJPY": "097741", "GBPUSD": "096742",
    "AUDUSD": "232741", "SPXUSD": "13874A",
}
DISAGG_CODES = {"XAUUSD": "088691"}
ASSETS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "XAUUSD", "SPXUSD"]
YEARS = range(2010, 2025)
MIN_HISTORY = 52
TOP_BOTTOM = 2
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_BLOCK = 10
BOOTSTRAP_SEED = 22035
ANN = 252


def _archive_frame(kind, year):
    path = Path("cftc_history") / f"{kind}_{year}.zip"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run download_cftc_positioning.py")
    manifest = pd.read_csv("cftc_positioning_manifest.csv")
    expected = manifest.query("kind == @kind and year == @year").iloc[0]
    payload = path.read_bytes()
    if sha256(payload).hexdigest() != expected.sha256 or len(payload) != expected.bytes:
        raise ValueError(f"CFTC archive hash/size mismatch: {path}")
    with zipfile.ZipFile(path) as zf:
        raw = zf.read(zf.namelist()[0]).decode("latin1")
    return pd.read_csv(StringIO(raw), low_memory=False)


def load_positioning():
    tff = pd.concat([_archive_frame("tff", y) for y in YEARS], ignore_index=True)
    disagg = pd.concat([_archive_frame("disagg", y) for y in YEARS], ignore_index=True)
    rows = []
    for asset, code in TFF_CODES.items():
        x = tff[tff.CFTC_Contract_Market_Code.astype(str).str.strip() == code].copy()
        x["pressure"] = (
            pd.to_numeric(x.Lev_Money_Positions_Long_All, errors="coerce")
            - pd.to_numeric(x.Lev_Money_Positions_Short_All, errors="coerce")
        ) / pd.to_numeric(x.Open_Interest_All, errors="coerce")
        x["asset"] = asset
        rows.append(x[["Report_Date_as_YYYY-MM-DD", "asset", "pressure"]])
    for asset, code in DISAGG_CODES.items():
        x = disagg[disagg.CFTC_Contract_Market_Code.astype(str).str.strip() == code].copy()
        x["pressure"] = (
            pd.to_numeric(x.M_Money_Positions_Long_All, errors="coerce")
            - pd.to_numeric(x.M_Money_Positions_Short_All, errors="coerce")
        ) / pd.to_numeric(x.Open_Interest_All, errors="coerce")
        x["asset"] = asset
        rows.append(x[["Report_Date_as_YYYY-MM-DD", "asset", "pressure"]])
    frame = pd.concat(rows, ignore_index=True)
    frame["report_date"] = pd.to_datetime(frame["Report_Date_as_YYYY-MM-DD"])
    frame = frame.drop(columns="Report_Date_as_YYYY-MM-DD").dropna()
    frame = frame.drop_duplicates(["report_date", "asset"], keep="last")
    frame.loc[frame.asset == "USDJPY", "pressure"] *= -1.0
    frame = frame.sort_values(["asset", "report_date"])
    grouped = frame.groupby("asset").pressure
    mean = grouped.transform(lambda s: s.expanding(MIN_HISTORY).mean())
    std = grouped.transform(lambda s: s.expanding(MIN_HISTORY).std())
    frame["zscore"] = (frame.pressure - mean) / std
    frame["release_date"] = frame.report_date + pd.Timedelta(days=3)
    return frame


def load_daily_panel():
    daily = {}
    for asset in ASSETS:
        frame, _ = load_m1(asset)
        daily[asset] = reconstruct_daily(frame)
    common = daily[ASSETS[0]].index
    for asset in ASSETS[1:]:
        common = common.intersection(daily[asset].index)
    opens = pd.concat({a: daily[a].Open.loc[common] for a in ASSETS}, axis=1)
    return opens.sort_index()


def target_from_scores(scores, assets=ASSETS):
    valid = scores.reindex(assets).dropna()
    if len(valid) < 2 * TOP_BOTTOM:
        return pd.Series(0.0, index=assets)
    target = pd.Series(0.0, index=assets)
    target.loc[valid.nsmallest(TOP_BOTTOM).index] = -1.0 / (2 * TOP_BOTTOM)
    target.loc[valid.nlargest(TOP_BOTTOM).index] = 1.0 / (2 * TOP_BOTTOM)
    return target


def targets_at_sessions(positioning, opens, assets=ASSETS):
    pivot = positioning.pivot(index="release_date", columns="asset", values="zscore")
    current = pd.Series(0.0, index=assets)
    rows = []
    events = {}
    for release, scores in pivot.iterrows():
        candidates = opens.index[opens.index > release.tz_localize("UTC")]
        if len(candidates) and candidates[0].year == 2024:
            events[candidates[0]] = target_from_scores(scores, assets)
    for dt in opens.index:
        if dt in events:
            current = events[dt]
        rows.append(current.copy())
    return pd.DataFrame(rows, index=opens.index)


def transaction_cost(turnover, opens, asset, multiplier=1.0):
    unit, amount = ASSET_COSTS[asset]
    if unit == "bps":
        return turnover * amount * 1e-4 * multiplier
    pip = 0.01 if asset.endswith("JPY") else 0.0001
    return turnover * amount * pip / opens * multiplier


def simulate(positioning, opens, assets=ASSETS, cost_multiplier=1.0):
    target = targets_at_sessions(positioning, opens, assets)
    forward = np.log(opens.shift(-1) / opens)
    turnover = target.diff().abs().fillna(target.abs())
    gross = (target * forward).sum(axis=1)
    costs = sum(
        transaction_cost(turnover[a], opens[a], a, cost_multiplier) for a in assets
    )
    active = (target.abs().sum(axis=1) > 0) & gross.notna()
    net = (gross - costs).loc[active]
    return net, gross.loc[net.index], costs.loc[net.index], turnover, target


def metrics(series):
    equity = np.exp(series.cumsum())
    dd = equity / equity.cummax() - 1
    return {
        "observations": len(series), "start": str(series.index[0].date()),
        "end": str(series.index[-1].date()),
        "net_total_return": equity.iloc[-1] - 1,
        "net_sharpe": np.sqrt(ANN) * series.mean() / series.std(),
        "max_drawdown": dd.min(),
    }


def bootstrap(series):
    values = series.to_numpy(float)
    idx = stationary_indices(len(values), BOOTSTRAP_SAMPLES, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED)
    means = values[idx].mean(axis=1)
    return {
        "samples": BOOTSTRAP_SAMPLES,
        "expected_block_sessions": BOOTSTRAP_BLOCK,
        "probability_mean_positive": float((means > 0).mean()),
        "annualized_mean_ci_low": float(np.quantile(means, .025) * ANN),
        "annualized_mean_ci_high": float(np.quantile(means, .975) * ANN),
    }


def run():
    positioning = load_positioning()
    opens = load_daily_panel()
    net, gross, costs, turnover, targets = simulate(positioning, opens)
    main = pd.DataFrame([{**metrics(net),
        "gross_total_return": np.exp(gross.sum()) - 1,
        "cost_drag_log_return": costs.sum(),
        "annualized_turnover": turnover.sum(axis=1).mean() * ANN,
    }])
    loo = []
    for excluded in ASSETS:
        included = [a for a in ASSETS if a != excluded]
        n, _, _, _, _ = simulate(positioning, opens[included], included)
        loo.append({"excluded_asset": excluded, **metrics(n)})
    attribution = []
    forward = np.log(opens.shift(-1) / opens)
    turns = targets.diff().abs().fillna(targets.abs())
    for asset in ASSETS:
        s = (targets[asset] * forward[asset] - transaction_cost(turns[asset], opens[asset], asset)).dropna()
        attribution.append({"asset": asset, **metrics(s)})
    boot = pd.DataFrame([bootstrap(net)])
    cost_stress = []
    for multiplier in [0.0, 0.5, 1.0, 2.0]:
        stressed, _, _, _, _ = simulate(
            positioning, opens, cost_multiplier=multiplier
        )
        cost_stress.append({"cost_multiplier_vs_locked": multiplier, **metrics(stressed)})
    market_state = np.log(opens.SPXUSD / opens.SPXUSD.shift(20)).shift(1)
    regimes = []
    for name, mask in {"spx_trailing_up": market_state >= 0,
                       "spx_trailing_down": market_state < 0}.items():
        sample = net[mask.reindex(net.index).fillna(False)]
        regimes.append({"regime": name, **metrics(sample)})
    positive_loo = int((pd.DataFrame(loo).net_total_return > 0).sum())
    summary = pd.DataFrame([{
        "positive_net_return": bool(main.iloc[0].net_total_return > 0),
        "positive_leave_one_out": positive_loo,
        "bootstrap_probability_positive": boot.iloc[0].probability_mean_positive,
        "preregistered_hypothesis_supported": bool(
            main.iloc[0].net_total_return > 0 and positive_loo >= 4
            and boot.iloc[0].probability_mean_positive >= .95
        ),
    }])
    return (main, pd.DataFrame(attribution), pd.DataFrame(loo), boot, summary,
            pd.DataFrame(cost_stress), pd.DataFrame(regimes))


if __name__ == "__main__":
    outputs = run()
    names = ["results", "attribution", "leave_one_out", "bootstrap", "summary",
             "cost_stress", "regimes"]
    for name, frame in zip(names, outputs):
        frame.to_csv(f"real_cftc_speculative_pressure_{name}.csv", index=False)
        print(name, frame.to_string(index=False))
