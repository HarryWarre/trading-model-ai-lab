import numpy as np
import pandas as pd
import pytest

from real_fomc_crossfamily_jumps import block_bootstrap, controls_for_asset, jump_bps


def test_exact_quote_boundaries_and_missing():
    t = pd.Timestamp("2024-01-31T19:00:00Z")
    bars = pd.DataFrame({"EURUSD": [1., 1.01]}, index=[t-pd.Timedelta(minutes=5), t+pd.Timedelta(minutes=5)])
    assert np.isclose(jump_bps(bars,"EURUSD",t), 1e4 * np.log(1.01))
    with pytest.raises(ValueError, match="missing exact"):
        jump_bps(bars.drop(t+pd.Timedelta(minutes=5)),"EURUSD",t)


def test_dst_preserves_2pm_local_and_controls_are_past_only():
    t = pd.Timestamp("2024-03-20T18:00:00Z")
    before = (t.tz_convert("America/New_York")-pd.DateOffset(weeks=1)).tz_convert("UTC")
    assert before == pd.Timestamp("2024-03-13T18:00:00Z")
    assert before < t


def test_block_bootstrap_deterministic():
    x = np.array([2., -1., 3., 0., 1.])
    assert block_bootstrap(x) == block_bootstrap(x)
