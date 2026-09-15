import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from real_fomc_prior_weekday_controls import (
    ASSETS, aggregate, circular_block_bootstrap, load_events, load_panel,
)


def test_event_file_is_official_and_preserves_dst():
    events = load_events(Path("data/fomc_2023_2025_official.csv"))
    assert len(events) == 24
    local = events.release_timestamp_utc.dt.tz_convert("America/New_York")
    assert ((local.dt.hour == 14) & (local.dt.minute == 0)).all()
    assert events.iloc[0].release_timestamp_utc.hour == 19
    assert events.iloc[1].release_timestamp_utc.hour == 18


def test_block_bootstrap_is_deterministic_and_directional():
    first = circular_block_bootstrap(np.array([0.01, 0.02, 0.03, 0.04]))
    second = circular_block_bootstrap(np.array([0.01, 0.02, 0.03, 0.04]))
    assert first == second
    assert first[0] == 1.0


def test_aggregate_reweights_after_omission():
    rows = []
    for asset, vol, ret in zip(ASSETS, [1, 2, 3, 4], [0.01, 0.02, -0.01, 0.00]):
        rows.append({"event_id": "e", "release_timestamp_utc": pd.Timestamp("2024-01-01", tz="UTC"),
                     "asset": asset, "pre_event_vol": vol, "gross_log_return": ret,
                     "start_price": 100.0})
    result = aggregate(pd.DataFrame(rows), ["event_id"], omitted_asset="SPXUSD")
    assert result.assets.iloc[0] == 3
    assert np.isfinite(result.net_log_return.iloc[0])


def test_panel_fails_closed_on_hash_or_row_mismatch(tmp_path):
    panel = tmp_path / "panel.csv"
    pd.DataFrame({"timestamp": ["2023-01-01T00:00:00Z"],
                  **{asset: [100.0] for asset in ASSETS}}).to_csv(panel, index=False)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"output": {"sha256": "bad", "format": "wide_close",
                                                "asset_count": 15, "years_requested": [2023, 2024, 2025],
                                                "rows": 1}}))
    with pytest.raises(ValueError, match="SHA-256"):
        load_panel(panel, manifest)
