"""What start.bat runs: a .env when there is none, the demo users, the pages opened once the server answers."""
import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sqlmodel import Session, select

from src.api import launch
from src.api.db import init_db, make_engine
from src.api.tables import Job, User

EXAMPLE = "# a comment\nJWT_SECRET=\nJWT_EXPIRE_MINUTES=1440\nDEMO_MODE=1\n"


class EnsureEnvTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".env.example").write_text(EXAMPLE, encoding="utf-8")

    def test_without_a_env_it_writes_one_from_the_example_with_a_new_secret(self):
        self.assertTrue(launch.ensure_env(self.root))
        lines = (self.root / ".env").read_text(encoding="utf-8").splitlines()
        secret = next(line for line in lines if line.startswith("JWT_SECRET=")).removeprefix("JWT_SECRET=")
        self.assertGreaterEqual(len(secret), 32)
        self.assertEqual([line for line in lines if not line.startswith("JWT_SECRET=")],
                         ["# a comment", "JWT_EXPIRE_MINUTES=1440", "DEMO_MODE=1"])

    def test_two_new_env_files_get_different_secrets(self):
        launch.ensure_env(self.root)
        first = (self.root / ".env").read_text(encoding="utf-8")
        (self.root / ".env").unlink()
        launch.ensure_env(self.root)
        self.assertNotEqual((self.root / ".env").read_text(encoding="utf-8"), first)

    def test_an_existing_env_is_never_touched(self):
        (self.root / ".env").write_text("JWT_SECRET=mine\n", encoding="utf-8")
        self.assertFalse(launch.ensure_env(self.root))
        self.assertEqual((self.root / ".env").read_text(encoding="utf-8"), "JWT_SECRET=mine\n")


class OpenWhenReadyTests(unittest.TestCase):
    def test_the_page_opens_once_the_health_check_answers(self):
        answers = iter([False, False, True])
        opened = []
        self.assertTrue(launch.open_when_ready("http://page", "http://health", opened.append,
                                               fetch=lambda url: next(answers), timeout=5, pause=0))
        self.assertEqual(opened, ["http://page"])

    def test_it_gives_up_quietly_when_the_server_never_answers(self):
        opened = []
        self.assertFalse(launch.open_when_ready("http://page", "http://health", opened.append,
                                                fetch=lambda url: False, timeout=0.05, pause=0.01))
        self.assertEqual(opened, [])


class MainTests(unittest.TestCase):
    def test_it_makes_the_env_seeds_then_serves_on_this_computer_only(self):
        calls = []
        root = Path(tempfile.mkdtemp())
        with mock.patch.object(launch, "ensure_env", lambda path: calls.append("env") or False), \
                mock.patch.object(launch, "seed_demo", lambda: calls.append("seed")), \
                mock.patch.object(launch, "open_in_background", lambda: calls.append("open")), \
                mock.patch("uvicorn.run", lambda app, **options: calls.append(("serve", app, options))):
            launch.main(root)
        self.assertEqual(calls, ["env", "seed", "open", ("serve", "src.api.main:app", {"host": "127.0.0.1", "port": 8000})])


