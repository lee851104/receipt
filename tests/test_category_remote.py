"""Protected Space download tests; all fixture weights and manifests are fictional."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.ml.category import digest, verified_manifest
from src.ml.category_remote import download_space_model
from src.api.settings import Settings
from src.api import container, backends
from tests.test_category_model import bundle
from tests.api_support import SECRET

class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/"source"; self.source.mkdir()
        meta = bundle(self.source)
        self.sha = meta["files"]["model.safetensors"]
        self.manifest = {"format":"category-demo-1","categories":meta["categories"],
                         "models":{"bert":{"max_length":32,"files":{"bert/"+n:v for n,v in meta["files"].items()}}}}
        self.calls = []
        self.destination = self.root/"installed"

    def fetch(self, **kw):
        self.calls.append(kw)
        if kw["filename"] == "models/manifest.json":
            p = self.root/"remote-manifest.json"
            p.write_text(json.dumps(self.manifest),encoding="utf-8")
            return str(p)
        return str(self.source/Path(kw["filename"]).name)

    def run_download(self, **changes):
        args = dict(repo_id="owner/protected", revision="a"*40, destination=self.destination,
                    expected_sha256=self.sha, token="fictional-secret", fetch=self.fetch)
        return download_space_model(**{**args, **changes})

    def test_white_list_fixed_revision_clean_install_and_offline_reuse(self):
        self.assertEqual(self.run_download(), "downloaded")
        self.assertEqual(digest(self.destination/"model.safetensors"),self.sha)
        self.assertEqual(set(verified_manifest(self.destination)),{"format_version","categories","files","max_length"})
        self.assertEqual(len(self.calls),5)
        self.assertEqual({c["repo_type"] for c in self.calls},{"space"})
        self.assertEqual({c["revision"] for c in self.calls},{"a"*40})
        self.assertEqual({c["endpoint"] for c in self.calls},{"https://huggingface.co"})
        self.assertTrue(all(c["force_download"] for c in self.calls))
        self.assertTrue(all(c["token"] == "fictional-secret" for c in self.calls))
        self.calls.clear()
        self.assertEqual(self.run_download(token=False), "present")
        self.assertEqual(self.calls,[])
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),["installed","remote-manifest.json","source"])

    def test_invalid_revision_hash_and_repo_fail_before_network(self):
        for changes in ({"revision":"main"},{"revision":"abc123"},{"expected_sha256":"wrong"},{"repo_id":"https://bad"},
                        {"repo_id":"../private"}):
            with self.subTest(changes=changes),self.assertRaises(RuntimeError):
                self.run_download(**changes)
        self.assertEqual(self.calls,[])
        self.assertFalse(self.destination.exists())

    def test_missing_credential_and_remote_error_do_not_echo_secret(self):
        for token in (None,False,""):
            with patch("src.ml.category_remote.local_token",return_value=None):
                with self.assertRaisesRegex(RuntimeError,"category_download_failed"):
                    self.run_download(token=token)
        def broken(**kw):
            raise RuntimeError("fictional-secret private-item https://signed.invalid")
        with self.assertRaises(RuntimeError) as caught:
            self.run_download(fetch=broken)
        self.assertEqual(str(caught.exception),"category_download_failed")
        self.assertFalse(self.destination.exists())

    def test_manifest_traversal_extra_file_wrong_labels_or_weight_hash_rejected(self):
        original=json.loads(json.dumps(self.manifest))
        for mutate in (
            lambda m: m["models"]["bert"]["files"].update({"bert/../../escape":"0"*64}),
            lambda m: m["models"]["bert"]["files"].update({"bert/training.jsonl":"0"*64}),
            lambda m: m["models"]["bert"]["files"].__setitem__("bert/model.safetensors","0"*64),
            lambda m: m.__setitem__("categories",list(reversed(m["categories"]))),
            lambda m: m["models"]["bert"].__setitem__("max_length",True),
        ):
            self.manifest=json.loads(json.dumps(original)); mutate(self.manifest); self.calls=[]
            with self.assertRaises(RuntimeError): self.run_download()
            self.assertEqual(len(self.calls),1)
            self.assertFalse(self.destination.exists())

    def test_corruption_and_existing_unrelated_directory_are_preserved(self):
        (self.source/"tokenizer.json").write_text("corrupted")
        with self.assertRaises(RuntimeError):self.run_download()
        self.assertFalse(self.destination.exists())
        self.destination.mkdir(); (self.destination/"notes.txt").write_text("keep")
        self.calls.clear()
        with self.assertRaises(RuntimeError):self.run_download()
        self.assertEqual((self.destination/"notes.txt").read_text(),"keep")
        self.assertEqual(self.calls,[])

    def settings(self, **kw):
        return Settings(jwt_secret=SECRET,category_model="bert",category_model_dir=str(self.destination),
                        category_model_repo="owner/protected",category_model_revision="a"*40,
                        category_model_repo_type="space",category_model_sha256=self.sha,**kw)

    def test_container_dispatch_and_pin_enforcement_before_loading(self):
        with patch("src.ml.category_remote.download_space_model",return_value="downloaded") as remote:
            self.assertEqual(container.ensure_category_model(self.settings()),"downloaded")
            self.assertEqual(remote.call_args.kwargs["expected_sha256"],self.sha)
        with patch("src.ml.category_remote.download_space_model",side_effect=RuntimeError("secret")):
            with self.assertLogs("src.api.container",level="WARNING") as logs:
                self.assertEqual(container.ensure_category_model(self.settings()),"failed")
            self.assertNotIn("secret"," ".join(logs.output))
        self.destination.mkdir(); bundle(self.destination)
        with patch("src.ml.category.load") as loader:
            settings=Settings(jwt_secret=SECRET,category_model="bert",category_model_dir=str(self.destination),
                              category_model_sha256="0"*64)
            with self.assertLogs("src.api.backends",level="WARNING"):
                self.assertEqual(backends.category_backend(settings)[0],"unavailable")
            loader.assert_not_called()

    def test_settings_reject_unpinned_space_and_unknown_repo_type(self):
        env={"JWT_SECRET":SECRET,"CATEGORY_MODEL_REPO":"owner/protected","CATEGORY_MODEL_REPO_TYPE":"space",
             "CATEGORY_MODEL_REVISION":"a"*40,"CATEGORY_MODEL_SHA256":self.sha}
        settings=Settings.from_env(env)
        self.assertEqual(settings.category_model_repo_type,"space")
        self.assertEqual(settings.category_model_sha256,self.sha)
        for changes in ({"CATEGORY_MODEL_REVISION":"main"},{"CATEGORY_MODEL_SHA256":""},
                        {"CATEGORY_MODEL_REPO_TYPE":"dataset"}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                Settings.from_env({**env,**changes})
