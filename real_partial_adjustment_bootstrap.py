"""Stationary-bootstrap uncertainty for the locked partial-adjustment holdout."""
import numpy as np
import pandas as pd

from real_partial_adjustment_holdout import (
    ANN, COST_BPS, HOLDOUT_END, HOLDOUT_START, LAMBDAS, load_prices,
    partial_adjust, sparse_weights, target_weights,
)

N_BOOT = 2000
MEAN_BLOCK = 20
SEED = 20260904


def net_returns():
    prices = load_prices()
    target = target_weights(prices)
    configs = {f"partial_{speed:.2f}": partial_adjust(target, speed)
               for speed in LAMBDAS}
    configs["sparse_20"] = sparse_weights(target)
    returns = np.log(prices).diff()
    out = {}
    for name, weights in configs.items():
        turnover = weights.diff().abs().fillna(weights.abs())
        gross = (weights * returns).mean(axis=1)
        costs = sum(turnover[a] * COST_BPS[a] * 1e-4
                    for a in prices.columns) / len(prices.columns)
        out[name] = (gross - costs).loc[HOLDOUT_START:HOLDOUT_END].dropna()
    return pd.DataFrame(out).dropna()


def stationary_indices(n, n_boot=N_BOOT, mean_block=MEAN_BLOCK, seed=SEED):
    rng = np.random.default_rng(seed)
    indices = np.empty((n_boot, n), dtype=np.int32)
    indices[:, 0] = rng.integers(0, n, size=n_boot)
    restart_prob = 1.0 / mean_block
    for t in range(1, n):
        restart = rng.random(n_boot) < restart_prob
        continuation = (indices[:, t - 1] + 1) % n
        fresh = rng.integers(0, n, size=n_boot)
        indices[:, t] = np.where(restart, fresh, continuation)
    return indices


def run():
    returns = net_returns()
    idx = stationary_indices(len(returns))
    distributions = {}
    rows = []
    for model in returns.columns:
        samples = returns[model].to_numpy()[idx]
        ann_mean = samples.mean(axis=1) * ANN
        sharpe = np.sqrt(ANN) * samples.mean(axis=1) / samples.std(axis=1, ddof=1)
        distributions[model] = (ann_mean, sharpe)
        rows.append({
            "model": model,
            "observed_ann_mean": returns[model].mean() * ANN,
            "observed_sharpe": np.sqrt(ANN) * returns[model].mean() / returns[model].std(),
            "ann_mean_ci_low": np.quantile(ann_mean, 0.025),
            "ann_mean_ci_high": np.quantile(ann_mean, 0.975),
            "sharpe_ci_low": np.quantile(sharpe, 0.025),
            "sharpe_ci_high": np.quantile(sharpe, 0.975),
            "bootstrap_prob_ann_mean_positive": (ann_mean > 0).mean(),
        })

    paired_rows = []
    for model in ["partial_0.50", "partial_0.25", "partial_0.10"]:
        for benchmark in ["partial_1.00", "sparse_20"]:
            mean_diff = distributions[model][0] - distributions[benchmark][0]
            sharpe_diff = distributions[model][1] - distributions[benchmark][1]
            paired_rows.append({
                "model": model,
                "benchmark": benchmark,
                "ann_mean_diff_ci_low": np.quantile(mean_diff, 0.025),
                "ann_mean_diff_ci_high": np.quantile(mean_diff, 0.975),
                "prob_ann_mean_diff_positive": (mean_diff > 0).mean(),
                "sharpe_diff_ci_low": np.quantile(sharpe_diff, 0.025),
                "sharpe_diff_ci_high": np.quantile(sharpe_diff, 0.975),
                "prob_sharpe_diff_positive": (sharpe_diff > 0).mean(),
            })
    return pd.DataFrame(rows), pd.DataFrame(paired_rows)


if __name__ == "__main__":
    summary, paired = run()
    summary.to_csv("real_partial_adjustment_bootstrap_summary.csv", index=False)
    paired.to_csv("real_partial_adjustment_bootstrap_paired.csv", index=False)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print(paired.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
