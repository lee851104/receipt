"""The demo upload file gives a new account a ready profile and matches, with the fake models start.bat uses."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts import make_demo_upload
from src.ml import fakes
from tests.api_support import drain, login, make_client, register, upload


class DemoUploadTests(unittest.TestCase):
    def test_every_name_is_fictional_reviewed_and_never_left_to_be_checked(self):
        names = {row[5] for row in make_demo_upload.demo_rows()}
        self.assertGreaterEqual(len(names), 8)
        self.assertTrue(all(name.startswith("示範") for name in names))
        for answer in fakes.classify(sorted(names)):
            self.assertGreaterEqual(max(answer["probs"]), 0.5)  # CATEGORY_MIN_PROB's default: not 10 待確認

    def test_an_uploaded_demo_file_makes_a_ready_profile_that_finds_matches(self):
        data = make_demo_upload.demo_csv("2026-06")
        with make_client() as client:
            for username in ("check_a", "check_b"):
                self.assertEqual(register(client, username=username).status_code, 201)
                headers = login(client, username=username)
                response = upload(client, headers, data)
                self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(response.json()["month"], "2026-06")
            drain(client)
            profile = client.get("/api/me/profile", headers=headers).json()
            self.assertTrue(profile["ready"])
            self.assertEqual(profile["item_count"], make_demo_upload.LINES)
            people = client.get("/api/matches", headers=headers).json()["people"]
            self.assertEqual([person["display_name"] for person in people], ["check_a"])

    def test_the_command_writes_the_file_for_the_month_asked(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "demo.csv"
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                make_demo_upload.main(["--month", "2026-07", "--out", str(out)])
            self.assertIn("40 fictional lines for 2026-07", printed.getvalue())
            text = out.read_bytes().decode("utf-8-sig")
        self.assertTrue(text.startswith("發票日期,"))
        self.assertIn("20260701", text)
        self.assertEqual(text.count("示範"), make_demo_upload.LINES * 2 + make_demo_upload.LINES)


if __name__ == "__main__":
    unittest.main()
