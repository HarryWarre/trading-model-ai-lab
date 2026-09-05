import numpy as np
import pandas as pd

import real_cftc_speculative_pressure as model


def test_target_is_market_neutral_and_gross_one():
    scores = pd.Series(dict(zip(model.ASSETS, range(6))))
    target = model.target_from_scores(scores)
    assert np.isclose(target.sum(), 0.0)
    assert np.isclose(target.abs().sum(), 1.0)
    assert (target > 0).sum() == 2 and (target < 0).sum() == 2


def test_release_lag_and_jpy_inversion():
    frame = model.load_positioning()
    assert (frame.release_date - frame.report_date == pd.Timedelta(days=3)).all()
    assert set(model.ASSETS).issubset(set(frame.asset))


def test_holdout_and_outputs():
    results, attribution, loo, boot, summary, stress, regimes = model.run()
    assert results.iloc[0].start.startswith("2024-")
    assert results.iloc[0].end.startswith("2024-")
    assert len(attribution) == len(model.ASSETS)
    assert len(loo) == len(model.ASSETS)
    assert 0 <= boot.iloc[0].probability_mean_positive <= 1
    assert summary.iloc[0].positive_leave_one_out <= len(model.ASSETS)
    assert stress.cost_multiplier_vs_locked.tolist() == [0.0, 0.5, 1.0, 2.0]
    assert set(regimes.regime) == {"spx_trailing_up", "spx_trailing_down"}
