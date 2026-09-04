import numpy as np

from real_fxcm_partial_adjustment_holdout import run
from real_fxcm_reality_check import (
    PARTIAL_SPEEDS,
    daily_net_return_panel,
    decision,
    run_reality_check,
    stationary_indices,
)


def test_daily_panel_exactly_reconciles_research_015():
    panel = daily_net_return_panel()
    prior = run().query("spread_multiplier == 2.0").set_index("adjustment_speed")
    assert list(panel.columns) == [1.0, 0.5, 0.25, 0.10]
    for speed in panel.columns:
        total = np.exp(panel[speed].sum()) - 1.0
        assert np.isclose(total, prior.loc[speed, "net_total_return"], atol=1e-12)


def test_stationary_indices_are_valid_and_deterministic():
    a = stationary_indices(305, 10, np.random.default_rng(7))
    b = stationary_indices(305, 10, np.random.default_rng(7))
    assert np.array_equal(a, b)
    assert len(a) == 305
    assert a.min() >= 0 and a.max() < 305


def test_reality_check_shapes_and_repeatability():
    ga, ma = run_reality_check(bootstraps=100, seed=99)
    gb, mb = run_reality_check(bootstraps=100, seed=99)
    assert ga.equals(gb) and ma.equals(mb)
    assert len(ga) == 3 and len(ma) == 9
    assert set(ma.adjustment_speed) == set(PARTIAL_SPEEDS)
    assert ((ga.reality_check_p_value > 0) & (ga.reality_check_p_value <= 1)).all()
    assert np.isfinite(ma.select_dtypes(include=[np.number])).all().all()
    assert len(decision(ga)) == 1
