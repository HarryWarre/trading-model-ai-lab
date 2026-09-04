import numpy as np

from real_partial_adjustment_bootstrap import net_returns, run, stationary_indices


def test_stationary_bootstrap_is_reproducible_and_paired():
    r = net_returns()
    i1 = stationary_indices(len(r), n_boot=50)
    i2 = stationary_indices(len(r), n_boot=50)
    assert np.array_equal(i1, i2)
    assert i1.shape == (50, len(r))
    a, ap = run()
    b, bp = run()
    assert a.equals(b) and ap.equals(bp)
    assert len(a) == 5 and len(ap) == 6
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
    assert np.isfinite(ap.select_dtypes(include=[np.number])).all().all()
