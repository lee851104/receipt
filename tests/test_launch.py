"""What start.bat runs: a .env when there is none, the demo users, the pages opened once the server answers."""
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


if __name__ == "__main__":
    unittest.main()
