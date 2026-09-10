import pandas as pd

from quant_core.backtest import run_cross_sectional_with_context


def prices():
    times = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame({
        "timestamp": [times[0], times[0], times[1], times[1], times[2], times[2]],
        "asset": ["A", "B"] * 3,
        "close": [100.0, 100.0, 101.0, 99.0, 102.0, 98.0],
    })


def test_context_signal_never_sees_future_rows():
    times = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    context = pd.DataFrame({
        "timestamp": [times[0], times[2]],
        "vix": [20.0, 40.0],
    })
    seen = []

    def signal(history, context_history):
        seen.append((history.index.max(), context_history.index.max() if len(context_history) else None))
        return pd.Series({"A": 1.0, "B": -1.0})

    result = run_cross_sectional_with_context(prices(), context, signal)
    assert seen[0][1] == times[0]
    assert seen[1][1] == times[0]
    assert result.decisions["context_rows_available"].tolist() == [1, 1]


def test_context_duplicate_timestamps_fail_closed():
    times = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    context = pd.DataFrame({"timestamp": [times[0], times[0]], "vix": [20, 21]})
    try:
        run_cross_sectional_with_context(prices(), context, lambda *_: pd.Series({"A": 1, "B": -1}))
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate context was accepted")
