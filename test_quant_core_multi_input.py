import pandas as pd

from quant_core.multi_input import linear_price_context_signal


def test_context_is_asset_specific_and_uses_only_seen_rows():
    times = pd.date_range("2024-01-01", periods=3, freq="5min", tz="UTC")
    history = pd.DataFrame(
        [[100, 100], [101, 99], [102, 98]],
        index=times, columns=["A", "B"],
    )
    context = pd.DataFrame(
        [[1.0, -1.0], [2.0, -2.0]],
        index=times[:2], columns=["vix__A", "vix__B"],
    )
    signal = linear_price_context_signal(
        history, context, price_lookback=1, feature_weights={"vix": 1.0}
    )
    assert signal["A"] > signal["B"]


def test_missing_context_is_safe():
    times = pd.date_range("2024-01-01", periods=2, freq="5min", tz="UTC")
    history = pd.DataFrame([[100, 100], [101, 99]], index=times, columns=["A", "B"])
    context = pd.DataFrame(index=times[:1])
    signal = linear_price_context_signal(
        history, context, price_lookback=1, feature_weights={"vix": 1.0}
    )
    assert signal["A"] > 0
    assert signal["B"] < 0
