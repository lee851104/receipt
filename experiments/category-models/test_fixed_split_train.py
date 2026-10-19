"""Fixed-split training tests. All item names and models are fictional fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parent


def write_rows(path, rows):
    path.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')


def fixture(folder):
    from dataset_split import save_dataset
    real=[dict(id=f'real-{c}-{i}',name=f'虛構留出{c}號{i}',category=c,
               source='real',review_status='human_confirmed') for c in range(10) for i in range(10)]
    synthetic=[dict(name=f'合成資料{c}號{i}',category=c,source='synthetic') for c in range(10) for i in range(50)]
    source=folder/'real.jsonl'; synth=folder/'synth.jsonl'
    write_rows(source,real); write_rows(synth,synthetic)
    out=folder/'split'; save_dataset(source,synth,out)
    return out


class FixedSplitTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'fixed_split_data.py').exists(), 'fixed split loader is required')
        self.assertTrue((ROOT/'fixed_split_train.py').exists(), 'fixed split training is required')
        import fixed_split_data, fixed_split_train
        self.data,self.runner=fixed_split_data,fixed_split_train
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_loader_retains_sources_and_rejects_modified_input(self):
        folder=fixture(self.root)
        parts,manifest,identity=self.data.load_dataset(folder)
        self.assertEqual(sum(r['source']=='synthetic' for r in parts['train']),500)
        self.assertEqual(sum(r['source']=='real' for r in parts['train']),80)
        self.assertEqual(len(parts['validation']),10)
        self.assertEqual(len(parts['test']),10)
        self.assertEqual(identity,hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest())
        with (folder/'train.jsonl').open('a') as f:f.write('{}\n')
        with self.assertRaises(ValueError):self.data.load_dataset(folder)

    def test_metrics_exclude_below_five_and_empty_is_not_zero(self):
        score=self.data.score([0]*5+[1]*4,[0]*4+[1]*5)
        self.assertEqual(score['evaluated_categories'],[0])
        self.assertAlmostEqual(score['macro_f1'],8/9)
        self.assertIsNone(score['per_class']['1']['f1'])
        self.assertIsNone(self.data.score([1,2],[1,2])['macro_f1'])
        self.assertIsNone(self.data.score([],[])['accuracy'])
        for actual,predicted in (([0],[]),([True],[0]),([0],[10])):
            with self.assertRaises(ValueError):self.data.score(actual,predicted)

    def test_a_fits_train_only_and_never_predicts_test(self):
        import tfidf_lr
        folder=fixture(self.root)
        parts,_,_=self.data.load_dataset(folder)
        # A unique artificial character only in validation/test must not enter the TF-IDF vocabulary.
        held={r['name'] for r in parts['validation']+parts['test']}
        test_names={r['name'] for r in parts['test']}
        calls=[]; fits=[]
        predict=tfidf_lr.Classifier.predict
        fit=tfidf_lr.fit
        def record_predict(model,names):
            calls.extend(names)
            return predict(model,names)
        def record_fit(model,names,labels):
            fits.extend(names)
            return fit(model,names,labels)
        out=self.root/'a'
        with patch.object(tfidf_lr.Classifier,'predict',record_predict),patch.object(tfidf_lr,'fit',record_fit):
            report=self.runner.run('tfidf',folder,out,benchmark_count=12)
        self.assertEqual(set(fits),{r['name'] for r in parts['train']})
        self.assertFalse(set(fits)&held)
        self.assertFalse(set(calls)&test_names)
        self.assertEqual(report['test_evaluation'],'not_run')
        self.assertEqual(report['validation']['model']['support'],10)
        self.assertIsNone(report['validation']['model']['macro_f1'])
        self.assertTrue(report['reload_verified'])
        self.assertEqual(report['cost']['benchmark_count'],12)
        self.assertNotIn('虛構留出',json.dumps(report,ensure_ascii=False))
        self.assertNotIn('合成資料',json.dumps(report,ensure_ascii=False))
        import joblib
        bundle=joblib.load(out/'model.joblib')
        self.assertEqual(bundle['training_sources'],{'real':80,'synthetic':500})
        self.assertEqual(len(bundle['training_names']),580)
        self.assertFalse((out/'test-predictions.jsonl').exists())

    def test_b_tiny_local_encoder_roundtrip_and_full_pipeline_cost(self):
        from test_embedding_lr import EmbeddingTest
        maker=EmbeddingTest(); maker.root=self.root
        encoder=maker.encoder_fixture()
        folder=fixture(self.root)
        report=self.runner.run('embedding',folder,self.root/'b',encoder_dir=encoder,benchmark_count=12)
        self.assertTrue(report['reload_verified'])
        self.assertEqual(report['test_evaluation'],'not_run')
        self.assertEqual(report['training_sources'],{'real':80,'synthetic':500})
        self.assertGreater(report['cost']['model_bytes'],report['cost']['classifier_bytes'])
        self.assertEqual(report['cost']['benchmark_count'],12)
        self.assertGreater(report['cost']['inference_seconds'],0)

    def test_models_use_same_manifest_and_validation_ids(self):
        from test_embedding_lr import EmbeddingTest
        maker=EmbeddingTest();maker.root=self.root
        folder=fixture(self.root); encoder=maker.encoder_fixture()
        a=self.runner.run('tfidf',folder,self.root/'a',benchmark_count=2)
        b=self.runner.run('embedding',folder,self.root/'b',encoder_dir=encoder,benchmark_count=2)
        self.assertEqual(a['dataset'],b['dataset'])
        def ids(p):return [json.loads(s)['id'] for s in p.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(ids(self.root/'a/validation-predictions.jsonl'),ids(self.root/'b/validation-predictions.jsonl'))

    def test_refuses_existing_output_and_bad_model_before_writing(self):
        folder=fixture(self.root)
        original=(folder/'train.jsonl').read_bytes()
        with self.assertRaises(FileExistsError):self.runner.run('tfidf',folder,folder)
        self.assertEqual(original,(folder/'train.jsonl').read_bytes())
        for kind in ('bert','unknown'):
            with self.assertRaises(ValueError):self.runner.run(kind,folder,self.root/'new')
            self.assertFalse((self.root/'new').exists())

    def test_empty_validation_still_requires_roundtrip_prediction_check(self):
        import tfidf_lr
        from dataset_split import save_dataset
        real=self.root/'real.jsonl'; synth=self.root/'synthetic.jsonl'
        write_rows(real,[dict(id=f'r-{c}',name=f'虛構稀少{c}',category=c,source='real',review_status='human_confirmed') for c in range(10)])
        write_rows(synth,[dict(name=f'合成訓練{c}號{i}',category=c,source='synthetic') for c in range(10) for i in range(50)])
        folder=self.root/'split';save_dataset(real,synth,folder)
        class BrokenReload:
            def predict(self,names):
                return [dict(category=0,probabilities=[float('nan')]*10) for _ in names]
        with patch.object(tfidf_lr.Classifier,'load',return_value=BrokenReload()):
            with self.assertRaises(ValueError):
                self.runner.run('tfidf',folder,self.root/'broken',benchmark_count=2)
        self.assertFalse((self.root/'broken/report.json').exists())
        report=self.runner.run('tfidf',folder,self.root/'valid',benchmark_count=2)
        self.assertTrue(report['reload_verified'])
        self.assertGreater(report['reload_probe_items'],0)
        self.assertIsNone(report['validation']['model']['accuracy'])

    def test_source_change_during_fit_prevents_success_report(self):
        import tfidf_lr
        folder=fixture(self.root)
        fit=tfidf_lr.fit
        def change_source(model,names,labels):
            result=fit(model,names,labels)
            with (folder/'manifest.json').open('a',encoding='utf-8') as f:f.write(' ')
            return result
        with patch.object(tfidf_lr,'fit',change_source):
            with self.assertRaises(ValueError):
                self.runner.run('tfidf',folder,self.root/'run',benchmark_count=2)
        self.assertFalse((self.root/'run/report.json').exists())

    def test_cli_errors_do_not_echo_private_input(self):
        folder=fixture(self.root)
        (folder/'train.jsonl').write_text('SECRET_INVOICE_NAME',encoding='utf-8')
        result=subprocess.run([sys.executable,str(ROOT/'fixed_split_train.py'),'--model','tfidf','--dataset',str(folder),'--out',str(self.root/'run')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('SECRET_INVOICE_NAME',result.stdout+result.stderr)
        self.assertNotIn('Traceback',result.stderr)


if __name__=='__main__':unittest.main()
