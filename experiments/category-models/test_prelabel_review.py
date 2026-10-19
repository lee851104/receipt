import csv
import json
from pathlib import Path
import tempfile
import unittest

import prelabel_review as review

class ReviewTests(unittest.TestCase):
    def csv(self, root, rows, name='dummy.csv'):
        path = Path(root) / name
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['發票日期','發票狀態','消費明細_品名','消費明細_金額'])
            writer.writeheader()
            for item, amount, status, date in rows:
                writer.writerow(dict(zip(writer.fieldnames, [date, status, item, amount])))
        return path

    def test_ingestion_deduplicates_and_filters_without_exporting_transactions(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.csv(root, [('虛構Ａ茶',30,'開立已確認','20261001'),('虛構A茶',40,'開立已確認','20261002'),('虛構折讓',-10,'開立已確認','20261001'),('虛構小額',9,'開立已確認','20261001'),('虛構小數',12.5,'開立已確認','20261001'),('虛構作廢',30,'作廢已確認','20261001'),('總計',100,'','')])
            rows, summary = review.read_invoices([path])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['occurrences'], 2)
            self.assertEqual(rows[0]['name'], '虛構A茶')
            self.assertNotIn('amount', rows[0])
            self.assertEqual(summary['eligible_rows'], 2)
            self.assertEqual(summary['excluded_amount'], 3)
            self.assertEqual(summary['excluded_void'], 1)
            self.assertEqual(summary['excluded_footer'], 1)

    def test_bad_cells_fail_without_echo(self):
        with tempfile.TemporaryDirectory() as root:
            for amount in ['PRIVATE-CELL', 'NaN', 'inf']:
                path = self.csv(root, [('PRIVATE-NAME',amount,'開立已確認','20261001')])
                with self.assertRaisesRegex(ValueError, '^invalid_invoice_amount$'):
                    review.read_invoices([path])

    def test_all_predictions_remain_pending_and_low_margin_is_prioritized(self):
        rows = [dict(id='a',name='虛構茶',occurrences=1)]
        bert = [dict(category=1, probabilities=[.01,.8,.1,.02,.01,.01,.01,.01,.02,.01])]
        other = [dict(category=0, probabilities=[.91]+[.01]*9)]
        drafts = review.make_drafts(rows, bert, other)
        self.assertIsNone(drafts[0]['category'])
        self.assertEqual(drafts[0]['review_status'], 'model_pending')
        self.assertEqual(drafts[0]['suggested_category'], 1)
        self.assertIn('model_disagreement', drafts[0]['review_reasons'])
        self.assertEqual(drafts[0]['source'], 'real')

    def test_invalid_prediction_cannot_become_draft(self):
        with self.assertRaises(ValueError):
            review.make_drafts([dict(id='a',name='虛構茶',occurrences=1)], [dict(category=10, probabilities=[.1]*10)], [])

    def test_html_escapes_private_strings_and_contains_no_network_dependencies(self):
        payload = dict(batch_id='dummy', rows=[dict(id='a',name='</script><img src=x onerror=alert(1)>')])
        html = review.render_review(payload)
        self.assertNotIn('</script><img', html)
        self.assertIn('\\u003c/script>', html)
        self.assertIn("connect-src 'none'", html)
        self.assertNotIn('<script src=', html)

    def test_output_is_exclusive_and_summary_never_contains_names(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/'review'
            payload = dict(batch_id='dummy', rows=[dict(id='a',name='PRIVATE-NAME',review_status='model_pending',category=None,suggested_category=1,review_reasons=[])])
            review.write_review(out, payload, {'unique_names':1}, {})
            self.assertNotIn('PRIVATE-NAME', (out/'summary.json').read_text())
            self.assertTrue((out/'review.html').exists())
            with self.assertRaises(FileExistsError):
                review.write_review(out, payload, {}, {})

if __name__ == '__main__':
    unittest.main()
