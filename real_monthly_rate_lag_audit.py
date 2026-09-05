"""Audit m+2 versus conservative m+3 monthly-rate availability."""
import numpy as np
import pandas as pd

import real_fx_carry_2025 as carry
import real_reer_value_2025 as value25
import real_reer_value_2024_confirmation as value24


def load_rates(month_begins):
    rates = []
    for currency, series in carry.RATE_SERIES.items():
        frame = carry.checked_csv(f"fred_{series}.csv", carry.RATE_SHA256[series])
        frame.columns = ["observation_date", "rate"]
        frame.observation_date = pd.to_datetime(frame.observation_date)
        frame.rate = pd.to_numeric(frame.rate, errors="coerce")
        frame["currency"] = currency
        rates.append(frame.dropna())
    wide = pd.concat(rates).pivot(index="observation_date", columns="currency",
                                  values="rate")
    wide.index = wide.index + pd.offsets.MonthBegin(month_begins)
    scores = pd.DataFrame(index=wide.index)
    for asset in ["EURUSD", "GBPUSD", "AUDUSD"]:
        scores[asset] = (wide[asset[:3]] - wide.USD) / 100.0
    scores["USDJPY"] = (wide.USD - wide.JPY) / 100.0
    return scores.sort_index()


def value_checks(opens, value, rates, year):
    net, *_ = value25.simulate(opens, value, rates)
    loo = []
    for excluded in carry.ASSETS:
        assets = [asset for asset in carry.ASSETS if asset != excluded]
        sample, *_ = value25.simulate(opens[assets], value, rates, assets)
        loo.append({"model": f"reer_value_{year}", "excluded_asset": excluded,
                    **value25.metrics(sample)})
    stress = []
    for multiplier in [0.0, 1.0, 2.0]:
        sample, *_ = value25.simulate(opens, value, rates,
                                      cost_multiplier=multiplier)
        stress.append({"model": f"reer_value_{year}",
                       "cost_multiplier_vs_locked": multiplier,
                       **value25.metrics(sample)})
    if year == 2025:
        boot = value25.bootstrap(net).iloc[0].to_dict()
    else:
        boot = value24.bootstrap(net, value24.BOOTSTRAP_SEED)
    positive_loo = sum(row["total_return"] > 0 for row in loo)
    double_return = next(row["total_return"] for row in stress
                         if row["cost_multiplier_vs_locked"] == 2.0)
    supported = bool(net.sum() > 0 and positive_loo >= 3
                     and boot["probability_mean_positive"] >= .95
                     and double_return > 0)
    return net, loo, stress, boot, supported


