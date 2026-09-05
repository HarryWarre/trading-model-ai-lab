"""Preregistered two-full-month-lagged REER currency-value test."""
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

import real_carry_crash_risk as crash
import real_fx_carry_2025 as carry
from real_histdata_2024_confirmation import stationary_indices


CURRENCIES = ["AUD", "EUR", "GBP", "JPY", "USD"]
SERIES = {
    "AUD": ("RBAUBIS", "85c04afaa44952d520db7fcc3284b512d76e295957ac934a5187712919e0695f"),
    "EUR": ("RBXMBIS", "8b50a87fa5ca7a10c57adf37edc4b67fb94ad19d492210d4ea6465202a077eb1"),
    "GBP": ("RBGBBIS", "a9f6645fdefc318a369cc619e5d9eef861e8be0f8b4546d698a88792ff82b656"),
    "JPY": ("RBJPBIS", "061af9920f500c9fbe660a40a3bc3a27c13a15e1856e5921cfe51d08dc941dcc"),
    "USD": ("RBUSBIS", "790a309666a797011401b62bc7d34a3d714ef4eb3805cae6c6f3859bbfb0f03a"),
}
LOOKBACK_MONTHS = 60
ANN = 252
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_BLOCK = 10
BOOTSTRAP_SEED = 25038


def load_reer():
    frames = []
    for currency, (series, expected) in SERIES.items():
        path = Path(f"fred_{series}.csv")
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"REER hash mismatch: {series}")
        frame = pd.read_csv(path)
        frame.columns = ["date", "reer"]
        frame.date = pd.to_datetime(frame.date)
        frame.reer = pd.to_numeric(frame.reer, errors="coerce")
        frame["currency"] = currency
        frames.append(frame.dropna())
    wide = (pd.concat(frames).pivot(index="date", columns="currency", values="reer")
            .sort_index()[CURRENCIES])
    logs = np.log(wide)
    prior_mean = logs.shift(1).rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS).mean()
    value = prior_mean - logs
    # January observation becomes usable April 1: February and March fully elapse.
    value.index = value.index + pd.offsets.MonthBegin(3)
    return wide, value.dropna()


def currency_weights(value):
    weights = pd.DataFrame(0.0, index=value.index, columns=CURRENCIES)
    for date, row in value[CURRENCIES].iterrows():
        ordered = row.sort_values(kind="mergesort")
        # Low value = overvalued; high value = undervalued.
        weights.loc[date, ordered.index[:2]] = -0.25
        weights.loc[date, ordered.index[-2:]] = 0.25
    return weights


def instrument_weights(value, sessions, assets=carry.ASSETS):
    cw = currency_weights(value)
    available = cw.reindex(sessions.tz_localize(None), method="ffill").set_axis(sessions)
    weights = pd.DataFrame(index=sessions, columns=carry.ASSETS, dtype=float)
    weights["EURUSD"] = available.EUR
    weights["GBPUSD"] = available.GBP
    weights["AUDUSD"] = available.AUD
    weights["USDJPY"] = -available.JPY
    excluded = [asset for asset in carry.ASSETS if asset not in assets]
    weights[excluded] = 0.0
    gross = weights.abs().sum(axis=1)
    weights = weights.div(gross.where(gross > 0), axis=0).fillna(0.0)
    return weights, available


def simulate(opens, value, carry_scores, assets=carry.ASSETS, cost_multiplier=1.0):
    weights, available = instrument_weights(value, opens.index, assets)
    forward = np.log(opens.shift(-1) / opens)
    spot = (weights[list(assets)] * forward[list(assets)]).sum(axis=1)
    rate = carry_scores.reindex(opens.index.tz_localize(None), method="ffill").set_axis(opens.index)
    calendar_days = ((opens.index.to_series().shift(-1) - opens.index.to_series())
                     .dt.total_seconds() / 86400.0)
    accrual = ((weights[list(assets)] * rate[list(assets)]).sum(axis=1)
               * calendar_days / 365.0)
    turnover = weights.diff().abs().fillna(weights.abs())
    trading_cost = carry.costs(turnover[list(assets)], opens[list(assets)], cost_multiplier)
    active = ((weights[list(assets)].abs().sum(axis=1) > 0)
              & opens[list(assets)].shift(-1).notna().all(axis=1))
    net = (spot + accrual - trading_cost).loc[active]
    return net, spot.loc[active], accrual.loc[active], trading_cost.loc[active], turnover, weights, available


