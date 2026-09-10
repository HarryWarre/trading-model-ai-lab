import numpy as np
import pandas as pd
import pytest

from quant_core.backtest import run_cross_sectional, wide_prices


def panel():
    times = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame({
        "timestamp": [times[0], times[0], times[1], times[1], times[2], times[2]],
        "asset": ["A", "B"] * 3,
        "close": [100.0, 100.0, 110.0, 90.0, 121.0, 81.0],
    })


def test_next_bar_execution_and_history_only_signal():
    seen = []
    def signal(history):
        seen.append(history.index.max())
        return pd.Series({"A": 1.0, "B": -1.0})

    result = run_cross_sectional(panel(), signal)
    assert len(result.decisions) == 2
    assert result.decisions["decision_timestamp"].tolist() == seen
    expected = 0.5 * np.log(110 / 100) - 0.5 * np.log(90 / 100)
    assert result.decisions["gross_log_return"].iloc[0] == pytest.approx(expected)


def test_cost_is_charged_from_initial_trade_and_turnover():
    result = run_cross_sectional(panel(), lambda _: pd.Series({"A": 1, "B": -1}), one_way_cost=0.01)
    assert result.decisions["turnover"].iloc[0] == pytest.approx(1.0)
    assert result.decisions["cost_log_return"].iloc[0] == pytest.approx(0.01)
    assert result.decisions["turnover"].iloc[1] == pytest.approx(0.0)


def test_duplicate_rows_fail_closed():
    duplicated = pd.concat([panel(), panel().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        wide_prices(duplicated)
