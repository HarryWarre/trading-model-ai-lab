import ast
import unittest

SOURCE = "download_histdata_multicfd.py"


class MultiCFDDownloaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SOURCE, encoding="utf-8") as handle:
            cls.tree = ast.parse(handle.read())

    def test_target_universe_has_at_least_fifteen_assets(self):
        targets = next(
            node.value for node in self.tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "TARGETS" for t in node.targets)
        )
        self.assertGreaterEqual(len(targets), 15)

    def test_downloader_rejects_non_zip_response(self):
        source = open(SOURCE, encoding="utf-8").read()
        self.assertIn('blob.startswith(b"PK\\x03\\x04")', source)
        self.assertIn('status": "blocked"', source)


if __name__ == "__main__":
    unittest.main()
