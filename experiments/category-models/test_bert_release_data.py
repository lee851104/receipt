"""Only fictional records; test-file access must fail throughout preparation/training."""
import importlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from common import fingerprint
from prepare_data import write_json
import test_bert_ratio_cv

class ReleaseTests(unittest.TestCase):
 def setUp(self):
  self.data=importlib.import_module('bert_release_data')
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def fixture(self):
  import bert_ratio_cv
  helper=test_bert_ratio_cv.RatioCVTests();helper.root=self.root
  source=helper.fixture();cv=self.root/'cv';bert_ratio_cv.prepare(source,cv)
  write_json(cv/'summary.json',dict(plan_sha256=fingerprint(cv/'plan.json'),results={'synthetic_25':{}}))
  return source,cv
 def test_no_test_access_preserves_split_and_ratio(self):
  src,cv=self.fixture();out=self.root/'release';original=Path.open
  def guard(p,*a,**kw):
   if p.name=='test.jsonl':raise AssertionError('test opened')
   return original(p,*a,**kw)
  with patch.object(Path,'open',guard):
   result=self.data.prepare(src,cv,out)
   parts,manifest,identity=self.data.load(out)
  self.assertEqual(result['train']['real'],160)
  self.assertEqual(result['train']['synthetic'],53)
  self.assertEqual(result['validation']['real'],40)
  self.assertEqual(set(parts),{'train','validation'})
  self.assertFalse((out/'test.jsonl').exists())
  from dataset_split import read_rows
  self.assertEqual(parts['validation'],read_rows(src/'validation.jsonl'))
  self.assertEqual([r for r in parts['train'] if r['source']=='real'],[r for r in read_rows(src/'train.jsonl') if r['source']=='real'])
  with self.assertRaises(FileExistsError):self.data.prepare(src,cv,out)
  with (out/'train.jsonl').open('a') as stream:stream.write('\n')
  with self.assertRaises(ValueError):self.data.load(out)
 def test_reject_cv_source_and_summary_changes(self):
  src,cv=self.fixture();out=self.root/'release'
  report=cv/'summary.json';saved=report.read_bytes()
  write_json(report,dict(plan_sha256='wrong',results={'synthetic_25':{}}))
  with self.assertRaises(ValueError):self.data.prepare(src,cv,out)
  report.write_bytes(saved);self.data.prepare(src,cv,out)
  with report.open('a') as stream:stream.write('\n')
  with self.assertRaises(ValueError):self.data.load(out)
 def test_tiny_training_no_test_read_reload_and_no_warm_start(self):
  import bert_finetune
  from test_embedding_lr import EmbeddingTest
  src,cv=self.fixture();folder=self.root/'release';self.data.prepare(src,cv,folder)
  maker=EmbeddingTest();maker.root=self.root;base=maker.encoder_fixture()
  original=Path.open
  def guard(p,*a,**kw):
   if p.name=='test.jsonl':raise AssertionError('test opened')
   return original(p,*a,**kw)
  with patch.object(Path,'open',guard):
   report=bert_finetune.run(folder,base,self.root/'run',device='cpu',epochs=2,benchmark_count=3,development_only=True)
  self.assertTrue(report['reload_verified'])
  self.assertEqual(report['test_access'],'not_opened')
  self.assertEqual(report['test_evaluation'],'not_run')
  self.assertEqual(report['training_sources'],{'real':160,'synthetic':53})
  self.assertEqual(report['validation']['model']['support'],40)
  with self.assertRaises(ValueError):
   bert_finetune.run(folder,base,self.root/'warm',device='cpu',warm_start=True,development_only=True)
  (base/'classifier-manifest.json').write_text('{}')
  with self.assertRaises(ValueError):
   bert_finetune.run(folder,base,self.root/'bad',device='cpu',development_only=True)

 def test_reject_false_ratio_metadata(self):
  src,cv=self.fixture();out=self.root/'release';self.data.prepare(src,cv,out)
  path=out/'manifest.json';metadata=json.loads(path.read_text(encoding='utf-8'))
  metadata['actual_synthetic_fraction']=.99;write_json(path,metadata)
  with self.assertRaises(ValueError):self.data.load(out)

if __name__=='__main__':unittest.main()
