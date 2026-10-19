"""Fictional fixtures only; no torch/private data required."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace
from src.ml import category
from tests.model_contract import check_classify
from tests.api_support import SECRET
from src.api.settings import Settings
from src.api.backends import load_backends

def bundle(path):
    files={"config.json":json.dumps({"model_type":"bert","id2label":{str(i):n for i,n in enumerate(category.CATEGORIES)}}),
           "model.safetensors":"fictional-weights","tokenizer_config.json":"{}","tokenizer.json":"{}"}
    for n,t in files.items():(path/n).write_text(t,encoding="utf-8")
    meta={"format_version":"bert-category-1","categories":list(category.CATEGORIES),"max_length":32,
          "files":{n:hashlib.sha256((path/n).read_bytes()).hexdigest() for n in files}}
    (path/"classifier-manifest.json").write_text(json.dumps(meta),encoding="utf-8")
    return meta

class Rows:
    def __init__(self,rows):self.rows=rows
    def softmax(self,dim):return self
    def cpu(self):return self
    def tolist(self):return self.rows
class FakeTokenizer:
    def __init__(self):self.calls=[]
    def __call__(self,names,**kw):
        self.calls.append((names,kw));return {"names":names}
class FakeModel:
    def __init__(self):
        self.config=SimpleNamespace(num_labels=10,model_type="bert",id2label=dict(enumerate(category.CATEGORIES)))
        self.bad=None;self.active=0;self.peak=0
    def to(self,**kw):return self
    def eval(self):return self
    def __call__(self,names):
        import time
        self.active+=1;self.peak=max(self.peak,self.active);time.sleep(.002)
        try:
            if self.bad=="raise":raise RuntimeError(names[0])
            rows=[[.91 if i==sum(map(ord,n))%10 else .01 for i in range(10)] for n in names]
            if self.bad=="nan":rows[0][0]=float("nan")
            if self.bad=="count":rows=[]
            return SimpleNamespace(logits=Rows(rows))
        finally:self.active-=1
class CategoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name);bundle(self.path);self.model=FakeModel();self.tokenizer=FakeTokenizer()
        self.torch=SimpleNamespace(float32="float32",set_num_threads=mock.Mock(),inference_mode=nullcontext)
        self.tokenloader=mock.Mock(return_value=self.tokenizer)
        self.modelloader=mock.Mock(return_value=(self.model,{}))
        self.dependencies=(self.torch,SimpleNamespace(from_pretrained=self.tokenloader),SimpleNamespace(from_pretrained=self.modelloader))
    def load(self,**kw):
        with mock.patch.object(category,"_dependencies",return_value=self.dependencies):return category.load(self.path,**kw)
    def test_contract_batch_order_normalization_and_lock(self):
        classify=self.load(batch_size=2);check_classify(self,classify)
        self.assertEqual(classify(["  ＡＢＣ  "]),classify(["ABC"]))
        names=["示範品項"+str(i) for i in range(7)]
        self.assertEqual(classify(names),sum([classify([n]) for n in names],[]))
        with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(classify,[names]*3))
        self.assertEqual(self.model.peak,1)
        self.assertTrue(all(len(v[0])<=2 for v in self.tokenizer.calls))
        for loader in (self.tokenloader,self.modelloader):
            self.assertTrue(loader.call_args.kwargs["local_files_only"]);self.assertFalse(loader.call_args.kwargs["trust_remote_code"])
        self.assertTrue(self.modelloader.call_args.kwargs["use_safetensors"])
    def test_invalid_input_and_runtime_errors_do_not_echo_names(self):
        classify=self.load()
        for names in ("secret-name",[None],["   "]):
            with self.assertRaisesRegex(ValueError,"invalid_category_input"):classify(names)
        for issue in ("nan","count","raise"):
            self.model.bad=issue
            with self.assertRaisesRegex(RuntimeError,"category_inference_failed") as caught:classify(["DO-NOT-ECHO"])
            self.assertNotIn("DO-NOT-ECHO",str(caught.exception))
    def test_manifest_rejects_invalid_files_before_dependencies(self):
        for change in ("digest","traversal","max_length","labels","extra","missing"):
            with self.subTest(change=change):
                meta=bundle(self.path)
                if change=="digest":meta["files"]["model.safetensors"]="0"*64
                if change=="traversal":meta["files"]["../outside"]="0"*64
                if change=="max_length":meta["max_length"]=True
                if change=="labels":meta["categories"]=list(reversed(category.CATEGORIES))
                if change=="extra":(self.path/"arbitrary.py").write_text("no")
                if change=="missing":(self.path/"model.safetensors").unlink()
                (self.path/"classifier-manifest.json").write_text(json.dumps(meta),encoding="utf-8")
                with mock.patch.object(category,"_dependencies") as deps:
                    with self.assertRaisesRegex(RuntimeError,"category_model_unavailable"):category.load(self.path)
                    deps.assert_not_called()
                (self.path/"arbitrary.py").unlink(missing_ok=True)
    def test_random_head_wrong_labels_and_missing_dependencies_rejected(self):
        for issue in ("missing_keys","unexpected_keys","mismatched_keys","error_msgs"):
            self.modelloader.return_value=(self.model,{issue:["bad"]})
            with self.assertRaisesRegex(RuntimeError,"category_model_unavailable"):self.load()
        self.modelloader.return_value=(self.model,{})
        self.model.config.id2label={i:str(i) for i in range(10)}
        with self.assertRaisesRegex(RuntimeError,"category_model_unavailable"):self.load()
        with mock.patch.object(category,"_dependencies",side_effect=ImportError("private-token")):
            with self.assertRaisesRegex(RuntimeError,"category_model_unavailable") as caught:category.load(self.path)
            self.assertNotIn("private-token",str(caught.exception))
    def test_backend_loads_once_and_failure_is_unavailable_without_details(self):
        settings=Settings(jwt_secret=SECRET,category_model="bert",category_model_dir=str(self.path));classify=self.load()
        with mock.patch.object(category,"load",return_value=classify) as loader:
            backends=load_backends(settings);check_classify(self,backends.classify)
            self.assertEqual(backends.category,"bert");loader.assert_called_once_with(self.path)
        with mock.patch.object(category,"load",side_effect=RuntimeError("DO-NOT-ECHO")):
            with self.assertLogs("src.api.backends",level="WARNING") as logs:backends=load_backends(settings)
            self.assertEqual(backends.category,"unavailable");self.assertNotIn("DO-NOT-ECHO"," ".join(logs.output))
            with self.assertRaises(RuntimeError):backends.classify(["示範"])
    def test_invalid_batch_and_threads_rejected(self):
        for kw in ({"batch_size":0},{"batch_size":True},{"threads":0},{"threads":True}):
            with self.assertRaisesRegex(RuntimeError,"category_model_unavailable"):self.load(**kw)
