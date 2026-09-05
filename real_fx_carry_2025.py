"""Preregistered, two-month-lagged FX carry test on 2025 HistData bars."""
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from real_histdata_2024_confirmation import stationary_indices


ASSETS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD"]
CSV_SHA256 = {
    "EURUSD": "d476f9b73a5210e5dd0a7a2f1b2e6da28fbc6ee9b124b05a04c892bd8731d984",
    "USDJPY": "2be5ead3405ef7d5ff46c2ac8d1c2bb3f93cf26681ad6148777d7acf44681b74",
    "GBPUSD": "2e8aaf4ab712008542843f923cee0224ae87ce69dfa6da197454f9de150705f9",
    "AUDUSD": "46ade9508f256c90a78aaab48fed37305022f3f75b90fdd5a0483337aff71a85",
}
RATE_SERIES = {
    "USD": "IR3TIB01USM156N", "EUR": "IR3TIB01EZM156N",
    "JPY": "IR3TIB01JPM156N", "GBP": "IR3TIB01GBM156N",
    "AUD": "IR3TIB01AUM156N",
}
RATE_SHA256 = {
    "IR3TIB01USM156N": "3a51abf105c27499ec6b28cf5edec386274d578e7da66df4c82ae7d0b4cef23b",
    "IR3TIB01EZM156N": "bda18d6a61bc490560965e6acd9fc21e213f026ca68ac4670d3c9ec835043ce5",
    "IR3TIB01JPM156N": "7a1132087e2a21c5b24f74e7209d70be75118357c8996c24a6a826cd06f1166f",
    "IR3TIB01GBM156N": "40c23cc654a1380ed278a2b0be691f368d5cc1648493cadbbf1a2a2f654d33d4",
    "IR3TIB01AUM156N": "369327f8d506c467783f4b1c53659ae873f02db17b7be461fb07248074ecd947",
}
MIN_MINUTES = 1000
SESSION_CLOSE_EST = 17
PIP_COST = 4.4
ANN = 252
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_BLOCK = 10
BOOTSTRAP_SEED = 23036


def checked_csv(path, expected, **kwargs):
    path = Path(path)
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Hash mismatch: {path}")
    return pd.read_csv(path, **kwargs)


def load_daily(asset):
    cols = ["timestamp", "Open", "High", "Low", "Close", "Volume"]
    frame = checked_csv(
        f"DAT_ASCII_{asset}_M1_2025.csv", CSV_SHA256[asset], sep=";",
        header=None, names=cols,
    )
    frame.timestamp = pd.to_datetime(frame.timestamp, format="%Y%m%d %H%M%S")
    duplicates = frame.timestamp.duplicated(keep=False)
    if duplicates.any():
        groups = frame.loc[duplicates].groupby("timestamp")
        if any(len(group.drop_duplicates()) != 1 for _, group in groups):
            raise ValueError(f"Conflicting duplicate timestamps: {asset}")
        frame = frame.drop_duplicates()
    bad = ((frame[["Open", "High", "Low", "Close"]] <= 0).any(axis=1)
           | (frame.Low > frame[["Open", "Close"]].min(axis=1))
           | (frame.High < frame[["Open", "Close"]].max(axis=1)))
    if bad.any():
        raise ValueError(f"Invalid OHLC rows: {asset}")
    session = (frame.timestamp - pd.Timedelta(hours=SESSION_CLOSE_EST)).dt.normalize()
    daily = frame.assign(session=session).groupby("session").agg(
        Open=("Open", "first"), High=("High", "max"), Low=("Low", "min"),
        Close=("Close", "last"), minute_count=("Open", "size"),
    )
    daily = daily[daily.minute_count >= MIN_MINUTES]
    daily.index = daily.index.tz_localize("Etc/GMT+5").tz_convert("UTC")
    return daily


def load_rates():
    rates = []
    for currency, series in RATE_SERIES.items():
        frame = checked_csv(f"fred_{series}.csv", RATE_SHA256[series])
        frame.columns = ["observation_date", "rate"]
        frame.observation_date = pd.to_datetime(frame.observation_date)
        frame.rate = pd.to_numeric(frame.rate, errors="coerce")
        frame["currency"] = currency
        rates.append(frame.dropna())
    wide = pd.concat(rates).pivot(index="observation_date", columns="currency", values="rate")
    # Month m is available only from the first day of month m+2.
    wide.index = wide.index + pd.offsets.MonthBegin(2)
    scores = pd.DataFrame(index=wide.index)
    for asset in ["EURUSD", "GBPUSD", "AUDUSD"]:
        scores[asset] = (wide[asset[:3]] - wide.USD) / 100.0
    scores["USDJPY"] = (wide.USD - wide.JPY) / 100.0
    return scores.sort_index()


def build_panel():
    daily = {asset: load_daily(asset) for asset in ASSETS}
    common = daily[ASSETS[0]].index
    for asset in ASSETS[1:]:
        common = common.intersection(daily[asset].index)
    return pd.concat({a: daily[a].Open.loc[common] for a in ASSETS}, axis=1)


def targets(scores, sessions, assets=ASSETS):
    available = scores.reindex(sessions.tz_localize(None), method="ffill").set_axis(sessions)
    result = pd.DataFrame(0.0, index=sessions, columns=assets)
    for date, row in available[assets].iterrows():
        valid = row.dropna()
        if len(valid) >= 2:
            result.loc[date, valid.idxmax()] = 0.5
            result.loc[date, valid.idxmin()] = -0.5
    return result, available[assets]


