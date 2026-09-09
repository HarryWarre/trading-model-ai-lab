import unittest
import real_cfd_universe_coverage as m

class TestCoverage(unittest.TestCase):
    def test_universe_size(self):
        self.assertEqual(len(m.UNIVERSE),16)
    def test_fail_closed(self):
        out=m.audit()
        self.assertEqual(len(out),16)
        self.assertEqual(int((out.status=='available').sum()),6)
        self.assertEqual(int((out.status=='blocked').sum()),10)

if __name__=='__main__': unittest.main()
