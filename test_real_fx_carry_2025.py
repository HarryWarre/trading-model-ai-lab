import numpy as np

import real_fx_carry_2025 as model


def test_rate_lag_and_quote_directions():
    scores = model.load_rates()
    assert (scores.index.day == 1).all()
    # A January observation is first eligible in March by construction.
    assert scores.loc["2025-03-01"].notna().all()
    assert np.isfinite(scores.loc["2025-03-01", "USDJPY"])


def test_weights_are_market_neutral():
    opens = model.build_panel()
    weights, _ = model.targets(model.load_rates(), opens.index)
    active = weights.abs().sum(axis=1) > 0
    assert np.allclose(weights.loc[active].sum(axis=1), 0)
    assert np.allclose(weights.loc[active].abs().sum(axis=1), 1)


def test_holdout_outputs():
    main, attribution, loo, stress, regimes, boot, summary = model.run()
    assert main.iloc[0].start.startswith("2025-01")
    assert main.iloc[0].end.startswith("2025-")
    assert len(attribution) == 4 and len(loo) == 4
    assert stress.cost_multiplier_vs_locked.tolist() == [0.0, 0.5, 1.0, 2.0]
    assert set(regimes.regime) == {
        "low_usdjpy_vol", "high_usdjpy_vol", "warmup_unclassified"
    }
    assert 0 <= boot.iloc[0].probability_mean_positive <= 1
    assert summary.iloc[0].positive_leave_one_out <= 4
