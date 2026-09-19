import unittest
import numpy as np
import pandas as pd
from real_fomc_statement_pressconference_2023_2025 import (
    block_probability, exact, model_signals, PIP, WARMUP
)

class Research047Tests(unittest.TestCase):
    def test_exact_quote_fails_closed(self):
        t=pd.Timestamp("2024-01-31T19:20:00Z")
        p=pd.DataFrame({"EURUSD":[1.1]},index=[t])
        self.assertEqual(exact(p,"EURUSD",t),1.1)
        with self.assertRaisesRegex(ValueError,"timestamp absent"):
            exact(p,"EURUSD",t+pd.Timedelta(minutes=5))

    def test_fixed_pip_contract(self):
        self.assertEqual(PIP["EURUSD"],0.0001)
        self.assertEqual(PIP["USDJPY"],0.01)
        self.assertEqual(PIP["XAGUSD"],0.001)
        self.assertEqual(PIP["SPXUSD"],0.1)

    def test_block_bootstrap_deterministic(self):
        x=np.array([.01,-.02,.03,0,.01])
        self.assertEqual(block_probability(x),block_probability(x))

    def test_walk_forward_never_signals_warmup(self):
        events=[f"E{i:02d}" for i in range(WARMUP+1)]
        rows=[]
        for i,e in enumerate(events):
            for asset in ("EURUSD","GBPUSD","AUDUSD"):
                rows.append({"event_id":e,"release_timestamp_utc":pd.Timestamp("2024-01-01",tz="UTC")+pd.Timedelta(days=7*i),
                             "asset":asset,"statement_z":i+.1,"family_loo_z":i+.2,
                             "global_family_z":i+.3,"log_prevol":-5.,"vix":15.+i,
                             "statement_vix":(i+.1)*(15+i),"target_z":.1*i,
                             "prevol":.001,"cost_1x":.0001})
        x=pd.DataFrame(rows)
        s=model_signals(x,events)
        self.assertTrue((s[x.event_id.isin(events[:WARMUP])]==0).all())

if __name__=="__main__":
    unittest.main()
