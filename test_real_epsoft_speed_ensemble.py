import numpy as np

from real_epsoft_speed_ensemble import (
    cross_source_validation,
    hypothesis_summary,
    load_prices,
    run,
)


def test_source_data_quality_and_holdout_coverage():
    open_prices, close_prices = load_prices()
    assert list(open_prices.columns) == ["EURUSD", "USDJPY"]
    assert open_prices.index.equals(close_prices.index)
    assert open_prices.index.is_monotonic_increasing
    assert not open_prices.index.has_duplicates
    assert (open_prices > 0).all().all() and (close_prices > 0).all().all()
    assert str(open_prices.index[-1].date()) == "2023-02-28"


def test_ensemble_run_is_complete_finite_and_deterministic():
    ra, aa = run()
    rb, ab = run()
    assert ra.equals(rb) and aa.equals(ab)
    assert len(ra) == 4 and len(aa) == 8
    assert not ra.duplicated(["model", "cost_pips"]).any()
    assert set(ra.model) == {"full", "ensemble"}
    assert set(ra.cost_pips) == {2.2, 4.4}
    assert np.isfinite(ra.select_dtypes(include=[np.number])).all().all()
    assert np.isfinite(aa.select_dtypes(include=[np.number])).all().all()
    assert set(ra.oos_start) == {"2021-01-01"}
    assert set(ra.oos_end) == {"2023-02-27"}


def test_hypothesis_summary_is_complete():
    results, _ = run()
    summary = hypothesis_summary(results)
    assert len(summary) == 1
    assert summary.notna().all().all()


def test_pre_holdout_feed_crosscheck_is_strong():
    crosscheck = cross_source_validation()
    assert len(crosscheck) == 2
    assert (crosscheck.overlap_observations >= 1200).all()
    assert (crosscheck.same_date_return_correlation > 0.90).all()
