import pandas as pd

import real_epsoft_h1_session_reconstruction as model


def _fixture():
    times = pd.date_range("2021-01-03 17:00", periods=24, freq="h")
    frame = pd.DataFrame({
        "local_timestamp": times,
        "utc_timestamp": times.tz_localize("Etc/GMT+5").tz_convert("UTC"),
        "Open": range(100, 124),
        "High": range(102, 126),
        "Low": range(99, 123),
        "Close": range(101, 125),
        "Volume": 1.0,
    })
    return frame


def test_new_york_17_reconstructs_complete_session():
    daily = model.reconstruct_daily(_fixture(), "new_york_17")
    assert len(daily) == 1
    row = daily.iloc[0]
    assert row.Open == 100
    assert row.High == 125
    assert row.Low == 99
    assert row.Close == 124
    assert row.active_hours == 24


def test_incomplete_session_is_rejected():
    daily = model.reconstruct_daily(_fixture().iloc[:19], "new_york_17")
    assert daily.empty


def test_session_rules_are_explicit():
    frame = _fixture().iloc[:1]
    assert model.session_labels(frame, "new_york_17").iloc[0].hour == 0
    assert model.session_labels(frame, "new_york_00").iloc[0].hour == 0
    assert model.session_labels(frame, "utc_00").iloc[0].hour == 0


def test_costs_are_nonnegative_and_lag_is_applied():
    daily = model.reconstructed_panel("new_york_17")
    _, weights, _, _, costs, _ = model.run_model(daily, model.annualization(daily[model.PAIRS[0]].index))
    assert (costs >= 0).all().all()
    assert (weights.iloc[: model.LOOKBACK + 1] == 0).all().all()


def test_annualization_uses_only_pre_holdout_counts():
    index = pd.DatetimeIndex(
        list(pd.date_range("2019-01-01", periods=10, tz="UTC"))
        + list(pd.date_range("2020-01-01", periods=20, tz="UTC"))
        + list(pd.date_range("2021-01-01", periods=100, tz="UTC"))
    )
    assert model.annualization(index) == 15


def test_preregistered_summary_requires_every_condition():
    results = pd.DataFrame({
        "net_total_return": [0.1, 0.1, 0.1],
        "net_sharpe": [0.6, 0.7, 0.8],
    })
    attribution = pd.DataFrame({
        "asset": ["EURUSD"] * 3 + ["USDJPY"] * 3,
        "net_total_return_standalone": [0.1, 0.1, -0.1, 0.1, 0.1, -0.1],
    })
    summary = model.hypothesis_summary(results, attribution).iloc[0]
    assert bool(summary.preregistered_hypothesis_supported)
