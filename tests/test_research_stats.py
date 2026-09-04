import numpy as np
from research_stats import newey_west_mean_tstat, moving_block_bootstrap_mean, time_block_placebo


def test_statistics_are_finite_and_shape_safe():
    x = np.sin(np.arange(300) / 8) + 0.05
    assert np.isfinite(newey_west_mean_tstat(x, lags=8))
    boot = moving_block_bootstrap_mean(x, block_size=12, repetitions=100, seed=7)
    assert boot.shape == (100,)
    placebo = time_block_placebo(x, block_size=12, seed=7)
    assert placebo.shape == x.shape
    assert np.isclose(placebo.mean(), x.mean())


if __name__ == '__main__':
    test_statistics_are_finite_and_shape_safe()
    print('Research statistics tests passed')
