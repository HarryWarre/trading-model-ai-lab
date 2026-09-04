import numpy as np

from real_multasset_ramom import paired_comparison, run


def test_ramom_run_is_complete_finite_and_deterministic():
    a = run()
    b = run()
    assert a.equals(b)
    assert len(a) == 24
    assert set(a["signal"]) == {"tsmom", "ramom"}
    assert set(a["lookback_h4"]) == {6, 12, 30}
    assert set(a["adjustment_speed"]) == {1.0, 0.5, 0.25, 0.10}
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()


def test_every_ramom_result_has_one_matched_tsmom_control():
    result = run()
    paired = paired_comparison(result)
    assert len(paired) == 12
    assert not paired.duplicated(["lookback_h4", "adjustment_speed"]).any()
    assert np.isfinite(paired.select_dtypes(include=[np.number])).all().all()
