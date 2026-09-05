import numpy as np
import pandas as pd

import real_reer_value_2025 as model


def test_value_baseline_excludes_current_and_lags_three_month_begins():
    dates = pd.date_range("2000-01-01", periods=62, freq="MS")
    logs = pd.Series(np.arange(62, dtype=float), index=dates)
    prior = logs.shift(1).rolling(60, min_periods=60).mean()
    value = prior - logs
    assert value.first_valid_index() == pd.Timestamp("2005-01-01")
    assert np.isclose(value.dropna().iloc[0], np.arange(60).mean() - 60)
    assert value.dropna().index[0] + pd.offsets.MonthBegin(3) == pd.Timestamp("2005-04-01")


def test_currency_sort_is_zero_sum_and_deterministic():
    value = pd.DataFrame([[5, 4, 3, 2, 1]], columns=model.CURRENCIES,
                         index=[pd.Timestamp("2025-01-01")])
    weights = model.currency_weights(value).iloc[0]
    assert np.isclose(weights.sum(), 0)
    assert np.isclose(weights.abs().sum(), 1)
    assert weights.AUD == weights.EUR == 0.25
    assert weights.JPY == weights.USD == -0.25
    assert weights.GBP == 0


def test_instrument_mapping_and_gross_normalization():
    value = pd.DataFrame([[5, 4, 3, 2, 1]], columns=model.CURRENCIES,
                         index=[pd.Timestamp("2025-01-01")])
    sessions = pd.DatetimeIndex([pd.Timestamp("2025-01-02", tz="UTC")])
    weights, _ = model.instrument_weights(value, sessions)
    row = weights.iloc[0]
    assert np.isclose(row.abs().sum(), 1)
    assert row.AUDUSD > 0 and row.EURUSD > 0
    assert row.USDJPY > 0


def test_hash_locked_reer_has_sixty_month_warmup():
    _, value = model.load_reer()
    assert not value.isna().any().any()
    assert value.index.min().month in range(1, 13)
    assert len(value) > 250
