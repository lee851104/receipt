"""Offline, invented examples for private attribute-review scoring and publication gates."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.ml.attributes import MODEL_VERSION
from src.ml.fields import FIELDS

ROOT = Path(__file__).resolve().parents[1]


def dataset():
    groups = []
    for group in range(4):
        groups.append([{'id': f'r{group*25+i}', 'name': f'fictional-private-marker-{group*25+i}',
                        'source': 'real', 'review_status': 'human_confirmed',
                        'attributes': {k: None if k in ('sugar','fun','species') else False for k in FIELDS}}
                       for i in range(25)])
    predictions = [{**copy.deepcopy(row), 'model_version': MODEL_VERSION} for rows in groups for row in rows]
    return groups, predictions


class PrivateAttributeReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.attribute_review'), 'Private evaluation tool is missing')
        from scripts import attribute_review
        self.review = attribute_review

    def test_boolean_abstention_and_unknown_gold_have_distinct_denominators(self):
        score = self.review.score_field('alcohol', [True, True, False, None], [True, None, True, True])
        self.assertEqual((score['tp'], score['fp'], score['fn']), (1, 1, 1))
        self.assertEqual((score['precision'], score['recall'], score['f1']), (.5, .5, .5))
        self.assertEqual(score['known_gold'], 3)
        self.assertEqual(score['null_ratio'], .25)

    def test_categorical_wrong_label_and_abstention_are_not_dropped(self):
        score = self.review.score_field('species', ['cat', 'dog', 'dog', None], ['cat', 'cat', None, 'dog'])
        self.assertEqual((score['tp'], score['fp'], score['fn']), (1, 1, 2))
        self.assertEqual(score['precision'], .5)
        self.assertAlmostEqual(score['recall'], 1/3)
        self.assertAlmostEqual(score['f1'], .4)
        self.assertEqual(score['null_ratio'], .25)

    def test_zero_sugar_is_a_class_and_empty_gold_is_not_perfect(self):
        score = self.review.score_field('sugar', [0, .5, None], [0, 1, None])
        self.assertEqual((score['tp'], score['fp'], score['fn']), (1, 1, 1))
        self.assertEqual(self.review.score_field('fun', [None], [None])['f1'], None)

    def test_pending_review_blocks_metrics_until_all_four_groups_complete(self):
        groups, predictions = dataset()
        groups[1][0]['review_status'] = 'pending_human_review'
        result = self.review.evaluate(groups, predictions, MODEL_VERSION)
        self.assertEqual(result['status'], 'pending_human_review')
        self.assertEqual(result['human_confirmed'], 99)
        self.assertNotIn('metrics', result)
        groups[1][0]['review_status'] = 'human_confirmed'
        result = self.review.evaluate(groups, predictions, MODEL_VERSION)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(set(result['metrics']), set(FIELDS))
        self.assertNotIn('fictional-private-marker', json.dumps(result))

    def test_invalid_cohorts_predictions_and_values_are_rejected_without_names(self):
        for change in ('duplicate', 'name_mismatch', 'old_version', 'synthetic', 'missing_prediction', 'bool_as_sugar', 'extra_field'):
            groups, predictions = dataset()
            if change == 'duplicate': groups[0][1]['id'] = groups[0][0]['id']
            if change == 'name_mismatch': predictions[0]['name'] = 'unexpected-secret'
            if change == 'old_version': predictions[0]['model_version'] = 'old-secret'
            if change == 'synthetic': groups[0][0]['source'] = 'synthetic'
            if change == 'missing_prediction': predictions.pop()
            if change == 'bool_as_sugar': groups[0][0]['attributes']['sugar'] = True
            if change == 'extra_field': groups[0][0]['attributes']['unexpected-secret'] = True
            with self.subTest(change=change), self.assertRaises(ValueError) as caught:
                self.review.evaluate(groups, predictions, MODEL_VERSION)
            self.assertNotIn('secret', str(caught.exception))
            self.assertNotIn('fictional-private-marker', str(caught.exception))

    def test_missing_inference_is_pending_instead_of_a_scored_negative(self):
        groups, predictions = dataset()
        predictions[0]['attributes'] = None
        result = self.review.evaluate(groups, predictions, MODEL_VERSION)
        self.assertEqual(result['status'], 'pending_predictions')
        self.assertEqual(result['predicted_items'], 99)
        self.assertNotIn('metrics', result)

    def test_cli_writes_only_aggregate_results_and_never_publishes_pending(self):
        groups, predictions = dataset()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for i, rows in enumerate(groups, 1):
                (root/f'reviewer-{i}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
            (root/'predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in predictions), encoding='utf-8')
            output = root/'report.md'
            command = [sys.executable, '-m', 'scripts.attribute_review', '--review-dir', str(root),
                       '--predictions', str(root/'predictions.jsonl'), '--output', str(output)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stderr)
            text = output.read_text(encoding='utf-8') + output.with_suffix('.json').read_text(encoding='utf-8') + run.stdout + run.stderr
            self.assertNotIn('fictional-private-marker', text)
            self.assertIn('precision', text)
            original = output.read_bytes()
            groups[0][0]['review_status'] = 'pending_human_review'
            (root/'reviewer-1.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in groups[0]), encoding='utf-8')
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 2)
            self.assertEqual(output.read_bytes(), original)
            self.assertNotIn('fictional-private-marker', run.stdout + run.stderr)

    def test_cli_malformed_private_input_does_not_print_traceback_or_content(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'reviewer-1.jsonl').write_text('{"private-marker":"private-data', encoding='utf-8')
            run = subprocess.run([sys.executable, '-m', 'scripts.attribute_review', '--review-dir', folder,
                                  '--predictions', str(Path(folder)/'predictions.jsonl')], cwd=ROOT,
                                 capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 1)
            self.assertNotIn('private-marker', run.stdout + run.stderr)
            self.assertNotIn('Traceback', run.stdout + run.stderr)

    def test_status_output_cannot_overwrite_private_review_inputs(self):
        groups, predictions = dataset()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for i, rows in enumerate(groups, 1):
                (root/f'reviewer-{i}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
            (root/'predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in predictions), encoding='utf-8')
            protected = root/'reviewer-1.jsonl'
            before = protected.read_bytes()
            run = subprocess.run([sys.executable, '-m', 'scripts.attribute_review', '--review-dir', str(root),
                                  '--predictions', str(root/'predictions.jsonl'), '--status-only', '--status-output', str(protected)],
                                 cwd=ROOT, capture_output=True)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(protected.read_bytes(), before)
