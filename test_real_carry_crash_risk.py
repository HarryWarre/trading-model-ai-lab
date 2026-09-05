import numpy as np

import real_carry_crash_risk as model


def test_vix_is_lagged_and_threshold_is_historical():
    vix = model.load_vix()
    valid = vix.dropna()
    first = valid.index[0]
    previous = vix.index[vix.index.get_loc(first) - 1]
    assert np.isclose(vix.loc[first, "lagged_vix"], vix.loc[previous, "vix"])


def test_complete_alignment_and_locked_return():
    net, _ = model.carry_components()
    aligned = model.align_vix(net.index)
    assert len(aligned) == len(net)
    assert aligned[["lagged_vix", "threshold_75"]].notna().all().all()


def test_outputs_and_preregistered_thresholds():
    regimes, tails, boot, summary, coverage = model.run()
    assert set(regimes.vix_quantile) == set(model.QUANTILES)
    assert set(regimes.regime) == {"low", "high"}
    assert set(tails.loss_tail_probability) == {0.05, 0.10}
    assert 0 <= boot.iloc[0].probability_high_mean_below_low <= 1
    assert np.isfinite(boot.iloc[0].annualized_difference_ci_low)
    assert np.isfinite(boot.iloc[0].annualized_difference_ci_high)
    assert len(summary) == 1 and coverage.iloc[0].carry_observations == 258
