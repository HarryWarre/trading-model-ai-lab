"""Research 046 stdlib tests, including fail-closed boundaries and DST."""
import unittest
import pandas as pd
from real_fomc_quote_selection_audit import inspect, previous_controls

class QuoteSelectionTests(unittest.TestCase):
    def test_nearest_only_diagnostic_not_backfill(self):
        t = pd.Timestamp("2023-03-22T18:00:00Z")
        bars = pd.DataFrame({"EURUSD": [1., 1.01]},
                            index=[t-pd.Timedelta(minutes=10), t+pd.Timedelta(minutes=10)])
        result = inspect(bars, "EURUSD", t)
        self.assertFalse(result["both_present"])
        self.assertEqual(result["before_gap_minutes"], 5)
        self.assertEqual(result["after_gap_minutes"], 5)

    def test_exact_both_required(self):
        t = pd.Timestamp("2023-03-22T18:00:00Z")
        bars = pd.DataFrame({"EURUSD": [1., 1.01]},
                            index=[t-pd.Timedelta(minutes=5), t+pd.Timedelta(minutes=5)])
        self.assertTrue(inspect(bars, "EURUSD", t)["both_present"])

    def test_same_new_york_clock_across_dst_and_skip_fomc(self):
        t = pd.Timestamp("2024-03-20T18:00:00Z")
        events = pd.DataFrame({"release_timestamp_utc": [t, pd.Timestamp("2024-03-13T18:00:00Z")]})
        c = previous_controls(events, t)
        self.assertEqual(len(c), 4)
        self.assertEqual(c[0], pd.Timestamp("2024-03-06T19:00:00Z"))
        self.assertTrue(all(x < t for x in c))
        self.assertTrue(all(x.tz_convert("America/New_York").hour == 14 for x in c))

if __name__ == "__main__":
    unittest.main()
