import unittest
import pandas as pd
import real_multifactor_fx_2024_2025 as m

class TestMultifactor(unittest.TestCase):
    def test_jpy_cost_uses_usdjpy_quote(self):
        row=pd.Series({'USDJPY':150.0})
        self.assertAlmostEqual(m.trade_fee('JPY',.5,row),.5*4.4*.01/150)
    def test_feature_set_is_locked(self):
        self.assertEqual(len(m.FEATURES),7)
        self.assertEqual(m.ALPHA,10.)
    def test_execution_horizon(self):
        self.assertEqual(m.H,5)
        self.assertGreaterEqual(m.MIN_TRAIN,100)

if __name__=='__main__': unittest.main()
