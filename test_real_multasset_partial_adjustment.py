import numpy as np

from real_multasset_partial_adjustment import load_prices, run


def test_multasset_partial_adjustment_complete():
    prices = load_prices()
    assert list(prices.columns) == ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    assert prices.index.is_monotonic_increasing
    assert not prices.index.has_duplicates
    assert prices.notna().all().all()
    a = run()
    b = run()
    assert a.equals(b)
    assert len(a) == 12
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
