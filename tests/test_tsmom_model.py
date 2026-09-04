import numpy as np
import pandas as pd
from tsmom_model import tsmom_position, purged_splits


def test_signal_is_lagged():
    idx = pd.date_range('2020-01-01', periods=200, freq='D', tz='UTC')
    prices = pd.DataFrame({'A': np.exp(np.linspace(0, 1, len(idx)))}, index=idx)
    pos = tsmom_position(prices, lookback=5, vol_window=10)
    assert pos.index.equals(prices.index)
    assert pos.iloc[5, 0] == 0.0  # insufficient volatility history and shifted execution
    assert np.isfinite(pos.to_numpy()).all()


def test_purged_splits_have_embargo():
    idx = pd.date_range('2020-01-01', periods=30, freq='D', tz='UTC')
    splits = list(purged_splits(idx, train_size=10, test_size=5, embargo=2))
    assert splits
    for train, test in splits:
        assert test.start - train.stop == 2
        assert train.stop <= test.start


if __name__ == '__main__':
    test_signal_is_lagged()
    test_purged_splits_have_embargo()
    print('TSMOM model tests passed')
