"""Reconstruct daily FX sessions from EPSOFT H1 and test a locked TSMOM model."""
from pathlib import Path

import numpy as np
import pandas as pd


PAIRS = ["EURUSD", "USDJPY"]
FILES = {pair: f"epsoft_{pair}_h1.csv" for pair in PAIRS}
SOURCE_BLOBS = {
    "EURUSD": "bab77995a0d180a102495a53710ed954c726e878",
    "USDJPY": "2c4e813476dff231877f70fd9e32373f959c71bf",
}
SOURCE_SHA256 = {
    "EURUSD": "ef14fa999b9c9db7ffe00074393817f4834d64381051e589ed903b599c6938c1",
    "USDJPY": "06de9cea0cdd79d84b05ec4f7063f5cc18783feed19c4610011e7ade7a723cc9",
}
SESSION_RULES = ["new_york_17", "new_york_00", "utc_00"]
LOOKBACK = 20
VOL_WINDOW = 20
TARGET_VOL = 0.10
COST_PIPS = 4.4
MIN_ACTIVE_HOURS = 20
HOLDOUT_START = pd.Timestamp("2021-01-01", tz="UTC")


def load_h1(pair):
    filename = FILES[pair]
    if not Path(filename).exists():
        raise FileNotFoundError(
            f"Missing {filename}; fetch EPSOFT Git blob {SOURCE_BLOBS[pair]}"
        )
    frame = pd.read_csv(filename)
    required = {"Local time", "Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{filename} missing H1 OHLCV columns")

    extracted = frame["Local time"].str.extract(
        r"^(?P<local>.+) GMT(?P<offset>[+-]\d{4})$"
    )
    if extracted.isna().any().any():
        raise ValueError(f"{filename} has timestamps without explicit GMT offset")
    frame["local_timestamp"] = pd.to_datetime(
        extracted["local"], format="%d.%m.%Y %H:%M:%S.%f"
    )
    # Parsing the explicit offset before normalizing to UTC preserves both sides
    # of the New York DST transition.
    aware_strings = extracted["local"] + " " + extracted["offset"]
    frame["utc_timestamp"] = pd.to_datetime(
        aware_strings, format="%d.%m.%Y %H:%M:%S.%f %z", utc=True
    )
    if frame["utc_timestamp"].duplicated().any():
        raise ValueError(f"{filename} has duplicate absolute timestamps")
    if not frame["utc_timestamp"].is_monotonic_increasing:
        frame = frame.sort_values("utc_timestamp")

    ohlc = frame[["Open", "High", "Low", "Close"]]
    bad = (
        (ohlc <= 0).any(axis=1)
        | (frame["Low"] > frame[["Open", "Close"]].min(axis=1))
        | (frame["High"] < frame[["Open", "Close"]].max(axis=1))
        | (frame["Low"] > frame["High"])
        | (frame["Volume"] < 0)
    )
    if bad.any():
        raise ValueError(f"{filename} has {int(bad.sum())} invalid OHLCV rows")
    return frame.reset_index(drop=True)


def session_labels(frame, rule):
    if rule == "new_york_17":
        labels = (frame["local_timestamp"] - pd.Timedelta(hours=17)).dt.normalize()
    elif rule == "new_york_00":
        labels = frame["local_timestamp"].dt.normalize()
    elif rule == "utc_00":
        labels = frame["utc_timestamp"].dt.tz_convert(None).dt.normalize()
    else:
        raise ValueError(f"Unknown session rule: {rule}")
    return labels.dt.tz_localize("UTC")


def reconstruct_daily(frame, rule):
    active = (frame["Volume"] > 0) & (frame["High"] > frame["Low"])
    work = frame.loc[active].copy()
    work["session"] = session_labels(work, rule)
    grouped = work.groupby("session", sort=True)
    daily = grouped.agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        Volume=("Volume", "sum"),
        active_hours=("Open", "size"),
    )
    daily = daily[daily["active_hours"] >= MIN_ACTIVE_HOURS]
    bad = (
        (daily["Low"] > daily[["Open", "Close"]].min(axis=1))
        | (daily["High"] < daily[["Open", "Close"]].max(axis=1))
        | (daily["Low"] > daily["High"])
    )
    if bad.any():
        raise AssertionError("Reconstructed session violates OHLC invariants")
    return daily


def reconstructed_panel(rule):
    daily = {pair: reconstruct_daily(load_h1(pair), rule) for pair in PAIRS}
    common = daily[PAIRS[0]].index
    for pair in PAIRS[1:]:
        common = common.intersection(daily[pair].index)
    return {pair: daily[pair].loc[common].copy() for pair in PAIRS}


def annualization(index):
    """Observed full-session frequency, estimated only before the holdout."""
    pre = pd.Series(1, index=index[(index.year >= 2017) & (index.year <= 2020)])
    if pre.empty:
        raise ValueError("Need pre-holdout sessions to estimate annualization")
    return float(pre.groupby(pre.index.year).sum().median())


