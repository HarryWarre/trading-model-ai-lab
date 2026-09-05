"""Download and hash-lock CFTC annual futures-only COT archives."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen


START_YEAR = 2010
END_YEAR = 2024
OUT = Path("cftc_history")
SERIES = {
    "tff": "https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip",
    "disagg": "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip",
}


def download():
    OUT.mkdir(exist_ok=True)
    rows = []
    for kind, template in SERIES.items():
        for year in range(START_YEAR, END_YEAR + 1):
            path = OUT / f"{kind}_{year}.zip"
            if not path.exists():
                path.write_bytes(urlopen(template.format(year=year), timeout=60).read())
            payload = path.read_bytes()
            if not payload.startswith(b"PK"):
                raise ValueError(f"Not a ZIP archive: {path}")
            rows.append((kind, year, sha256(payload).hexdigest(), len(payload)))
    manifest = "kind,year,sha256,bytes\n" + "".join(
        f"{kind},{year},{digest},{size}\n" for kind, year, digest, size in rows
    )
    Path("cftc_positioning_manifest.csv").write_text(manifest)


if __name__ == "__main__":
    download()
