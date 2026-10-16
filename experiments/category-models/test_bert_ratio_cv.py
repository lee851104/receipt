"""Fictional regression tests for grouped ratio CV."""
import importlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from prepare_data import write_json,write_jsonl
from common import fingerprint
class RatioCVTests(unittest.TestCase):
 def setUp(self):
  self.cv=importlib.import_module('bert_ratio_cv')
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def fixture(self):
  src=self.root/'source';src.mkdir()
  real=[dict(id=f'r{c}-{i}',name=f'fictional real {c} {i}',category=c,group=f'g{c}-{i//2}',source='real',review_status='human_confirmed') for c in range(10) for i in range(20)]
  synth=[dict(id=f's{c}-{i}',name=f'fictional synthetic {c} {i}',category=c,group=f's{c}-{i}',source='synthetic',review_status='synthetic_generated') for c in range(10) for i in range(40)]
  train=[r for r in real if int(r['id'].split('-')[1])<16]+synth;val=[r for r in real if int(r['id'].split('-')[1])>=16]
  for p,rows in [('train',train),('validation',val)]:write_jsonl(src/f'{p}.jsonl',rows)
  from dataset_split import audit_split
  write_json(src/'manifest.json',dict(schema_version='bert-continuation-1',summary=audit_split(dict(train=train,validation=val,test=[])),files_sha256={p:fingerprint(src/f'{p}.jsonl') for p in ('train','validation')}))
  (src/'test.jsonl').write_text('DO NOT READ THIS FILE')
  return src
 def test_shared_folds_ratios_no_test_access_and_tamper(self):
  src=self.fixture();out=self.root/'cv';orig=Path.open
  def guard(p,*a,**kw):
   if p.name=='test.jsonl':raise AssertionError('test touched')
   return orig(p,*a,**kw)
  with patch.object(Path,'open',guard):
   self.assertEqual(self.cv.prepare(src,out)['real_count'],200)
   outer_all=[]
   for fold in range(5):
    reference=None;subsets={}
    for regime in self.cv.REGIMES:
     parts,plan=self.cv.load_fold(out,fold,regime)
     groups=[{r['group'] for r in parts[p]} for p in ('train','inner','outer')]
     self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
     self.assertTrue(all(r['source']=='real' for p in ('inner','outer') for r in parts[p]))
     ids={r['id'] for r in parts['outer']}
     if reference is None:reference=ids;outer_all.extend(ids)
     self.assertEqual(reference,ids)
     nr=sum(r['source']=='real' for r in parts['train']);ns=len(parts['train'])-nr
     subsets[regime]={r['id'] for r in parts['train'] if r['source']=='synthetic'}
     if regime=='real_only':self.assertEqual(ns,0)
     elif regime=='synthetic_25':self.assertLessEqual(abs(ns-nr/3),1)
     else:self.assertLessEqual(abs(ns/nr-400/160),.01)
    self.assertTrue(subsets['synthetic_25']<=subsets['synthetic_current'])
   self.assertEqual(len(outer_all),len(set(outer_all)));self.assertEqual(len(outer_all),200)
  with self.assertRaises(FileExistsError):self.cv.prepare(src,out)
  with (out/'fold-0/inner.jsonl').open('a') as f:f.write('\n')
  with self.assertRaises(ValueError):self.cv.load_fold(out,0,'real_only')
 def test_train_selects_inner_and_predicts_outer_once(self):
  src=self.fixture();out=self.root/'cv';self.cv.prepare(src,out)
  from test_embedding_lr import EmbeddingTest
  maker=EmbeddingTest();maker.root=self.root;base=maker.encoder_fixture()
  parts,_=self.cv.load_fold(out,0,'real_only')
  fitted=[];validated=[];predicted=[]
  fit=self.cv.train_epoch;val=self.cv.validation_loss;pred=self.cv.Classifier.predict
  def fit_spy(m,t,rows,*args):fitted.extend(r['id'] for r in rows);return fit(m,t,rows,*args)
  def val_spy(m,t,rows,*args):validated.extend(r['id'] for r in rows);return val(m,t,rows,*args)
  def pred_spy(m,names):predicted.extend(names);return pred(m,names)
  with patch.object(self.cv,'train_epoch',fit_spy),patch.object(self.cv,'validation_loss',val_spy),patch.object(self.cv.Classifier,'predict',pred_spy):
   result=self.cv.train_fold(out,base,0,'real_only',device='cpu',epochs=2)
  self.assertEqual(set(fitted),{r['id'] for r in parts['train']})
  self.assertEqual(set(validated),{r['id'] for r in parts['inner']})
  self.assertEqual(predicted,[r['name'] for r in parts['outer']])
  self.assertEqual(result['outer']['support'],len(parts['outer']))
  self.assertEqual(result['best_epoch'],min(result['history'],key=lambda h:h['inner_loss'])['epoch'])
  with self.assertRaises(FileExistsError):self.cv.train_fold(out,base,0,'real_only',device='cpu',epochs=2)
  with self.assertRaises(ValueError):self.cv.summarize_runs(out)
 def test_corrupt_source(self):
  src=self.fixture()
  with (src/'train.jsonl').open('a') as f:f.write('\n')
  with self.assertRaises(ValueError):self.cv.prepare(src,self.root/'cv')
if __name__=='__main__':unittest.main()
