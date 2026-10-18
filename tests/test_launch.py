"""What start.bat runs: a .env when there is none, the demo users, the pages opened once the server answers."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.api import launch

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


class DemoSeedRefusesTests(unittest.TestCase):
    """Demo users are optional: a seed that stops must not keep a person's own accounts and data from starting."""

    def launch(self, seed):
        """What main did, in order, and what it printed, when the demo seed is the given function."""
        calls, printed = [], io.StringIO()
        with mock.patch.object(launch, "ensure_env", lambda path: calls.append("env") or False), \
                mock.patch.object(launch, "seed_demo", seed), \
                mock.patch.object(launch, "open_in_background", lambda: calls.append("open")), \
                mock.patch("uvicorn.run", lambda app, **options: calls.append("serve")), \
                contextlib.redirect_stdout(printed):
            launch.main(Path(tempfile.mkdtemp()))
        return calls, printed.getvalue()

    def seed_raising(self, error):
        def seed():
            raise error
        return seed

    def test_a_seed_that_exits_with_a_message_prints_one_line_and_the_server_still_starts(self):
        calls, printed = self.launch(self.seed_raising(SystemExit("error: demo_001 is 'x' in the database")))
        self.assertEqual(calls, ["env", "open", "serve"])
        self.assertEqual(printed, "示範帳號沒有更新：error: demo_001 is 'x' in the database；伺服器照常啟動\n")

    def test_a_seed_that_fails_otherwise_prints_its_type_and_message_and_the_server_still_starts(self):
        calls, printed = self.launch(self.seed_raising(RuntimeError("a later seed broke")))
        self.assertEqual(calls, ["env", "open", "serve"])
        self.assertEqual(printed, "示範帳號沒有更新：RuntimeError: a later seed broke；伺服器照常啟動\n")

    def test_the_reason_is_one_short_line_without_a_traceback(self):
        reasons = [SystemExit(1), SystemExit(), RuntimeError(), ValueError("first\nsecond\n  third"),
                   SystemExit("error: " + "demo_001 is not who it should be; " * 40)]
        for error in reasons:
            with self.subTest(error=repr(error)[:40]):
                _, printed = self.launch(self.seed_raising(error))
                self.assertEqual(len(printed.splitlines()), 1)
                self.assertTrue(printed.startswith("示範帳號沒有更新：") and printed.endswith("；伺服器照常啟動\n"))
                self.assertLess(len(printed), 300)
                self.assertNotIn("Traceback", printed)
        self.assertIn("ValueError: first second third；", self.launch(self.seed_raising(reasons[3]))[1])

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
        calls, printed = self.launch(lambda: None)
        self.assertEqual((calls, printed), (["env", "open", "serve"], ""))


if __name__ == "__main__":
    unittest.main()
