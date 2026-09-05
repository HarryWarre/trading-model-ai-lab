"""Download and validate the World Bank current-account (% GDP) archive."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import pandas as pd


URL = "https://api.worldbank.org/v2/en/indicator/BN.CAB.XOKA.GD.ZS?downloadformat=csv"
ARCHIVE = Path("world_bank_current_account.zip")
ARCHIVE_SHA256 = "5f20b759b6f56162d9d733df58803aaef8ec47a10c13db257c74f23d9172e83f"
MEMBER = "API_BN.CAB.XOKA.GD.ZS_DS2_en_csv_v2_33256.csv"
MEMBER_SHA256 = "b03e63f156ae136742a0c1457c5990be0522f367acec3c7dae587cc7f8ef113c"
COUNTRIES = {"AUS": "AUD", "EMU": "EUR", "GBR": "GBP", "JPN": "JPY", "USA": "USD"}
YEARS = list(range(2018, 2026))


def checked_archive(path=ARCHIVE):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("World Bank archive hash mismatch")
    with ZipFile(BytesIO(raw)) as archive:
        member = archive.read(MEMBER)
    if sha256(member).hexdigest() != MEMBER_SHA256:
        raise ValueError("World Bank CSV member hash mismatch")
    return member


def normalize(path=ARCHIVE):
    frame = pd.read_csv(BytesIO(checked_archive(path)), skiprows=4)
    selected = frame.loc[frame["Country Code"].isin(COUNTRIES),
                         ["Country Name", "Country Code", *map(str, YEARS)]].copy()
    selected["currency"] = selected["Country Code"].map(COUNTRIES)
    long = selected.melt(
        id_vars=["Country Name", "Country Code", "currency"],
        value_vars=list(map(str, YEARS)), var_name="year", value_name="current_account_pct_gdp",
    )
    long["year"] = long.year.astype(int)
    return long.sort_values(["currency", "year"]).reset_index(drop=True)


def main(download=False):
    if download:
        ARCHIVE.write_bytes(urlopen(URL, timeout=120).read())
    normalized = normalize()
    normalized.to_csv("world_bank_current_account_selected.csv", index=False)
    pd.DataFrame([
        {"file": str(ARCHIVE), "sha256": ARCHIVE_SHA256, "source_url": URL,
         "source_last_updated": "2026-07-13", "retrieved_utc": "2026-09-05"},
        {"file": MEMBER, "sha256": MEMBER_SHA256, "source_url": URL,
         "source_last_updated": "2026-07-13", "retrieved_utc": "2026-09-05"},
    ]).to_csv("current_account_imbalance_manifest.csv", index=False)
    print(normalized.to_string(index=False))


if __name__ == "__main__":
    main()
