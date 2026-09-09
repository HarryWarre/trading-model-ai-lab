import unittest
import real_cfd_15asset_turnover_audit as audit
class TurnoverAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary,cls.daily,cls.decisions,cls.vix=audit.run()
    def test_cost_only_on_trade_or_final_liquidation(self):
        unchanged=self.daily["gross_turnover"].eq(0); non_terminal=unchanged.copy(); non_terminal.iloc[-1]=False
        self.assertTrue((self.daily.loc[non_terminal,"turnover_cost_log"]==0).all())
        self.assertGreater(self.daily["turnover_cost_log"].iloc[-1],0)
    def test_corrected_cost_lower(self):
        old=self.summary.loc[self.summary.model.eq("prior_block_fee_approximation"),"charged_cost_log"].iloc[0]
        new=self.summary.loc[self.summary.model.eq("corrected_turnover_cost"),"charged_cost_log"].iloc[0]
        self.assertLess(new,old)
    def test_panel_and_decisions(self):
        self.assertEqual(self.daily.shape[0],305); self.assertEqual(len(self.decisions),61)
if __name__=="__main__": unittest.main()
