import numpy as np
import pandas as pd

from real_xauusd_h4_cfd_replication import load_prices, run


def test_xau_data_quality_and_reproducibility():
    p = load_prices()
    assert p.index.is_monotonic_increasing
    assert not p.index.has_duplicates
    assert p.notna().all()
    a = pd.DataFrame(run(12))
    b = pd.DataFrame(run(12))
    assert a.equals(b)
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
    assert (a.oos_observations > 1000).all()
