import numpy as np

from real_reference_regime_analysis import regimes, run


def test_regimes_are_point_in_time_and_complete():
    s = regimes().dropna()
    assert set(s.unique()) == {
        "low_vol_up", "low_vol_down", "high_vol_up", "high_vol_down"
    }
    a = run()
    b = run()
    assert a.equals(b)
    assert len(a) == 24
    assert (a.observations > 20).all()
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
