import numpy as np
import pandas as pd

from real_fx_scaling_decomposition import run


def test_scaling_decomposition_is_deterministic():
    a = pd.DataFrame(run(12))
    b = pd.DataFrame(run(12))
    assert a.equals(b)
    assert set(a.model) == {
        "unscaled_unit", "vol_scaled_cap_1x", "vol_scaled_cap_3x"
    }
    numeric = a.select_dtypes(include=[np.number]).drop(
        columns=["cap_fraction_oos"]
    )
    assert np.isfinite(numeric).all().all()
    assert np.isnan(a.loc[a.model == "unscaled_unit", "cap_fraction_oos"]).all()


def test_costs_do_not_improve_total_return():
    x = pd.DataFrame(run(12, cost_pips=2.2))
    assert (x.net_total_return <= x.gross_total_return).all()
