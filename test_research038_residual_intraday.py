import numpy as np
import pandas as pd

from research038_residual_intraday import choose_weights, stationary_bootstrap_probability


def test_family_cap_and_gross_exposure():
    assets = ["AUDUSD", "EURJPY", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD",
              "USDCHF", "USDJPY", "GRXEUR", "NSXUSD", "SPXUSD", "UKXGBP",
              "BCOUSD", "XAGUSD", "XAUUSD"]
    families = ["fx"] * 8 + ["equity"] * 4 + ["commodity"] * 3
    frame = pd.DataFrame({"asset": assets, "family": families,
                          "p": np.arange(15), "vol120": np.linspace(.001, .003, 15),
                          "realized": .001})
    w = choose_weights(frame, "p", 0.0)
    assert np.isclose(sum(abs(x) for x in w.values()), 1.0)
    for family in set(families):
        assert sum(w[a] != 0 for a, f in zip(assets, families) if f == family) == 2


def test_abstention():
    frame = pd.DataFrame({"asset": ["AUDUSD"] * 10, "family": ["fx"] * 10,
                          "p": 0.0, "vol120": .001, "realized": .001})
    assert all(v == 0 for v in choose_weights(frame, "p", 1.0).values())


def test_stationary_bootstrap_sign():
    p, ci = stationary_bootstrap_probability(np.full(100, .001), samples=100)
    assert p == 1.0 and ci[0] > 0
