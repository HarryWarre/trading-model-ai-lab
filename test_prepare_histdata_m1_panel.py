from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from colab.prepare_histdata_m1_panel import (
    digest, load_archive, resample_5m, to_wide_panel,
    validate_download_manifest,
)


def write_zip(path: Path, rows: list[str], member_asset: str = "EURUSD") -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr(
            f"DAT_ASCII_{member_asset}_M1_2023.txt",
            "\n".join(rows) + "\n",
        )


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


def test_wide_panel_preserves_missing_quotes_without_filling():
    timestamps = pd.to_datetime(
        ["2023-01-03T22:00:00Z", "2023-01-03T22:05:00Z"]
    )
    long = pd.DataFrame({
        "timestamp": [timestamps[0], timestamps[1], timestamps[0]],
        "asset": ["EURUSD", "EURUSD", "GBPUSD"],
        "close": [1.05, 1.06, 1.20],
    })
    wide = to_wide_panel(long, ["EURUSD", "GBPUSD"])
    assert list(wide.columns) == ["timestamp", "EURUSD", "GBPUSD"]
    assert wide["EURUSD"].tolist() == [1.05, 1.06]
    assert wide["GBPUSD"].iloc[0] == 1.20
    assert pd.isna(wide["GBPUSD"].iloc[1])


def test_download_manifest_must_match_bytes_and_sha(tmp_path):
    path = tmp_path / "histdata_EURUSD_M1_2023.zip"
    write_zip(path, ["20230103 170000;1;1;1;1.05;10"])
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{
        "asset": "EURUSD", "year": 2023, "status": "downloaded",
        "archive": str(path), "sha256": digest(path),
        "bytes": path.stat().st_size, "error": "",
    }]).to_csv(manifest, index=False)
    verified = validate_download_manifest(
        manifest, tmp_path, ["EURUSD"], [2023]
    )
    assert verified[("EURUSD", 2023)] == digest(path)

    data = pd.read_csv(manifest)
    data.loc[0, "sha256"] = "0" * 64
    data.to_csv(manifest, index=False)
    with pytest.raises(ValueError, match="SHA-256"):
        validate_download_manifest(manifest, tmp_path, ["EURUSD"], [2023])


def test_manifest_rejects_blocked_or_missing_asset_year(tmp_path):
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame([{
        "asset": "EURUSD", "year": 2023, "status": "blocked",
        "archive": "", "sha256": "", "bytes": 0, "error": "blocked",
    }]).to_csv(manifest, index=False)
    with pytest.raises(ValueError, match="unverified archive status"):
        validate_download_manifest(manifest, tmp_path, ["EURUSD"], [2023])
    with pytest.raises(ValueError, match="coverage mismatch"):
        validate_download_manifest(manifest, tmp_path, ["GBPUSD"], [2023])


def test_parser_rejects_non_zip(tmp_path):
    path = tmp_path / "histdata_EURUSD_M1_2023.zip"
    path.write_text("not a zip", encoding="utf-8")
    with pytest.raises(ValueError, match="not a ZIP"):
        load_archive(path, "EURUSD")
