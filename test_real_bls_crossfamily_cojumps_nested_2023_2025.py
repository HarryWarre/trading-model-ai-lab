import unittest
from unittest.mock import patch

import pandas as pd

import real_bls_crossfamily_cojumps_nested_2023_2025 as r56


class Research056Tests(unittest.TestCase):
    def test_strict_historical_extreme_rejects_tie(self):
        self.assertTrue(r56.strict_historical_extreme(5.0, [1.0, 2.0, 3.0, 4.0]))
        self.assertFalse(r56.strict_historical_extreme(4.0, [1.0, 2.0, 3.0, 4.0]))

    def test_family_activation_uses_half_threshold(self):
        flags = {"EURUSD": True, "GBPUSD": True, "USDJPY": False, "USDCHF": False}
        self.assertTrue(r56.family_activation(flags, ["fx"])["fx"])

    def test_target_flags_uses_only_prior_anchors(self):
        target = pd.Timestamp("2025-06-12 12:30:00+00:00")
        values = {
            target - pd.Timedelta(weeks=i): {a: float(10 - i) for a in r56.r52.ASSETS}
            for i in range(5)
        }
        side_effect = lambda _prices, timestamp: values.get(timestamp, {})
        with patch.object(r56, "jumps_at", side_effect=side_effect):
            result = r56.target_flags(pd.DataFrame(), target, set())
        self.assertIsNotNone(result)
        flags, anchors = result
        self.assertEqual(len(anchors), 4)
        self.assertTrue(all(anchor < target for anchor in anchors))
        self.assertTrue(all(flags.values()))

    def test_later_event_cannot_change_prior_target_label(self):
        target = pd.Timestamp("2025-06-05 12:30:00+00:00")
        future_event = target + pd.Timedelta(weeks=1)
        values = {target: {a: 5.0 for a in r56.r52.ASSETS}}
        for i in range(1, 5):
            values[target - pd.Timedelta(weeks=i)] = {a: float(i) for a in r56.r52.ASSETS}
        values[future_event] = {a: 1_000.0 for a in r56.r52.ASSETS}
        side_effect = lambda _prices, timestamp: values.get(timestamp, {})
        with patch.object(r56, "jumps_at", side_effect=side_effect):
            before = r56.target_flags(pd.DataFrame(), target, set())
        values[future_event] = {a: -1_000.0 for a in r56.r52.ASSETS}
        with patch.object(r56, "jumps_at", side_effect=side_effect):
            after = r56.target_flags(pd.DataFrame(), target, set())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
