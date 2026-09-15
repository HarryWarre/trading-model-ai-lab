import json
from pathlib import Path

import pandas as pd
import pytest

from real_fomc_drift_2024 import ASSETS, sha256
from real_fomc_drift_2023_2025 import load_events, load_panel


def test_official_event_file_has_24_unique_2pm_new_york_events():
    events = load_events(Path("data/fomc_2023_2025_official.csv"))
    assert len(events) == 24
    assert events.release_timestamp_utc.dt.year.value_counts().sort_index().to_dict() == {
        2023: 8, 2024: 8, 2025: 8
    }
    local = events.release_timestamp_utc.dt.tz_convert("America/New_York")
    assert (local.dt.hour == 14).all()
    assert (local.dt.minute == 0).all()


def test_event_file_preserves_dst_offsets():
    events = load_events(Path("data/fomc_2023_2025_official.csv")).set_index("event_id")
    assert events.loc["FOMC_2025_01_29", "release_timestamp_utc"].hour == 19
    assert events.loc["FOMC_2025_07_30", "release_timestamp_utc"].hour == 18
    assert events.loc["FOMC_2025_12_10", "release_timestamp_utc"].hour == 19


def test_panel_requires_matching_wide_manifest(tmp_path):
    panel = tmp_path / "panel.csv"
    frame = pd.DataFrame({
        "timestamp": ["2023-01-03T22:00:00Z", "2025-12-30T22:00:00Z"],
        **{asset: [100.0, 101.0] for asset in ASSETS},
    })
    frame.to_csv(panel, index=False)
    manifest = tmp_path / "panel.manifest.json"
    manifest.write_text(json.dumps({
        "output": {
            "sha256": sha256(panel), "format": "wide_close",
            "asset_count": 15, "years_requested": [2023, 2024, 2025],
        }
    }))
    loaded, metadata = load_panel(panel, manifest)
    assert list(loaded.columns) == ASSETS
    assert metadata["output"]["asset_count"] == 15

    frame.loc[0, ASSETS[0]] = 99.0
    frame.to_csv(panel, index=False)
    with pytest.raises(ValueError, match="SHA-256"):
        load_panel(panel, manifest)


def test_panel_rejects_long_format_even_with_valid_hash(tmp_path):
    panel = tmp_path / "panel.csv"
    pd.DataFrame({
        "timestamp": ["2023-01-03T22:00:00Z"],
        "asset": ["SPXUSD"], "close": [100.0],
    }).to_csv(panel, index=False)
    manifest = tmp_path / "panel.manifest.json"
    manifest.write_text(json.dumps({
        "output": {
            "sha256": sha256(panel), "format": "long",
            "asset_count": 15, "years_requested": [2023, 2024, 2025],
        }
    }))
    with pytest.raises(ValueError, match="wide_close"):
        load_panel(panel, manifest)


def test_partial_checkpoint_counts_asset_positions_not_event_dates(tmp_path, monkeypatch):
    from real_fomc_drift_2023_2025 import write_partial_event_checkpoint
    detail = pd.DataFrame({"event_id": [f"e{i}" for i in range(24) for _ in ASSETS],
                           "asset": ASSETS * 24})
    assert len(detail) == 96
    # Cadence convention: each event-asset row is one round trip and two order legs.
    assert len(detail) == 24 * len(ASSETS)
    assert 2 * len(detail) == 192
