import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from real_fomc_drift_2024 import ASSETS, last_observed, leave_one_out, load_events, pre_event_vol


class TestResearch040(unittest.TestCase):
    def test_official_events_are_unique_and_utc(self):
        events = load_events(Path("data/fomc_2024_official.csv"))
        self.assertEqual(len(events), 8)
        self.assertEqual(str(events.release_timestamp_utc.dt.tz), "UTC")
        self.assertTrue(events.source_url.str.contains("federalreserve.gov").all())

    def test_stale_boundary_rejected(self):
        idx = pd.DatetimeIndex(["2024-01-01T00:00:00Z"])
        with self.assertRaisesRegex(ValueError, "stale"):
            last_observed(pd.Series([1.0], index=idx), pd.Timestamp("2024-01-01T00:15:00Z"))

    def test_volatility_uses_only_past_and_rejects_large_gaps(self):
        idx = pd.date_range("2024-01-01", periods=200, freq="5min", tz="UTC")
        values = np.exp(np.arange(200) * 0.0001)
        series = pd.Series(values, index=idx)
        start = idx[-1] + pd.Timedelta(minutes=5)
        self.assertGreater(pre_event_vol(series, start), 0)

    def test_duplicate_event_id_rejected(self):
        events = pd.read_csv("data/fomc_2024_official.csv")
        events.loc[1, "event_id"] = events.loc[0, "event_id"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.csv"
            events.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "eight unique"):
                load_events(path)

    def test_dst_matching_preserves_new_york_wall_clock(self):
        release = pd.Timestamp("2024-11-07T19:00:00Z")
        local = release.tz_convert("America/New_York")
        prior = (local + pd.DateOffset(days=-7)).tz_convert("UTC")
        self.assertEqual(prior, pd.Timestamp("2024-10-31T18:00:00Z"))
        self.assertEqual(prior.tz_convert("America/New_York").hour, 14)

    def test_leave_one_out_reweights_remaining_assets(self):
        rows = []
        for event in ("e1", "e2"):
            for asset in ASSETS:
                rows.append({
                    "event_id": event, "asset": asset, "pre_event_vol": 0.01,
                    "gross_log_return": 0.001, "start_price": 5000.0,
                })
        result = leave_one_out(pd.DataFrame(rows))
        self.assertEqual(set(result.omitted_asset), set(ASSETS))
        self.assertTrue((result.net_return > 0).all())


if __name__ == "__main__":
    unittest.main()
