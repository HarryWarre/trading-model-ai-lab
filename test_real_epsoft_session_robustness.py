import numpy as np

from real_epsoft_session_robustness import (
    SESSION_RULES,
    apply_session_rule,
    hypothesis_summary,
    load_ohlc,
    run,
)
from real_epsoft_speed_ensemble import run as run_research_017


def test_session_filters_have_expected_structure():
    raw = load_ohlc()
    calendar = apply_session_rule(raw, "calendar_all")
    active = apply_session_rule(raw, "nonzero_range")
    full = apply_session_rule(raw, "full_session")
    assert len(calendar["EURUSD"]) > len(active["EURUSD"]) > len(full["EURUSD"])
    assert not (active["EURUSD"].High == active["EURUSD"].Low).any()
    assert set(full["EURUSD"].index.dayofweek).issubset({6, 0, 1, 2, 3})


def test_calendar_variant_reconciles_research_017():
    result, _ = run()
    prior, _ = run_research_017()
    current = result.set_index("session_rule").loc["calendar_all", "net_total_return"]
    expected = prior.set_index(["model", "cost_pips"]).loc[("full", 4.4), "net_total_return"]
    assert np.isclose(current, expected, atol=1e-12)


def test_session_robustness_complete_and_deterministic():
    ra, aa = run()
    rb, ab = run()
    assert ra.equals(rb) and aa.equals(ab)
    assert len(ra) == 3 and len(aa) == 6
    assert set(ra.session_rule) == set(SESSION_RULES)
    assert np.isfinite(ra.select_dtypes(include=[np.number])).all().all()
    assert np.isfinite(aa.select_dtypes(include=[np.number])).all().all()
    assert len(hypothesis_summary(ra, aa)) == 1
