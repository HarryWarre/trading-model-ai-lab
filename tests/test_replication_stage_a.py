import numpy as np
import pandas as pd
from replication_stage_a import tsmom_returns, return_attribution, class_equal_weight


def test_replication_outputs_and_attribution():
    idx = pd.date_range('2010-01-31', periods=40, freq='ME', tz='UTC')
    p = pd.DataFrame({'A': np.exp(np.linspace(0, 1, 40)), 'B': np.exp(np.linspace(0.2, -0.3, 40))}, index=idx)
    r = tsmom_returns(p)
    assert r.shape == p.shape
    assert np.isfinite(r.iloc[20:].to_numpy()).all()
    attr = return_attribution(r, r * 0.8, r * 0.1)
    expected = (r * 0.1).loc[attr.index]
    assert np.allclose(attr['residual'].to_numpy(), expected.to_numpy())
    ew = class_equal_weight(r, {'A': 'equity', 'B': 'rates'})
    assert len(ew) == len(r)


if __name__ == '__main__':
    test_replication_outputs_and_attribution()
    print('Stage A replication tests passed')
