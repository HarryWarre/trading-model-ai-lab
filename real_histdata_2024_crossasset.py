"""Cross-asset extension of the locked HistData 2024 TSMOM confirmation."""
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from real_histdata_2024_confirmation import (
    ANN,
    BOOTSTRAP_BLOCK,
    BOOTSTRAP_SAMPLES,
    BOOTSTRAP_SEED,
    LOOKBACK,
    MIN_MINUTES,
    TARGET_VOL,
    VOL_WINDOW,
    stationary_indices,
)


CONTROL_ASSETS = ["EURUSD", "USDJPY"]
REGISTERED_FRESH_ASSETS = ["GBPUSD", "AUDUSD", "XAUUSD", "WTIUSD", "SPXUSD"]
AVAILABLE_FRESH_ASSETS = ["GBPUSD", "AUDUSD", "XAUUSD", "SPXUSD"]
AVAILABLE_ASSETS = CONTROL_ASSETS + AVAILABLE_FRESH_ASSETS
BLOCKED_ASSETS = {
    "WTIUSD": "HistData 2024 ASCII M1 page returned an empty download token"
}
FILES = {a: f"DAT_ASCII_{a}_M1_2024.csv" for a in AVAILABLE_ASSETS}
CSV_SHA256 = {
    "EURUSD": "0f2412690abe983064f665f3273bd24553e2f4f7bfe96a606b30f65fd74b231d",
    "USDJPY": "a5f671ee6d4cf607c929e0189252b5732a5730080e056fe57f83d490bfe9efee",
    "GBPUSD": "0de617c38f1804541da10b4134e185efe71e7b2a7c9e7581b073644089b9439b",
    "AUDUSD": "f2b5fe69de2e48691d5e2e6b3f38329dcee57dc34c81a5d64a3e4dad4a8cb62d",
    "XAUUSD": "03dec44d8965c88eeba54e8ef5d13e31f28deca6f01fa727f9db55641bee5480",
    "SPXUSD": "8f5414848aadd4e503db73400f319352ae82dbd3f00928fa9277b7c0d8027a4b",
}
SESSION_CLOSE_EST = 17
ASSET_COSTS = {
    "EURUSD": ("pips", 4.4),
    "USDJPY": ("pips", 4.4),
    "GBPUSD": ("pips", 4.4),
    "AUDUSD": ("pips", 4.4),
    "XAUUSD": ("bps", 10.0),
    "SPXUSD": ("bps", 10.0),
}


def load_m1(asset):
    path = Path(FILES[asset])
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run download_histdata_crossasset_2024.py")
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != CSV_SHA256[asset]:
        raise ValueError(f"Hash mismatch for {asset}: {actual} != {CSV_SHA256[asset]}")
    columns = ["timestamp", "Open", "High", "Low", "Close", "Volume"]
    frame = pd.read_csv(path, sep=";", header=None, names=columns)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], format="%Y%m%d %H%M%S")
    duplicate_rows = frame["timestamp"].duplicated(keep=False)
    removed = 0
    if duplicate_rows.any():
        groups = frame.loc[duplicate_rows].groupby("timestamp", sort=False)
        if any(len(group.drop_duplicates()) != 1 for _, group in groups):
            raise ValueError(f"{asset} has conflicting duplicate timestamps")
        removed = int(duplicate_rows.sum() / 2)
        frame = frame.drop_duplicates()
    frame = frame.sort_values("timestamp")
    bad = (
        (frame[["Open", "High", "Low", "Close"]] <= 0).any(axis=1)
        | (frame["Low"] > frame[["Open", "Close"]].min(axis=1))
        | (frame["High"] < frame[["Open", "Close"]].max(axis=1))
        | (frame["Low"] > frame["High"])
    )
    if bad.any():
        raise ValueError(f"{asset} has {int(bad.sum())} invalid OHLC rows")
    return frame.reset_index(drop=True), removed


def reconstruct_daily(frame):
    session = (frame["timestamp"] - pd.Timedelta(hours=SESSION_CLOSE_EST)).dt.normalize()
    daily = frame.assign(session=session).groupby("session", sort=True).agg(
        Open=("Open", "first"), High=("High", "max"), Low=("Low", "min"),
        Close=("Close", "last"), minute_count=("Open", "size"),
    )
    daily = daily[daily["minute_count"] >= MIN_MINUTES]
    daily.index = daily.index.tz_localize("Etc/GMT+5").tz_convert("UTC")
    return daily


