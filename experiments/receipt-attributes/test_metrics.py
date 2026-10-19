import unittest
from metrics import score
from followup_report import checked_score


class MetricsTests(unittest.TestCase):
    def test_hand_calculated_confusion_counts(self):
        gold = [{'id': str(i), 'attributes': {'alcohol': v}} for i, v in enumerate([True, True, False, False])]
        pred = [{'id': str(i), 'attributes': {'alcohol': v}} for i, v in enumerate([True, False, True, False])]
        result = score(gold, pred)
        self.assertEqual(result['micro'], {'tp': 1, 'fp': 1, 'fn': 1, 'precision': .5, 'recall': .5, 'f1': .5})
        self.assertEqual(result['accuracy'], .5)

    def test_abstentions_and_missing_predictions_cannot_inflate_accuracy(self):
        gold = [{'id': 'a', 'attributes': {'alcohol': True}}, {'id': 'b', 'attributes': {'alcohol': False}}]
        result = score(gold, [{'id': 'b', 'attributes': {'alcohol': None}}])
        self.assertEqual(result['accuracy'], 0)
        self.assertEqual(result['micro']['fn'], 1)
        self.assertEqual(result['micro']['f1'], 0)
        self.assertEqual(result['abstained_fields'], 2)

    def test_zero_sugar_is_positive_and_wrong_subtype_counts_fp_and_fn(self):
        gold = [{'id': 'a', 'attributes': {'sugar': 0, 'fun': 'movie', 'species': None}}]
        pred = [{'id': 'a', 'attributes': {'sugar': 0, 'fun': 'game', 'species': 'cat'}}]
        result = score(gold, pred)
        self.assertEqual(result['micro']['tp'], 1)
        self.assertEqual(result['micro']['fp'], 2)
        self.assertEqual(result['micro']['fn'], 1)
        self.assertAlmostEqual(result['micro']['f1'], .4)
        self.assertAlmostEqual(result['accuracy'], 1/3)

    def test_unknown_gold_boolean_is_masked_and_no_support_macro_excluded(self):
        gold = [{'id':'a', 'attributes': {'alcohol':None, 'bulk':True, 'home':False}}]
        pred = [{'id':'a', 'attributes': {'alcohol':True, 'bulk':True, 'home':False}}]
        result = score(gold, pred)
        self.assertEqual(result['known_fields'], 2)
        self.assertEqual(result['macro_f1_supported'], 1)
        self.assertEqual(result['supported_attributes'], ['bulk'])
        self.assertEqual(result['fields']['home']['f1'], 0)

    def test_duplicate_and_extra_ids_are_rejected(self):
        gold = [{'id':'a', 'attributes': {'bulk':True}}]
        for predictions in ([{'id':'x','attributes':{}}], [{'id':'a','attributes':{}}]*2):
            with self.assertRaises(ValueError):
                score(gold, predictions)

    def test_comparison_rejects_partial_run_and_wrong_source(self):
        ref = [{'id':'a', 'attributes':{'bulk':True}}, {'id':'b', 'attributes':{'bulk':False}}]
        result = {'source_sha256':'source', 'prompt_sha256':'prompt', 'requested_ids':['a','b'],
                  'predictions':[{'id':'a', 'attributes':{'bulk':True}}], 'failures':[], 'elapsed_seconds':1}
        with self.assertRaises(ValueError):
            checked_score(result, ref, 'source', 'prompt')
        result['failures'] = [{'ids':['b']}]
        report = checked_score(result, ref, 'source', 'prompt')
        self.assertEqual(report['accuracy'], .5)
        self.assertEqual(report['failed_batches'], 1)
        with self.assertRaises(ValueError):
            checked_score(result, ref, 'different-source', 'prompt')

    def test_cli_failed_batch_returns_nonzero(self):
        import runpy
        from pathlib import Path
        from unittest.mock import patch
        script = Path(__file__).with_name('run_followup.py')
        with patch('sys.argv', [str(script), '--models', '0.5b']), patch('run_models.run', return_value=False):
            with self.assertRaises(SystemExit) as caught:
                runpy.run_path(str(script), run_name='__main__')
        self.assertEqual(caught.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
