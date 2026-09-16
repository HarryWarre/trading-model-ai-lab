"""stdlib-only CI checks for Research 045 when pytest is unavailable."""
from io import BytesIO
from zipfile import ZipFile
import unittest

import numpy as np
import pandas as pd

from real_fomc_crossfamily_jumps import block_bootstrap, jump_bps
from download_usmpd_official import validate_xlsx


class Research045Tests(unittest.TestCase):
    def test_exact_bars_and_missing_quote(self):
        t = pd.Timestamp("2024-01-31T19:00:00Z")
        bars = pd.DataFrame({"EURUSD": [1., 1.01]}, index=[t-pd.Timedelta(minutes=5), t+pd.Timedelta(minutes=5)])
        self.assertAlmostEqual(jump_bps(bars, "EURUSD", t), 1e4 * np.log(1.01))
        with self.assertRaisesRegex(ValueError, "missing exact"):
            jump_bps(bars.iloc[:1], "EURUSD", t)

    def test_dst_uses_new_york_clock(self):
        t = pd.Timestamp("2024-03-20T18:00:00Z")
        self.assertEqual((t.tz_convert("America/New_York")-pd.DateOffset(weeks=1)).tz_convert("UTC"),
                         pd.Timestamp("2024-03-13T18:00:00Z"))

    def test_bootstrap_reproducible(self):
        x = np.array([2., -1., 3., 0., 1.])
        self.assertEqual(block_bootstrap(x), block_bootstrap(x))

    def test_reject_fake_workbook(self):
        with self.assertRaises(ValueError):
            validate_xlsx(b"<html>access denied</html>")
        with BytesIO() as buf:
            with ZipFile(buf, "w") as z:
                z.writestr("foo.txt", "wrong container" * 100)
            with self.assertRaises(ValueError):
                validate_xlsx(buf.getvalue())

    def test_accepts_structurally_valid_workbook(self):
        with BytesIO() as buf:
            with ZipFile(buf, "w") as z:
                z.writestr("xl/workbook.xml", "<workbook/>")
                z.writestr("[Content_Types].xml", "<Types/>")
                z.writestr("xl/worksheets/sheet1.xml", "<sheetData/>" * 90)
            self.assertIn("xl/workbook.xml", validate_xlsx(buf.getvalue()))


if __name__ == "__main__":
    unittest.main()
