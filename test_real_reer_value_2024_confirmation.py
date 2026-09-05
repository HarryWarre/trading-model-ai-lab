import numpy as np

import real_reer_value_2024_confirmation as model


def test_2024_hash_locked_panel_has_all_registered_assets():
    opens = model.build_2024_opens()
    assert list(opens.columns) == model.ASSETS
    assert not opens.isna().any().any()
    assert opens.index.is_monotonic_increasing


def test_replication_uses_frozen_reer_model_constants():
    assert model.value_model.LOOKBACK_MONTHS == 60
    assert model.carry.PIP_COST == 4.4
    assert model.BOOTSTRAP_SAMPLES == 5000
    assert model.BOOTSTRAP_BLOCK == 10


def test_primary_and_prior_periods_do_not_overlap():
    opens24 = model.build_2024_opens()
    opens25 = model.carry.build_panel()
    assert opens24.index.max() < opens25.index.min()


def test_bootstrap_is_reproducible():
    series = model.build_2024_opens().EURUSD.pct_change().dropna()
    first = model.bootstrap(series, model.BOOTSTRAP_SEED)
    second = model.bootstrap(series, model.BOOTSTRAP_SEED)
    for key in first:
        if isinstance(first[key], float):
            assert np.isclose(first[key], second[key])
        else:
            assert first[key] == second[key]
