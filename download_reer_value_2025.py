"""Download and hash-lock the BIS/FRED REER inputs for Research 025."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen


SERIES = {
    "RBAUBIS": "85c04afaa44952d520db7fcc3284b512d76e295957ac934a5187712919e0695f",
    "RBXMBIS": "8b50a87fa5ca7a10c57adf37edc4b67fb94ad19d492210d4ea6465202a077eb1",
    "RBGBBIS": "a9f6645fdefc318a369cc619e5d9eef861e8be0f8b4546d698a88792ff82b656",
    "RBJPBIS": "061af9920f500c9fbe660a40a3bc3a27c13a15e1856e5921cfe51d08dc941dcc",
    "RBUSBIS": "790a309666a797011401b62bc7d34a3d714ef4eb3805cae6c6f3859bbfb0f03a",
}


def download():
    rows = ["kind,id,sha256"]
    for series, expected in SERIES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        payload = urlopen(url, timeout=90).read()
        path = Path(f"fred_{series}.csv")
        actual = sha256(payload).hexdigest()
        if actual != expected:
            raise ValueError(f"Hash mismatch for {series}: {actual} != {expected}")
        path.write_bytes(payload)
        rows.append(f"fred_bis_reer,{series},{actual}")
    Path("reer_value_2025_manifest.csv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    download()
