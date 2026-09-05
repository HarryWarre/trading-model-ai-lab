import numpy as np
import pandas as pd

import real_histdata_2024_confirmation as model


def _minutes(n=1200):
    timestamp = pd.date_range("2024-01-01 17:00", periods=n, freq="min")
    price = np.linspace(1.1, 1.2, n)
    return pd.DataFrame({
        "timestamp": timestamp,
        "Open": price,
        "High": price + 0.001,
        "Low": price - 0.001,
        "Close": price + 0.0001,
        "Volume": 0,
    })


def test_fixed_est_session_reconstruction():
    daily = model.reconstruct_daily(_minutes(), 17)
    assert len(daily) == 1
    assert daily.iloc[0].minute_count == 1200
    assert daily.iloc[0].Open == 1.1


def test_short_session_is_rejected():
    assert model.reconstruct_daily(_minutes(999), 17).empty


def test_stationary_indices_are_reproducible_and_bounded():
    a = model.stationary_indices(50, 10, 5, 7)
    b = model.stationary_indices(50, 10, 5, 7)
    assert np.array_equal(a, b)
    assert a.min() >= 0 and a.max() < 50


def test_costs_nonnegative_and_signal_is_lagged():
    daily, _ = model.build_panel(17)
    _, weights, _, _, costs, _ = model.run_model(daily)
    assert (costs >= 0).all().all()
    assert (weights.iloc[: model.LOOKBACK + 1] == 0).all().all()
    assert (weights.abs().sum(axis=1) > 0).any()


def test_summary_requires_all_conditions():
    results = pd.DataFrame({"net_total_return": [.1, .2, .3], "net_sharpe": [.6, .7, .8]})
    attribution = pd.DataFrame({
        "asset": ["EURUSD"] * 3 + ["USDJPY"] * 3,
        "net_total_return_standalone": [.1, .1, -.1, .1, .1, -.1],
    })
    bootstrap = pd.DataFrame({"probability_mean_positive": [.96]})
    assert bool(model.hypothesis_summary(results, attribution, bootstrap).iloc[0]["preregistered_hypothesis_supported"])
