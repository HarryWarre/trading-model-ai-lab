"""Download public AQR TSMOM benchmark workbooks.

The files are public benchmark data, not the unreleased daily panel of the
underlying futures/forwards. Hashes and retrieval date should be recorded by
the downstream pipeline before analysis.
"""
from pathlib import Path
from urllib.request import urlretrieve


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE = "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/"
FILES = {
    "Time-Series-Momentum-Original-Paper-Data.xlsx": BASE + "Time-Series-Momentum-Original-Paper-Data.xlsx",
    "Time-Series-Momentum-Factors-Monthly.xlsx": BASE + "Time-Series-Momentum-Factors-Monthly.xlsx",
}


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for filename, url in FILES.items():
        destination = RAW / filename
        if destination.exists():
            print(f"exists: {destination}")
            continue
        print(f"downloading: {filename}")
        urlretrieve(url, destination)


if __name__ == "__main__":
    download()
