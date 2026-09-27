import tempfile
import unittest
from pathlib import Path

import pandas as pd

import real_bls_jump_risk_raw_recovery_2023_2025 as r53


class Research053Tests(unittest.TestCase):
    def test_raw_resample_is_fixed_est_and_right_labelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DAT_ASCII_EURUSD_M1_2023.csv"
            path.write_text(
                "20230103 082500;1;1;1;1.1;0\n"
                "20230103 082600;1;1;1;1.2;0\n"
                "20230103 083000;1;1;1;1.3;0\n",
                encoding="utf-8",
            )
            bars, qa = r53.load_raw_m1(path)
            self.assertEqual(qa["asset"], "EURUSD")
            self.assertEqual(bars.at[pd.Timestamp("2023-01-03 13:25", tz="UTC")], 1.1)
            self.assertEqual(bars.at[pd.Timestamp("2023-01-03 13:30", tz="UTC")], 1.3)

    def test_raw_duplicate_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DAT_ASCII_EURUSD_M1_2023.csv"
            path.write_text(
                "20230103 082500;1;1;1;1.1;0\n"
                "20230103 082500;1;1;1;1.2;0\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate or unsorted"):
                r53.load_raw_m1(path)

    def test_raw_nonpositive_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DAT_ASCII_EURUSD_M1_2023.csv"
            path.write_text("20230103 082500;1;1;1;0;0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid raw close"):
                r53.load_raw_m1(path)


if __name__ == "__main__":
    unittest.main()
