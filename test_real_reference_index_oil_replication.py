import numpy as np
import pandas as pd

from real_reference_index_oil_replication import load_prices, run


def test_reference_data_and_reproducibility():
    p = load_prices()
    assert list(p.columns) == ["SP500", "WTI"]
    assert p.index.is_monotonic_increasing
    assert not p.index.has_duplicates
    assert (p > 0).all().all()
    a = pd.DataFrame(run(10))
    b = pd.DataFrame(run(10))
    assert a.equals(b)
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
    assert (a.oos_observations > 300).all()
