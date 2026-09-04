"""Selection-adjusted inference for FXCM partial-adjustment speed search."""
import numpy as np
import pandas as pd

from real_fxcm_partial_adjustment_holdout import (
    HOLDOUT_YEAR,
    LOOKBACK,
    TARGET_VOL,
    VOL_WINDOW,
    _annualization,
    load_quotes,
    partial_adjust,
)

PARTIAL_SPEEDS = [0.50, 0.25, 0.10]
FULL_SPEED = 1.0
SPREAD_MULTIPLIER = 2.0
BLOCK_LENGTHS = [5, 10, 20]
PRIMARY_BLOCK_LENGTH = 10
BOOTSTRAPS = 5000
SEED = 20260904


def daily_net_return_panel():
    """Reconstruct #28 daily net log returns at 2x observed open spread."""
    open_mid, close_mid, half_spread, _ = load_quotes()
    ann = _annualization(open_mid.index)
    close_returns = np.log(close_mid).diff()
    vol = close_returns.rolling(VOL_WINDOW).std() * np.sqrt(ann)
    score = np.log(close_mid / close_mid.shift(LOOKBACK))
    target = (np.sign(score) * (TARGET_VOL / vol.clip(lower=0.02))).clip(-1, 1)
    forward_open_return = np.log(open_mid.shift(-1) / open_mid)
    is_oos = open_mid.index.year == HOLDOUT_YEAR
    out = {}
    for speed in [FULL_SPEED] + PARTIAL_SPEEDS:
        weights = partial_adjust(target, speed)
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = (weights * forward_open_return).mean(axis=1)
        spread_cost = (turnover * half_spread / open_mid).mean(axis=1)
        out[speed] = gross - SPREAD_MULTIPLIER * spread_cost
    return pd.concat(out, axis=1).loc[is_oos].dropna()


def stationary_indices(n, expected_block_length, rng):
    """Politis-Romano stationary-bootstrap index path with circular wrapping."""
    indices = np.empty(n, dtype=int)
    indices[0] = rng.integers(n)
    restart_probability = 1.0 / expected_block_length
    for t in range(1, n):
        if rng.random() < restart_probability:
            indices[t] = rng.integers(n)
        else:
            indices[t] = (indices[t - 1] + 1) % n
    return indices


def run_reality_check(bootstraps=BOOTSTRAPS, seed=SEED):
    panel = daily_net_return_panel()
    differential = panel[PARTIAL_SPEEDS].subtract(panel[FULL_SPEED], axis=0)
    values = differential.to_numpy()
    n = len(values)
    means = values.mean(axis=0)
    scales = values.std(axis=0, ddof=1)
    observed_t = np.sqrt(n) * means / scales
    centered = values - means
    # Annualization must come from the pre-holdout archive, not the sliced
    # 2020 panel (which intentionally contains no pre-holdout rows).
    ann = _annualization(load_quotes()[0].index)
    global_rows, model_rows = [], []

    for block in BLOCK_LENGTHS:
        rng = np.random.default_rng(seed + block)
        bootstrap_max_t = np.empty(bootstraps)
        bootstrap_means = np.empty((bootstraps, len(PARTIAL_SPEEDS)))
        for b in range(bootstraps):
            indices = stationary_indices(n, block, rng)
            bootstrap_means[b] = values[indices].mean(axis=0)
            null_mean = centered[indices].mean(axis=0)
            bootstrap_max_t[b] = np.max(np.sqrt(n) * null_mean / scales)

        observed_max_t = float(np.max(observed_t))
        p_value = (1 + np.sum(bootstrap_max_t >= observed_max_t)) / (bootstraps + 1)
        global_rows.append({
            "expected_block_length": block,
            "observations": n,
            "models_compared": len(PARTIAL_SPEEDS),
            "bootstrap_samples": bootstraps,
            "observed_max_t": observed_max_t,
            "reality_check_p_value": p_value,
            "reject_global_null_5pct": bool(p_value < 0.05),
        })
        for j, speed in enumerate(PARTIAL_SPEEDS):
            low, high = np.quantile(bootstrap_means[:, j] * ann, [0.025, 0.975])
            model_rows.append({
                "expected_block_length": block,
                "adjustment_speed": speed,
                "annualized_mean_log_return_difference": means[j] * ann,
                "observed_studentized_t": observed_t[j],
                "bootstrap_95pct_low": low,
                "bootstrap_95pct_high": high,
                "ci_excludes_zero": bool(low > 0 or high < 0),
            })
    return pd.DataFrame(global_rows), pd.DataFrame(model_rows)


def decision(global_results):
    primary = global_results.loc[
        global_results.expected_block_length == PRIMARY_BLOCK_LENGTH,
        "reality_check_p_value",
    ].iloc[0]
    robust = bool((global_results.reality_check_p_value < 0.05).all())
    return pd.DataFrame([{
        "primary_block_length": PRIMARY_BLOCK_LENGTH,
        "primary_adjusted_p_value": primary,
        "all_block_lengths_below_5pct": robust,
        "selection_adjusted_superiority_supported": robust,
    }])


if __name__ == "__main__":
    global_result, model_result = run_reality_check()
    final_decision = decision(global_result)
    global_result.to_csv("real_fxcm_reality_check_global.csv", index=False)
    model_result.to_csv("real_fxcm_reality_check_models.csv", index=False)
    final_decision.to_csv("real_fxcm_reality_check_decision.csv", index=False)
    print(global_result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nModel intervals")
    print(model_result.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("\nDecision")
    print(final_decision.to_string(index=False))
