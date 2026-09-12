import json
import unittest
from pathlib import Path
import pandas as pd
import real_post_fomc_multinput_2024 as m

ROOT=Path(__file__).parent

class Research041Tests(unittest.TestCase):
    def test_frozen_inputs_and_event_provenance(self):
        prices=m.load_panel(ROOT/'data/cfd_intraday_5m_15_2024.csv')
        events=m.load_events(ROOT/'data/fomc_2024_official.csv')
        self.assertEqual(len(prices.columns),15)
        self.assertEqual(len(events),8)
        self.assertEqual(m.sha256(ROOT/'data/cfd_intraday_5m_15_2024.csv'),m.PANEL_SHA)

    def test_no_signal_uses_future_data(self):
        events=m.load_events(ROOT/'data/fomc_2024_official.csv')
        prices=m.load_panel(ROOT/'data/cfd_intraday_5m_15_2024.csv')
        rows=m.build_rows(prices,events,ROOT/'data/fred_VIXCLS.csv')
        x=m.strategy(rows,'expanding_ridge')
        self.assertTrue((x.q1 >= x.release_timestamp_utc+pd.Timedelta(minutes=5)).all())
        self.assertTrue((x.qe >= x.q1).all())

    def test_deterministic_summary(self):
        out=ROOT/'results/research041/research041_summary.json'
        s=json.loads(out.read_text())
        self.assertEqual(s['valid_rows'],98)
        self.assertEqual(s['models']['price_only'][1]['round_trips'],88)
        self.assertEqual(s['models']['expanding_ridge'][1]['round_trips'],97)

if __name__=='__main__': unittest.main()

