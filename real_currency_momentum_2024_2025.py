"""Preregistered 21-session cross-sectional currency momentum test."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

import real_carry_crash_risk as crash
import real_fx_carry_2025 as carry
import real_monthly_rate_lag_audit as lag_audit
import real_reer_value_2025 as value_model
import real_histdata_2024_crossasset as hist2024
from real_histdata_2024_confirmation import stationary_indices


CURRENCIES = ["AUD", "EUR", "GBP", "JPY"]
CURRENCY_TO_ASSET = {"AUD": "AUDUSD", "EUR": "EURUSD",
                     "GBP": "GBPUSD", "JPY": "USDJPY"}
FORMATION = 21
HOLDING = 21
PRIMARY_OFFSET = 0
PHASE_OFFSETS = [0, 5, 10, 15]
ANN = 252
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_BLOCK = 10
BOOTSTRAP_SEED = 29042

ZIP_2024_SHA256 = {
    "EURUSD": "58f074ba6b835eb2fbeaeb6678502a23b26768eefdfa509eb75ff5296bb2904d",
    "USDJPY": "dc99fe4b3e0ae1b457f6bfccc5d36cf6f628812f704f5556aa0a74ff3e7e8c81",
    "GBPUSD": "030b05b4c670c7e152bf4aa4112488c96695d2dcc2b31ca13a3b4834b8431077",
    "AUDUSD": "56338ceb24d7013137e31810be1fe4326d0a4480342829e74fd9355e5efbb7f0",
}


def load_2024_daily(asset):
    """Read the hash-locked archive, not a mutable extracted workspace file."""
    path = Path(f"histdata_{asset}_M1_2024.zip")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != ZIP_2024_SHA256[asset]:
        raise ValueError(f"2024 archive hash mismatch: {asset}")
    with ZipFile(BytesIO(raw)) as archive:
        member = archive.read(f"DAT_ASCII_{asset}_M1_2024.csv")
    if sha256(member).hexdigest() != hist2024.CSV_SHA256[asset]:
        raise ValueError(f"2024 CSV member hash mismatch: {asset}")
    columns = ["timestamp", "Open", "High", "Low", "Close", "Volume"]
    frame = pd.read_csv(BytesIO(member), sep=";", header=None, names=columns)
    frame.timestamp = pd.to_datetime(frame.timestamp, format="%Y%m%d %H%M%S")
    return hist2024.reconstruct_daily(frame)


def build_opens():
    daily24 = {asset: load_2024_daily(asset) for asset in carry.ASSETS}
    common24 = daily24[carry.ASSETS[0]].index
    for asset in carry.ASSETS[1:]:
        common24 = common24.intersection(daily24[asset].index)
    opens24 = pd.concat({asset: daily24[asset].Open.loc[common24]
                         for asset in carry.ASSETS}, axis=1)
    opens = pd.concat([opens24, carry.build_panel()]).sort_index()
    if opens.index.duplicated().any() or not opens.index.is_monotonic_increasing:
        raise ValueError("Combined HistData session index is not unique and sorted")
    return opens[carry.ASSETS]


def currency_prices(opens):
    result = pd.DataFrame(index=opens.index)
    for currency in ["AUD", "EUR", "GBP"]:
        result[currency] = opens[f"{currency}USD"]
    result["JPY"] = 1.0 / opens.USDJPY
    return result


def currency_rate_differentials(rate_scores, sessions):
    aligned = rate_scores.reindex(sessions.tz_localize(None), method="ffill").set_axis(sessions)
    result = pd.DataFrame(index=sessions)
    for currency in ["AUD", "EUR", "GBP"]:
        result[currency] = aligned[f"{currency}USD"]
    result["JPY"] = -aligned.USDJPY
    return result


def formation_scores(opens, rate_scores):
    prices = currency_prices(opens)
    rates = currency_rate_differentials(rate_scores, opens.index)
    days = ((opens.index.to_series().shift(-1) - opens.index.to_series())
            .dt.total_seconds() / 86400.0)
    interval_carry = rates.mul(days, axis=0) / 365.0
    trailing_carry = interval_carry.rolling(FORMATION).sum().shift(1)
    trailing_spot = np.log(prices / prices.shift(FORMATION))
    return trailing_spot + trailing_carry, rates


def currency_targets(scores, currencies=CURRENCIES, offset=PRIMARY_OFFSET):
    weights = pd.DataFrame(0.0, index=scores.index, columns=CURRENCIES)
    audit = []
    for position in range(FORMATION + offset, len(scores) - 1, HOLDING):
        signal = scores.iloc[position][list(currencies)].dropna()
        if len(signal) != len(currencies) or len(signal) < 2:
            continue
        ordered = signal.sort_values(kind="mergesort")
        target = pd.Series(0.0, index=CURRENCIES)
        target[ordered.index[0]] = -0.5
        target[ordered.index[-1]] = 0.5
        start = position + 1  # one-session execution lag
        end = min(start + HOLDING, len(scores))
        weights.iloc[start:end] = target.to_numpy()
        audit.append({
            "formation_session": scores.index[position],
            "execution_session": scores.index[start], "offset": offset,
            "winner": ordered.index[-1], "loser": ordered.index[0],
            **{f"score_{c}": scores.iloc[position][c] for c in CURRENCIES},
        })
    return weights, pd.DataFrame(audit)


def instrument_weights(currency_weights):
    result = pd.DataFrame(0.0, index=currency_weights.index, columns=carry.ASSETS)
    result.AUDUSD = currency_weights.AUD
    result.EURUSD = currency_weights.EUR
    result.GBPUSD = currency_weights.GBP
    result.USDJPY = -currency_weights.JPY
    return result


def simulate(opens, rate_scores, currencies=CURRENCIES, offset=PRIMARY_OFFSET,
             cost_multiplier=1.0):
    scores, currency_rates = formation_scores(opens, rate_scores)
    currency_weight, audit = currency_targets(scores, currencies, offset)
    weight = instrument_weights(currency_weight)
    assets = [CURRENCY_TO_ASSET[c] for c in currencies]
    forward = np.log(opens.shift(-1) / opens)
    days = ((opens.index.to_series().shift(-1) - opens.index.to_series())
            .dt.total_seconds() / 86400.0)
    spot = (weight[assets] * forward[assets]).sum(axis=1)
    accrual = (currency_weight[list(currencies)] * currency_rates[list(currencies)]
               ).sum(axis=1) * days / 365.0
    turnover = weight.diff().abs().fillna(weight.abs())
    trading_cost = carry.costs(turnover[assets], opens[assets], cost_multiplier)
    active = ((weight[assets].abs().sum(axis=1) > 0)
              & opens[assets].shift(-1).notna().all(axis=1))
    net = (spot + accrual - trading_cost).loc[active]
    return (net, spot.loc[active], accrual.loc[active], trading_cost.loc[active],
            turnover, weight, currency_weight, scores, audit)


def bootstrap(series):
    values = series.to_numpy(float)
    idx = stationary_indices(len(values), BOOTSTRAP_SAMPLES, BOOTSTRAP_BLOCK,
                             BOOTSTRAP_SEED)
    means = values[idx].mean(axis=1)
    return pd.DataFrame([{
        "samples": BOOTSTRAP_SAMPLES, "expected_block_sessions": BOOTSTRAP_BLOCK,
        "probability_mean_positive": float((means > 0).mean()),
        "annualized_mean_ci_low": np.quantile(means, .025) * ANN,
        "annualized_mean_ci_high": np.quantile(means, .975) * ANN,
    }])


def run():
    opens, rates = build_opens(), lag_audit.load_rates(3)
    sim = simulate(opens, rates)
    net, spot, accrual, trading_cost, turnover, weights, currency_weight, scores, audit = sim
    primary = pd.DataFrame([{
        **value_model.metrics(net), "spot_total_return": np.exp(spot.sum()) - 1,
        "carry_log_contribution": accrual.sum(), "cost_log_drag": trading_cost.sum(),
        "annualized_turnover": turnover.sum(axis=1).mean() * ANN,
        "break_even_cost_multiplier": ((spot.sum() + accrual.sum()) / trading_cost.sum()
                                        if trading_cost.sum() > 0 else np.nan),
    }])

    annual = []
    for year in [2024, 2025]:
        sample = net[net.index.year == year]
        annual.append({"year": year, **value_model.metrics(sample)})

    forward = np.log(opens.shift(-1) / opens)
    currency_rates = currency_rate_differentials(rates, opens.index)
    days = ((opens.index.to_series().shift(-1) - opens.index.to_series())
            .dt.total_seconds() / 86400.0)
    attribution = []
    for currency in CURRENCIES:
        asset = CURRENCY_TO_ASSET[currency]
        sign = -1.0 if currency == "JPY" else 1.0
        component = (weights[asset] * forward[asset]
                     + currency_weight[currency] * currency_rates[currency] * days / 365.0
                     - carry.costs(turnover[[asset]], opens[[asset]])).loc[net.index]
        attribution.append({"currency": currency, "asset": asset,
                            "spot_orientation": sign, **value_model.metrics(component)})

    loo = []
    for excluded in CURRENCIES:
        currencies = [c for c in CURRENCIES if c != excluded]
        sample, *_ = simulate(opens, rates, currencies=currencies)
        loo.append({"excluded_currency": excluded, **value_model.metrics(sample)})
    loo_frame = pd.DataFrame(loo)

    stress = []
    for multiplier in [0.0, 1.0, 2.0]:
        sample, *_ = simulate(opens, rates, cost_multiplier=multiplier)
        stress.append({"cost_multiplier_vs_locked": multiplier,
                       **value_model.metrics(sample)})
    stress_frame = pd.DataFrame(stress)

    phase = []
    for offset in PHASE_OFFSETS:
        sample, *_ = simulate(opens, rates, offset=offset)
        phase.append({"offset_sessions": offset, **value_model.metrics(sample)})
    phase_frame = pd.DataFrame(phase)

    aligned = crash.align_vix(net.index)
    high = aligned.lagged_vix > aligned.threshold_75
    regimes = []
    for name, mask in [("low_vix", ~high), ("high_vix", high)]:
        regimes.append({"regime": name, **value_model.metrics(net[mask])})

    boot = bootstrap(net)
    annual_frame = pd.DataFrame(annual)
    positive_years = int((annual_frame.total_return > 0).sum())
    positive_loo = int((loo_frame.total_return > 0).sum())
    double_positive = bool(stress_frame.loc[
        stress_frame.cost_multiplier_vs_locked.eq(2), "total_return"].iloc[0] > 0)
    median_phase = float(phase_frame.total_return.median())
    summary = pd.DataFrame([{
        "pooled_net_positive": bool(primary.total_return.iloc[0] > 0),
        "positive_years": positive_years,
        "positive_leave_one_out": positive_loo,
        "bootstrap_probability_positive": boot.probability_mean_positive.iloc[0],
        "double_cost_positive": double_positive,
        "median_phase_return": median_phase,
        "median_phase_positive": bool(median_phase > 0),
        "preregistered_hypothesis_supported": bool(
            primary.total_return.iloc[0] > 0 and positive_years == 2
            and positive_loo >= 3 and boot.probability_mean_positive.iloc[0] >= .95
            and double_positive and median_phase > 0),
    }])
    coverage = pd.DataFrame([{
        "data_status": "new_hypothesis_reused_sample",
        "sessions_total": len(opens), "active_return_sessions": len(net),
        "price_start": str(opens.index.min().date()),
        "price_end": str(opens.index.max().date()),
        "formation_sessions": FORMATION, "holding_sessions": HOLDING,
        "primary_rebalances": len(audit), "capacity_quantifiable": False,
        "source_2024": "hash-locked ZIP members",
        "truncated_extracted_gbpusd_2024_excluded": True,
    }])
    return (primary, annual_frame, pd.DataFrame(attribution), loo_frame,
            stress_frame, phase_frame, pd.DataFrame(regimes), boot, summary,
            audit, coverage)


if __name__ == "__main__":
    names = ["results", "annual", "attribution", "leave_one_out", "cost_stress",
             "phase_robustness", "regimes", "bootstrap", "summary",
             "target_audit", "coverage"]
    for name, frame in zip(names, run()):
        frame.to_csv(f"real_currency_momentum_2024_2025_{name}.csv", index=False)
        print(name, frame.to_string(index=False))
