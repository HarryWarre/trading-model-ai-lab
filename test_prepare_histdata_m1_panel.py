from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from colab.prepare_histdata_m1_panel import load_archive, resample_5m


def write_zip(path: Path, rows: list[str]) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("DAT_ASCII_EURUSD_M1_2023.csv", "\n".join(rows) + "\n")


def test_histdata_parser_converts_fixed_est_to_utc(tmp_path):
    path = tmp_path / "histdata_EURUSD_M1_2023.zip"
    write_zip(path, [
        "20230103 170000;1.0;1.1;0.9;1.05;10",
        "20230103 170100;1.0;1.1;0.9;1.06;11",
    ])
    frame = load_archive(path, "EURUSD")
    assert frame["timestamp"].dt.tz is not None
    assert frame["timestamp"].iloc[0] == pd.Timestamp("2023-01-03 22:00:00+00:00")
    assert frame["close"].tolist() == [1.05, 1.06]


def test_resample_uses_observed_last_close_and_does_not_fill(tmp_path):
    path = tmp_path / "histdata_EURUSD_M1_2023.zip"
    write_zip(path, [
        "20230103 170000;1;1;1;1.05;10",
        "20230103 170400;1;1;1;1.09;10",
        "20230103 171000;1;1;1;1.10;10",
    ])
    five = resample_5m(load_archive(path, "EURUSD"))
    assert five["close"].tolist() == [1.05, 1.09, 1.10]
    assert five["timestamp"].tolist() == [
        pd.Timestamp("2023-01-03 22:00:00+00:00"),
        pd.Timestamp("2023-01-03 22:05:00+00:00"),
        pd.Timestamp("2023-01-03 22:10:00+00:00"),
    ]


def test_parser_rejects_non_zip(tmp_path):
    path = tmp_path / "histdata_EURUSD_M1_2023.zip"
    path.write_text("not a zip", encoding="utf-8")
    with pytest.raises(ValueError, match="not a ZIP"):
        load_archive(path, "EURUSD")
