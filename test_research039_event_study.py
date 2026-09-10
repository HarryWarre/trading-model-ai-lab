import numpy as np
import pandas as pd

from run_research039_event_study import (
    ASSET_FAMILY,
    choose_weights,
    past_standardized_surprise,
)


def test_surprise_uses_only_earlier_events():
    events = pd.DataFrame({
        "category": ["cpi"] * 12,
        "raw_surprise": list(range(11)) + [10_000],
    })
    z = past_standardized_surprise(events)
    expected = (10 - 4.5) / np.std(np.arange(10), ddof=1)
    assert np.isclose(z.iloc[10], expected)
    # The final enormous value cannot change the already-computed event 11.
    assert np.isclose(z.iloc[10], expected)


def test_family_neutral_weights():
    rows = []
    for number, (asset, family) in enumerate(ASSET_FAMILY.items()):
        rows.append({
            "asset": asset, "family": family, "prediction": number,
            "pre_vol": .001 + number * .0001, "realized": .001,
        })
    weights = choose_weights(pd.DataFrame(rows), pd.Series(
        [r["prediction"] for r in rows]
    ))
    assert np.isclose(sum(abs(x) for x in weights.values()), 1.0)
    for family in set(ASSET_FAMILY.values()):
        assert sum(
            weights[asset] != 0 for asset, f in ASSET_FAMILY.items() if f == family
        ) == 2
