"""What the Docker container does before it serves: the secret, the category model, the demo users."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def names(self, folder=None):
        return sorted(path.name for path in (folder or self.folder).iterdir())

    def ensure(self, download=None, **changes):
        return container.ensure_category_model(self.settings(**changes), download or self.download)

    def test_the_download_is_put_in_place_without_a_partial_folder_left_behind(self):
        self.assertEqual(self.ensure(), "downloaded")
        self.assertEqual(self.names(), ["config.json"])

    def test_a_folder_that_holds_something_else_keeps_it(self):
        self.folder.mkdir(parents=True)
        (self.folder / "notes.txt").write_text("mine", encoding="utf-8")
        self.assertEqual(self.ensure(), "downloaded")
        self.assertEqual(self.names(), ["config.json", "notes.txt"])
        self.assertEqual((self.folder / "notes.txt").read_text(encoding="utf-8"), "mine")

    def test_a_downloaded_entry_replaces_the_one_of_the_same_name_and_only_that_one(self):
        self.folder.mkdir(parents=True)
        (self.folder / "tokenizer").mkdir()
        (self.folder / "tokenizer" / "old.txt").write_text("old", encoding="utf-8")
        (self.folder / "model.bin").write_text("old", encoding="utf-8")
        (self.folder / "notes.txt").write_text("mine", encoding="utf-8")

        def download(repo_id, revision, local_dir):
            Path(local_dir, "tokenizer").mkdir(parents=True)
            Path(local_dir, "tokenizer", "vocab.txt").write_text("new", encoding="utf-8")
            Path(local_dir, "model.bin").write_text("new", encoding="utf-8")
            Path(local_dir, "config.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.ensure(download), "downloaded")
        self.assertEqual(self.names(), ["config.json", "model.bin", "notes.txt", "tokenizer"])
        self.assertEqual(self.names(self.folder / "tokenizer"), ["vocab.txt"])
        self.assertEqual((self.folder / "model.bin").read_text(encoding="utf-8"), "new")
        self.assertEqual((self.folder / "notes.txt").read_text(encoding="utf-8"), "mine")

    def test_config_json_is_moved_last_so_a_half_finished_move_is_never_a_model(self):
        moved, real = [], shutil.move

        def recording(source, target):
            moved.append(Path(source).name)
            return real(source, target)

        def download(repo_id, revision, local_dir):
            for name in ("config.json", "model.bin", "vocab.txt"):  # config.json first on purpose
                Path(local_dir).mkdir(parents=True, exist_ok=True)
                Path(local_dir, name).write_text("x", encoding="utf-8")
        with mock.patch.object(container.shutil, "move", recording):
            self.assertEqual(self.ensure(download), "downloaded")
        self.assertEqual(moved[-1], "config.json")
        self.assertEqual(sorted(moved), ["config.json", "model.bin", "vocab.txt"])

    def test_a_download_without_config_json_is_a_failure_and_the_folder_is_as_it_was(self):
        def empty_handed(repo_id, revision, local_dir):
            Path(local_dir).mkdir(parents=True, exist_ok=True)
            Path(local_dir, "README.md").write_text("no model here", encoding="utf-8")
        with self.assertLogs("src.api.container", level="WARNING") as logs:
            self.assertEqual(self.ensure(empty_handed), "failed")
        self.assertIn("no model", "\n".join(logs.output))
        self.assertFalse(self.folder.exists())  # it was not there before either
        self.folder.mkdir(parents=True)
        (self.folder / "notes.txt").write_text("mine", encoding="utf-8")
        with self.assertLogs("src.api.container", level="WARNING"):
            self.assertEqual(self.ensure(empty_handed), "failed")
        self.assertEqual(self.names(), ["notes.txt"])

    def test_a_move_that_fails_is_a_failure_not_a_crash_and_leaves_no_config_json(self):
        real = shutil.move

        def move_all_but_the_last(source, target):
            if Path(source).name == "config.json":
                raise OSError("disk full")
            return real(source, target)

        def download(repo_id, revision, local_dir):
            Path(local_dir).mkdir(parents=True, exist_ok=True)
            Path(local_dir, "model.bin").write_text("x", encoding="utf-8")
            Path(local_dir, "config.json").write_text("{}", encoding="utf-8")
        with mock.patch.object(container.shutil, "move", move_all_but_the_last), \
                self.assertLogs("src.api.container", level="WARNING") as logs:
            self.assertEqual(self.ensure(download), "failed")
        self.assertIn("disk full", "\n".join(logs.output))
        self.assertFalse((self.folder / "config.json").exists())
        self.assertFalse((self.folder / ".partial").exists())
        self.assertEqual(self.ensure(), "downloaded")  # the next start tries again

    def test_a_partial_folder_left_by_a_crash_is_cleared_before_the_next_download(self):
        (self.folder / ".partial").mkdir(parents=True)
        (self.folder / ".partial" / "stale.bin").write_text("half", encoding="utf-8")
        seen = []

        def download(repo_id, revision, local_dir):
            seen.append(sorted(path.name for path in Path(local_dir).iterdir()))
            self.download(repo_id, revision, local_dir)
        self.assertEqual(self.ensure(download), "downloaded")
        self.assertEqual(seen, [[]])
        self.assertEqual(self.names(), ["config.json"])

    def test_an_error_that_spans_lines_is_one_log_line(self):
        def broken(repo_id, revision, local_dir):
            raise OSError("401 Client Error\n\nRepository Not Found for url:\n  https://example.invalid/x")
        with self.assertLogs("src.api.container", level="WARNING") as logs:
            self.assertEqual(self.ensure(broken), "failed")
        self.assertEqual(len(logs.records), 1)
        self.assertNotIn("\n", logs.records[0].getMessage())
        self.assertIn("401 Client Error Repository Not Found for url: https://example.invalid/x",
                      logs.records[0].getMessage())


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
