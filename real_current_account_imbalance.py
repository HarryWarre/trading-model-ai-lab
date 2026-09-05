"""Preregistered current-account currency-premium test with a hard data gate.

No return is calculated unless all five preregistered currency observations are
available. This prevents silent universe changes after inspecting source data.
"""
import pandas as pd

from download_current_account_imbalance import COUNTRIES, normalize


CURRENCIES = list(COUNTRIES.values())
REQUIRED_SOURCE_YEARS = [2022, 2023]


def availability_date(year):
    """Conservative rule locked in issue #41: year y is usable 1 July y+2."""
    return pd.Timestamp(year=year + 2, month=7, day=1)


def source_panel():
    data = normalize()
    return data.pivot(index="year", columns="currency", values="current_account_pct_gdp")


def validate_preregistered_universe(panel):
    required = panel.reindex(index=REQUIRED_SOURCE_YEARS, columns=CURRENCIES)
    missing = required.isna()
    if missing.any().any():
        cells = [f"{year}:{currency}" for year, row in missing.iterrows()
                 for currency, absent in row.items() if absent]
        raise ValueError("Missing preregistered World Bank observations: " + ", ".join(cells))
    return required


def currency_weights(row):
    """Long two largest debtors, short two largest creditors, median flat."""
    if row.reindex(CURRENCIES).isna().any():
        raise ValueError("Cannot rank an incomplete preregistered currency universe")
    premium = -row.reindex(CURRENCIES)
    ordered = premium.sort_values(kind="mergesort")
    weights = pd.Series(0.0, index=CURRENCIES)
    weights.loc[ordered.index[:2]] = -0.25
    weights.loc[ordered.index[-2:]] = 0.25
    return weights


def run():
    panel = source_panel()
    try:
        validate_preregistered_universe(panel)
    except ValueError as error:
        coverage = panel.reindex(index=REQUIRED_SOURCE_YEARS, columns=CURRENCIES)
        coverage.index.name = "source_year"
        coverage.reset_index().to_csv("real_current_account_imbalance_coverage.csv", index=False)
        summary = pd.DataFrame([{
            "status": "blocked_before_pnl", "pnl_calculated": False,
            "reason": str(error), "silent_substitution_used": False,
            "hypothesis_supported": False,
        }])
        summary.to_csv("real_current_account_imbalance_summary.csv", index=False)
        return summary, coverage.reset_index()
    raise RuntimeError("Data gate unexpectedly passed; implement and review P&L before use")


if __name__ == "__main__":
    for name, frame in zip(["summary", "coverage"], run()):
        print(name, frame.to_string(index=False))
