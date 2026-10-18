"""Regression checks for Claude's role-2 review; fictional inputs only."""
import os
import unittest
from unittest import mock
from src.api import container
from src.api.settings import Settings
from tests.api_support import SECRET
from tests import test_category_model as fixtures

class SourcePolicyTests(unittest.TestCase):
    def env(self):
        return dict(JWT_SECRET=SECRET, CATEGORY_MODEL="bert", CATEGORY_MODEL_REPO="owner/fictional",
                    CATEGORY_MODEL_REVISION="a"*40)

    def test_model_repo_is_rejected_before_container_download(self):
        env=self.env()
        with self.assertRaisesRegex(ValueError, "remote downloads require CATEGORY_MODEL_REPO_TYPE=space"):
            Settings.from_env(env)
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(container, "ensure_category_model") as download:
            with self.assertRaisesRegex(SystemExit, "remote downloads require CATEGORY_MODEL_REPO_TYPE=space"):
                container.main()
            download.assert_not_called()

    def test_local_bert_and_fake_are_still_valid(self):
        env=self.env(); env["CATEGORY_MODEL_REPO"]=""
        self.assertEqual(Settings.from_env(env).category_model, "bert")
        env=self.env(); env["CATEGORY_MODEL"]="fake"
        self.assertEqual(Settings.from_env(env).category_model, "fake")

    def test_pinned_space_is_valid(self):
        env=self.env(); env.update(CATEGORY_MODEL_REPO_TYPE="space", CATEGORY_MODEL_SHA256="b"*64)
        self.assertEqual(Settings.from_env(env).category_model_repo_type, "space")

class BatchLockTests(unittest.TestCase):
    def test_long_request_releases_lock_between_batches(self):
        fixture=fixtures.CategoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        classify=fixture.load(batch_size=2)
        released=[]
        class TrackedLock:
            def __enter__(self): return self
            def __exit__(self,*args): released.append(len(fixture.tokenizer.calls))
        classify.lock=TrackedLock()
        classify(["示範"+str(i) for i in range(5)])
        self.assertEqual(released,[1,2,3])