def metrics(series):
    equity = np.exp(series.cumsum())
    drawdown = equity / equity.cummax() - 1
    std = series.std()
    return {
        "observations": len(series), "start": str(series.index[0].date()),
        "end": str(series.index[-1].date()), "total_return": equity.iloc[-1] - 1,
        "annualized_mean": series.mean() * ANN,
        "sharpe": np.sqrt(ANN) * series.mean() / std if std > 0 else np.nan,
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
    opens, carry_scores = carry.build_panel(), carry.load_rates()
    reer, value = load_reer()
    net, spot, accrual, trading_cost, turnover, weights, available = simulate(
        opens, value, carry_scores)
    main = pd.DataFrame([{
        **metrics(net), "spot_total_return": np.exp(spot.sum()) - 1,
        "carry_log_contribution": accrual.sum(), "cost_log_drag": trading_cost.sum(),
        "annualized_turnover": turnover.sum(axis=1).mean() * ANN,
    }])
    forward = np.log(opens.shift(-1) / opens)
    rate = carry_scores.reindex(opens.index.tz_localize(None), method="ffill").set_axis(opens.index)
    days = ((opens.index.to_series().shift(-1) - opens.index.to_series())
            .dt.total_seconds() / 86400.0)
    attribution = []
    for asset in carry.ASSETS:
        component = (weights[asset] * (forward[asset] + rate[asset] * days / 365.0)
                     - carry.costs(turnover[[asset]], opens[[asset]])).loc[net.index]
        attribution.append({"asset": asset, **metrics(component)})
    loo = []
    for excluded in carry.ASSETS:
        assets = [asset for asset in carry.ASSETS if asset != excluded]
        sample, *_ = simulate(opens[assets], value, carry_scores, assets)
        loo.append({"excluded_asset": excluded, **metrics(sample)})
    stress = []
    for multiplier in [0.0, 1.0, 2.0]:
        sample, *_ = simulate(opens, value, carry_scores, cost_multiplier=multiplier)
        stress.append({"cost_multiplier_vs_locked": multiplier, **metrics(sample)})
    aligned = crash.align_vix(net.index)
    high = aligned.lagged_vix > aligned.threshold_75
    regimes = []
    for name, mask in [("low_vix", ~high), ("high_vix", high)]:
        regimes.append({"regime": name, **metrics(net[mask])})
    boot = bootstrap(net)
    loo_frame, stress_frame = pd.DataFrame(loo), pd.DataFrame(stress)
    positive_loo = int((loo_frame.total_return > 0).sum())
    double_cost_positive = bool(
        stress_frame.loc[stress_frame.cost_multiplier_vs_locked == 2.0,
                         "total_return"].iloc[0] > 0)
    summary = pd.DataFrame([{
        "positive_net_return": bool(main.iloc[0].total_return > 0),
        "positive_leave_one_out": positive_loo,
        "bootstrap_probability_positive": boot.iloc[0].probability_mean_positive,
        "positive_at_double_cost": double_cost_positive,
        "preregistered_hypothesis_supported": bool(
            main.iloc[0].total_return > 0 and positive_loo >= 3
            and boot.iloc[0].probability_mean_positive >= .95
            and double_cost_positive),
    }])
    changed = weights.ne(weights.shift()).any(axis=1)
    audit = pd.concat([available.add_prefix("currency_weight_"),
                       weights.add_prefix("instrument_weight_")], axis=1).loc[changed]
    coverage = pd.DataFrame([{
        "reer_history_start": str(reer.index.min().date()),
        "reer_history_end": str(reer.index.max().date()),
        "first_value_effective_date": str(value.index.min().date()),
        "active_sessions": len(net), "target_changes": int(changed.sum()),
    }])
    return (main, pd.DataFrame(attribution), loo_frame, stress_frame,
            pd.DataFrame(regimes), boot, summary, audit.reset_index(), coverage)


if __name__ == "__main__":
    names = ["results", "attribution", "leave_one_out", "cost_stress", "regimes",
             "bootstrap", "summary", "target_audit", "coverage"]
    for name, frame in zip(names, run()):
        frame.to_csv(f"real_reer_value_2025_{name}.csv", index=False)
        print(name, frame.to_string(index=False))
