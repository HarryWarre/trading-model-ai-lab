import unittest
import real_nonlinear_learning_curve as m

class TestLearningCurve(unittest.TestCase):
    def test_locked_inference(self):
        self.assertEqual((m.SAMPLES,m.BLOCK,m.SEED),(1000,10,33046))
    def test_partition_and_result(self):
        s,q,d=m.evaluate()
        self.assertEqual(len(q),4); self.assertEqual(len(d),73)
        self.assertEqual(int(q.decisions.sum()),73)
        self.assertFalse(bool(s.hypothesis_supported.iloc[0]))

if __name__=='__main__': unittest.main()
