from io import BytesIO
from zipfile import ZipFile

import pytest

from download_usmpd_official import validate_xlsx


def test_rejects_html_and_fake_zip():
    with pytest.raises(ValueError, match="XLSX"):
        validate_xlsx(b"<html>access denied</html>")
    with BytesIO() as buf:
        with ZipFile(buf, "w") as z:
            z.writestr("foo.txt", "wrong container")
        with pytest.raises(ValueError):
            validate_xlsx(buf.getvalue())


def test_accepts_valid_zip_container():
    with BytesIO() as buf:
        with ZipFile(buf, "w") as z:
            z.writestr("xl/workbook.xml", "<workbook/>")
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("xl/worksheets/sheet1.xml", "<sheetData/>" * 80)
        assert "xl/workbook.xml" in validate_xlsx(buf.getvalue())
