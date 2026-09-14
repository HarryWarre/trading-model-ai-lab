from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from colab.revalidate_histdata_manifest import digest, revalidate


def write_archive(path: Path, close: float = 1.0) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "DAT_ASCII_EURUSD_M1_2023.txt",
            f"20230103 170000;1;1;1;{close};10\n",
        )


def write_manifest(path: Path, archive: Path, status: str = "downloaded") -> None:
    pd.DataFrame([{
        "asset": "EURUSD", "year": 2023, "status": status,
        "archive": str(archive), "sha256": digest(archive),
        "bytes": archive.stat().st_size, "error": "",
    }]).to_csv(path, index=False)


def test_revalidation_preserves_original_and_records_no_change(tmp_path):
    archive = tmp_path / "histdata_EURUSD_M1_2023.zip"
    original = tmp_path / "original.csv"
    output = tmp_path / "revalidated.csv"
    write_archive(archive)
    write_manifest(original, archive)
    before = original.read_bytes()
    result = revalidate(original, tmp_path, output, ["EURUSD"], [2023])
    assert original.read_bytes() == before
    assert result["rows"] == 1
    assert result["changed_rows"] == 0
    row = pd.read_csv(output).iloc[0]
    assert row.status == "existing_verified"
    assert not bool(row.changed_from_original)


def test_revalidation_records_changed_archive_without_hiding_it(tmp_path):
    archive = tmp_path / "histdata_EURUSD_M1_2023.zip"
    original = tmp_path / "original.csv"
    output = tmp_path / "revalidated.csv"
    write_archive(archive, 1.0)
    write_manifest(original, archive)
    original_sha = pd.read_csv(original).iloc[0].sha256
    write_archive(archive, 1.1)
    result = revalidate(original, tmp_path, output, ["EURUSD"], [2023])
    assert result["changed_rows"] == 1
    row = pd.read_csv(output).iloc[0]
    assert bool(row.changed_from_original)
    assert row.original_sha256 == original_sha
    assert row.sha256 == digest(archive)


def test_revalidation_rejects_blocked_status(tmp_path):
    archive = tmp_path / "histdata_EURUSD_M1_2023.zip"
    original = tmp_path / "original.csv"
    write_archive(archive)
    write_manifest(original, archive, status="blocked")
    with pytest.raises(ValueError, match="unverified original"):
        revalidate(original, tmp_path, tmp_path / "out.csv", ["EURUSD"], [2023])


def test_revalidation_rejects_corrupt_zip(tmp_path):
    archive = tmp_path / "histdata_EURUSD_M1_2023.zip"
    archive.write_bytes(b"not a zip")
    original = tmp_path / "original.csv"
    pd.DataFrame([{
        "asset": "EURUSD", "year": 2023, "status": "downloaded",
        "archive": str(archive), "sha256": digest(archive),
        "bytes": archive.stat().st_size, "error": "",
    }]).to_csv(original, index=False)
    with pytest.raises(ValueError, match="not a ZIP"):
        revalidate(original, tmp_path, tmp_path / "out.csv", ["EURUSD"], [2023])
