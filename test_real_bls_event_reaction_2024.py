import json
import unittest
from pathlib import Path

import pandas as pd

import real_bls_event_reaction_2024 as model

ROOT = Path(__file__).parent


class Research042Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = model.load_events(ROOT / "data/bls_major_releases_2024.csv")
        cls.prices = model.load_panel(ROOT / "data/cfd_intraday_5m_15_2024.csv")
        cls.rows = model.build_rows(cls.prices, cls.events, model.load_vix(ROOT / "data/fred_VIXCLS.csv"))

    def test_official_event_count_and_dst(self):
        self.assertEqual(len(self.events), 24)
        self.assertEqual(self.events.groupby("category").size().to_dict(), {"cpi": 12, "employment": 12})
        january = self.events.loc[self.events.event_id == "EMP_2024_01_05", "release_timestamp_utc"].iloc[0]
        july = self.events.loc[self.events.event_id == "EMP_2024_07_05", "release_timestamp_utc"].iloc[0]
        self.assertEqual(january.hour, 13)
        self.assertEqual(july.hour, 12)

    def test_no_future_information_at_entry(self):
        self.assertTrue((self.rows.q0 >= self.rows.release_timestamp_utc).all())
        self.assertTrue((self.rows.q1 >= self.rows.release_timestamp_utc + pd.Timedelta(minutes=5)).all())
        self.assertTrue((self.rows.qend >= self.rows.release_timestamp_utc + pd.Timedelta(minutes=60)).all())
        ridge = model.make_strategy(self.rows, "expanding_ridge")
        first_trade = ridge.release_timestamp_utc.min()
        prior_events = self.rows.loc[self.rows.release_timestamp_utc < first_trade, "event_id"].nunique()
        self.assertGreaterEqual(prior_events, 4)

    def test_common_subset_and_cost_monotonicity(self):
        common = model.common_ridge_subset(self.rows)
        ridge = model.make_strategy(self.rows, "expanding_ridge")
        reversal = model.make_strategy(common, "reversal")
        self.assertEqual(ridge.event_id.nunique(), reversal.event_id.nunique())
        returns = [model.summarize(ridge, m)[0]["net_return"] for m in (0, 1, 2, 4)]
        self.assertTrue(all(a >= b for a, b in zip(returns, returns[1:])))

    def test_saved_summary_matches_rerun(self):
        saved = json.loads((ROOT / "results/research042/research042_summary.json").read_text())
        rerun = model.run(ROOT / "data/cfd_intraday_5m_15_2024.csv",
                          ROOT / "data/bls_major_releases_2024.csv",
                          ROOT / "data/fred_VIXCLS.csv",
                          ROOT / "results/research042_rerun")
        self.assertEqual(saved, rerun)


if __name__ == "__main__":
    unittest.main()
