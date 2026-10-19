"""Installation must never overwrite another release or copy training records."""
import tempfile,unittest
from pathlib import Path
from src.ml.category import digest
from scripts.install_category_model import install
from tests.test_category_model import bundle
class InstallTests(unittest.TestCase):
    def test_verified_whitelist_install_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"source";source.mkdir();bundle(source)
            target=root/"installed"
            result=install(source,target,digest(source/"model.safetensors"))
            self.assertTrue((target/"model.safetensors").is_file())
            self.assertEqual(result["model_sha256"],digest(target/"model.safetensors"))
            self.assertEqual({p.name for p in target.iterdir()},{p.name for p in source.iterdir()})
            with self.assertRaises(FileExistsError):install(source,target,result["model_sha256"])
            self.assertTrue((target/"model.safetensors").is_file())
    def test_bad_hash_or_extra_file_never_creates_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/"source";source.mkdir();bundle(source)
            for extra in (False,True):
                if extra:(source/"training.jsonl").write_text("fictional")
                with self.assertRaises(ValueError):install(source,root/"installed","0"*64)
                self.assertFalse((root/"installed").exists())
