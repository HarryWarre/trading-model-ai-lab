import unittest

import numpy as np
import pandas as pd

import real_currency_momentum_2024_2025 as model


class CurrencyMomentumTest(unittest.TestCase):
    def test_currency_price_orientation(self):
        idx = pd.date_range("2024-01-01", periods=2, tz="UTC")
        opens = pd.DataFrame({"AUDUSD": [0.7, .71], "EURUSD": [1.1, 1.11],
                              "GBPUSD": [1.2, 1.21], "USDJPY": [140., 142.]}, index=idx)
        prices = model.currency_prices(opens)
        self.assertAlmostEqual(prices.JPY.iloc[1], 1 / 142.)
        self.assertLess(np.log(prices.JPY.iloc[1] / prices.JPY.iloc[0]), 0)

    def test_rank_is_market_neutral(self):
        idx = pd.date_range("2024-01-01", periods=50, tz="UTC")
        scores = pd.DataFrame({c: np.arange(50) + i for i, c in enumerate(model.CURRENCIES)},
                              index=idx, dtype=float)
        weights, audit = model.currency_targets(scores)
        active = weights.abs().sum(axis=1) > 0
        self.assertTrue((weights.loc[active].sum(axis=1) == 0).all())
        self.assertTrue((weights.loc[active].abs().sum(axis=1) == 1).all())
        self.assertGreater(len(audit), 0)

    def test_execution_is_lagged_one_session(self):
        idx = pd.date_range("2024-01-01", periods=50, tz="UTC")
        scores = pd.DataFrame({c: np.arange(50) + i for i, c in enumerate(model.CURRENCIES)},
                              index=idx, dtype=float)
        weights, audit = model.currency_targets(scores)
        formation = idx.get_loc(audit.formation_session.iloc[0])
        execution = idx.get_loc(audit.execution_session.iloc[0])
        self.assertEqual(execution, formation + 1)
        self.assertEqual(weights.iloc[formation].abs().sum(), 0)
        self.assertEqual(weights.iloc[execution].abs().sum(), 1)

    def test_phase_grid_is_locked(self):
        self.assertEqual(model.PHASE_OFFSETS, [0, 5, 10, 15])
        self.assertEqual(model.FORMATION, model.HOLDING)

    def test_hash_locked_gbpusd_archive_is_complete(self):
        daily = model.load_2024_daily("GBPUSD")
        self.assertEqual(str(daily.index.min().date()), "2024-01-01")
        self.assertEqual(str(daily.index.max().date()), "2024-12-30")
        self.assertGreater(len(daily), 250)


if __name__ == "__main__":
    unittest.main()
