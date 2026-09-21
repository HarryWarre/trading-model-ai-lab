from pathlib import Path

import numpy as np
import pandas as pd

from real_usmpd_economic_rule_audit import event_table, exact_sign_flip_p, run


def test_exact_sign_flip_known_case():
    assert exact_sign_flip_p(np.array([1.0, 1.0])) == 0.25


def test_event_table_reweights_after_exclusion():
    trades = pd.DataFrame({
        "event_id": ["e", "e"], "asset": ["a", "b"], "family": ["fx", "fx"],
        "year": [2024, 2024], "invvol": [1.0, 3.0], "signal": [1.0, 1.0],
        "press_return": [0.01, -0.01], "cost_1x": [0.001, 0.001],
    })
    full = event_table(trades, ["e"], 1)
    only_a = event_table(trades[trades.asset == "a"], ["e"], 1)
    assert np.isclose(full.net.iloc[0], -0.006)
    assert np.isclose(only_a.net.iloc[0], 0.009)


def test_full_run_and_hash_fail_closed(tmp_path):
    source = Path("results/research048")
    result = run(source, tmp_path / "out")
    assert result["evaluation_events"] == 12
    assert (tmp_path / "out" / "research049_manifest.json").is_file()
    assert result["decision"] == "research_only_same_inspected_sample"

