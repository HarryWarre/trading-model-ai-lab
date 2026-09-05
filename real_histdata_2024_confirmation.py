"""Locked independent 2024 confirmation on HistData M1 BID OHLC."""
from pathlib import Path
from hashlib import sha256

import numpy as np
import pandas as pd


PAIRS = ["EURUSD", "USDJPY"]
FILES = {pair: f"DAT_ASCII_{pair}_M1_2024.csv" for pair in PAIRS}
ZIP_SHA256 = {
    "EURUSD": "58f074ba6b835eb2fbeaeb6678502a23b26768eefdfa509eb75ff5296bb2904d",
    "USDJPY": "dc99fe4b3e0ae1b457f6bfccc5d36cf6f628812f704f5556aa0a74ff3e7e8c81",
}
CSV_SHA256 = {
    "EURUSD": "0f2412690abe983064f665f3273bd24553e2f4f7bfe96a606b30f65fd74b231d",
    "USDJPY": "a5f671ee6d4cf607c929e0189252b5732a5730080e056fe57f83d490bfe9efee",
}
SESSION_CLOSE_HOURS_EST = [16, 17, 18]
PRIMARY_CLOSE_HOUR_EST = 17
MIN_MINUTES = 1000
LOOKBACK = 20
VOL_WINDOW = 20
TARGET_VOL = 0.10
ANN = 252.0
COST_PIPS = 4.4
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_BLOCK = 20.0
BOOTSTRAP_SEED = 20240905


def load_m1(pair):
    filename = FILES[pair]
    if not Path(filename).exists():
        raise FileNotFoundError(f"Missing {filename}; run download_histdata_2024.py")
    actual_hash = sha256(Path(filename).read_bytes()).hexdigest()
    if actual_hash != CSV_SHA256[pair]:
        raise ValueError(
            f"Hash mismatch for {filename}: {actual_hash} != {CSV_SHA256[pair]}"
        )
    columns = ["timestamp", "Open", "High", "Low", "Close", "Volume"]
    frame = pd.read_csv(filename, sep=";", header=None, names=columns)
    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"], format="%Y%m%d %H%M%S"
    )
    duplicated = frame["timestamp"].duplicated(keep=False)
    if duplicated.any():
        groups = frame.loc[duplicated].groupby("timestamp", sort=False)
        if any(len(group.drop_duplicates()) != 1 for _, group in groups):
            raise ValueError(f"{filename} has conflicting duplicate timestamps")
        frame = frame.drop_duplicates()
    if not frame["timestamp"].is_monotonic_increasing:
        frame = frame.sort_values("timestamp")
    ohlc = frame[["Open", "High", "Low", "Close"]]
    bad = (
        (ohlc <= 0).any(axis=1)
        | (frame["Low"] > frame[["Open", "Close"]].min(axis=1))
        | (frame["High"] < frame[["Open", "Close"]].max(axis=1))
        | (frame["Low"] > frame["High"])
    )
    if bad.any():
        raise ValueError(f"{filename} has {int(bad.sum())} invalid OHLC rows")
    return frame.reset_index(drop=True), int(duplicated.sum() / 2)


def reconstruct_daily(frame, close_hour_est):
    # HistData explicitly documents fixed EST without daylight-saving changes.
    session = (frame["timestamp"] - pd.Timedelta(hours=close_hour_est)).dt.normalize()
    work = frame.assign(session=session)
    daily = work.groupby("session", sort=True).agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        minute_count=("Open", "size"),
    )
    daily = daily[daily["minute_count"] >= MIN_MINUTES]
    daily.index = daily.index.tz_localize("Etc/GMT+5").tz_convert("UTC")
    bad = (
        (daily["Low"] > daily[["Open", "Close"]].min(axis=1))
        | (daily["High"] < daily[["Open", "Close"]].max(axis=1))
        | (daily["Low"] > daily["High"])
    )
    if bad.any():
        raise AssertionError("Reconstructed OHLC invariants failed")
    return daily


def build_panel(close_hour_est):
    loaded = {pair: load_m1(pair) for pair in PAIRS}
    daily = {
        pair: reconstruct_daily(loaded[pair][0], close_hour_est) for pair in PAIRS
    }
    common = daily[PAIRS[0]].index
    for pair in PAIRS[1:]:
        common = common.intersection(daily[pair].index)
    return (
        {pair: daily[pair].loc[common].copy() for pair in PAIRS},
        {pair: loaded[pair][1] for pair in PAIRS},
    )


def run_model(daily):
    index = daily[PAIRS[0]].index
    opens = pd.concat({p: daily[p]["Open"] for p in PAIRS}, axis=1)
    closes = pd.concat({p: daily[p]["Close"] for p in PAIRS}, axis=1)
    close_returns = np.log(closes).diff()
    vol = close_returns.rolling(VOL_WINDOW).std() * np.sqrt(ANN)
    score = np.log(closes / closes.shift(LOOKBACK))
    target = (np.sign(score) * TARGET_VOL / vol.clip(lower=0.02)).clip(-1, 1)
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


def stationary_indices(n, samples, expected_block, seed):
    rng = np.random.default_rng(seed)
    indices = np.empty((samples, n), dtype=np.int32)
    restart_probability = 1.0 / expected_block
    for b in range(samples):
        current = int(rng.integers(n))
        for t in range(n):
            if t == 0 or rng.random() < restart_probability:
                current = int(rng.integers(n))
            else:
                current = (current + 1) % n
            indices[b, t] = current
    return indices


