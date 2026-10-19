import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bert_continuation_eval import choose, claim

class ContinuationEvaluationTests(unittest.TestCase):
    def test_selection_uses_validation_loss_then_seed_only(self):
        reports=[dict(seed=44,best_validation_loss=.3),dict(seed=43,best_validation_loss=.2),dict(seed=42,best_validation_loss=.2)]
        self.assertEqual(choose(reports),42)
        with self.assertRaises(ValueError):choose([reports[0],reports[0],reports[2]])

    def test_final_comparison_scores_only_parent_and_validation_winner_once(self):
        import bert_continuation_eval as evaluator
        from test_bert_continuation import ContinuationDataTests
        helper=ContinuationDataTests();helper.setUp();self.addCleanup(helper.doCleanups)
        dataset=helper.root/'continued';helper.prepare(dataset)
        parts,manifest,identity=evaluator.load(dataset)
        parent=helper.root/'parent-run';parent.mkdir()
        entries={str(parent.resolve()):dict(kind='bert',run=str(parent.resolve()),seed=42,dataset_sha256=manifest['parent_dataset_sha256'],files={'classifier-manifest.json':manifest['parent_classifier_manifest_sha256']})}
        candidates=[]
        for seed,loss in ((42,.5),(43,.2),(44,.3)):
            path=helper.root/f'candidate-{seed}';path.mkdir();candidates.append(path)
            report=dict(seed=seed,best_validation_loss=loss,best_epoch=1,settings=dict(seed=seed,initialization='verified_classifier_warm_start'),test_evaluation='not_run',pretrained=dict(files={}),validation=dict(model=dict(accuracy=.5)))
            (path/'report.json').write_text(json.dumps(report))
            entries[str(path.resolve())]=dict(kind='bert',run=str(path.resolve()),seed=seed,dataset_sha256=identity,files={})
        truth={row['name']:row['category'] for row in parts['test']}
        loaded=[]
        class FakeClassifier:
            def __init__(self,path):self.path=path
            def predict(self,names):
                outputs=[]
                for name in names:
                    category=truth[name] if 'candidate-43' in str(self.path) else 0
                    probs=[0.0]*10;probs[category]=1.0
                    outputs.append(dict(category=category,probabilities=probs))
                return outputs
        def fake_load(path):loaded.append(str(path));return FakeClassifier(path)
        with patch.object(evaluator,'model_identity',side_effect=lambda kind,path:entries[str(Path(path).resolve())]),patch.object(evaluator.Classifier,'load',side_effect=fake_load):
            result=evaluator.run(dataset,parent,candidates,helper.root/'comparison')
            self.assertEqual(result['selected_seed'],43)
            self.assertEqual(result['results']['after']['accuracy'],1.0)
            self.assertEqual(len(loaded),2)
            self.assertIn('candidate-43',loaded[1])
            with self.assertRaises(FileExistsError):evaluator.run(dataset,parent,candidates,helper.root/'other-output')
            self.assertEqual(len(loaded),2)

    def test_claim_is_fixed_to_dataset_and_plan_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dataset=root/'dataset';dataset.mkdir()
            plan=root/'plan.json';plan.write_text(json.dumps(dict(dataset_sha256='expected')))
            with patch('bert_continuation_eval.load',return_value=({}, {}, 'expected')):
                claim(dataset,plan,'expected')
                data=json.loads((dataset/'test-evaluation-claimed.json').read_text())
                self.assertEqual(data['dataset_sha256'],'expected')
                self.assertEqual(len(data['plan_sha256']),64)
                other=root/'other-plan.json';other.write_text(plan.read_text())
                with self.assertRaises(FileExistsError):claim(dataset,other,'expected')
            with patch('bert_continuation_eval.load',return_value=({}, {}, 'changed')):
                with self.assertRaises(ValueError):claim(dataset,plan,'expected')

if __name__=='__main__':unittest.main()
