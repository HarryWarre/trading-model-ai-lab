"""Download the hash-locked VIX history used by Research 024."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen


EXPECTED = "6b2cd4028784f69ae160250c3c10dbce88150e125f5fdc18f0c8d43ae557d5a3"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"


def download():
    payload = urlopen(URL, timeout=90).read()
    actual = sha256(payload).hexdigest()
    if actual != EXPECTED:
        raise ValueError(f"VIXCLS hash mismatch: {actual} != {EXPECTED}")
    Path("fred_VIXCLS.csv").write_bytes(payload)


if __name__ == "__main__":
    download()
