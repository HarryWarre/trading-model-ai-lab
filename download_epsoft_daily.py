"""Download the exact EPSOFT daily BID files used by Research 017."""
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/EPSOFT/Database-Currency-Pair/main/"
FILES = {
    "epsoft_EURUSD_d1.csv": (
        "EURUSD/EURUSD_Candlestick_1_D_BID_01.01.2007-28.02.2023.csv",
        "bd1ba7f5a98578c362c6652a6d457386411a1aed6a666058c50fe13b5f522538",
    ),
    "epsoft_USDJPY_d1.csv": (
        "USDJPY/USDJPY_Candlestick_1_D_BID_01.01.2007-02.04.2023.csv",
        "31082ccba4194dc954225ac0dbee094e5b788382e4e9641940a5234592dab31b",
    ),
}


def download():
    for local_name, (remote_path, expected_hash) in FILES.items():
        payload = urlopen(BASE + quote(remote_path), timeout=60).read()
        actual_hash = sha256(payload).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                f"Hash mismatch for {remote_path}: {actual_hash} != {expected_hash}"
            )
        Path(local_name).write_bytes(payload)
        print(f"saved {local_name} sha256={actual_hash}")


if __name__ == "__main__":
    download()
