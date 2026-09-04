"""Locked 2021-2023 test of an equal-weight partial-adjustment ensemble."""
from pathlib import Path

import numpy as np
import pandas as pd

PAIRS = ["EURUSD", "USDJPY"]
FILES = {pair: f"epsoft_{pair}_d1.csv" for pair in PAIRS}
SOURCE_BLOBS = {
    "EURUSD": "7a0cb1bd65e0419c51539c78da840583a266ec7f",
    "USDJPY": "bee114de8fb8363b570fbf799933862afe834a7e",
}
PARTIAL_SPEEDS = [0.50, 0.25, 0.10]
LOOKBACK = 20
VOL_WINDOW = 20
TARGET_VOL = 0.10
HOLDOUT_START = pd.Timestamp("2021-01-01", tz="UTC")
ANN = 365.0
COST_PIPS = [2.2, 4.4]


def load_prices():
    opens, closes = {}, {}
    for pair, filename in FILES.items():
        if not Path(filename).exists():
            raise FileNotFoundError(
                f"Missing {filename}; fetch the documented EPSOFT Git blob "
                f"{SOURCE_BLOBS[pair]}"
            )
        frame = pd.read_csv(filename)
        required = {"Local time", "Open", "High", "Low", "Close"}
        if not required.issubset(frame.columns):
            raise ValueError(f"{filename} missing required OHLC columns")
        frame["timestamp"] = pd.to_datetime(
            frame["Local time"].str.slice(0, 10), dayfirst=True, utc=True
        )
        if frame.timestamp.duplicated().any():
            raise ValueError(f"{filename} has duplicate dates")
        bad = ((frame.Low > frame[["Open", "Close"]].min(axis=1))
               | (frame.High < frame[["Open", "Close"]].max(axis=1))
               | (frame.Low > frame.High)
               | (frame[["Open", "High", "Low", "Close"]] <= 0).any(axis=1))
        if bad.any():
            raise ValueError(f"{filename} has {int(bad.sum())} invalid OHLC rows")
        frame = frame.sort_values("timestamp").set_index("timestamp")
        opens[pair], closes[pair] = frame.Open, frame.Close
    open_prices = pd.concat(opens, axis=1).dropna()
    close_prices = pd.concat(closes, axis=1).reindex(open_prices.index).dropna()
    common = open_prices.index.intersection(close_prices.index)
    return open_prices.loc[common], close_prices.loc[common]


def partial_adjust(target, speed):
    values = target.to_numpy(float)
    positions = np.empty_like(values)
    current = np.zeros(values.shape[1])
    for i in range(len(values)):
        available = np.isfinite(values[i])
        current[available] += speed * (values[i, available] - current[available])
        positions[i] = current
    # Close-t signal is first tradable at open t+1.
    return pd.DataFrame(positions, index=target.index,
                        columns=target.columns).shift(1).fillna(0.0)


def position_panel():
    open_prices, close_prices = load_prices()
    close_returns = np.log(close_prices).diff()
    vol = close_returns.rolling(VOL_WINDOW).std() * np.sqrt(ANN)
    score = np.log(close_prices / close_prices.shift(LOOKBACK))
    target = (np.sign(score) * (TARGET_VOL / vol.clip(lower=0.02))).clip(-1, 1)
    full = partial_adjust(target, 1.0)
    components = [partial_adjust(target, speed) for speed in PARTIAL_SPEEDS]
    ensemble = sum(components) / len(components)
    return open_prices, {"full": full, "ensemble": ensemble}


