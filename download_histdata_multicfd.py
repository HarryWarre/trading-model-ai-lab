"""Research 034: reproducible multi-CFD HistData downloader.

This tool downloads only after the source page returns a live token, writes the
raw ZIP hash to a manifest, and fails closed on HTML/error responses. It does
not claim that a download succeeded until the manifest records the archive.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import csv
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

# HistData symbols, not broker CFD symbols.
TARGETS = {
    "EURUSD": (2024, 2025), "GBPUSD": (2024, 2025),
    "AUDUSD": (2024, 2025), "NZDUSD": (2024, 2025),
    "USDJPY": (2024, 2025), "USDCHF": (2024, 2025),
    "USDCAD": (2024, 2025), "EURJPY": (2024, 2025),
    "XAUUSD": (2024,), "XAGUSD": (2024,),
    "SPXUSD": (2024,), "NSXUSD": (2024,),
    "GRXEUR": (2024,), "UKXGBP": (2024,),
    "WTIUSD": (2024,), "BCOUSD": (2024,),
}

BASE = "https://www.histdata.com"
MANIFEST = Path("histdata_multicfd_manifest.csv")


def _download(pair: str, year: int) -> tuple[Path, str]:
    referer = (
        f"{BASE}/download-free-forex-historical-data/"
        f"?/ascii/1-minute-bar-quotes/{pair.lower()}/{year}"
    )
    page = urlopen(referer, timeout=60).read()
    text = page.decode("utf-8", errors="replace")
    token = re.search(r'id="tk" value="([^"]+)"', text)
    if not token:
        raise RuntimeError(f"live HistData token unavailable for {pair} {year}")
    payload = urlencode({
        "tk": token.group(1), "date": str(year), "datemonth": str(year),
        "platform": "ASCII", "timeframe": "M1", "fxpair": pair,
    }).encode()
    request = Request(
        f"{BASE}/get.php",
        data=payload,
        headers={"Referer": referer, "Origin": BASE},
    )
    blob = urlopen(request, timeout=180).read()
    if not blob.startswith(b"PK\\x03\\x04"):
        raise RuntimeError(f"non-ZIP response for {pair} {year}")
    path = Path(f"histdata_{pair}_M1_{year}.zip")
    path.write_bytes(blob)
    digest = sha256(blob).hexdigest()
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt ZIP member {bad}")
        archive.extractall(Path(f"histdata_{pair}_{year}"))
    return path, digest


def main() -> None:
    rows = []
    for pair, years in TARGETS.items():
        for year in years:
            row = {"pair": pair, "year": year, "status": "blocked",
                   "archive": "", "sha256": "", "error": ""}
            try:
                path, digest = _download(pair, year)
                row.update(status="downloaded", archive=str(path), sha256=digest)
            except Exception as exc:
                row["error"] = str(exc)
            rows.append(row)
            print(row)
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
