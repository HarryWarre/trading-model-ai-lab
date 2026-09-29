import unittest

import pandas as pd

import real_bls_delayed_volatility_2023_2025 as r57


class Research057Tests(unittest.TestCase):
    def test_exact_moves_separates_initial_and_delayed_returns(self):
        release = pd.Timestamp("2025-06-12 13:30:00+00:00")
        index = [release - pd.Timedelta(minutes=5), release + pd.Timedelta(minutes=5),
                 release + pd.Timedelta(minutes=30)]
        immediate, delayed = r57.exact_moves(pd.Series([100.0, 102.0, 101.0], index=index), release)
        self.assertGreater(immediate, 0)
        self.assertGreater(delayed, 0)
        self.assertNotEqual(immediate, delayed)

    def test_exact_moves_fails_closed_on_missing_boundary(self):
        release = pd.Timestamp("2025-06-12 13:30:00+00:00")
        series = pd.Series([100.0, 101.0], index=[release - pd.Timedelta(minutes=5),
                                                  release + pd.Timedelta(minutes=30)])
        with self.assertRaises(ValueError):
            r57.exact_moves(series, release)

    def test_breadth_uses_half_family_threshold(self):
        assets = set(r57.r52.ASSETS)
        flags = {asset: False for asset in assets}
        flags.update({"EURUSD": True, "GBPUSD": True, "AUDUSD": True, "NZDUSD": True,
                      "XAUUSD": True, "SPXUSD": True, "NSXUSD": True, "BCOUSD": True})
        self.assertEqual(r57.breadth(flags, assets), 1.0)

    def test_immediate_at_does_not_require_t_plus_30(self):
        release = pd.Timestamp("2025-06-12 13:30:00+00:00")
        frame = pd.DataFrame(index=[release - pd.Timedelta(minutes=5),
                                    release + pd.Timedelta(minutes=5)],
                             columns=r57.r52.ASSETS, data=[[100.0] * 15, [101.0] * 15])
        self.assertEqual(len(r57.immediate_at(frame, release)), 15)

    def test_spearman_positive_for_monotone_values(self):
        self.assertEqual(r57.spearman(pd.Series([1, 2, 3]), pd.Series([10, 20, 30])), 1.0)


if __name__ == "__main__":
    unittest.main()
