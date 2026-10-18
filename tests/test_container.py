"""What the Docker container does before it serves: the secret, the category model, the demo users."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sqlalchemy import inspect
from sqlmodel import Session, select

from src.api import container
from src.api.db import MEMORY, ROOT, init_db, make_engine
from src.api.settings import Settings
from src.api.tables import User
from src.receipt.traits import load_context


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
    """container.seed_demo with role 3's seed replaced by a recorder: what it is called with and how a refusal is
    reported. The seed itself (and a real run of it) is tested in tests/test_role3_seed.py."""
    SUMMARY = {"users": 300, "added_users": 300, "skipped": False}

    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)
        self.addCleanup(self.engine.dispose)
        # Patched where the seed lives: container.seed_demo imports it when it runs, so the patch is what it finds.
        patch = mock.patch("src.api.seed.seed_demo_population", return_value=dict(self.SUMMARY))
        self.seed = patch.start()
        self.addCleanup(patch.stop)

    def test_demo_mode_seeds_the_300_demo_users_with_the_current_context(self):
        self.assertEqual(container.seed_demo(self.engine, demo_mode=True), self.SUMMARY)
        self.seed.assert_called_once()
        engine, people, context = self.seed.call_args.args
        self.assertIs(engine, self.engine)
        self.assertEqual(len(people), 300)
        self.assertEqual(context["calendar"], load_context(ROOT)["calendar"])
        self.assertEqual(self.seed.call_args.kwargs, {})  # the seed's own cache file

    def test_a_database_with_people_in_it_is_still_seeded_in_demo_mode(self):
        # Every start runs it: the seed skips a complete population and repairs a stale one (a new MODEL_VERSION, an
        # older image's 40 bare demo users), so an occupied database is no reason to stay away.
        with Session(self.engine) as session:
            session.add(User(username="amy", display_name="Amy", password_hash="x"))
            session.commit()
        self.assertEqual(container.seed_demo(self.engine, demo_mode=True), self.SUMMARY)
        self.seed.assert_called_once()

    def test_demo_mode_off_seeds_nothing(self):
        self.assertIsNone(container.seed_demo(self.engine, demo_mode=False))
        self.seed.assert_not_called()

    def test_a_seed_that_refuses_is_one_log_line_and_the_start_goes_on(self):
        self.seed.side_effect = ValueError("first line\nsecond line")
        with self.assertLogs("src.api.container", "WARNING") as logs:
            self.assertIsNone(container.seed_demo(self.engine, demo_mode=True))
        self.assertEqual(len(logs.records), 1)
        message = logs.records[0].getMessage()
        self.assertNotIn("\n", message)
        self.assertIn("first line second line", message)

    def test_a_seed_that_breaks_any_other_way_is_also_one_log_line_and_the_start_goes_on(self):
        self.seed.side_effect = OSError("disk\nfull")
        with self.assertLogs("src.api.container", "WARNING") as logs:
            self.assertIsNone(container.seed_demo(self.engine, demo_mode=True))
        self.assertEqual(len(logs.records), 1)
        self.assertNotIn("\n", logs.records[0].getMessage())
        self.assertIn("disk full", logs.records[0].getMessage())


class MainTests(unittest.TestCase):
    """container.main() with nothing real: a temp folder for /data, an in-memory database, and no download, seeding
    or server (each replaced by a recorder). os.environ is restored afterwards."""
    SETTINGS = ("JWT_SECRET", "JWT_EXPIRE_MINUTES", "DEMO_MODE", "DATABASE_URL", "LLAMA_SERVER_URL", "CATEGORY_MODEL",
                "ATTRIBUTES_MODEL", "CATEGORY_MIN_PROB", "CATEGORY_MODEL_DIR", "CATEGORY_MODEL_REPO",
                "CATEGORY_MODEL_REVISION")

    def setUp(self):
        self.data = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.data, ignore_errors=True)
        self.events = []
        self.summary = {"users": 300, "added_users": 300, "skipped": False}  # what the recorder says the seed did
        self.env = {"DEMO_MODE": "1", "DATABASE_URL": "sqlite://", "CATEGORY_MODEL": "bert",
                    "CATEGORY_MODEL_DIR": str(self.data / "category"), "CATEGORY_MODEL_REPO": "someone/receipt-bert",
                    "CATEGORY_MODEL_REVISION": "abc123"}
        for patch in (mock.patch.object(container, "DATA", self.data),
                      mock.patch.object(container, "ensure_category_model", side_effect=self.ensure),
                      mock.patch.object(container, "seed_demo", side_effect=self.seed),
                      mock.patch.object(container.logging, "basicConfig"),
                      mock.patch("uvicorn.run", side_effect=self.serve)):
            patch.start()
            self.addCleanup(patch.stop)

    def ensure(self, settings):
        self.events.append(("model", os.environ["JWT_SECRET"], settings.category_model_repo))
        return "downloaded"

    def seed(self, engine, demo_mode):
        self.events.append(("seed", demo_mode, inspect(engine).has_table("users")))
        return self.summary

    def serve(self, app, **options):
        self.events.append(("serve", app, options, os.environ["JWT_SECRET"]))

    def run_main(self, **env):
        # A blank value is the default, so nothing of the developer's own environment reaches the settings.
        with mock.patch.dict(os.environ, {**dict.fromkeys(self.SETTINGS, ""), **self.env, **env}):
            container.main()

    def test_it_makes_the_secret_then_the_model_then_the_users_then_serves_on_all_interfaces(self):
        self.run_main()
        secret = (self.data / "jwt-secret").read_text(encoding="utf-8").strip()
        self.assertGreaterEqual(len(secret), 32)
        self.assertEqual(self.events, [
            ("model", secret, "someone/receipt-bert"),  # the secret is already in the environment
            ("seed", True, True),                       # demo mode, and the tables exist
            ("serve", "src.api.main:app", {"host": "0.0.0.0", "port": 8000}, secret)])

    def test_a_secret_in_the_environment_is_used_and_nothing_is_kept(self):
        self.run_main(JWT_SECRET="e" * 40)
        self.assertEqual([(event[0], event[1]) for event in self.events[:1]], [("model", "e" * 40)])
        self.assertEqual([event[0] for event in self.events], ["model", "seed", "serve"])
        self.assertEqual(self.events[-1][3], "e" * 40)
        self.assertFalse((self.data / "jwt-secret").exists())

    def test_what_the_seed_did_is_one_info_line(self):
        with self.assertLogs("src.api.container", "INFO") as logs:
            self.run_main()
        self.assertEqual([record.getMessage() for record in logs.records], ["demo users: 300 in all, 300 added"])
        self.summary = {"users": 300, "added_users": 0, "skipped": True}
        with self.assertLogs("src.api.container", "INFO") as logs:
            self.run_main()
        self.assertEqual([record.getMessage() for record in logs.records],
                         ["demo users: 300 in all, 0 added (already complete)"])

    def test_a_seed_that_did_not_run_leaves_no_summary_line_and_the_server_still_starts(self):
        self.summary = None  # demo mode off, or the seed refused (which seed_demo already logged as a warning)
        with self.assertNoLogs("src.api.container", "INFO"):
            self.run_main()
        self.assertEqual([event[0] for event in self.events], ["model", "seed", "serve"])

    def test_a_bad_setting_stops_it_with_one_line_and_nothing_else_runs(self):
        for name, value in (("JWT_SECRET", "too short"), ("CATEGORY_MODEL", "nope"),
                            ("DATABASE_URL", "postgres://x/y"), ("CATEGORY_MIN_PROB", "high")):
            with self.subTest(name=name):
                with self.assertRaises(SystemExit) as stopped:
                    self.run_main(**{name: value})
                message = stopped.exception.code
                self.assertIsInstance(message, str)  # printed to stderr with exit status 1: not a traceback
                self.assertTrue(message.startswith("error: "), message)
                self.assertNotIn("\n", message)
                self.assertIn(name, message)
                self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
