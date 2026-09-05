"""Download and hash-lock the HistData 2024 M1 BID archives for Research 020."""
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

PAIRS = ["EURUSD", "USDJPY"]
EXPECTED_ZIP_SHA256 = {
    "EURUSD": "58f074ba6b835eb2fbeaeb6678502a23b26768eefdfa509eb75ff5296bb2904d",
    "USDJPY": "dc99fe4b3e0ae1b457f6bfccc5d36cf6f628812f704f5556aa0a74ff3e7e8c81",
}


def download():
    for pair in PAIRS:
        referer = (
            "https://www.histdata.com/download-free-forex-historical-data/"
            f"?/ascii/1-minute-bar-quotes/{pair.lower()}/2024"
        )
        page = urlopen(referer, timeout=60).read().decode("utf-8", errors="replace")
        match = re.search(r'id="tk" value="([^"]+)"', page)
        if not match:
            raise RuntimeError(f"HistData token unavailable for {pair}")
        payload = urlencode({
            "tk": match.group(1), "date": "2024", "datemonth": "2024",
            "platform": "ASCII", "timeframe": "M1", "fxpair": pair,
        }).encode()
        request = Request(
            "https://www.histdata.com/get.php", data=payload,
            headers={"Referer": referer, "Origin": "https://www.histdata.com"},
        )
        archive = urlopen(request, timeout=180).read()
        actual = sha256(archive).hexdigest()
        expected = EXPECTED_ZIP_SHA256[pair]
        if actual != expected:
            raise ValueError(f"Hash mismatch for {pair}: {actual} != {expected}")
        archive_path = Path(f"histdata_{pair}_M1_2024.zip")
        archive_path.write_bytes(archive)
        with ZipFile(archive_path) as zipped:
            zipped.extractall(".")
        print(f"saved {archive_path} sha256={actual}")


if __name__ == "__main__":
    download()
