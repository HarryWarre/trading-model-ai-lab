import math
import unittest

from real_usmpd_2026_proxy_holdout import EVENTS, portfolio, weight_rows


class Research051Tests(unittest.TestCase):
    def test_information_event_is_frozen_abstention(self):
        self.assertEqual(EVENTS["2026-09-16"]["label"], "information")

    def test_equal_family_then_equal_asset_weights(self):
        rows = [
            {"family": "fx"}, {"family": "fx"},
            {"family": "metal"}, {"family": "equity"},
        ]
        weight_rows(rows)
        self.assertAlmostEqual(sum(r["weight"] for r in rows), 1.0)
        self.assertAlmostEqual(sum(r["weight"] for r in rows if r["family"] == "fx"), 1 / 3)

    def test_cost_is_subtracted_once_per_round_trip(self):
        rows = [{"family": "fx", "economic": 1, "press_return": 0.01, "cost_1x": 0.001}]
        self.assertTrue(math.isclose(portfolio(rows, "economic", 2), 0.008))


if __name__ == "__main__":
    unittest.main()
