import json
import unittest
from pathlib import Path

import pandas as pd

from real_bls_jump_risk_2023_2025 import family_balance, jump_bps, load_events


class Research052Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(Path("data/research052_input_manifest.json").read_text())

    def test_official_event_counts(self):
        events = load_events([Path(f"data/bls_schedule_{year}.html") for year in (2023, 2024, 2025)], self.manifest)
        self.assertEqual(len(events), 70)
        self.assertEqual(events.groupby("category").size().to_dict(), {"cpi": 35, "employment": 35})
        self.assertEqual(set(events.panel_clock_offset_minutes), {0, 60})
        self.assertTrue((events.release_timestamp_utc.dt.hour == 13).all())

    def test_jump_requires_exact_boundaries(self):
        release = pd.Timestamp("2024-01-05 13:30:00+00:00")
        series = pd.Series([100.0, 101.0], index=[release - pd.Timedelta(minutes=5), release + pd.Timedelta(minutes=30)])
        self.assertGreater(jump_bps(series, release), 0)
        with self.assertRaises(ValueError):
            jump_bps(series.iloc[:1], release)

    def test_equal_family_aggregation(self):
        rows = pd.DataFrame({"family": ["fx", "fx", "metal", "equity", "energy"],
                             "value": [1.0, 3.0, 4.0, 6.0, 8.0]})
        self.assertEqual(family_balance(rows, ["value"])["value"], 5.0)


if __name__ == "__main__":
    unittest.main()
