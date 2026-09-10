from pathlib import Path

import pandas as pd
import pytest

from news_event_schema import build_manifest, load_and_validate_events


def write_events(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "events.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def valid_rows() -> list[dict]:
    return [
        {"event_id": "cpi-2024-01", "timestamp_utc": "2024-01-11T13:30:00Z",
         "country": "US", "category": "cpi", "actual": 3.4,
         "consensus": 3.2, "source": "documented-point-in-time-source"},
        {"event_id": "jobs-2024-01", "timestamp_utc": "2024-02-02T13:30:00Z",
         "country": "US", "category": "employment", "actual": 353.0,
         "consensus": 180.0, "source": "documented-point-in-time-source"},
    ]


def test_valid_events_are_canonical_and_hashed(tmp_path: Path):
    path = write_events(tmp_path, valid_rows())
    events = load_and_validate_events(path)
    assert events.timestamp_utc.dt.tz is not None
    assert list(events.raw_surprise) == [0.2, 173.0]
    manifest = build_manifest(path, events)
    assert manifest["rows"] == 2
    assert len(manifest["sha256"]) == 64


def test_missing_consensus_fails_closed(tmp_path: Path):
    rows = valid_rows()
    rows[0]["consensus"] = None
    with pytest.raises(ValueError, match="actual or consensus"):
        load_and_validate_events(write_events(tmp_path, rows))


def test_duplicate_event_fails_closed(tmp_path: Path):
    rows = valid_rows() + [valid_rows()[0]]
    with pytest.raises(ValueError, match="Duplicate"):
        load_and_validate_events(write_events(tmp_path, rows))


def test_non_us_or_unknown_category_fails_closed(tmp_path: Path):
    rows = valid_rows()
    rows[0]["country"] = "GB"
    with pytest.raises(ValueError, match="US releases"):
        load_and_validate_events(write_events(tmp_path, rows))
    rows = valid_rows()
    rows[0]["category"] = "unknown"
    with pytest.raises(ValueError, match="Unknown"):
        load_and_validate_events(write_events(tmp_path, rows))
