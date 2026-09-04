"""Statistical utilities for Research 001.

These functions are deliberately small and dependency-light. They do not
replace a full econometrics package; they make the validation assumptions
explicit and reproducible.
"""
import numpy as np


def newey_west_mean_tstat(x, lags=None):
    """HAC t-statistic for the mean of a return series."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return np.nan
    if lags is None:
        lags = max(1, int(4 * (n / 100) ** (2 / 9)))
    centered = x - x.mean()
    gamma0 = np.dot(centered, centered) / n
    hac = gamma0
    for lag in range(1, min(lags, n - 1) + 1):
        gamma = np.dot(centered[lag:], centered[:-lag]) / n
        hac += 2 * (1 - lag / (lags + 1)) * gamma
    se = np.sqrt(max(hac, 0) / n)
    return x.mean() / se if se > 0 else np.nan


def moving_block_bootstrap_mean(x, block_size, repetitions=2_000, seed=42):
    """Bootstrap means while preserving local serial dependence."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n == 0 or block_size < 1:
        return np.array([])
    rng = np.random.default_rng(seed)
    starts = np.arange(max(1, n - block_size + 1))
    out = np.empty(repetitions)
    blocks_needed = int(np.ceil(n / block_size))
    for j in range(repetitions):
        sample = np.concatenate([x[s:s + block_size] for s in rng.choice(starts, blocks_needed)])[:n]
        out[j] = sample.mean()
    return out


def time_block_placebo(x, block_size, seed=42):
    """Shuffle complete blocks to preserve within-block dependence."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if block_size < 1 or n == 0:
        return x.copy()
    rng = np.random.default_rng(seed)
    blocks = [x[i:i + block_size] for i in range(0, n, block_size)]
    rng.shuffle(blocks)
    return np.concatenate(blocks)[:n]
