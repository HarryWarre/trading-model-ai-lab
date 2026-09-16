"""Fail-closed retrieval of the SF Fed USMPD raw workbook (not a trade signal)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from zipfile import ZipFile

SOURCE_PAGE = "https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/"
SOURCE_WORKBOOK = "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx"
MAX_BYTES = 10_000_000


def validate_xlsx(data: bytes) -> list[str]:
    if not data.startswith(b"PK\x03\x04") or len(data) > MAX_BYTES or len(data) < 1000:
        raise ValueError("invalid or unexpectedly sized XLSX")
    with ZipFile(BytesIO(data)) as zf:
        members = zf.namelist()
        if "xl/workbook.xml" not in members or "[Content_Types].xml" not in members:
            raise ValueError("not an XLSX workbook")
        if zf.testzip() is not None:
            raise ValueError("corrupt XLSX member")
    return members


def download(output_dir: Path) -> dict:
    with urlopen(SOURCE_WORKBOOK, timeout=40) as response:
        final_url = response.geturl()
        if urlparse(final_url).hostname not in {"frbsf.org", "www.frbsf.org"}:
            raise ValueError("unexpected redirect host")
        raw = response.read(MAX_BYTES + 1)
    members = validate_xlsx(raw)
    digest = hashlib.sha256(raw).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"usmpd_{digest[:16]}.xlsx"
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("existing source file has mismatched hash")
    else:
        path.write_bytes(raw)
    manifest = {"source_page": SOURCE_PAGE, "workbook_url": SOURCE_WORKBOOK,
                "resolved_url": final_url, "downloaded_utc": datetime.now(timezone.utc).isoformat(),
                "file": path.name, "bytes": len(raw), "sha256": digest,
                "zip_members": members, "status": "RAW_ONLY_NOT_TIMING_VALIDATED"}
    manifest_path = output_dir / f"usmpd_{digest[:16]}.manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    print(json.dumps(download(parser.parse_args().output_dir), indent=2))
