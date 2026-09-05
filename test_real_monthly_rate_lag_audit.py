import numpy as np
import pandas as pd

import real_monthly_rate_lag_audit as audit


def test_two_complete_months_maps_january_to_april():
    observation = pd.Timestamp("2024-01-01")
    assert observation + pd.offsets.MonthBegin(2) == pd.Timestamp("2024-03-01")
    assert observation + pd.offsets.MonthBegin(3) == pd.Timestamp("2024-04-01")


def test_corrected_panel_is_exactly_one_month_later():
    old, corrected = audit.load_rates(2), audit.load_rates(3)
    assert old.shape == corrected.shape
    assert all(new == old_date + pd.offsets.MonthBegin(1)
               for old_date, new in zip(old.index, corrected.index))
    assert np.allclose(old.to_numpy(), corrected.to_numpy(), equal_nan=True)


def test_corrected_scores_are_available_for_both_samples():
    corrected = audit.load_rates(3)
    opens24 = audit.value24.build_2024_opens()
    opens25 = audit.carry.build_panel()
    for opens in [opens24, opens25]:
        aligned = corrected.reindex(opens.index.tz_localize(None), method="ffill")
        assert not aligned[audit.carry.ASSETS].isna().any().any()


def test_audit_reuses_locked_cost_and_value_horizon():
    assert audit.carry.PIP_COST == 4.4
    assert audit.value25.LOOKBACK_MONTHS == 60