def run_model(daily, ann):
    index = daily[PAIRS[0]].index
    opens = pd.concat({pair: daily[pair]["Open"] for pair in PAIRS}, axis=1)
    closes = pd.concat({pair: daily[pair]["Close"] for pair in PAIRS}, axis=1)
    close_returns = np.log(closes).diff()
    vol = close_returns.rolling(VOL_WINDOW).std() * np.sqrt(ann)
    score = np.log(closes / closes.shift(LOOKBACK))
    target = (np.sign(score) * (TARGET_VOL / vol.clip(lower=0.02))).clip(-1, 1)
    # Close-t information can only establish the position at open t+1.
    weights = target.shift(1).fillna(0.0)
    turnover = weights.diff().abs().fillna(weights.abs())
    forward = np.log(opens.shift(-1) / opens)
    pip_size = pd.DataFrame(
        {p: (0.01 if p.endswith("JPY") else 0.0001) for p in PAIRS},
        index=index,
    )
    gross_assets = weights * forward
    costs = turnover * COST_PIPS * pip_size / opens
    net_assets = gross_assets - costs
    return opens, weights, turnover, gross_assets, costs, net_assets


def run():
    rows, attribution, coverage = [], [], []
    for rule in SESSION_RULES:
        daily = reconstructed_panel(rule)
        ann = annualization(daily[PAIRS[0]].index)
        opens, weights, turnover, gross_assets, costs, net_assets = run_model(daily, ann)
        is_oos = opens.index >= HOLDOUT_START
        portfolio = net_assets.mean(axis=1)[is_oos].dropna()
        gross = gross_assets.mean(axis=1)[is_oos].reindex(portfolio.index)
        cost = costs.mean(axis=1)[is_oos].reindex(portfolio.index)
        equity = np.exp(portfolio.cumsum())
        drawdown = equity / equity.cummax() - 1.0
        rows.append({
            "session_rule": rule,
            "oos_start": str(portfolio.index[0].date()),
            "oos_end": str(portfolio.index[-1].date()),
            "observations": len(portfolio),
            "annualization": ann,
            "gross_total_return": np.exp(gross.sum()) - 1.0,
            "net_total_return": equity.iloc[-1] - 1.0,
            "net_annualized_return": equity.iloc[-1] ** (ann / len(portfolio)) - 1.0,
            "net_sharpe": np.sqrt(ann) * portfolio.mean() / portfolio.std(),
            "net_max_drawdown": drawdown.min(),
            "annualized_turnover": turnover[is_oos].mean().mean() * ann,
            "cost_drag_log_return": cost.sum(),
        })
        for pair in PAIRS:
            asset = net_assets[pair][is_oos].dropna()
            attribution.append({
                "session_rule": rule,
                "asset": pair,
                "net_total_return_standalone": np.exp(asset.sum()) - 1.0,
                "net_sharpe_standalone": np.sqrt(ann) * asset.mean() / asset.std(),
                "annualized_turnover": turnover[pair][is_oos].mean() * ann,
            })
            sample = daily[pair]
            holdout_sample = sample.loc[sample.index >= HOLDOUT_START]
            gaps = holdout_sample.index.to_series().diff().dt.total_seconds().div(86400)
            coverage.append({
                "session_rule": rule,
                "asset": pair,
                "first_session": str(sample.index[0].date()),
                "last_session": str(sample.index[-1].date()),
                "valid_sessions": len(sample),
                "median_active_hours": sample["active_hours"].median(),
                "minimum_active_hours": sample["active_hours"].min(),
                "holdout_valid_sessions": len(holdout_sample),
                "holdout_max_calendar_gap_days": gaps.max(),
                "holdout_gaps_over_7_days": int((gaps > 7).sum()),
            })
    return pd.DataFrame(rows), pd.DataFrame(attribution), pd.DataFrame(coverage)


def hypothesis_summary(results, attribution):
    portfolio_pass = bool((results["net_total_return"] > 0).all())
    median_sharpe_pass = bool(results["net_sharpe"].median() > 0.5)
    positive_counts = (
        attribution.assign(positive=attribution["net_total_return_standalone"] > 0)
        .groupby("asset")["positive"]
        .sum()
    )
    asset_pass = bool((positive_counts >= 2).all())
    return pd.DataFrame([{
        "all_session_portfolios_positive": portfolio_pass,
        "median_portfolio_sharpe": results["net_sharpe"].median(),
        "median_sharpe_above_0_5": median_sharpe_pass,
        "each_asset_positive_in_at_least_two_rules": asset_pass,
        "preregistered_hypothesis_supported": (
            portfolio_pass and median_sharpe_pass and asset_pass
        ),
    }])


if __name__ == "__main__":
    result, attribution, coverage = run()
    summary = hypothesis_summary(result, attribution)
    result.to_csv("real_epsoft_h1_session_reconstruction_results.csv", index=False)
    attribution.to_csv(
        "real_epsoft_h1_session_reconstruction_attribution.csv", index=False
    )
    coverage.to_csv("real_epsoft_h1_session_reconstruction_coverage.csv", index=False)
    summary.to_csv("real_epsoft_h1_session_reconstruction_summary.csv", index=False)
    print(result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nAsset attribution")
    print(attribution.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nCoverage")
    print(coverage.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print("\nDecision")
    print(summary.to_string(index=False))
