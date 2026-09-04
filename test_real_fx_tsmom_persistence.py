import numpy as np
import pandas as pd

from real_fx_tsmom_persistence import run


def test_persistence_run_is_reproducible_and_finite():
    a = pd.DataFrame(run(12))
    b = pd.DataFrame(run(12))
    assert a.equals(b)
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
    assert set(a["model"]) == {"baseline", "persistence_gate"}
    assert (a["oos_observations"] > 1000).all()
