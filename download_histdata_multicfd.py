"""Research 034/039: fail-closed multi-year HistData acquisition.

Downloads are optional and each asset-year is independently recorded. A missing
archive never becomes a substituted asset or a fabricated price series. Existing
raw ZIPs are preserved by default and re-hashed instead of overwritten.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

# HistData source symbols, mapped to the frozen CFD-proxy universe.
TARGETS = (
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD",
    "EURJPY", "XAUUSD", "XAGUSD", "SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP",
    "WTIUSD", "BCOUSD",
)
BASE = "https://www.histdata.com"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def validate_zip(path: Path) -> None:
    if not path.read_bytes()[:4] == b"PK\x03\x04":
        raise RuntimeError("archive is not a ZIP")
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt ZIP member {bad}")
        if not archive.namelist():
            raise RuntimeError("ZIP has no members")


def download(pair: str, year: int, output: Path) -> tuple[Path, bool]:
    path = output / f"histdata_{pair}_M1_{year}.zip"
    if path.exists():
        validate_zip(path)
        return path, True

    referer = (
        f"{BASE}/download-free-forex-historical-data/"
        f"?/ascii/1-minute-bar-quotes/{pair.lower()}/{year}"
    )
    page = urlopen(referer, timeout=60).read()
    token = re.search(r'id="tk" value="([^"]+)"', page.decode("utf-8", errors="replace"))
    if not token:
        raise RuntimeError("live download token unavailable")
    payload = urlencode({
        "tk": token.group(1), "date": str(year), "datemonth": str(year),
        "platform": "ASCII", "timeframe": "M1", "fxpair": pair,
    }).encode()
    response = urlopen(Request(
        f"{BASE}/get.php", data=payload,
        headers={"Referer": referer, "Origin": BASE},
    ), timeout=180).read()
    if not response.startswith(b"PK\x03\x04"):
        raise RuntimeError("source returned non-ZIP response")
    path.write_bytes(response)
    try:
        validate_zip(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path, False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", default="2023,2024,2025",
                        help="Comma-separated calendar years.")
    parser.add_argument("--assets", default=",".join(TARGETS),
                        help="Comma-separated HistData symbols.")
    parser.add_argument("--output", type=Path, default=Path("histdata_raw"))
    parser.add_argument("--extract", action="store_true",
                        help="Extract only ZIPs that have passed validation.")
    args = parser.parse_args()

    years = [int(x) for x in args.years.split(",") if x.strip()]
    assets = [x.strip().upper() for x in args.assets.split(",") if x.strip()]
    unknown = sorted(set(assets) - set(TARGETS))
    if unknown:
        raise SystemExit(f"Unknown frozen-universe symbols: {unknown}")
    args.output.mkdir(parents=True, exist_ok=True)

    rows = []
    for asset in assets:
        for year in years:
            row = {
                "asset": asset, "year": year, "status": "blocked",
                "archive": "", "sha256": "", "bytes": 0, "error": "",
            }
            try:
                path, existed = download(asset, year, args.output)
                if args.extract:
                    with ZipFile(path) as archive:
                        archive.extractall(args.output / f"{asset}_{year}")
                row.update(
                    status="existing_verified" if existed else "downloaded",
                    archive=str(path), sha256=digest(path), bytes=path.stat().st_size,
                )
            except Exception as exc:
                row["error"] = str(exc)
            rows.append(row)
            print(row)

    manifest = args.output / "histdata_multiyear_manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    if not all(row["status"] in {"downloaded", "existing_verified"} for row in rows):
        print("Partial acquisition recorded; do not treat this as a complete panel.")


if __name__ == "__main__":
    main()
