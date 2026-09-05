"""Download and hash-lock Research 023 rates and 2025 HistData BID bars."""
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile


PAIRS = {
    "EURUSD": "b7c23d20b9577588a8b13508d58fedbe487e569b7b8b5dd368bd1d2b61115de0",
    "USDJPY": "7e4911e0971bf99e41327f37256154d351af5c8d883c4c5708a46d899b55cbaf",
    "GBPUSD": "7b69c334eadd10568168634cff3ca37b06e5fb9057db4da9b590e2ef2034854e",
    "AUDUSD": "3d2ecffedfc8e1fb5aecb9ceb7dbd7779f24361653e5f30b96b8c7bd9f5b8365",
}
RATES = {
    "IR3TIB01USM156N": "3a51abf105c27499ec6b28cf5edec386274d578e7da66df4c82ae7d0b4cef23b",
    "IR3TIB01EZM156N": "bda18d6a61bc490560965e6acd9fc21e213f026ca68ac4670d3c9ec835043ce5",
    "IR3TIB01JPM156N": "7a1132087e2a21c5b24f74e7209d70be75118357c8996c24a6a826cd06f1166f",
    "IR3TIB01GBM156N": "40c23cc654a1380ed278a2b0be691f368d5cc1648493cadbbf1a2a2f654d33d4",
    "IR3TIB01AUM156N": "369327f8d506c467783f4b1c53659ae873f02db17b7be461fb07248074ecd947",
}


def checked_write(path, payload, expected):
    actual = sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError(f"Hash mismatch for {path}: {actual} != {expected}")
    Path(path).write_bytes(payload)


def download():
    for pair, expected in PAIRS.items():
        referer = (
            "https://www.histdata.com/download-free-forex-historical-data/"
            f"?/ascii/1-minute-bar-quotes/{pair.lower()}/2025"
        )
        page = urlopen(referer, timeout=90).read().decode("utf-8", "replace")
        match = re.search(r'id="tk" value="([^"]+)"', page)
        if not match:
            raise RuntimeError(f"HistData token unavailable for {pair}")
        payload = urlencode({
            "tk": match.group(1), "date": "2025", "datemonth": "2025",
            "platform": "ASCII", "timeframe": "M1", "fxpair": pair,
        }).encode()
        request = Request(
            "https://www.histdata.com/get.php", data=payload,
            headers={"Referer": referer, "Origin": "https://www.histdata.com"},
        )
        path = f"histdata_{pair}_M1_2025.zip"
        checked_write(path, urlopen(request, timeout=240).read(), expected)
        with ZipFile(path) as archive:
            archive.extractall(".")
    for series, expected in RATES.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        checked_write(f"fred_{series}.csv", urlopen(url, timeout=90).read(), expected)


if __name__ == "__main__":
    download()
