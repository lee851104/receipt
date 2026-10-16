"""What the Docker container does before it serves: the secret, the category model, the demo users."""
import tempfile
import unittest
from pathlib import Path

from sqlmodel import Session, select

from src.api import container
from src.api.db import MEMORY, init_db, make_engine
from src.api.settings import Settings
from src.api.tables import User


class SecretTests(unittest.TestCase):
    def test_a_secret_in_the_environment_wins(self):
        folder = Path(tempfile.mkdtemp())
        self.assertEqual(container.jwt_secret({"JWT_SECRET": "x" * 40}, folder), "x" * 40)
        self.assertFalse((folder / "jwt-secret").exists())

    def test_without_one_a_secret_is_made_once_and_kept_in_the_data_volume(self):
        folder = Path(tempfile.mkdtemp())
        first = container.jwt_secret({}, folder)
        self.assertGreaterEqual(len(first), 32)
        self.assertEqual(container.jwt_secret({"JWT_SECRET": "  "}, folder), first)  # a rebuilt container


class CategoryModelTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp()) / "category"
        self.calls = []

    def settings(self, **changes):
        values = {"jwt_secret": "s" * 32, "category_model": "bert", "category_model_dir": str(self.folder),
                  "category_model_repo": "someone/receipt-bert", "category_model_revision": "abc123"}
        return Settings(**{**values, **changes})

    def download(self, repo_id, revision, local_dir):
        self.calls.append((repo_id, revision))
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        (Path(local_dir) / "config.json").write_text("{}", encoding="utf-8")

    def test_another_model_downloads_nothing(self):
        self.assertEqual(container.ensure_category_model(self.settings(category_model="fake"), self.download), "skipped")
        self.assertEqual(self.calls, [])

    def test_the_first_start_downloads_the_fixed_revision_and_the_next_one_does_not(self):
        self.assertEqual(container.ensure_category_model(self.settings(), self.download), "downloaded")
        self.assertTrue((self.folder / "config.json").exists())
        self.assertEqual(container.ensure_category_model(self.settings(), self.download), "present")
        self.assertEqual(self.calls, [("someone/receipt-bert", "abc123")])

    def test_a_failed_download_leaves_no_half_model_and_the_next_start_tries_again(self):
        def broken(repo_id, revision, local_dir):
            Path(local_dir).mkdir(parents=True, exist_ok=True)
            (Path(local_dir) / "config.json").write_text("{}", encoding="utf-8")
            raise OSError("no network")
        with self.assertLogs("src.api.container", level="WARNING") as logs:
            self.assertEqual(container.ensure_category_model(self.settings(), broken), "failed")
        self.assertIn("no network", "\n".join(logs.output))
        self.assertFalse(self.folder.exists())
        self.assertEqual(container.ensure_category_model(self.settings(), self.download), "downloaded")

    def test_without_a_repo_nothing_is_downloaded_and_it_says_so(self):
        with self.assertLogs("src.api.container", level="WARNING"):
            self.assertEqual(container.ensure_category_model(
                self.settings(category_model_repo="", category_model_revision=""), self.download), "no_repo")
        self.assertEqual(self.calls, [])


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)

    def users(self):
        with Session(self.engine) as session:
            return session.exec(select(User)).all()

    def test_an_empty_database_in_demo_mode_gets_the_demo_users(self):
        self.assertGreater(container.seed_if_empty(self.engine, demo_mode=True), 0)
        self.assertTrue(self.users())
        self.assertTrue(all(user.is_demo for user in self.users()))

    def test_a_database_with_anyone_in_it_or_demo_mode_off_is_left_alone(self):
        self.assertEqual(container.seed_if_empty(self.engine, demo_mode=False), 0)
        self.assertEqual(self.users(), [])
        with Session(self.engine) as session:
            session.add(User(username="amy", display_name="Amy", password_hash="x"))
            session.commit()
        self.assertEqual(container.seed_if_empty(self.engine, demo_mode=True), 0)
        self.assertEqual([user.username for user in self.users()], ["amy"])


if __name__ == "__main__":
    unittest.main()
