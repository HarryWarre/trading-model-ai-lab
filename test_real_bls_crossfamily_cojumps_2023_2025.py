import unittest

import numpy as np

import real_bls_crossfamily_cojumps_2023_2025 as r55


class Research055Tests(unittest.TestCase):
    def test_unique_max_flags_ties_produce_no_extreme(self):
        values = np.array([[1, 3, 2], [4, 4, 1], [0, 1, 2]], dtype=float)
        flags = r55.unique_max_flags(values)
        self.assertEqual(flags.tolist(), [[False, True, False], [False, False, False], [False, False, True]])

    def test_family_activation_uses_half_ceiling(self):
        flags = {
            "EURUSD": True, "GBPUSD": True, "AUDUSD": True, "NZDUSD": True,
            "USDJPY": False, "USDCHF": False, "USDCAD": False, "EURJPY": False,
            "XAUUSD": True, "XAGUSD": False,
            "SPXUSD": True, "NSXUSD": True, "GRXEUR": False, "UKXGBP": False,
            "BCOUSD": False,
        }
        active = r55.family_activation(flags)
        self.assertEqual(active, {"fx": True, "metal": True, "equity": True, "energy": False})

    def test_all_families_requires_energy(self):
        assets = {"EURUSD", "XAUUSD", "SPXUSD"}
        self.assertFalse(r55.all_families(assets))
        self.assertTrue(r55.all_families(assets | {"BCOUSD"}))


if __name__ == "__main__":
    unittest.main()
