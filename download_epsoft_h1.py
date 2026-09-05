"""Download and hash-lock the EPSOFT H1 BID files used by Research 019."""
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/EPSOFT/Database-Currency-Pair/main/"
FILES = {
    "epsoft_EURUSD_h1.csv": (
        "EURUSD/EURUSD_Candlestick_1_Hour_BID_01.01.2007-28.02.2023.csv",
        "ef14fa999b9c9db7ffe00074393817f4834d64381051e589ed903b599c6938c1",
    ),
    "epsoft_USDJPY_h1.csv": (
        "USDJPY/USDJPY_Candlestick_1_Hour_BID_01.01.2007-02.04.2023.csv",
        "06de9cea0cdd79d84b05ec4f7063f5cc18783feed19c4610011e7ade7a723cc9",
    ),
}


def download():
    for local_name, (remote_path, expected_hash) in FILES.items():
        payload = urlopen(BASE + quote(remote_path), timeout=180).read()
        actual_hash = sha256(payload).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                f"Hash mismatch for {remote_path}: {actual_hash} != {expected_hash}"
            )
        Path(local_name).write_bytes(payload)
        print(f"saved {local_name} sha256={actual_hash}")


if __name__ == "__main__":
    download()
