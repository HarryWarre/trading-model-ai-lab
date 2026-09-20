import json
from pathlib import Path

import numpy as np
import pandas as pd

import real_usmpd_statement_pressconference_2023_2025 as m


ROOT = Path(__file__).parent


def test_official_workbook_contract():
    x = m.validate_usmpd(ROOT / "USMPD_2026-09-18.xlsx",
                         ROOT / "data/usmpd_2026-09-18.manifest.json")
    assert len(x) == 279
    assert x.Date.max() == pd.Timestamp("2026-09-16")
    recent = x[x.Date.dt.year.isin([2023, 2024, 2025])]
    assert recent.groupby(recent.Date.dt.year).size().to_dict() == {2023: 8, 2024: 8, 2025: 8}
    assert recent.rate_surprise.notna().all()


def test_economic_rule_is_fixed_and_abstains_on_information_shock():
    base = {"rate_surprise": 0.01, "sp_future": -0.1}
    assert m.economic_signal(pd.Series({**base, "asset": "SPXUSD"})) == -1
    assert m.economic_signal(pd.Series({**base, "asset": "USDJPY"})) == 1
    assert m.economic_signal(pd.Series({**base, "asset": "EURUSD"})) == -1
    assert m.economic_signal(pd.Series({**base, "asset": "EURJPY"})) == 0
    assert m.economic_signal(pd.Series({"rate_surprise": 0.01, "sp_future": 0.1,
                                        "asset": "SPXUSD"})) == 0


def test_bootstrap_is_deterministic():
    a = m.block_probability(np.array([.01, -.02, .03, .04]))
    b = m.block_probability(np.array([.01, -.02, .03, .04]))
    assert a == b


def test_committed_summary_contract():
    p = ROOT / "results/research048/research048_summary.json"
    if not p.exists():
        return
    x = json.loads(p.read_text())
    assert x["usmpd_sha256"] == "f02bfcbf80cf597548d4fccb5a80b30cb1f4373a7d50e26fd1def097d43df1aa"
    assert x["eligible_events"] >= 16
    assert x["fixed_roundtrip_cost_pips"] == 4
    assert set(x["models"]) == {"price_only", "economic", "long", "ridge"}
