import pandas as pd
import unittest

import download_current_account_imbalance as download
import real_current_account_imbalance as model


class CurrentAccountImbalanceTest(unittest.TestCase):
    def test_locked_archive_and_indicator_coverage(self):
        data = download.normalize()
        self.assertEqual(set(data.currency), set(model.CURRENCIES))
        self.assertEqual(len(data), len(model.CURRENCIES) * len(download.YEARS))
        self.assertTrue(data.loc[data.currency.eq("EUR"),
                                 "current_account_pct_gdp"].isna().all())
        self.assertTrue(data.loc[data.currency.ne("EUR"),
                                 "current_account_pct_gdp"].notna().all())

    def test_conservative_annual_availability_rule(self):
        self.assertEqual(model.availability_date(2022), pd.Timestamp("2024-07-01"))
        self.assertEqual(model.availability_date(2023), pd.Timestamp("2025-07-01"))

    def test_incomplete_preregistered_universe_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "2022:EUR"):
            model.validate_preregistered_universe(model.source_panel())

    def test_complete_ranking_is_balanced_and_deterministic(self):
        row = pd.Series({"AUD": -1.0, "EUR": 2.0, "GBP": -3.0,
                         "JPY": 4.0, "USD": 0.0})
        weights = model.currency_weights(row)
        self.assertEqual(weights.sum(), 0)
        self.assertEqual(weights.abs().sum(), 1)
        self.assertEqual(weights.to_dict(), {"AUD": .25, "EUR": -.25,
                                              "GBP": .25, "JPY": -.25,
                                              "USD": 0.0})


if __name__ == "__main__":
    unittest.main()
