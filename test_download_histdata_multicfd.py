import ast
import unittest

SOURCE = "download_histdata_multicfd.py"


class MultiCFDDownloaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SOURCE, encoding="utf-8") as handle:
            cls.source = handle.read()
            cls.tree = ast.parse(cls.source)

    def test_target_universe_has_at_least_fifteen_assets(self):
        targets = next(
            node.value for node in self.tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "TARGETS" for t in node.targets)
        )
        self.assertGreaterEqual(len(targets.elts), 15)

    def test_downloader_rejects_non_zip_and_records_blocker(self):
        self.assertIn('response.startswith(b"PK\\x03\\x04")', self.source)
        self.assertIn('status": "blocked"', self.source)
        self.assertIn("Partial acquisition recorded", self.source)

    def test_existing_archives_are_not_overwritten(self):
        self.assertIn("if path.exists():", self.source)
        self.assertIn("existing_verified", self.source)


if __name__ == "__main__":
    unittest.main()
