import tempfile
import unittest
from pathlib import Path

import numpy as np

import real_bls_multiple_testing_audit_2023_2025 as r58


class Research058Tests(unittest.TestCase):
    def test_shared_signs_are_constant_within_two_event_blocks(self):
        signs = r58.shared_block_signs(7, draws=20, seed=1)
        self.assertTrue(np.array_equal(signs[:, 0], signs[:, 1]))
        self.assertTrue(np.array_equal(signs[:, 2], signs[:, 3]))
        self.assertTrue(np.array_equal(signs[:, 4], signs[:, 5]))

    def test_studentized_rejects_zero_variance(self):
        with self.assertRaises(ValueError):
            r58.studentized(np.ones((10, 2)))

    def test_holm_adjustment_is_monotone_in_order(self):
        raw = np.array([0.04, 0.01, 0.03])
        adjusted = r58.holm_adjust(raw)
        ordered = adjusted[np.argsort(raw)]
        self.assertTrue(np.all(np.diff(ordered) >= 0))
        self.assertTrue(np.all(adjusted >= raw))

    def test_romano_wolf_adjusted_not_below_marginal(self):
        observed = np.array([3.0, 2.0, 1.0])
        randomized = np.array([[0.0, 0.0, 0.0], [4.0, 0.0, 0.0],
                               [0.0, 3.0, 0.0], [0.0, 0.0, 2.0]])
        raw, adjusted = r58.romano_wolf(observed, randomized)
        self.assertTrue(np.all(adjusted >= raw))

    def test_top_positive_share(self):
        values = np.arange(1.0, 11.0)
        self.assertAlmostEqual(r58.top_positive_share(values), sum(range(6, 11)) / sum(range(1, 11)))

    def test_full_run_validates_hashes_and_common_intersection(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            summary = r58.run(Path("."), output)
            self.assertGreaterEqual(summary["common_events"], 45)
            self.assertEqual(summary["years"], [2023, 2024, 2025])
            self.assertTrue((output / "research058_manifest.json").exists())
            self.assertEqual(summary["trades"], 0)


if __name__ == "__main__":
    unittest.main()
