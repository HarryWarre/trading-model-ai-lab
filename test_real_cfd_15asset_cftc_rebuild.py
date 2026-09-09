import unittest
import real_cfd_15asset_cftc_rebuild as model
class CFTCRebuildTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.summary,cls.daily,cls.decisions,cls.vix=model.run()
 def test_mapped_features(self):
  self.assertEqual(self.summary.cftc_nonzero_assets.iloc[0],8);self.assertTrue((self.decisions.cftc_nonzero_features==8).all())
 def test_cost_follows_turnover(self):
  static=self.daily.gross_turnover.eq(0);non_terminal=static.copy();non_terminal.iloc[-1]=False;self.assertTrue((self.daily.loc[non_terminal,"turnover_cost_log"]==0).all());self.assertGreater(self.daily.turnover_cost_log.iloc[-1],0)
 def test_shape(self):
  self.assertEqual(len(self.daily),305);self.assertEqual(len(self.decisions),61)
if __name__=="__main__": unittest.main()
