import numpy as np
import pandas as pd

from real_fx_tsmom_sparse_rebalance import run


def test_sparse_rebalance_is_deterministic_and_lower_turnover():
    x = pd.DataFrame(run(12))
    y = pd.DataFrame(run(12))
    assert x.equals(y)
    assert np.isfinite(x.drop(columns=["breakeven_cost_pips"]).select_dtypes("number")).all().all()
    assert x.loc[x.model == "sparse", "annualized_turnover"].iloc[0] < x.loc[x.model == "continuous", "annualized_turnover"].iloc[0]
