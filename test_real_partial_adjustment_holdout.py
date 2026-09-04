import numpy as np

from real_partial_adjustment_holdout import load_prices, run


def test_partial_adjustment_holdout_is_complete():
    prices = load_prices()
    assert prices.index.is_monotonic_increasing
    assert not prices.index.has_duplicates
    assert (prices > 0).all().all()
    a, ay = run()
    b, by = run()
    assert a.equals(b) and ay.equals(by)
    assert len(a) == 5 and len(ay) == 25
    assert set(ay.year) == {2021, 2022, 2023, 2024, 2025}
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
