"""Exact 2024 temporal replication of the locked Research 025 REER value model."""
import numpy as np
import pandas as pd

import real_carry_crash_risk as crash
import real_fx_carry_2025 as carry
import real_histdata_2024_crossasset as hist2024
import real_reer_value_2025 as value_model
from real_histdata_2024_confirmation import stationary_indices


ASSETS = carry.ASSETS
ANN = 252
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_BLOCK = 10
BOOTSTRAP_SEED = 26039


def build_2024_opens():
    daily = {
        asset: hist2024.reconstruct_daily(hist2024.load_m1(asset)[0])
        for asset in ASSETS
    }
    common = daily[ASSETS[0]].index
    for asset in ASSETS[1:]:
        common = common.intersection(daily[asset].index)
    return pd.concat({asset: daily[asset].Open.loc[common] for asset in ASSETS}, axis=1)


def bootstrap(series, seed):
    values = series.to_numpy(float)
    idx = stationary_indices(len(values), BOOTSTRAP_SAMPLES, BOOTSTRAP_BLOCK, seed)
    means = values[idx].mean(axis=1)
    return {
        "samples": BOOTSTRAP_SAMPLES,
        "expected_block_sessions": BOOTSTRAP_BLOCK,
        "probability_mean_positive": (means > 0).mean(),
        "annualized_mean_ci_low": np.quantile(means, .025) * ANN,
        "annualized_mean_ci_high": np.quantile(means, .975) * ANN,
    }


def run():
    _, value = value_model.load_reer()
    rates = carry.load_rates()
    opens24, opens25 = build_2024_opens(), carry.build_panel()
    sim24 = value_model.simulate(opens24, value, rates)
    sim25 = value_model.simulate(opens25, value, rates)
    net24, spot24, accrual24, cost24, turn24, weights24, available24 = sim24
    net25 = sim25[0]

    results = []
    for period, net in [("2024_primary", net24), ("2025_prior", net25),
                        ("2024_2025_descriptive", pd.concat([net24, net25]))]:
        results.append({"period": period, **value_model.metrics(net)})
    results[0].update({
        "spot_total_return": np.exp(spot24.sum()) - 1,
        "carry_log_contribution": accrual24.sum(),
        "cost_log_drag": cost24.sum(),
        "annualized_turnover": turn24.sum(axis=1).mean() * ANN,
    })

    forward = np.log(opens24.shift(-1) / opens24)
    rate = rates.reindex(opens24.index.tz_localize(None), method="ffill").set_axis(opens24.index)
    days = ((opens24.index.to_series().shift(-1) - opens24.index.to_series())
            .dt.total_seconds() / 86400.0)
    attribution = []
    for asset in ASSETS:
        component = (weights24[asset] * (forward[asset] + rate[asset] * days / 365.0)
                     - carry.costs(turn24[[asset]], opens24[[asset]])).loc[net24.index]
        attribution.append({"asset": asset, **value_model.metrics(component)})

    loo = []
    for excluded in ASSETS:
        assets = [asset for asset in ASSETS if asset != excluded]
        sample, *_ = value_model.simulate(opens24[assets], value, rates, assets)
        loo.append({"excluded_asset": excluded, **value_model.metrics(sample)})
    loo_frame = pd.DataFrame(loo)

    stress = []
    for multiplier in [0.0, 1.0, 2.0]:
        sample, *_ = value_model.simulate(opens24, value, rates,
                                          cost_multiplier=multiplier)
        stress.append({"cost_multiplier_vs_locked": multiplier,
                       **value_model.metrics(sample)})
    stress_frame = pd.DataFrame(stress)

    aligned = crash.align_vix(net24.index)
    high = aligned.lagged_vix > aligned.threshold_75
    regimes = []
    for name, mask in [("low_vix", ~high), ("high_vix", high)]:
        regimes.append({"regime": name, **value_model.metrics(net24[mask])})

    pooled = pd.concat([net24, net25])
    boot = pd.DataFrame([
        {"period": "2024_primary", **bootstrap(net24, BOOTSTRAP_SEED)},
        {"period": "2024_2025_descriptive", **bootstrap(pooled, BOOTSTRAP_SEED + 1)},
    ])
    positive_loo = int((loo_frame.total_return > 0).sum())
    double_positive = bool(stress_frame.loc[
        stress_frame.cost_multiplier_vs_locked == 2, "total_return"].iloc[0] > 0)
    summary = pd.DataFrame([{
        "positive_2024_net_return": bool(net24.sum() > 0),
        "positive_leave_one_out": positive_loo,
        "bootstrap_probability_positive":
            boot.loc[boot.period == "2024_primary", "probability_mean_positive"].iloc[0],
        "positive_at_double_cost": double_positive,
        "preregistered_confirmation_supported": bool(
            net24.sum() > 0 and positive_loo >= 3
            and boot.loc[boot.period == "2024_primary",
                         "probability_mean_positive"].iloc[0] >= .95
            and double_positive),
    }])
    changed = weights24.ne(weights24.shift()).any(axis=1)
    audit = pd.concat([available24.add_prefix("currency_weight_"),
                       weights24.add_prefix("instrument_weight_")], axis=1).loc[changed]
    coverage = pd.DataFrame([{
        "primary_sessions": len(net24), "prior_sessions": len(net25),
        "pooled_sessions": len(pooled), "primary_target_changes": int(changed.sum()),
        "primary_start": str(net24.index.min().date()),
        "primary_end": str(net24.index.max().date()),
    }])
    return (pd.DataFrame(results), pd.DataFrame(attribution), loo_frame,
            stress_frame, pd.DataFrame(regimes), boot, summary,
            audit.reset_index(), coverage)


if __name__ == "__main__":
    names = ["results", "attribution", "leave_one_out", "cost_stress", "regimes",
             "bootstrap", "summary", "target_audit", "coverage"]
    for name, frame in zip(names, run()):
        frame.to_csv(f"real_reer_value_2024_confirmation_{name}.csv", index=False)
        print(name, frame.to_string(index=False))