def build_panel():
    loaded = {a: load_m1(a) for a in AVAILABLE_ASSETS}
    daily = {a: reconstruct_daily(loaded[a][0]) for a in AVAILABLE_ASSETS}
    return (
        daily,
        {a: loaded[a][1] for a in AVAILABLE_ASSETS},
    )


def asset_cost(turnover, opens, asset):
    unit, amount = ASSET_COSTS[asset]
    if unit == "bps":
        return turnover * amount * 1e-4
    pip = 0.01 if asset.endswith("JPY") else 0.0001
    return turnover * amount * pip / opens


def model_asset(daily, asset):
    opens = daily["Open"]
    closes = daily["Close"]
    returns = np.log(closes).diff()
    vol = returns.rolling(VOL_WINDOW).std() * np.sqrt(ANN)
    score = np.log(closes / closes.shift(LOOKBACK))
    target = (np.sign(score) * TARGET_VOL / vol.clip(lower=0.02)).clip(-1, 1)
    weights = target.shift(1).fillna(0.0)
    turnover = weights.diff().abs().fillna(weights.abs())
    forward = np.log(opens.shift(-1) / opens)
    gross = weights * forward
    costs = asset_cost(turnover, opens, asset)
    net = gross - costs
    investable = (weights.abs() > 0) & net.notna()
    return opens, weights, turnover, gross, costs, net, investable


def model_assets(daily):
    modeled = {a: model_asset(daily[a], a) for a in AVAILABLE_ASSETS}
    common = None
    for asset in AVAILABLE_ASSETS:
        idx = modeled[asset][5].index[modeled[asset][6]]
        common = idx if common is None else common.intersection(idx)

    def panel(position):
        return pd.concat(
            {a: modeled[a][position].loc[common] for a in AVAILABLE_ASSETS}, axis=1
        )

    return panel(0), panel(1), panel(2), panel(3), panel(4), panel(5)


def metrics(series):
    series = series.dropna()
    equity = np.exp(series.cumsum())
    drawdown = equity / equity.cummax() - 1.0
    return {
        "start": str(series.index[0].date()),
        "end": str(series.index[-1].date()),
        "observations": len(series),
        "net_total_return": equity.iloc[-1] - 1.0,
        "net_annualized_return": equity.iloc[-1] ** (ANN / len(series)) - 1.0,
        "net_sharpe": np.sqrt(ANN) * series.mean() / series.std(),
        "net_max_drawdown": drawdown.min(),
    }


def bootstrap_positive_mean(series):
    values = series.dropna().to_numpy(float)
    indices = stationary_indices(
        len(values), BOOTSTRAP_SAMPLES, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED + 21
    )
    means = values[indices].mean(axis=1)
    return pd.DataFrame([{
        "portfolio": "fresh_available_4",
        "samples": BOOTSTRAP_SAMPLES,
        "expected_block_sessions": BOOTSTRAP_BLOCK,
        "probability_mean_positive": (means > 0).mean(),
        "annualized_mean_ci_low": np.quantile(means, 0.025) * ANN,
        "annualized_mean_ci_high": np.quantile(means, 0.975) * ANN,
    }])


