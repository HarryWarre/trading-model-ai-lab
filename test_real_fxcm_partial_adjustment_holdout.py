from pathlib import Path

import numpy as np

from real_fxcm_partial_adjustment_holdout import (
    hypothesis_summary,
    load_quotes,
    run,
    validate_gzip_csv,
)


def test_archive_validator_rejects_html_disguised_as_gzip():
    bad = Path("fxcm_SPX500_2020.csv.gz")
    try:
        validate_gzip_csv(bad)
    except ValueError as error:
        assert "not a gzip archive" in str(error)
    else:
        raise AssertionError("HTML payload was accepted as gzip")


def test_valid_quotes_and_deterministic_holdout():
    open_mid, close_mid, spread, crossed = load_quotes()
    assert open_mid.shape[1] == close_mid.shape[1] == spread.shape[1] == 4
    assert open_mid.index.equals(close_mid.index)
    assert open_mid.index.equals(spread.index)
    assert (open_mid > 0).all().all() and (close_mid > 0).all().all()
    assert (spread >= 0).all().all()
    assert sum(crossed.values()) >= 0
    a, b = run(), run()
    assert a.equals(b)
    assert len(a) == 8
    assert not a.duplicated(["adjustment_speed", "spread_multiplier"]).any()
    assert np.isfinite(a.select_dtypes(include=[np.number])).all().all()
    assert set(a.oos_start) == {"2020-01-01"}
    assert set(a.oos_end) == {"2020-12-29"}


def test_hypothesis_summary_is_single_complete_row():
    summary = hypothesis_summary(run())
    assert len(summary) == 1
    assert int(summary.partial_configurations.iloc[0]) == 3
