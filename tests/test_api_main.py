"""The module uvicorn serves starts from the environment alone, and a setting it cannot use stops it in one line."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = "test-secret-0123456789abcdef0123456789"
IMPORT = "import src.api.main as main; print(type(main.app).__name__)"


def start(*, missing_attributes=False, **changes):
    """Import src.api.main in a fresh Python. Variables set here win over a local .env, which never overrides them.
    missing_attributes hides role 3's src/ml/attributes.py from that Python, as it was before its branch was merged."""
    variables = {**os.environ, "JWT_SECRET": SECRET, "DATABASE_URL": "sqlite://", "DEMO_MODE": "0",
                 "CATEGORY_MODEL": "fake", "ATTRIBUTES_MODEL": "fake", **changes}
    hide = 'import sys; sys.modules["src.ml.attributes"] = None; ' if missing_attributes else ""
    return subprocess.run([sys.executable, "-c", hide + IMPORT], cwd=ROOT, env=variables, capture_output=True,
                          text=True, encoding="utf-8", timeout=120)


class MainTests(unittest.TestCase):
    def test_the_app_starts_with_the_models_settings_ask_for(self):
        result = start()
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "FastAPI"), result.stderr)

    def test_a_model_that_is_not_there_yet_stops_it_in_one_line(self):
        # Role 3's src/ml/attributes.py is merged now, so the qwen case hides it from the subprocess: the check that
        # a missing module stops the server in one line must keep working for a checkout that lacks the file.
        for changes, message in (
                ({"CATEGORY_MODEL": "tfidf"}, "error: CATEGORY_MODEL=tfidf does not work yet"),
                ({"ATTRIBUTES_MODEL": "qwen", "missing_attributes": True},
                 "error: ATTRIBUTES_MODEL=qwen needs src/ml/attributes.py")):
            with self.subTest(changes=changes):
                result = start(**changes)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
                self.assertTrue(result.stderr.startswith(message), result.stderr)

    def test_qwen_starts_now_that_role_3s_module_is_merged(self):
        result = start(ATTRIBUTES_MODEL="qwen", LLAMA_SERVER_URL="http://127.0.0.1:8080")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "FastAPI"), result.stderr)

    def test_bert_without_its_model_still_starts_and_says_so_in_one_line(self):
        with tempfile.TemporaryDirectory() as folder:
            result = start(CATEGORY_MODEL="bert", CATEGORY_MODEL_DIR=folder)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "FastAPI"), result.stderr)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertIn("the category model is unavailable", result.stderr)
