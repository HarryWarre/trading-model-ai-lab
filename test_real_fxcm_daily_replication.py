import numpy as np
import pandas as pd

from real_fxcm_daily_replication import load_prices, run


def test_fxcm_data_quality_and_replication():
    prices = load_prices()
    assert list(prices.columns) == ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY"]
    assert prices.index.is_monotonic_increasing
    assert not prices.index.has_duplicates
    assert prices.notna().all().all()
    a = pd.DataFrame(run(5))
    b = pd.DataFrame(run(5))
    assert a.equals(b)
    assert np.isfinite(a.drop(columns=["breakeven_cost_pips"]).select_dtypes("number")).all().all()
    assert (a.oos_observations > 500).all()
