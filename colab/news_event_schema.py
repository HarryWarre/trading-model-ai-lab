"""Research 039 event-data gate for scheduled macro-news studies.

This module deliberately does not scrape web calendars.  It validates a supplied
point-in-time event file before it can be joined to intraday prices.  A file that
cannot establish event time, actual value and pre-release consensus is rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = (
    "event_id", "timestamp_utc", "country", "category",
    "actual", "consensus", "source",
)
ALLOWED_CATEGORIES = {"cpi", "employment", "growth", "retail_sales", "pmi", "rates"}
REQUIRED_COUNTRY = "US"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_events(path: Path, start: str | None = None,
                             end: str | None = None) -> pd.DataFrame:
    """Return a canonical event table or raise ValueError fail-closed."""
    raw = pd.read_csv(path)
    missing = set(REQUIRED_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    events = raw.loc[:, REQUIRED_COLUMNS].copy()
    events["timestamp_utc"] = pd.to_datetime(
        events["timestamp_utc"], utc=True, errors="coerce"
    )
    events["event_id"] = events["event_id"].astype(str).str.strip()
    events["country"] = events["country"].astype(str).str.upper().str.strip()
    events["category"] = events["category"].astype(str).str.lower().str.strip()
    events["source"] = events["source"].astype(str).str.strip()
    events["actual"] = pd.to_numeric(events["actual"], errors="coerce")
    events["consensus"] = pd.to_numeric(events["consensus"], errors="coerce")

    invalid = (
        events["timestamp_utc"].isna()
        | events["event_id"].eq("")
        | events["source"].eq("")
        | events["actual"].isna()
        | events["consensus"].isna()
        | ~np.isfinite(events["actual"])
        | ~np.isfinite(events["consensus"])
    )
    if invalid.any():
        raise ValueError(
            "Event file has missing/invalid time, source, actual or consensus; "
            "surprises cannot be reconstructed safely."
        )
    if (events["country"] != REQUIRED_COUNTRY).any():
        raise ValueError("Research 039 accepts US releases only in this first specification.")
    unknown = sorted(set(events["category"]) - ALLOWED_CATEGORIES)
    if unknown:
        raise ValueError(f"Unknown event categories: {unknown}")
    if events.duplicated(["event_id", "timestamp_utc"]).any():
        raise ValueError("Duplicate event_id/timestamp rows are not permitted.")
    if not events["timestamp_utc"].is_monotonic_increasing:
        events = events.sort_values(["timestamp_utc", "event_id"]).reset_index(drop=True)

    if start is not None:
        events = events[events["timestamp_utc"] >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        events = events[events["timestamp_utc"] < pd.Timestamp(end, tz="UTC")]
    if events.empty:
        raise ValueError("No valid events remain in the requested window.")

    # Surprise sign has no assumed economic direction.  Standardization occurs
    # using only prior events of the same category in walk-forward training.
    events["raw_surprise"] = events["actual"] - events["consensus"]
    return events.reset_index(drop=True)


def build_manifest(path: Path, events: pd.DataFrame) -> dict:
    return {
        "file": str(path),
        "sha256": sha256(path),
        "rows": int(len(events)),
        "first_timestamp_utc": events["timestamp_utc"].min().isoformat(),
        "last_timestamp_utc": events["timestamp_utc"].max().isoformat(),
        "categories": events.groupby("category").size().to_dict(),
        "source_values": sorted(events["source"].unique().tolist()),
        "fail_closed_schema": True,
        "requires_point_in_time_actual_and_consensus": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()

    events = load_and_validate_events(args.events, args.start, args.end)
    args.output.mkdir(parents=True, exist_ok=True)
    events.to_csv(args.output / "research039_events_validated.csv", index=False)
    (args.output / "research039_event_manifest.json").write_text(
        json.dumps(build_manifest(args.events, events), indent=2)
    )


if __name__ == "__main__":
    main()
