"""BERT tests use only fictional item names and tiny randomly initialized local weights."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_embedding_lr
from test_fixed_split_train import fixture


class BertTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('bert_finetune'), 'BERT training implementation required')
        import bert_finetune, bert_model
        self.train, self.model = bert_finetune, bert_model
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def setup_inputs(self):
        maker=test_embedding_lr.EmbeddingTest();maker.root=self.root
        return fixture(self.root),maker.encoder_fixture()

    def test_early_stop_uses_validation_loss_and_rejects_nonfinite(self):
        stop=self.train.EarlyStopping(patience=2,min_delta=1e-4)
        self.assertTrue(stop.update(1.0,1))
        self.assertTrue(stop.update(.9,2))
        self.assertFalse(stop.update(.90001,3))
        self.assertFalse(stop.should_stop)
        self.assertFalse(stop.update(.95,4))
        self.assertTrue(stop.should_stop)
        self.assertEqual(stop.best_epoch,2)
        with self.assertRaises(ValueError):stop.update(float('nan'),5)
        tiny=self.train.EarlyStopping()
        tiny.update(1.0,1)
        self.assertTrue(tiny.update(.99999,2))
        self.assertEqual(tiny.best_epoch,2)
        self.assertEqual(tiny.stale,1)

    def test_training_roundtrip_no_heldout_gradients_or_test_predictions(self):
        from fixed_split_data import load_dataset
        folder,base=self.setup_inputs()
        parts,_,_=load_dataset(folder)
        fit_names=[]; predicted=[]
        original_fit=self.train.train_epoch
        original_predict=self.model.Classifier.predict
        def fit(model,tokenizer,rows,*args,**kwargs):
            fit_names.extend(r['name'] for r in rows)
            return original_fit(model,tokenizer,rows,*args,**kwargs)
        def predict(model,names):
            predicted.extend(names)
            return original_predict(model,names)
        out=self.root/'run'
        with patch.object(self.train,'train_epoch',fit),patch.object(self.model.Classifier,'predict',predict):
            report=self.train.run(folder,base,out,seed=42,device='cpu',epochs=2,benchmark_count=3)
        self.assertEqual(set(fit_names),{r['name'] for r in parts['train']})
        self.assertFalse(set(predicted)&{r['name'] for r in parts['test']})
        self.assertTrue(report['reload_verified'])
        self.assertEqual(report['test_evaluation'],'not_run')
        self.assertEqual(report['training_sources'],{'real':80,'synthetic':500})
        self.assertEqual(report['validation']['model']['support'],10)
        self.assertIsNone(report['validation']['model']['macro_f1'])
        self.assertGreater(report['cost']['model_bytes'],0)
        self.assertEqual(report['cost']['benchmark_count'],3)
        self.assertEqual(report['best_epoch'],min(report['history'],key=lambda r:r['validation_loss'])['epoch'])
        model=self.model.Classifier.load(out/'model')
        preds=model.predict(['測試飯','測試茶'])
        self.assertEqual(len(preds),2)
        self.assertEqual(len(preds[0]['probabilities']),10)
        self.assertEqual(model.predict([]),[])
        public=json.dumps(report,ensure_ascii=False)
        self.assertNotIn('虛構留出',public)
        self.assertNotIn('合成資料',public)
        metadata=json.loads((out/'model/classifier-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['dataset_sha256'],report['dataset']['manifest_sha256'])
        with (out/'model/model.safetensors').open('ab') as f:f.write(b'corrupt')
        with self.assertRaises(ValueError):self.model.Classifier.load(out/'model')

    def test_rejects_existing_output_empty_validation_and_bad_settings(self):
        from dataset_split import save_dataset
        from test_fixed_split_train import write_rows
        folder,base=self.setup_inputs()
        with self.assertRaises(FileExistsError):self.train.run(folder,base,folder,device='cpu')
        for kwargs in ({'epochs':0},{'batch_size':0},{'lr':float('nan')},{'seed':True},{'device':'wrong'}):
            with self.assertRaises(ValueError):self.train.run(folder,base,self.root/'bad',**kwargs)
        real=self.root/'rare.jsonl'
        write_rows(real,[dict(id=f'r{c}',name=f'虛構稀少{c}',category=c,source='real',review_status='human_confirmed') for c in range(10)])
        rare=self.root/'rare';save_dataset(real,self.root/'synth.jsonl',rare)
        with self.assertRaises(ValueError):self.train.run(rare,base,self.root/'empty',device='cpu')
        self.assertFalse((self.root/'empty').exists())

    def test_cli_failure_does_not_echo_private_input(self):
        folder,base=self.setup_inputs()
        (folder/'train.jsonl').write_text('PRIVATE_BERT_MARKER',encoding='utf-8')
        p=subprocess.run([sys.executable,str(Path(__file__).with_name('bert_finetune.py')),'--dataset',str(folder),'--pretrained',str(base),'--out',str(self.root/'run'),'--device','cpu'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertNotIn('PRIVATE_BERT_MARKER',p.stdout+p.stderr)
        self.assertNotIn('Traceback',p.stderr)

if __name__=='__main__':unittest.main()
