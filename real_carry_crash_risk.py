"""Preregistered crash-risk attribution for the locked 2025 FX carry return."""
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

import real_fx_carry_2025 as carry
from real_histdata_2024_confirmation import stationary_indices


VIX_FILE = Path("fred_VIXCLS.csv")
VIX_SHA256 = "6b2cd4028784f69ae160250c3c10dbce88150e125f5fdc18f0c8d43ae557d5a3"
QUANTILES = [0.60, 0.75, 0.90]
MAIN_QUANTILE = 0.75
MIN_HISTORY = 252
BOOTSTRAP_SAMPLES = 5000
BOOTSTRAP_BLOCK = 10
BOOTSTRAP_SEED = 24037
ANN = 252


def load_vix():
    if sha256(VIX_FILE.read_bytes()).hexdigest() != VIX_SHA256:
        raise ValueError("VIXCLS hash mismatch")
    frame = pd.read_csv(VIX_FILE)
    frame.columns = ["date", "vix"]
    frame.date = pd.to_datetime(frame.date)
    frame.vix = pd.to_numeric(frame.vix, errors="coerce")
    frame = frame.dropna().set_index("date").sort_index()
    frame["lagged_vix"] = frame.vix.shift(1)
    for quantile in QUANTILES:
        frame[f"threshold_{int(quantile * 100)}"] = (
            frame.vix.expanding(MIN_HISTORY).quantile(quantile).shift(1)
        )
    return frame


def carry_components():
    opens, scores = carry.build_panel(), carry.load_rates()
    net, spot, accrual, costs, _, _ = carry.simulate(opens, scores)
    gross = spot + accrual
    return net, gross


def align_vix(index):
    vix = load_vix()
    session_dates = index.tz_convert("Etc/GMT+5").tz_localize(None).normalize()
    aligned = vix.reindex(session_dates, method="ffill").set_axis(index)
    if aligned[["lagged_vix", "threshold_75"]].isna().any().any():
        raise ValueError("Missing lagged VIX classification")
    return aligned


def series_metrics(series):
    equity = np.exp(series.cumsum())
    drawdown = equity / equity.cummax() - 1
    std = series.std()
    return {
        "observations": len(series),
        "total_return": equity.iloc[-1] - 1,
        "annualized_mean": series.mean() * ANN,
        "sharpe": np.sqrt(ANN) * series.mean() / std if std > 0 else np.nan,
        "skewness": series.skew(),
        "max_drawdown": drawdown.min(),
    }


def regime_table(net, gross, aligned):
    rows = []
    for quantile in QUANTILES:
        high = aligned.lagged_vix > aligned[f"threshold_{int(quantile * 100)}"]
        for regime, mask in [("low", ~high), ("high", high)]:
            row = {"vix_quantile": quantile, "regime": regime,
                   **series_metrics(net[mask])}
            row["gross_total_return"] = np.exp(gross[mask].sum()) - 1
            row["mean_lagged_vix"] = aligned.loc[mask, "lagged_vix"].mean()
            rows.append(row)
    return pd.DataFrame(rows)


def tail_table(net, aligned):
    rows = []
    for quantile in QUANTILES:
        high = aligned.lagged_vix > aligned[f"threshold_{int(quantile * 100)}"]
        unconditional = high.mean()
        for tail_probability in [0.05, 0.10]:
            tail = net <= net.quantile(tail_probability)
            conditional = high[tail].mean()
            rows.append({
                "vix_quantile": quantile,
                "loss_tail_probability": tail_probability,
                "tail_observations": int(tail.sum()),
                "unconditional_high_vix_share": unconditional,
                "tail_high_vix_share": conditional,
                "high_vix_enrichment": conditional / unconditional,
            })
    return pd.DataFrame(rows)


def bootstrap_difference(net, high):
    values = net.to_numpy(float)
    flags = high.to_numpy(bool)
    idx = stationary_indices(len(values), BOOTSTRAP_SAMPLES * 2, BOOTSTRAP_BLOCK,
                             BOOTSTRAP_SEED)
    sample_values, sample_flags = values[idx], flags[idx]
    high_count = sample_flags.sum(axis=1)
    low_count = (~sample_flags).sum(axis=1)
    valid = (high_count > 0) & (low_count > 0)
    sample_values = sample_values[valid][:BOOTSTRAP_SAMPLES]
    sample_flags = sample_flags[valid][:BOOTSTRAP_SAMPLES]
    high_count = high_count[valid][:BOOTSTRAP_SAMPLES]
    low_count = low_count[valid][:BOOTSTRAP_SAMPLES]
    if len(sample_values) != BOOTSTRAP_SAMPLES:
        raise RuntimeError("Insufficient valid stationary-bootstrap samples")
    high_mean = (sample_values * sample_flags).sum(axis=1) / high_count
    low_mean = (sample_values * (~sample_flags)).sum(axis=1) / low_count
    difference = (high_mean - low_mean) * ANN
    return pd.DataFrame([{
        "samples": BOOTSTRAP_SAMPLES,
        "candidate_samples_drawn": BOOTSTRAP_SAMPLES * 2,
        "expected_block_sessions": BOOTSTRAP_BLOCK,
        "probability_high_mean_below_low": (difference < 0).mean(),
        "annualized_difference_ci_low": np.quantile(difference, .025),
        "annualized_difference_ci_high": np.quantile(difference, .975),
    }])


def run():
    net, gross = carry_components()
    aligned = align_vix(net.index)
    regimes = regime_table(net, gross, aligned)
    tails = tail_table(net, aligned)
    high = aligned.lagged_vix > aligned.threshold_75
    boot = bootstrap_difference(net, high)
    main_regimes = regimes[regimes.vix_quantile == MAIN_QUANTILE].set_index("regime")
    main_tail = tails.query(
        "vix_quantile == @MAIN_QUANTILE and loss_tail_probability == 0.10"
    ).iloc[0]
    skew = net.skew()
    observed_difference = (
        main_regimes.loc["high", "annualized_mean"]
        - main_regimes.loc["low", "annualized_mean"]
    )
    summary = pd.DataFrame([{
        "full_sample_skewness": skew,
        "annualized_high_minus_low_mean": observed_difference,
        "bootstrap_probability_high_below_low":
            boot.iloc[0].probability_high_mean_below_low,
        "bottom_decile_high_vix_enrichment": main_tail.high_vix_enrichment,
        "preregistered_crash_signature_supported": bool(
            skew < 0 and observed_difference < 0
            and boot.iloc[0].probability_high_mean_below_low >= .90
            and main_tail.high_vix_enrichment > 1),
    }])
    coverage = pd.DataFrame([{
        "carry_observations": len(net),
        "classified_observations": int(high.notna().sum()),
        "vix_history_start": str(load_vix().index.min().date()),
        "vix_history_end": str(load_vix().index.max().date()),
        "vix_sha256": VIX_SHA256,
    }])
    return regimes, tails, boot, summary, coverage


if __name__ == "__main__":
    names = ["regimes", "tails", "bootstrap", "summary", "coverage"]
    for name, frame in zip(names, run()):
        frame.to_csv(f"real_carry_crash_risk_{name}.csv", index=False)
        print(name, frame.to_string(index=False))
