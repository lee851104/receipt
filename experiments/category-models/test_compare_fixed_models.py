"""One-shot comparison must freeze inputs before test evaluation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_fixed_split_train import fixture

class CompareTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('compare_fixed_models'),'comparison implementation required')
        import compare_fixed_models
        self.mod=compare_fixed_models
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_aggregate_uses_three_seeds_population_std_and_keeps_null(self):
        results=[dict(seed=s,metrics=dict(accuracy=v,macro_f1=None)) for s,v in zip((42,43,44),(.5,1.0,0.0))]
        summary=self.mod.aggregate_bert(results)
        self.assertEqual(summary['accuracy_mean'],.5)
        self.assertAlmostEqual(summary['accuracy_std'],(1/6)**.5)
        self.assertIsNone(summary['macro_f1_mean'])
        with self.assertRaises(ValueError):self.mod.aggregate_bert(results[:2])
        results[2]['seed']=42
        with self.assertRaises(ValueError):self.mod.aggregate_bert(results)

    def test_single_consumption_marker_prevents_second_test_run(self):
        folder=fixture(self.root)
        from fixed_split_data import load_dataset
        _,_,identity=load_dataset(folder)
        marker=self.mod.claim_test(folder,identity,{'fake_model':'abc'})
        self.assertTrue(marker.exists())
        with self.assertRaises(FileExistsError):self.mod.claim_test(folder,identity,{'fake_model':'abc'})
        self.assertEqual(json.loads(marker.read_text())['manifest_sha256'],identity)
        self.assertNotIn('虛構',marker.read_text(encoding='utf-8'))

    def test_real_five_model_pipeline_freezes_sources_and_scores_same_test_once(self):
        import test_embedding_lr
        from fixed_split_train import run as baseline_run
        from bert_finetune import run as bert_run
        folder=fixture(self.root)
        maker=test_embedding_lr.EmbeddingTest();maker.root=self.root
        base=maker.encoder_fixture()
        a=self.root/'a';b=self.root/'b'
        baseline_run('tfidf',folder,a,benchmark_count=1)
        baseline_run('embedding',folder,b,base,benchmark_count=1)
        seeds=[]
        for seed in (42,43,44):
            target=self.root/f'bert-{seed}'
            bert_run(folder,base,target,seed=seed,epochs=1,device='cpu',benchmark_count=1)
            seeds.append(target)
        # A mismatched source must be rejected before claiming the test split.
        report_path=a/'report.json'
        original=report_path.read_text(encoding='utf-8')
        report=json.loads(original);report['dataset']['manifest_sha256']='0'*64
        report_path.write_text(json.dumps(report),encoding='utf-8')
        with self.assertRaises(ValueError):self.mod.run(folder,a,b,seeds,self.root/'bad')
        self.assertFalse((folder/'test-evaluation-claimed.json').exists())
        report_path.write_text(original,encoding='utf-8')
        output=self.root/'comparison'
        summary=self.mod.run(folder,a,b,seeds,output)
        self.assertEqual(summary['test_count'],10)
        self.assertEqual(len(summary['models']),5)
        self.assertTrue(all(r['metrics']['support']==10 for r in summary['models']))
        self.assertTrue(all(r['metrics']['macro_f1'] is None for r in summary['models']))
        self.assertNotIn('虛構留出',json.dumps(summary,ensure_ascii=False))
        ids=[]
        for i in range(5):
            ids.append([json.loads(row)['id'] for row in (output/str(i)/'test-predictions.jsonl').read_text(encoding='utf-8').splitlines()])
        self.assertTrue(all(rows==ids[0] for rows in ids))
        with self.assertRaises(FileExistsError):self.mod.run(folder,a,b,seeds,self.root/'second')
        with self.assertRaises(FileExistsError):self.mod.evaluate_worker(output/'evaluation-plan.json',0)
        for index in (-1,5,True):
            with self.assertRaises(ValueError):self.mod.evaluate_worker(output/'evaluation-plan.json',index)
        plan=json.loads((output/'evaluation-plan.json').read_text(encoding='utf-8'))
        plan['out']=str(self.root/'alternate-output')
        (self.root/'alternate-output').mkdir()
        modified=self.root/'changed-plan.json'
        modified.write_text(json.dumps(plan),encoding='utf-8')
        with self.assertRaises(ValueError):self.mod.evaluate_worker(modified,0)


    def test_claim_rejects_changed_manifest_before_creating_marker(self):
        folder=fixture(self.root)
        with self.assertRaises(ValueError):self.mod.claim_test(folder,'0'*64,{})
        self.assertFalse((folder/'test-evaluation-claimed.json').exists())

if __name__=='__main__':unittest.main()
