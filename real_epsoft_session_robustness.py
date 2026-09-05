"""Session-definition robustness for the locked EPSOFT full TSMOM model."""
import numpy as np
import pandas as pd

from real_epsoft_speed_ensemble import (
    COST_PIPS,
    FILES,
    HOLDOUT_START,
    LOOKBACK,
    PAIRS,
    TARGET_VOL,
    VOL_WINDOW,
)

COST = max(COST_PIPS)
SESSION_RULES = ["calendar_all", "nonzero_range", "full_session"]


def load_ohlc():
    parts = {}
    for pair, filename in FILES.items():
        frame = pd.read_csv(filename)
        frame["timestamp"] = pd.to_datetime(
            frame["Local time"].str.slice(0, 10), dayfirst=True, utc=True
        )
        parts[pair] = frame.set_index("timestamp")[["Open", "High", "Low", "Close"]]
    common = parts[PAIRS[0]].index
    for pair in PAIRS[1:]:
        common = common.intersection(parts[pair].index)
    return {pair: parts[pair].loc[common].sort_index() for pair in PAIRS}


def apply_session_rule(ohlc, rule):
    index = ohlc[PAIRS[0]].index
    if rule == "calendar_all":
        mask = pd.Series(True, index=index)
    elif rule == "nonzero_range":
        mask = pd.concat(
            [(ohlc[pair].High > ohlc[pair].Low).rename(pair) for pair in PAIRS],
            axis=1,
        ).all(axis=1)
    elif rule == "full_session":
        # Source labels: Sunday-Thursday carry full active candles; Friday is
        # zero-range and Saturday is a short stub candle.
        mask = pd.Series(index.dayofweek.isin([6, 0, 1, 2, 3]), index=index)
    else:
        raise ValueError(f"Unknown session rule: {rule}")
    return {pair: frame.loc[mask] for pair, frame in ohlc.items()}


def _annualization(index):
    pre = pd.Series(1, index=index[(index.year >= 2017) & (index.year <= 2020)])
    return float(pre.groupby(pre.index.year).sum().median())


def run():
    raw = load_ohlc()
    rows, attribution = [], []
    for rule in SESSION_RULES:
        data = apply_session_rule(raw, rule)
        index = data[PAIRS[0]].index
        open_prices = pd.concat({p: data[p].Open for p in PAIRS}, axis=1)
        close_prices = pd.concat({p: data[p].Close for p in PAIRS}, axis=1)
        ann = _annualization(index)
        returns = np.log(close_prices).diff()
        vol = returns.rolling(VOL_WINDOW).std() * np.sqrt(ann)
        score = np.log(close_prices / close_prices.shift(LOOKBACK))
        target = (np.sign(score) * (TARGET_VOL / vol.clip(lower=0.02))).clip(-1, 1)
        weights = target.shift(1).fillna(0.0)
        turnover = weights.diff().abs().fillna(weights.abs())
        forward = np.log(open_prices.shift(-1) / open_prices)
        pip_size = pd.DataFrame(
            {p: (0.01 if p.endswith("JPY") else 0.0001) for p in PAIRS},
            index=index,
        )
        net_assets = weights * forward - turnover * COST * pip_size / open_prices
        is_oos = index >= HOLDOUT_START
        portfolio = net_assets.mean(axis=1)[is_oos].dropna()
        equity = np.exp(portfolio.cumsum())
        drawdown = equity / equity.cummax() - 1.0
        rows.append({
            "session_rule": rule,
            "annualization": ann,
            "oos_start": str(portfolio.index[0].date()),
            "oos_end": str(portfolio.index[-1].date()),
            "observations": len(portfolio),
            "net_total_return": equity.iloc[-1] - 1.0,
            "net_annualized_return": equity.iloc[-1] ** (ann / len(portfolio)) - 1.0,
            "net_sharpe": np.sqrt(ann) * portfolio.mean() / portfolio.std(),
            "net_max_drawdown": drawdown.min(),
            "annualized_turnover": turnover[is_oos].mean().mean() * ann,
        })
        for pair in PAIRS:
            asset = net_assets[pair][is_oos].dropna()
            attribution.append({
                "session_rule": rule,
                "asset": pair,
                "net_total_return_standalone": np.exp(asset.sum()) - 1.0,
                "net_sharpe_standalone": np.sqrt(ann) * asset.mean() / asset.std(),
            })
    return pd.DataFrame(rows), pd.DataFrame(attribution)


def hypothesis_summary(results, attribution):
    all_portfolios_positive = bool(
        (results.net_total_return > 0).all() and (results.net_sharpe > 0).all()
    )
    all_assets_positive = bool(
        (attribution.net_total_return_standalone > 0).all()
        and (attribution.net_sharpe_standalone > 0).all()
    )
    return pd.DataFrame([{
        "all_session_portfolios_positive": all_portfolios_positive,
        "all_session_asset_sleeves_positive": all_assets_positive,
        "session_robustness_supported": all_portfolios_positive and all_assets_positive,
    }])


if __name__ == "__main__":
    result, attribution = run()
    summary = hypothesis_summary(result, attribution)
    result.to_csv("real_epsoft_session_robustness_results.csv", index=False)
    attribution.to_csv("real_epsoft_session_robustness_attribution.csv", index=False)
    summary.to_csv("real_epsoft_session_robustness_summary.csv", index=False)
    print(result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nAsset sleeves")
    print(attribution.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nDecision")
    print(summary.to_string(index=False))
