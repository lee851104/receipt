import unittest
from bulk_rule import apply_bulk_rule


class BulkRuleTests(unittest.TestCase):
    def test_quantity_and_packaging_add_bulk_without_mutating_model_output(self):
        items = [{'id':'a','name':'餐點','quantity':3}, {'id':'b','name':'飲水24入','quantity':1}]
        predictions = [{'id':i,'attributes':{'bulk':False,'alcohol':None}} for i in ['a','b']]
        result = apply_bulk_rule(items, predictions)
        self.assertEqual(len(result['overrides']), 2)
        self.assertTrue(all(p['attributes']['bulk'] for p in result['predictions']))
        self.assertTrue(all(p['attributes']['bulk'] is False for p in predictions))
        self.assertIsNone(result['predictions'][0]['attributes']['alcohol'])

    def test_no_evidence_preserves_unknown_and_does_not_create_missing_prediction(self):
        items = [{'id':'a','name':'商品','quantity':1}, {'id':'b','name':'商品','quantity':3}]
        result = apply_bulk_rule(items, [{'id':'a','attributes':{'bulk':None}}])
        self.assertEqual(result['overrides'], [])
        self.assertEqual(len(result['predictions']), 1)
        self.assertIsNone(result['predictions'][0]['attributes']['bulk'])


if __name__ == '__main__':
    unittest.main()
