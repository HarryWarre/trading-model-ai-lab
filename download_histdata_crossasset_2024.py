"""Download hash-locked available HistData cross-asset files for Research 021."""
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

EXPECTED = {
    "EURUSD": "58f074ba6b835eb2fbeaeb6678502a23b26768eefdfa509eb75ff5296bb2904d",
    "USDJPY": "dc99fe4b3e0ae1b457f6bfccc5d36cf6f628812f704f5556aa0a74ff3e7e8c81",
    "GBPUSD": "030b05b4c670c7e152bf4aa4112488c96695d2dcc2b31ca13a3b4834b8431077",
    "AUDUSD": "56338ceb24d7013137e31810be1fe4326d0a4480342829e74fd9355e5efbb7f0",
    "XAUUSD": "5f77f59f90615ead7ce7e012ff34b04a658f1ab4f23e1721e3836e0328cc56c1",
    "SPXUSD": "759e1911963f4b3275cc30a35f8937435afb03ee1eaac2f6a28aa0c9c7068da7",
}
REGISTERED_BUT_BLOCKED = ["WTIUSD"]


def token_for(pair):
    referer = (
        "https://www.histdata.com/download-free-forex-historical-data/"
        f"?/ascii/1-minute-bar-quotes/{pair.lower()}/2024"
    )
    page = urlopen(referer, timeout=60).read().decode("utf-8", errors="replace")
    match = re.search(r'id="tk" value="([^"]*)"', page)
    return referer, (match.group(1) if match else "")


def download():
    for pair, expected in EXPECTED.items():
        referer, token = token_for(pair)
        if not token:
            raise RuntimeError(f"HistData token unavailable for registered asset {pair}")
        payload = urlencode({
            "tk": token, "date": "2024", "datemonth": "2024",
            "platform": "ASCII", "timeframe": "M1", "fxpair": pair,
        }).encode()
        request = Request(
            "https://www.histdata.com/get.php", data=payload,
            headers={"Referer": referer, "Origin": "https://www.histdata.com"},
        )
        archive = urlopen(request, timeout=180).read()
        actual = sha256(archive).hexdigest()
        if actual != expected:
            raise ValueError(f"Hash mismatch for {pair}: {actual} != {expected}")
        path = Path(f"histdata_{pair}_M1_2024.zip")
        path.write_bytes(archive)
        with ZipFile(path) as zipped:
            zipped.extractall(".")
        print(f"saved {path} sha256={actual}")
    for pair in REGISTERED_BUT_BLOCKED:
        _, token = token_for(pair)
        if not token:
            print(f"BLOCKED {pair}: HistData 2024 page has no download token")
        else:
            print(f"AVAILABLE_NOW {pair}: token appeared; validate before use")


if __name__ == "__main__":
    download()