def bootstrap_positive_mean(net):
    values = net.to_numpy(float)
    indices = stationary_indices(
        len(values), BOOTSTRAP_SAMPLES, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED
    )
    means = values[indices].mean(axis=1)
    return {
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "expected_block_sessions": BOOTSTRAP_BLOCK,
        "probability_mean_positive": float((means > 0).mean()),
        "annualized_mean_ci_low": float(np.quantile(means, 0.025) * ANN),
        "annualized_mean_ci_high": float(np.quantile(means, 0.975) * ANN),
    }


def run():
    rows, attribution, coverage = [], [], []
    primary_net = None
    for close_hour in SESSION_CLOSE_HOURS_EST:
        daily, duplicate_counts = build_panel(close_hour)
        opens, weights, turnover, gross_assets, costs, net_assets = run_model(daily)
        # Exclude the deterministic warm-up when no asset has a formed signal.
        # Keeping these zero-return rows would dilute volatility and bootstrap
        # inference despite there being no investable strategy yet.
        investable = weights.abs().sum(axis=1) > 0
        portfolio = net_assets.mean(axis=1)[investable].dropna()
        gross = gross_assets.mean(axis=1).reindex(portfolio.index)
        cost = costs.mean(axis=1).reindex(portfolio.index)
        equity = np.exp(portfolio.cumsum())
        drawdown = equity / equity.cummax() - 1.0
        rows.append({
            "session_close_est": close_hour,
            "start": str(portfolio.index[0].date()),
            "end": str(portfolio.index[-1].date()),
            "observations": len(portfolio),
            "gross_total_return": np.exp(gross.sum()) - 1.0,
            "net_total_return": equity.iloc[-1] - 1.0,
            "net_annualized_return": equity.iloc[-1] ** (ANN / len(portfolio)) - 1.0,
            "net_sharpe": np.sqrt(ANN) * portfolio.mean() / portfolio.std(),
            "net_max_drawdown": drawdown.min(),
            "annualized_turnover": turnover.loc[portfolio.index].mean().mean() * ANN,
            "cost_drag_log_return": cost.sum(),
        })
        if close_hour == PRIMARY_CLOSE_HOUR_EST:
            primary_net = portfolio
        for pair in PAIRS:
            asset = net_assets[pair].reindex(portfolio.index).dropna()
            attribution.append({
                "session_close_est": close_hour,
                "asset": pair,
                "net_total_return_standalone": np.exp(asset.sum()) - 1.0,
                "net_sharpe_standalone": np.sqrt(ANN) * asset.mean() / asset.std(),
                "annualized_turnover": turnover[pair].reindex(asset.index).mean() * ANN,
            })
            sample = daily[pair]
            coverage.append({
                "session_close_est": close_hour,
                "asset": pair,
                "first_session": str(sample.index[0].date()),
                "last_session": str(sample.index[-1].date()),
                "valid_sessions": len(sample),
                "median_minutes": sample["minute_count"].median(),
                "minimum_minutes": sample["minute_count"].min(),
                "identical_duplicate_timestamps_removed": duplicate_counts[pair],
            })
    bootstrap = bootstrap_positive_mean(primary_net)
    return (
        pd.DataFrame(rows),
        pd.DataFrame(attribution),
        pd.DataFrame(coverage),
        pd.DataFrame([bootstrap]),
    )


def hypothesis_summary(results, attribution, bootstrap):
    all_portfolios_positive = bool((results["net_total_return"] > 0).all())
    median_sharpe = float(results["net_sharpe"].median())
    counts = (
        attribution.assign(positive=attribution["net_total_return_standalone"] > 0)
        .groupby("asset")["positive"]
        .sum()
    )
    each_asset_positive_twice = bool((counts >= 2).all())
    probability = float(bootstrap.iloc[0]["probability_mean_positive"])
    return pd.DataFrame([{
        "all_boundary_portfolios_positive": all_portfolios_positive,
        "median_portfolio_sharpe": median_sharpe,
        "median_sharpe_above_0_5": median_sharpe > 0.5,
        "each_asset_positive_in_at_least_two_boundaries": each_asset_positive_twice,
        "primary_bootstrap_probability_positive": probability,
        "primary_probability_at_least_0_95": probability >= 0.95,
        "preregistered_hypothesis_supported": bool(
            all_portfolios_positive
            and median_sharpe > 0.5
            and each_asset_positive_twice
            and probability >= 0.95
        ),
    }])


if __name__ == "__main__":
    results, attribution, coverage, bootstrap = run()
    summary = hypothesis_summary(results, attribution, bootstrap)
    results.to_csv("real_histdata_2024_confirmation_results.csv", index=False)
    attribution.to_csv("real_histdata_2024_confirmation_attribution.csv", index=False)
    coverage.to_csv("real_histdata_2024_confirmation_coverage.csv", index=False)
    bootstrap.to_csv("real_histdata_2024_confirmation_bootstrap.csv", index=False)
    summary.to_csv("real_histdata_2024_confirmation_summary.csv", index=False)
    print(results.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nAsset attribution")
    print(attribution.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nCoverage")
    print(coverage.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print("\nBootstrap")
    print(bootstrap.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nDecision")
    print(summary.to_string(index=False))