class SeedDemoTests(unittest.TestCase):
    """What seed_demo does before role 3's seed runs, on a scratch database file; the seed itself is a recorder."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.url = "sqlite:///" + (self.folder / "app.db").as_posix()  # absolute, so the repository's data/ is untouched
        self.environment = {"DATABASE_URL": self.url, "JWT_SECRET": "t" * 40, "DEMO_MODE": "1"}

    def statuses(self):
        """The job statuses in the database, by user name then month."""
        engine = make_engine(self.url)
        try:
            with Session(engine) as session:
                rows = session.exec(select(User.username, Job.month, Job.status)
                                    .join(Job, Job.user_id == User.id).order_by(User.username, Job.month)).all()
        finally:
            engine.dispose()
        return [tuple(row) for row in rows]

    def seed_demo(self, seed):
        """launch.seed_demo with the given function as the seed and the developer's own .env never read; the call
        made to load it."""
        with mock.patch.dict(os.environ, self.environment), \
                mock.patch.object(launch, "load_dotenv") as load_dotenv, \
                mock.patch("src.api.seed.main", seed):
            launch.seed_demo()
        return load_dotenv

    def test_seed_demo_frees_a_demo_job_left_by_an_interrupted_seed_before_seeding(self):
        # The database a stopped first seed leaves, next to a real user's running job (another server may own it).
        engine = make_engine(self.url)
        init_db(engine)
        with Session(engine) as session:
            session.add_all([User(username="demo_001", display_name="Mia", is_demo=True, persona="咖啡上班族"),
                             User(username="amy", display_name="Amy")])
            session.commit()  # foreign keys are enforced, so the users must exist before their jobs
            session.add_all([Job(user_id=1, month="2026-05", status="running"),
                             Job(user_id=2, month="2026-05", status="running")])
            session.commit()
        engine.dispose()
        seen = []
        load_dotenv = self.seed_demo(lambda: seen.append(self.statuses()))
        # Read when the seed was called, not afterwards: the seed would refuse over the demo user's running job.
        self.assertEqual(seen, [[("amy", "2026-05", "running"), ("demo_001", "2026-05", "failed")]])
        # The root .env, as seed.main reads it; with its defaults, so a variable already set still wins.
        load_dotenv.assert_called_once_with(launch.ROOT / ".env")

    def test_seed_demo_works_on_a_database_that_does_not_exist_yet(self):
        seen = []
        self.seed_demo(lambda: seen.append(self.statuses()))
        self.assertEqual(seen, [[]])

    def test_a_bad_setting_stops_seed_demo_before_it_touches_the_database_or_seeds(self):
        self.environment["JWT_SECRET"] = "short"
        seen = []
        with self.assertRaisesRegex(ValueError, "JWT_SECRET must be at least"):
            self.seed_demo(lambda: seen.append("seeded"))
        self.assertEqual(seen, [])
        self.assertFalse((self.folder / "app.db").exists())


class DemoSeedRefusesTests(unittest.TestCase):
    """Demo users are optional: a seed that stops must not keep a person's own accounts and data from starting."""

    def launch(self, seed):
        """What main did, in order, and what it wrote to stdout and to stderr, when the demo seed is the given
        function."""
        calls, printed, complained = [], io.StringIO(), io.StringIO()
        with mock.patch.object(launch, "ensure_env", lambda path: calls.append("env") or False), \
                mock.patch.object(launch, "seed_demo", seed), \
                mock.patch.object(launch, "open_in_background", lambda: calls.append("open")), \
                mock.patch("uvicorn.run", lambda app, **options: calls.append("serve")), \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(complained):
            launch.main(Path(tempfile.mkdtemp()))
        return calls, printed.getvalue(), complained.getvalue()

    def seed_raising(self, error):
        def seed():
            raise error
        return seed

    def test_a_seed_that_exits_with_a_message_prints_one_line_and_the_server_still_starts(self):
        calls, printed, complained = self.launch(self.seed_raising(SystemExit("error: demo_001 is 'x' in the database")))
        self.assertEqual(calls, ["env", "open", "serve"])
        self.assertEqual(printed, "示範帳號沒有更新：error: demo_001 is 'x' in the database；繼續啟動伺服器\n")
        self.assertEqual(complained, "")

    def test_a_seed_that_fails_otherwise_prints_its_type_and_message_and_the_server_still_starts(self):
        calls, printed, complained = self.launch(self.seed_raising(RuntimeError("a later seed broke")))
        self.assertEqual(calls, ["env", "open", "serve"])
        self.assertEqual(printed, "示範帳號沒有更新：RuntimeError: a later seed broke；繼續啟動伺服器\n")
        self.assertEqual(complained, "")

    def test_the_reason_is_one_short_line_without_a_traceback(self):
        reasons = [SystemExit(1), SystemExit(), RuntimeError(), ValueError("first\nsecond\n  third"),
                   SystemExit("error: " + "demo_001 is not who it should be; " * 40)]
        for error in reasons:
            with self.subTest(error=repr(error)[:40]):
                _, printed, complained = self.launch(self.seed_raising(error))
                self.assertEqual(len(printed.splitlines()), 1)
                self.assertTrue(printed.startswith("示範帳號沒有更新：") and printed.endswith("；繼續啟動伺服器\n"))
                self.assertLess(len(printed), 300)
                # A traceback goes to stderr, so look there as well as at what the warning says.
                self.assertNotIn("Traceback", printed + complained)
                self.assertEqual(complained, "")
        self.assertIn("ValueError: first second third；", self.launch(self.seed_raising(reasons[3]))[1])

    def test_a_long_reason_keeps_its_beginning_and_the_instruction_at_its_end(self):
        # seed_demo_users joins one clash per demo user and ends with what to do about it; the cut must not lose that.
        clashes = "; ".join(f"demo_{number:03} is 'x' in the database but 'y' in the list" for number in range(1, 40))
        instruction = "Delete the database file and run the seed again."
        _, printed, _ = self.launch(self.seed_raising(SystemExit(f"error: {clashes}. {instruction}")))
        self.assertEqual(len(printed.splitlines()), 1)
        self.assertLess(len(printed), 300)
        self.assertIn("示範帳號沒有更新：error: demo_001 is", printed)
        self.assertIn(" … ", printed)
        self.assertTrue(printed.endswith(f"{instruction}；繼續啟動伺服器\n"))

    def test_ctrl_c_during_the_seed_still_stops_the_launch(self):
        calls = []
        with mock.patch.object(launch, "ensure_env", lambda path: False), \
                mock.patch.object(launch, "seed_demo", self.seed_raising(KeyboardInterrupt())), \
                mock.patch.object(launch, "open_in_background", lambda: calls.append("open")), \
                mock.patch("uvicorn.run", lambda app, **options: calls.append("serve")), \
                self.assertRaises(KeyboardInterrupt):
            launch.main(Path(tempfile.mkdtemp()))
        self.assertEqual(calls, [])

    def test_a_seed_that_works_prints_no_warning(self):
        calls, printed, complained = self.launch(lambda: None)
        self.assertEqual((calls, printed, complained), (["env", "open", "serve"], "", ""))


if __name__ == "__main__":
    unittest.main()
