import tempfile
import unittest
from pathlib import Path

import real_bls_jump_risk_raw_recovery_2023_2025 as recovery


class Research054Tests(unittest.TestCase):
    def test_exact_duplicate_rows_are_collapsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DAT_ASCII_EURUSD_M1_2023.csv"
            row = "20231029 190000;1;1;1;1.1;0\n"
            path.write_text(row + row, encoding="utf-8")
            bars, qa = recovery.load_raw_m1(path, allow_exact_duplicates=True)
            self.assertEqual(len(bars), 1)
            self.assertEqual(qa["duplicate_rows_collapsed"], 2)
            self.assertEqual(qa["conflicting_duplicate_timestamps"], 0)

    def test_conflicting_duplicate_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "DAT_ASCII_EURUSD_M1_2023.csv"
            path.write_text(
                "20231029 190000;1;1;1;1.1;0\n"
                "20231029 190000;1;1;1;1.2;0\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate or unsorted"):
                recovery.load_raw_m1(path, allow_exact_duplicates=True)


if __name__ == "__main__":
    unittest.main()