def run():
    daily, duplicates = build_panel()
    opens, weights, turnover, gross, costs, net = model_assets(daily)

    groups = {
        "fresh_available_4": AVAILABLE_FRESH_ASSETS,
        "all_available_6": AVAILABLE_ASSETS,
    }
    portfolio_rows = []
    portfolios = {}
    for name, assets in groups.items():
        series = net[assets].mean(axis=1)
        portfolios[name] = series
        row = {"portfolio": name, "asset_count": len(assets), **metrics(series)}
        row.update({
            "gross_total_return": np.exp(gross[assets].mean(axis=1).sum()) - 1.0,
            "annualized_turnover": turnover[assets].mean().mean() * ANN,
            "cost_drag_log_return": costs[assets].mean(axis=1).sum(),
        })
        portfolio_rows.append(row)

    attribution = []
    for asset in AVAILABLE_ASSETS:
        row = {"asset": asset, **metrics(net[asset])}
        row["annualized_turnover"] = turnover[asset].mean() * ANN
        attribution.append(row)

    leave_one_out = []
    for excluded in AVAILABLE_FRESH_ASSETS:
        included = [a for a in AVAILABLE_FRESH_ASSETS if a != excluded]
        leave_one_out.append({
            "excluded_asset": excluded,
            "included_assets": ",".join(included),
            **metrics(net[included].mean(axis=1)),
        })

    coverage = []
    for asset in AVAILABLE_ASSETS:
        sample = daily[asset]
        coverage.append({
            "asset": asset,
            "status": "available",
            "valid_asset_sessions": len(sample),
            "median_minutes": sample["minute_count"].median(),
            "minimum_minutes": sample["minute_count"].min(),
            "identical_duplicate_timestamps_removed": duplicates[asset],
            "blocker": "",
        })
    coverage.append({
        "asset": "WTIUSD", "status": "blocked", "valid_common_sessions": 0,
        "median_minutes": np.nan, "minimum_minutes": np.nan,
        "identical_duplicate_timestamps_removed": 0,
        "blocker": BLOCKED_ASSETS["WTIUSD"],
    })
    bootstrap = bootstrap_positive_mean(portfolios["fresh_available_4"])
    return (
        pd.DataFrame(portfolio_rows), pd.DataFrame(attribution),
        pd.DataFrame(leave_one_out), pd.DataFrame(coverage), bootstrap,
    )


def hypothesis_summary(portfolios, attribution, leave_one_out, bootstrap, coverage):
    fresh = portfolios.set_index("portfolio").loc["fresh_available_4"]
    all_available = portfolios.set_index("portfolio").loc["all_available_6"]
    fresh_attr = attribution[attribution.asset.isin(AVAILABLE_FRESH_ASSETS)]
    registered_complete = bool(
        set(REGISTERED_FRESH_ASSETS).issubset(set(coverage.query("status == 'available'").asset))
    )
    descriptive_conditions = bool(
        fresh.net_total_return > 0
        and fresh.net_sharpe > 0.5
        and (fresh_attr.net_total_return > 0).sum() >= 3
        and all_available.net_total_return > 0
        and (leave_one_out.net_total_return > 0).sum() >= 4
        and bootstrap.iloc[0].probability_mean_positive >= 0.95
    )
    return pd.DataFrame([{
        "registered_fresh_assets_available": int(coverage.query("status == 'available' and asset in @REGISTERED_FRESH_ASSETS").shape[0]),
        "registered_fresh_assets_required": len(REGISTERED_FRESH_ASSETS),
        "preregistered_test_evaluable": registered_complete,
        "fresh_available_net_return": fresh.net_total_return,
        "fresh_available_sharpe": fresh.net_sharpe,
        "fresh_available_positive_assets": int((fresh_attr.net_total_return > 0).sum()),
        "fresh_available_leave_one_out_positive": int((leave_one_out.net_total_return > 0).sum()),
        "fresh_available_bootstrap_probability_positive": bootstrap.iloc[0].probability_mean_positive,
        "descriptive_available_conditions_met": descriptive_conditions,
        "preregistered_hypothesis_supported": registered_complete and descriptive_conditions,
    }])


if __name__ == "__main__":
    portfolios, attribution, loo, coverage, bootstrap = run()
    summary = hypothesis_summary(portfolios, attribution, loo, bootstrap, coverage)
    portfolios.to_csv("real_histdata_2024_crossasset_portfolios.csv", index=False)
    attribution.to_csv("real_histdata_2024_crossasset_attribution.csv", index=False)
    loo.to_csv("real_histdata_2024_crossasset_leave_one_out.csv", index=False)
    coverage.to_csv("real_histdata_2024_crossasset_coverage.csv", index=False)
    bootstrap.to_csv("real_histdata_2024_crossasset_bootstrap.csv", index=False)
    summary.to_csv("real_histdata_2024_crossasset_summary.csv", index=False)
    print(portfolios.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nAttribution")
    print(attribution.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nLeave one out")
    print(loo.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nBootstrap")
    print(bootstrap.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nDecision")
    print(summary.to_string(index=False))