def costs(turnover, opens, multiplier=1.0):
    total = pd.Series(0.0, index=opens.index)
    for asset in opens:
        pip = 0.01 if asset.endswith("JPY") else 0.0001
        total += turnover[asset] * PIP_COST * pip / opens[asset] * multiplier
    return total


def simulate(opens, scores, assets=ASSETS, cost_multiplier=1.0):
    weight, daily_scores = targets(scores, opens.index, assets)
    spot = (weight * np.log(opens.shift(-1) / opens)).sum(axis=1)
    calendar_days = (
        opens.index.to_series().shift(-1) - opens.index.to_series()
    ).dt.total_seconds() / 86400.0
    carry = (weight * daily_scores).sum(axis=1) * calendar_days / 365.0
    turnover = weight.diff().abs().fillna(weight.abs())
    trading_cost = costs(turnover, opens, cost_multiplier)
    active = (weight.abs().sum(axis=1) > 0) & opens.shift(-1).notna().all(axis=1)
    return ((spot + carry - trading_cost).loc[active], spot.loc[active],
            carry.loc[active], trading_cost.loc[active], turnover, weight)


def metrics(series):
    equity = np.exp(series.cumsum())
    drawdown = equity / equity.cummax() - 1
    volatility = series.std()
    return {
        "observations": len(series), "start": str(series.index[0].date()),
        "end": str(series.index[-1].date()),
        "total_return": equity.iloc[-1] - 1,
        "sharpe": (np.sqrt(ANN) * series.mean() / volatility
                   if volatility > 0 else np.nan),
        "max_drawdown": drawdown.min(),
    }


def bootstrap(series):
    values = series.to_numpy(float)
    idx = stationary_indices(len(values), BOOTSTRAP_SAMPLES, BOOTSTRAP_BLOCK,
                             BOOTSTRAP_SEED)
    means = values[idx].mean(axis=1)
    return pd.DataFrame([{
        "samples": BOOTSTRAP_SAMPLES, "expected_block_sessions": BOOTSTRAP_BLOCK,
        "probability_mean_positive": (means > 0).mean(),
        "annualized_mean_ci_low": np.quantile(means, .025) * ANN,
        "annualized_mean_ci_high": np.quantile(means, .975) * ANN,
    }])


def run():
    opens, scores = build_panel(), load_rates()
    net, spot, carry, trading_cost, turnover, weight = simulate(opens, scores)
    main = pd.DataFrame([{
        **metrics(net), "spot_total_return": np.exp(spot.sum()) - 1,
        "carry_log_contribution": carry.sum(), "cost_log_drag": trading_cost.sum(),
        "annualized_turnover": turnover.sum(axis=1).mean() * ANN,
    }])
    attribution = []
    forward = np.log(opens.shift(-1) / opens)
    daily_scores = scores.reindex(opens.index.tz_localize(None), method="ffill").set_axis(opens.index)
    calendar_days = (
        opens.index.to_series().shift(-1) - opens.index.to_series()
    ).dt.total_seconds() / 86400.0
    turns = weight.diff().abs().fillna(weight.abs())
    active = net.index
    for asset in ASSETS:
        component = (weight[asset] * (forward[asset]
                     + daily_scores[asset] * calendar_days / 365)
                     - costs(turns[[asset]], opens[[asset]])).loc[active]
        attribution.append({"asset": asset, **metrics(component)})
    loo = []
    for excluded in ASSETS:
        included = [a for a in ASSETS if a != excluded]
        sample, *_ = simulate(opens[included], scores, included)
        loo.append({"excluded_asset": excluded, **metrics(sample)})
    stress = []
    for multiplier in [0.0, 0.5, 1.0, 2.0]:
        sample, *_ = simulate(opens, scores, cost_multiplier=multiplier)
        stress.append({"cost_multiplier_vs_locked": multiplier, **metrics(sample)})
    vol = np.log(opens.USDJPY).diff().rolling(20).std().shift(1)
    threshold = vol.expanding(60).median().shift(1)
    regimes = []
    regime_masks = {
        "low_usdjpy_vol": vol <= threshold,
        "high_usdjpy_vol": vol > threshold,
        "warmup_unclassified": threshold.isna(),
    }
    for name, mask in regime_masks.items():
        sample = net[mask.reindex(net.index).fillna(False)]
        regimes.append({"regime": name, **metrics(sample)})
    boot = bootstrap(net)
    loo_frame = pd.DataFrame(loo)
    positive_loo = int((loo_frame.total_return > 0).sum())
    summary = pd.DataFrame([{
        "positive_net_return": main.iloc[0].total_return > 0,
        "positive_leave_one_out": positive_loo,
        "bootstrap_probability_positive": boot.iloc[0].probability_mean_positive,
        "preregistered_hypothesis_supported": bool(
            main.iloc[0].total_return > 0 and positive_loo >= 3
            and boot.iloc[0].probability_mean_positive >= .95),
    }])
    return (main, pd.DataFrame(attribution), loo_frame, pd.DataFrame(stress),
            pd.DataFrame(regimes), boot, summary)


if __name__ == "__main__":
    names = ["results", "attribution", "leave_one_out", "cost_stress", "regimes",
             "bootstrap", "summary"]
    for name, frame in zip(names, run()):
        frame.to_csv(f"real_fx_carry_2025_{name}.csv", index=False)
        print(name, frame.to_string(index=False))
