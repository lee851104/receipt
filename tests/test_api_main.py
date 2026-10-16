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


def start(**changes):
    """Import src.api.main in a fresh Python. Variables set here win over a local .env, which never overrides them."""
    variables = {**os.environ, "JWT_SECRET": SECRET, "DATABASE_URL": "sqlite://", "DEMO_MODE": "0",
                 "CATEGORY_MODEL": "fake", "ATTRIBUTES_MODEL": "fake", **changes}
    return subprocess.run([sys.executable, "-c", IMPORT], cwd=ROOT, env=variables, capture_output=True,
                          text=True, encoding="utf-8", timeout=120)


class MainTests(unittest.TestCase):
    def test_the_app_starts_with_the_models_settings_ask_for(self):
        result = start()
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "FastAPI"), result.stderr)

    def test_a_model_that_is_not_there_yet_stops_it_in_one_line(self):
        # The subprocess has no role 3 file src/ml/attributes.py, so qwen stops it until that branch is merged.
        for changes, message in (({"CATEGORY_MODEL": "tfidf"}, "error: CATEGORY_MODEL=tfidf does not work yet"),
                                 ({"ATTRIBUTES_MODEL": "qwen"}, "error: ATTRIBUTES_MODEL=qwen needs src/ml/attributes.py")):
            with self.subTest(changes=changes):
                result = start(**changes)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
                self.assertTrue(result.stderr.startswith(message), result.stderr)

    def test_bert_without_its_model_still_starts_and_says_so_in_one_line(self):
        with tempfile.TemporaryDirectory() as folder:
            result = start(CATEGORY_MODEL="bert", CATEGORY_MODEL_DIR=folder)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "FastAPI"), result.stderr)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertIn("the category model is unavailable", result.stderr)
