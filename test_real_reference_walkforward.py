import numpy as np

from real_reference_walkforward import run, summarize


def test_walkforward_complete_and_deterministic():
    a = run()
    b = run()
    assert a.equals(b)
    assert len(a) == 72
    assert set(a.entity) == {"SP500", "WTI", "portfolio"}
    assert set(a.test_year) == {2016, 2017, 2018, 2019}
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
    s = summarize(a)
    assert len(s) == 6
    assert s.positive_year_fraction.between(0, 1).all()
