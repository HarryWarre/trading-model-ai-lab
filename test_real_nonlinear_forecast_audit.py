import unittest
import pandas as pd
import real_nonlinear_forecast_audit as m

class TestForecastAudit(unittest.TestCase):
    def test_locked_bootstrap(self):
        self.assertEqual((m.SAMPLES,m.BLOCK,m.SEED),(1000,10,32045))
    def test_outputs(self):
        s,a,d=m.evaluate()
        self.assertEqual(int(s.decisions.iloc[0]),73)
        self.assertEqual(len(a),2)
        self.assertTrue({'rank_correlation','realized_winner_minus_loser'}.issubset(d.columns))

if __name__=='__main__': unittest.main()
