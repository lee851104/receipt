"""Private prediction runner uses only invented in-memory data in tests."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from test_private_attribute_review import dataset
from src.ml.attributes import MODEL_VERSION


class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.predict_private_attributes'), 'Private prediction runner is missing')
        from scripts import predict_private_attributes
        self.runner = predict_private_attributes

    def test_predictions_do_not_fill_blind_answers_or_replace_old_predictions(self):
        groups, predictions = dataset()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'data/private/review';root.mkdir(parents=True)
            for i, rows in enumerate(groups, 1):
                for row in rows:row['review_status']='pending_human_review'
                (root/f'reviewer-{i}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
            old = root/'predictions.jsonl';old.write_text('older-output',encoding='utf-8')
            before = {p.name:p.read_bytes() for p in root.iterdir()}
            def local_model(names):
                self.assertEqual(len(names),100)
                return [row['attributes'] for row in predictions]
            result = self.runner.predict(root, local_model, MODEL_VERSION)
            self.assertEqual(result['predicted_items'],100)
            self.assertNotIn('fictional-private-marker',json.dumps(result))
            self.assertTrue(all((root/name).read_bytes()==value for name,value in before.items()))
            output = list(root.glob('predictions-*.jsonl'))
            self.assertEqual(len(output),1)
            new = [json.loads(x) for x in output[0].read_text(encoding='utf-8').splitlines()]
            self.assertTrue(all(row['review_status']=='unreviewed_model_prediction' for row in new))
            with self.assertRaises(FileExistsError):self.runner.predict(root, local_model, MODEL_VERSION)

    def test_output_requires_private_directory(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            self.runner.predict(Path(folder), lambda names: [], MODEL_VERSION)

    def test_assisted_draft_copies_predictions_without_claiming_human_confirmation(self):
        groups, predictions = dataset()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'data/private/review';root.mkdir(parents=True)
            draft = self.runner.prepare_assisted(root, groups, predictions, MODEL_VERSION)
            rows = [json.loads(line) for path in draft.glob('reviewer-*.jsonl') for line in path.read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(rows),100)
            self.assertTrue(all(row['review_status']=='pending_human_review' for row in rows))
            self.assertTrue(all(row['review_method']=='model_assisted' for row in rows))
            self.assertTrue((draft/'review-preview.md').exists())
            with self.assertRaises(FileExistsError):self.runner.prepare_assisted(root, groups, predictions, MODEL_VERSION)
