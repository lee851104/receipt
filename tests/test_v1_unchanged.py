"""v2 leaves v1 alone (web-app spec, 建置 v2): the published report and its build source keep the content recorded in
tests/fixtures/v1-files.json. Changing v1 on purpose means updating that file in the same commit, so it is seen."""
import hashlib
import json
import subprocess
import unittest

from src.api.db import ROOT

RECORDED = json.loads((ROOT / "tests/fixtures/v1-files.json").read_text(encoding="utf-8"))


def digest(path):
    # Line endings depend on the checkout (core.autocrlf), so they are not part of the content.
    return hashlib.sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


class V1UnchangedTests(unittest.TestCase):
    def test_the_v1_report_and_its_source_keep_their_recorded_content(self):
        for path, expected in RECORDED.items():
            with self.subTest(path=path):
                self.assertEqual(digest(path), expected)

    def test_no_v1_file_was_added_or_removed(self):
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "invoice-insights.html", "src/web"],
                                 capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(sorted(tracked), sorted(RECORDED))


if __name__ == "__main__":
    unittest.main()