def run():
    open_prices, positions = position_panel()
    forward_returns = np.log(open_prices.shift(-1) / open_prices)
    is_oos = open_prices.index >= HOLDOUT_START
    rows, attribution = [], []
    for model, weights in positions.items():
        turnover = weights.diff().abs().fillna(weights.abs())
        gross_assets = weights * forward_returns
        for cost_pips in COST_PIPS:
            pip_size = pd.DataFrame(
                {p: (0.01 if p.endswith("JPY") else 0.0001)
                 for p in open_prices.columns}, index=open_prices.index
            )
            costs = turnover * cost_pips * pip_size / open_prices
            net_assets = gross_assets - costs
            net = net_assets.mean(axis=1)[is_oos].dropna()
            gross = gross_assets.mean(axis=1)[is_oos].reindex(net.index)
            equity = np.exp(net.cumsum())
            drawdown = equity / equity.cummax() - 1.0
            yearly = net.groupby(net.index.year).sum().map(np.exp).sub(1.0)
            rows.append({
                "model": model,
                "cost_pips": cost_pips,
                "oos_start": str(net.index[0].date()),
                "oos_end": str(net.index[-1].date()),
                "observations": len(net),
                "gross_total_return": np.exp(gross.sum()) - 1.0,
                "net_total_return": equity.iloc[-1] - 1.0,
                "net_annualized_return": equity.iloc[-1] ** (ANN / len(net)) - 1.0,
                "net_sharpe": np.sqrt(ANN) * net.mean() / net.std(),
                "net_max_drawdown": drawdown.min(),
                "annualized_turnover": turnover[is_oos].mean().mean() * ANN,
                "positive_calendar_year_fraction": (yearly > 0).mean(),
            })
            for pair in open_prices.columns:
                asset_net = net_assets[pair][is_oos].reindex(net.index)
                attribution.append({
                    "model": model,
                    "cost_pips": cost_pips,
                    "asset": pair,
                    "net_total_return_standalone": np.exp(asset_net.sum()) - 1.0,
                    "annualized_turnover": turnover[pair][is_oos].mean() * ANN,
                })
    return pd.DataFrame(rows), pd.DataFrame(attribution)


def hypothesis_summary(results):
    base = results.set_index(["model", "cost_pips"])
    full = base.loc[("full", 2.2)]
    ensemble = base.loc[("ensemble", 2.2)]
    stressed = base.loc[("ensemble", 4.4)]
    passes = bool(
        ensemble.net_total_return > full.net_total_return
        and ensemble.net_sharpe > full.net_sharpe
        and stressed.net_total_return > 0
    )
    return pd.DataFrame([{
        "ensemble_return_delta_at_2_2_pips": (
            ensemble.net_total_return - full.net_total_return
        ),
        "ensemble_sharpe_delta_at_2_2_pips": (
            ensemble.net_sharpe - full.net_sharpe
        ),
        "ensemble_net_return_at_4_4_pips": stressed.net_total_return,
        "preregistered_hypothesis_supported": passes,
    }])


def cross_source_validation():
    """Compare pre-holdout close returns with the independent FXCM archive."""
    from real_fxcm_daily_replication import load_prices as load_fxcm_prices

    _, epsoft_close = load_prices()
    fxcm_close = load_fxcm_prices()
    rows = []
    for pair in PAIRS:
        epsoft_return = np.log(epsoft_close[pair]).diff()
        fxcm_return = np.log(fxcm_close[pair]).diff()
        epsoft_return.index = epsoft_return.index.tz_convert(None).normalize()
        fxcm_return.index = fxcm_return.index.tz_convert(None).normalize()
        aligned = pd.concat(
            [epsoft_return.rename("epsoft"), fxcm_return.rename("fxcm")], axis=1
        ).dropna()
        rows.append({
            "asset": pair,
            "overlap_observations": len(aligned),
            "same_date_return_correlation": aligned.corr().iloc[0, 1],
            "median_absolute_return_difference_bps": (
                (aligned.epsoft - aligned.fxcm).abs().median() * 10000
            ),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    result, attribution = run()
    summary = hypothesis_summary(result)
    crosscheck = cross_source_validation()
    result.to_csv("real_epsoft_speed_ensemble_results.csv", index=False)
    attribution.to_csv("real_epsoft_speed_ensemble_attribution.csv", index=False)
    summary.to_csv("real_epsoft_speed_ensemble_summary.csv", index=False)
    crosscheck.to_csv("real_epsoft_feed_crosscheck.csv", index=False)
    print(result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nAsset attribution")
    print(attribution.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nDecision")
    print(summary.to_string(index=False))
    print("\nIndependent pre-holdout feed cross-check")
    print(crosscheck.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
