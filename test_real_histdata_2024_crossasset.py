import numpy as np
import pandas as pd

import real_histdata_2024_crossasset as model


def test_cost_units():
    idx = pd.date_range("2024-01-01", periods=2, tz="UTC")
    turnover = pd.Series([1.0, 1.0], index=idx)
    fx = model.asset_cost(turnover, pd.Series([1.1, 1.1], index=idx), "EURUSD")
    gold = model.asset_cost(turnover, pd.Series([2000, 2000], index=idx), "XAUUSD")
    assert np.isclose(fx.iloc[0], 4.4e-4 / 1.1)
    assert np.isclose(gold.iloc[0], 10e-4)


def test_all_costs_are_nonnegative_and_lagged():
    daily, _ = model.build_panel()
    _, weights, _, _, costs, _, _ = model.model_asset(daily["EURUSD"], "EURUSD")
    assert (costs >= 0).all()
    assert (weights.iloc[: model.LOOKBACK + 1] == 0).all()


def test_wti_blocker_prevents_confirmatory_pass():
    portfolios, attribution, loo, coverage, bootstrap = model.run()
    summary = model.hypothesis_summary(
        portfolios, attribution, loo, bootstrap, coverage
    ).iloc[0]
    assert not bool(summary.preregistered_test_evaluable)
    assert not bool(summary.preregistered_hypothesis_supported)


def test_bootstrap_is_reproducible():
    x = pd.Series(np.linspace(-0.01, 0.02, 100))
    a = model.bootstrap_positive_mean(x)
    b = model.bootstrap_positive_mean(x)
    pd.testing.assert_frame_equal(a, b)
