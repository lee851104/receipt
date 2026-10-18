"""Fictional-only tests for paired seeds on fixed grouped folds."""
import importlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_bert_ratio_cv
from common import fingerprint
from prepare_data import write_json,write_jsonl,CATEGORIES
from embedding_features import local_manifest

class MultiSeedTests(unittest.TestCase):
 def setUp(self):
  self.ms=importlib.import_module('bert_multiseed_cv')
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def fixture(self):
  import bert_ratio_cv as cv
  from test_embedding_lr import EmbeddingTest
  helper=test_bert_ratio_cv.RatioCVTests();helper.root=self.root
  src=helper.fixture();parent=self.root/'parent';cv.prepare(src,parent)
  maker=EmbeddingTest();maker.root=self.root;base=maker.encoder_fixture()
  config=dict(epochs=1,lr=2e-5,batch_size=16,max_length=32,weight_decay=.01,patience=2,min_delta=1e-4,device='cpu',initialization='public_encoder',encoder=local_manifest(base),plan_sha256=fingerprint(parent/'plan.json'))
  write_json(parent/'training-config.json',config)
  return src,parent,base
 def test_protocol_no_test_access_groups_and_source_freeze(self):
  src,parent,base=self.fixture();out=self.root/'repeat';original=Path.open
  def guard(p,*a,**kw):
   if p.name=='test.jsonl':raise AssertionError('test opened')
   return original(p,*a,**kw)
  with patch.object(Path,'open',guard):
   protocol=self.ms.prepare(parent,out)
   self.ms.load(out)
  self.assertEqual(protocol['seeds'],[42,43,44]);self.assertEqual(protocol['expected_runs'],30)
  self.assertEqual(protocol['groups']['count'],100);self.assertEqual(protocol['groups']['multi_item'],100)
  with self.assertRaises(FileExistsError):self.ms.prepare(parent,out)
  with self.assertRaises(ValueError):self.ms.prepare(parent,parent/'bad')
  with (parent/'training-config.json').open('a') as f:f.write('\n')
  with self.assertRaises(ValueError):self.ms.load(out)
 def test_seed_override_output_isolation_and_inner_only(self):
  import bert_ratio_cv as cv
  src,parent,base=self.fixture();out=self.root/'repeat';self.ms.prepare(parent,out)
  before=fingerprint(parent/'training-config.json');trained=[];inner=[];predicted=[]
  fit,val,pred=cv.train_epoch,cv.validation_loss,cv.Classifier.predict
  def fit_spy(m,t,rows,*args):trained.extend(r['id'] for r in rows);return fit(m,t,rows,*args)
  def val_spy(m,t,rows,*args):inner.extend(r['id'] for r in rows);return val(m,t,rows,*args)
  def pred_spy(m,names):predicted.extend(names);return pred(m,names)
  with patch.object(cv,'train_epoch',fit_spy),patch.object(cv,'validation_loss',val_spy),patch.object(cv.Classifier,'predict',pred_spy):
   report=self.ms.train(out,base,0,'synthetic_25',43)
  parts,_=cv.load_fold(parent,0,'synthetic_25')
  self.assertEqual(set(trained),{r['id'] for r in parts['train']})
  self.assertEqual(set(inner),{r['id'] for r in parts['inner']})
  self.assertEqual(predicted,[r['name'] for r in parts['outer']])
  self.assertEqual(report['seed'],43);self.assertEqual(fingerprint(parent/'training-config.json'),before)
  self.assertFalse((parent/'runs').exists())
  with self.assertRaises(FileExistsError):self.ms.train(out,base,0,'synthetic_25',43)
  with self.assertRaises(ValueError):self.ms.train(out,base,0,'synthetic_25',99)
  for seed in (True,-1,2**32):
   with self.assertRaises(ValueError):cv.train_fold(parent,base,0,'synthetic_25',device='cpu',epochs=1,seed=seed,output_root=self.root/'bad')
  with self.assertRaises(ValueError):cv.train_fold(parent,base,0,'synthetic_25',seed=42,output_root=parent)
  with self.assertRaises(ValueError):cv.train_fold(parent,base,0,'synthetic_25',seed=42)
 def test_complete_30_run_summary_not_independent_triple_sample_and_tamper(self):
  import bert_ratio_cv as cv
  from bert_model import save_bundle
  from evaluate_reviewed import summarize
  from transformers import AutoTokenizer,BertForSequenceClassification
  src,parent,base=self.fixture();out=self.root/'repeat';protocol=self.ms.prepare(parent,out)
  with self.assertRaises(ValueError):self.ms.summarize_runs(out)
  tok=AutoTokenizer.from_pretrained(base,local_files_only=True)
  model=BertForSequenceClassification.from_pretrained(base,num_labels=10,local_files_only=True)
  for seed in protocol['seeds']:
   seedroot=out/f'seed-{seed}';seedroot.mkdir()
   cfg=dict(protocol['training_config'],initialization_seed=seed);write_json(seedroot/'training-config.json',cfg)
   for regime,divisor in [('synthetic_25',10),('synthetic_current',5)]:
    for fold in range(5):
     parts,plan=cv.load_fold(parent,fold,regime)
     run=seedroot/'runs'/f'{regime}-fold-{fold}';run.mkdir(parents=True)
     preds=[dict(id=r['id'],actual=r['category'],predicted=(r['category']+1)%10 if i%divisor==0 else r['category']) for i,r in enumerate(parts['outer'])]
     write_jsonl(run/'private-outer-predictions.jsonl',preds)
     save_bundle(model,tok,run/'model',dict(categories=list(CATEGORIES),max_length=32,dataset_sha256=protocol['parent_plan_sha256'],seed=seed,cv_fold=fold,cv_regime=regime,pretrained=local_manifest(base)))
     write_json(run/'report.json',dict(fold=fold,regime=regime,seed=seed,best_epoch=1,outer=summarize([p['actual'] for p in preds],[p['predicted'] for p in preds]),training_counts=plan['folds'][fold]['counts'][regime],training_seconds=1,gradient_steps=1,plan_sha256=protocol['parent_plan_sha256'],config_sha256=fingerprint(seedroot/'training-config.json'),predictions_sha256=fingerprint(run/'private-outer-predictions.jsonl'),model_manifest_sha256=fingerprint(run/'model/classifier-manifest.json'),original_test='not_opened_or_evaluated'))
  result=self.ms.summarize_runs(out)
  self.assertEqual(result['unique_real_items'],200);self.assertEqual(result['completed_runs'],30)
  self.assertAlmostEqual(result['results']['synthetic_25']['mean_accuracy'],.9)
  self.assertEqual(result['results']['synthetic_25']['seed_mean_sd'],0)
  self.assertEqual(result['paired']['wins_25'],15)
  self.assertAlmostEqual(result['paired']['mean_delta_pp'],10)
  rp=out/'seed-42/runs/synthetic_25-fold-0/report.json';saved=rp.read_bytes();bad=json.loads(saved);bad['seed']=99;write_json(rp,bad)
  with self.assertRaises(ValueError):self.ms.summarize_runs(out)
  rp.write_bytes(saved);bad=json.loads(saved);bad['outer']['accuracy']=1;write_json(rp,bad)
  with self.assertRaises(ValueError):self.ms.summarize_runs(out)
  rp.write_bytes(saved)
  with (rp.parent/'private-outer-predictions.jsonl').open('a') as f:f.write('\n')
  with self.assertRaises(ValueError):self.ms.summarize_runs(out)


 def test_reject_epochs_outside_frozen_protocol_cap(self):
  src,parent,base=self.fixture()
  cp=parent/'training-config.json';cfg=json.loads(cp.read_text(encoding='utf-8'))
  for index,epochs in enumerate((11,0,True)):
   cfg['epochs']=epochs;write_json(cp,cfg)
   with self.subTest(epochs=epochs):
    with self.assertRaises(ValueError):self.ms.prepare(parent,self.root/f'invalid-{index}')

if __name__=='__main__':unittest.main()
