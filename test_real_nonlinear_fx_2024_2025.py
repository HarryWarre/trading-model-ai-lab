import unittest
import pandas as pd
import real_nonlinear_fx_2024_2025 as m

class TestNonlinear(unittest.TestCase):
    def test_locked_model(self):
        self.assertEqual((m.TREES,m.DEPTH,m.LEARNING_RATE),(50,2,.05))
    def test_cost_orientation(self):
        row=pd.Series({'USDJPY':150.0})
        self.assertAlmostEqual(m.linear.trade_fee('JPY',.5,row),.5*4.4*.01/150)
    def test_horizon_and_seed(self):
        self.assertEqual(m.linear.H,5); self.assertEqual(m.SEED,31044)

if __name__=='__main__': unittest.main()
