import numpy as np

from real_reference_cost_stress import run


def test_cost_stress_is_monotonic_and_complete():
    a = run()
    b = run()
    assert a.equals(b)
    assert len(a) == 24
    assert set(a.cost_multiplier) == {0.5, 1.0, 2.0, 4.0}
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
    for _, group in a.groupby(["model", "lookback_days"]):
        group = group.sort_values("cost_multiplier")
        assert group.net_total_return.is_monotonic_decreasing
    assert (a.capacity_status == "not_quantifiable_no_volume").all()
