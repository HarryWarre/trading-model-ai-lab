"""2020 FXCM daily bid/ask holdout for partial-adjustment TSMOM."""
from pathlib import Path
import gzip

import numpy as np
import pandas as pd

PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY"]
YEARS = range(2017, 2021)
SPEEDS = [1.0, 0.5, 0.25, 0.10]
SPREAD_MULTIPLIERS = [1.0, 2.0]
LOOKBACK = 20
VOL_WINDOW = 20
TARGET_VOL = 0.10
HOLDOUT_YEAR = 2020
REQUIRED = {
    "DateTime", "BidOpen", "AskOpen", "BidClose", "AskClose",
}


def validate_gzip_csv(path):
    """Reject HTML/error payloads and malformed archives before parsing."""
    path = Path(path)
    with path.open("rb") as fh:
        if fh.read(2) != b"\x1f\x8b":
            raise ValueError(f"{path} is not a gzip archive")
    with gzip.open(path, "rt") as fh:
        frame = pd.read_csv(fh)
    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError(f"{path} is empty")
    return frame


def load_quotes():
    opens, closes, half_spreads = {}, {}, {}
    crossed = {}
    for pair in PAIRS:
        frames = []
        for year in YEARS:
            frame = validate_gzip_csv(f"fxcm_{pair}_{year}.csv.gz")
            frame["timestamp"] = pd.to_datetime(frame["DateTime"], utc=True)
            frames.append(frame)
        frame = (pd.concat(frames).sort_values("timestamp")
                 .drop_duplicates("timestamp").set_index("timestamp"))
        open_spread = frame["AskOpen"] - frame["BidOpen"]
        crossed[pair] = int((open_spread < 0).sum())
        opens[pair] = (frame["AskOpen"] + frame["BidOpen"]) / 2.0
        closes[pair] = (frame["AskClose"] + frame["BidClose"]) / 2.0
        # A crossed quote must never generate a negative transaction cost.
        half_spreads[pair] = open_spread.clip(lower=0.0) / 2.0
    open_mid = pd.concat(opens, axis=1).dropna()
    common = open_mid.index
    close_mid = pd.concat(closes, axis=1).reindex(common)
    half_spread = pd.concat(half_spreads, axis=1).reindex(common)
    valid = close_mid.notna().all(axis=1) & half_spread.notna().all(axis=1)
    return open_mid.loc[valid], close_mid.loc[valid], half_spread.loc[valid], crossed


def partial_adjust(target, speed):
    values = target.to_numpy(dtype=float)
    position = np.empty_like(values)
    current = np.zeros(values.shape[1], dtype=float)
    for i in range(len(values)):
        available = np.isfinite(values[i])
        current[available] += speed * (values[i, available] - current[available])
        position[i] = current
    # Signal observed at close t is executable no earlier than open t+1.
    return pd.DataFrame(position, index=target.index,
                        columns=target.columns).shift(1).fillna(0.0)


def _annualization(index):
    pre = pd.Series(1, index=index[index.year < HOLDOUT_YEAR])
    return float(pre.groupby(pre.index.year).sum().median())


def run():
    open_mid, close_mid, half_spread, crossed = load_quotes()
    ann = _annualization(open_mid.index)
    close_returns = np.log(close_mid).diff()
    vol = close_returns.rolling(VOL_WINDOW).std() * np.sqrt(ann)
    score = np.log(close_mid / close_mid.shift(LOOKBACK))
    target = (np.sign(score) * (TARGET_VOL / vol.clip(lower=0.02))).clip(-1, 1)
    forward_open_return = np.log(open_mid.shift(-1) / open_mid)
    is_oos = open_mid.index.year == HOLDOUT_YEAR
    rows = []

    for speed in SPEEDS:
        weights = partial_adjust(target, speed)
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = (weights * forward_open_return).mean(axis=1)
        base_cost = (turnover * half_spread / open_mid).mean(axis=1)
        for spread_multiplier in SPREAD_MULTIPLIERS:
            oos = (gross - spread_multiplier * base_cost)[is_oos].dropna()
            gross_oos = gross[is_oos].reindex(oos.index)
            equity = np.exp(oos.cumsum())
            drawdown = equity / equity.cummax() - 1.0
            rows.append({
                "lookback_sessions": LOOKBACK,
                "adjustment_speed": speed,
                "spread_multiplier": spread_multiplier,
                "oos_start": str(oos.index[0].date()),
                "oos_end": str(oos.index[-1].date()),
                "observations": len(oos),
                "annualization_from_pre_holdout": ann,
                "gross_total_return": np.exp(gross_oos.sum()) - 1.0,
                "net_total_return": equity.iloc[-1] - 1.0,
                "net_annualized_return": equity.iloc[-1] ** (ann / len(oos)) - 1.0,
                "net_sharpe": np.sqrt(ann) * oos.mean() / oos.std(),
                "net_max_drawdown": drawdown.min(),
                "annualized_turnover": turnover[is_oos].mean().mean() * ann,
                "observed_spread_cost_return": base_cost[is_oos].reindex(oos.index).sum(),
                "crossed_open_quotes_total": sum(crossed.values()),
            })
    return pd.DataFrame(rows)


def hypothesis_summary(results):
    base = results[results.spread_multiplier == 1.0].set_index("adjustment_speed")
    full_sharpe = base.loc[1.0, "net_sharpe"]
    partial = base.loc[[0.5, 0.25, 0.10]]
    turnover_reduction = 1.0 - partial.annualized_turnover / base.loc[1.0, "annualized_turnover"]
    stress = results[(results.spread_multiplier == 2.0)
                     & (results.adjustment_speed < 1.0)]
    return pd.DataFrame([{
        "partial_sharpe_wins_vs_full_at_1x": int((partial.net_sharpe > full_sharpe).sum()),
        "partial_configurations": len(partial),
        "median_turnover_reduction_at_1x": turnover_reduction.median(),
        "positive_partial_configs_at_2x": int((stress.net_total_return > 0).sum()),
        "mechanism_supported": bool(
            (partial.net_sharpe > full_sharpe).sum() >= 2
            and turnover_reduction.median() >= 0.25
        ),
        "investability_gate_passed": bool((stress.net_total_return > 0).any()),
    }])


if __name__ == "__main__":
    result = run()
    summary = hypothesis_summary(result)
    result.to_csv("real_fxcm_partial_adjustment_holdout_results.csv", index=False)
    summary.to_csv("real_fxcm_partial_adjustment_holdout_summary.csv", index=False)
    print(result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nPreregistered tests")
    print(summary.to_string(index=False))
