"""Boundary checks; no real personal data or model downloads needed."""
import csv
from pathlib import Path
import tempfile
import unittest
from lab_core import prepare, decode_prediction, decode_sparse, attach
from evaluate import evaluate
from run_models import begin_output
from make_draft_reference import check_fixture


class ContractTests(unittest.TestCase):
    def fixture(self, folder):
        path = Path(folder) / 'sample.csv'
        fields = ['發票日期', '發票狀態', '發票號碼', '賣方名稱', '消費明細_品名', '消費明細_數量', '消費明細_金額']
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            w = csv.writer(stream); w.writerow(fields)
            w.writerows([
                ['20260301', '開立已確認', 'SECRET-A', '商家甲', '商品', 1, 100],
                ['20260302', '開立已確認', 'SECRET-B', '商家乙', '商品', 1, 50],
                ['20260303', '開立已確認', 'SECRET-C', '商家甲', '商品', 1, -10],
            ])
        return path

    def test_same_name_at_different_merchants_stays_separate_and_preserves_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            result = prepare(self.fixture(folder))
            self.assertIsNotNone(result)
            self.assertEqual(len(result['items']), 2)
            self.assertEqual(result['items'][0]['row_ids'], ['r0001', 'r0003'])
            self.assertEqual(result['total_amount'], 140)
            self.assertEqual(len(result['rows']), 3)
            self.assertNotIn('SECRET', str(result['items']))

    def test_unknown_false_and_zero_sugar_are_distinct(self):
        attrs = [False, 0, None, False, False, False, False, False, False, False, False, None, False, False, None, False]
        result = decode_prediction({'id': 'i0001', 'attributes': attrs, 'basic': [True, False, True, False, False, False, False]})
        self.assertIsNotNone(result)
        self.assertEqual(result['attributes']['sugar'], 0)
        self.assertIs(result['attributes']['clearance'], False)
        self.assertIsNone(result['attributes']['quick'])

    def test_incorrect_field_types_and_missing_fields_are_rejected(self):
        for attributes in ([False] * 15, ['false'] * 16, [False] * 16):
            with self.subTest(attributes=attributes):
                with self.assertRaises(ValueError):
                    decode_prediction({'id': 'i0001', 'attributes': attributes, 'basic': [None] * 7})

    def test_attach_rejects_missing_duplicate_and_unknown_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            data = prepare(self.fixture(folder))
            for predictions in ([], [{'id': 'fake'}], [{'id': 'i0001'}, {'id': 'i0001'}]):
                with self.subTest(predictions=predictions):
                    with self.assertRaises(ValueError):
                        attach(data, predictions)

    def test_attachment_preserves_amounts_and_source_links(self):
        with tempfile.TemporaryDirectory() as folder:
            data = prepare(self.fixture(folder))
            predictions = [{'id': 'i0001', 'attributes': {'clearance': True}},
                           {'id': 'i0002', 'attributes': {'clearance': None}}]
            result = attach(data, predictions)
            self.assertIsNotNone(result)
            self.assertEqual([r['amount'] for r in result], [100, 50, -10])
            self.assertEqual([r['row_id'] for r in result], ['r0001', 'r0002', 'r0003'])
            self.assertIs(result[2]['prediction']['attributes']['clearance'], True)

    def test_rerun_cannot_mix_old_full_annotations_with_new_partial_predictions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / '0.5b'; old.mkdir()
            (old / 'annotated-rows.json').write_text('old-full-run')
            (old / 'batch-009.json').write_text('old-batch')
            fresh = begin_output(root, '0.5b')
            self.assertEqual(list(fresh.iterdir()), [])
            archived = list((root / 'archive').glob('*/annotated-rows.json'))
            self.assertEqual(len(archived), 1)
            self.assertEqual(archived[0].read_text(), 'old-full-run')

    def test_failed_requested_positive_counts_against_end_to_end_recall(self):
        from lab_core import ATTRIBUTES, BASIC
        attrs = dict.fromkeys(ATTRIBUTES, False)
        attrs.update(clearance=True, sugar=None, fun=None, species=None)
        basic = dict.fromkeys(BASIC, False)
        ref = {'source_sha256': 'x', 'status': 'draft', 'items': [
            {'id': i, 'name': 'fixture', 'attributes': attrs, 'basic': basic, 'notes': ''} for i in ['a', 'b']]}
        result = {'source_sha256': 'x', 'model': 'fixture', 'requested_items': 2, 'requested_ids': ['a', 'b'],
                  'predictions': [{'id': 'a', 'attributes': attrs, 'basic': basic}],
                  'failures': [{'ids': ['b']}], 'elapsed_seconds': 1}
        report = evaluate(result, ref)
        self.assertEqual(report['attribute_positive_recall'], 0.5)
        self.assertEqual(report['missing_predictions'], 1)

    def test_draft_reference_rejects_another_source_even_with_same_item_count(self):
        with self.assertRaises(ValueError):
            check_fixture({'source_sha256': 'different-source'})

    def test_named_labels_preserve_unknown_and_apply_negative_contract(self):
        result = decode_sparse({'id': 'i0001', 'yes': ['food', 'drink'], 'unknown': ['stationery'],
                                'sugar': 0, 'fun': None, 'species': None})
        self.assertIsNotNone(result)
        self.assertIs(result['basic']['drink'], True)
        self.assertIs(result['attributes']['clearance'], False)
        self.assertIsNone(result['attributes']['stationery'])
        self.assertEqual(result['attributes']['sugar'], 0)

    def test_named_labels_reject_overlap_unknown_fields_and_duplicates(self):
        for yes, unknown in [(['food'], ['food']), (['unsupported'], []), (['food', 'food'], [])]:
            with self.subTest(yes=yes, unknown=unknown), self.assertRaises(ValueError):
                decode_sparse({'id': 'i0001', 'yes': yes, 'unknown': unknown, 'sugar': None, 'fun': None, 'species': None})


if __name__ == '__main__':
    unittest.main()