def run():
    old_rates, corrected_rates = load_rates(2), load_rates(3)
    opens25, opens24 = carry.build_panel(), value24.build_2024_opens()
    _, value = value25.load_reer()

    old_carry = carry.simulate(opens25, old_rates)
    new_carry = carry.simulate(opens25, corrected_rates)
    old_carry_net, new_carry_net = old_carry[0], new_carry[0]
    carry_loo = []
    for excluded in carry.ASSETS:
        assets = [asset for asset in carry.ASSETS if asset != excluded]
        sample, *_ = carry.simulate(opens25[assets], corrected_rates, assets)
        carry_loo.append({"model": "carry_2025", "excluded_asset": excluded,
                          **carry.metrics(sample)})
    carry_stress = []
    for multiplier in [0.0, 1.0, 2.0]:
        sample, *_ = carry.simulate(opens25, corrected_rates,
                                    cost_multiplier=multiplier)
        carry_stress.append({"model": "carry_2025",
                             "cost_multiplier_vs_locked": multiplier,
                             **carry.metrics(sample)})
    carry_boot = carry.bootstrap(new_carry_net).iloc[0].to_dict()
    carry_positive_loo = sum(row["total_return"] > 0 for row in carry_loo)
    carry_supported = bool(new_carry_net.sum() > 0 and carry_positive_loo >= 3
                           and carry_boot["probability_mean_positive"] >= .95)

    old_v25 = value25.simulate(opens25, value, old_rates)[0]
    new_v25, loo25, stress25, boot25, support25 = value_checks(
        opens25, value, corrected_rates, 2025)
    old_v24 = value25.simulate(opens24, value, old_rates)[0]
    new_v24, loo24, stress24, boot24, support24 = value_checks(
        opens24, value, corrected_rates, 2024)

    pairs = [
        ("carry_2025", old_carry_net, new_carry_net),
        ("reer_value_2025", old_v25, new_v25),
        ("reer_value_2024", old_v24, new_v24),
    ]
    comparison = []
    for model, old, new in pairs:
        old_m, new_m = value25.metrics(old), value25.metrics(new)
        delta = new - old
        comparison.append({
            "model": model, "old_m_plus_2_return": old_m["total_return"],
            "corrected_m_plus_3_return": new_m["total_return"],
            "return_difference": new_m["total_return"] - old_m["total_return"],
            "old_sharpe": old_m["sharpe"], "corrected_sharpe": new_m["sharpe"],
            "sharpe_difference": new_m["sharpe"] - old_m["sharpe"],
            "changed_daily_returns": int((delta.abs() > 1e-15).sum()),
            "max_absolute_daily_return_change": delta.abs().max(),
        })

    old_weights, new_weights = old_carry[5], new_carry[5]
    target_diff = pd.DataFrame([{
        "carry_sessions": len(old_weights),
        "sessions_with_any_target_difference": int(
            old_weights.ne(new_weights).any(axis=1).sum()),
        "maximum_absolute_weight_difference":
            (old_weights - new_weights).abs().to_numpy().max(),
    }])

    boot = pd.DataFrame([
        {"model": "carry_2025", **carry_boot},
        {"model": "reer_value_2025", **boot25},
        {"model": "reer_value_2024", **boot24},
    ])
    loo = pd.DataFrame(carry_loo + loo25 + loo24)
    stress = pd.DataFrame(carry_stress + stress25 + stress24)
    summary = pd.DataFrame([
        {"model": "carry_2025", "corrected_net_positive": new_carry_net.sum() > 0,
         "corrected_positive_leave_one_out": carry_positive_loo,
         "corrected_bootstrap_probability_positive":
             carry_boot["probability_mean_positive"],
         "corrected_double_cost_positive": np.nan,
         "original_decision_rejected": True,
         "corrected_support_criteria_met": carry_supported},
        {"model": "reer_value_2025", "corrected_net_positive": new_v25.sum() > 0,
         "corrected_positive_leave_one_out": sum(r["total_return"] > 0 for r in loo25),
         "corrected_bootstrap_probability_positive": boot25["probability_mean_positive"],
         "corrected_double_cost_positive": next(r["total_return"] > 0 for r in stress25
                                                   if r["cost_multiplier_vs_locked"] == 2),
         "original_decision_rejected": True,
         "corrected_support_criteria_met": support25},
        {"model": "reer_value_2024", "corrected_net_positive": new_v24.sum() > 0,
         "corrected_positive_leave_one_out": sum(r["total_return"] > 0 for r in loo24),
         "corrected_bootstrap_probability_positive": boot24["probability_mean_positive"],
         "corrected_double_cost_positive": next(r["total_return"] > 0 for r in stress24
                                                   if r["cost_multiplier_vs_locked"] == 2),
         "original_decision_rejected": True,
         "corrected_support_criteria_met": support24},
    ])
    availability = pd.DataFrame([{
        "example_observation_month": "2024-01-01",
        "historical_m_plus_2_effective": "2024-03-01",
        "corrected_m_plus_3_effective": "2024-04-01",
        "complete_intervening_months_old": 1,
        "complete_intervening_months_corrected": 2,
        "input_type": "FRED current-history, not vintage",
    }])
    return (pd.DataFrame(comparison), summary, loo, stress, boot, target_diff,
            availability)


if __name__ == "__main__":
    names = ["comparison", "summary", "leave_one_out", "cost_stress",
             "bootstrap", "target_diff", "availability"]
    for name, frame in zip(names, run()):
        frame.to_csv(f"real_monthly_rate_lag_audit_{name}.csv", index=False)
        print(name, frame.to_string(index=False))
