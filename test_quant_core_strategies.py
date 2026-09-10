import numpy as np
import pandas as pd

from quant_core.strategies import run_cost_stress, trailing_momentum


def panel():
    times = pd.date_range("2024-01-01", periods=16, freq="5min", tz="UTC")
    rows = []
    for i, timestamp in enumerate(times):
        rows.extend([
            {"timestamp": timestamp, "asset": "A", "close": 100 + i},
            {"timestamp": timestamp, "asset": "B", "close": 100 - i * 0.5},
        ])
    return pd.DataFrame(rows)


def test_momentum_waits_for_lookback():
    history = panel().pivot(index="timestamp", columns="asset", values="close")
    early = trailing_momentum(history.iloc[:5], lookback=12)
    later = trailing_momentum(history, lookback=12)
    assert (early == 0).all()
    assert later["A"] > 0
    assert later["B"] < 0


def test_cost_stress_has_locked_levels():
    result = run_cost_stress(panel(), trailing_momentum, [0.0, 0.01])
    assert result["one_way_cost"].tolist() == [0.0, 0.01]
    assert np.isfinite(result["net_return"]).all()
    assert result.loc[1, "net_return"] <= result.loc[0, "net_return"]
