import unittest
from sugar_guard import apply_sugar_guard


class SugarGuardTests(unittest.TestCase):
    def test_unspecified_sweetness_is_unknown_even_if_model_guesses_a_number(self):
        items = [{'id':'a','name':'瓶裝烏龍茶','quantity':1}, {'id':'b','name':'巧克力甜點','quantity':1}]
        predictions = [{'id':i,'attributes':{'sugar':v,'bulk':False}} for i,v in [('a',0),('b',1)]]
        output = apply_sugar_guard(items, predictions)
        self.assertTrue(all(p['attributes']['sugar'] is None for p in output['predictions']))
        self.assertEqual(len(output['overrides']),2)
        self.assertEqual(predictions[0]['attributes']['sugar'],0)
        self.assertFalse(output['predictions'][0]['attributes']['bulk'])

    def test_explicit_zero_sugar_and_fraction_are_not_erased(self):
        items = [{'id':'a','name':'烏龍茶 0分糖'}, {'id':'b','name':'紅茶 半糖'}]
        predictions = [{'id':'a','attributes':{'sugar':0}}, {'id':'b','attributes':{'sugar':.5}}]
        result = apply_sugar_guard(items,predictions)
        self.assertEqual(result['predictions'],predictions)
        self.assertEqual(result['overrides'],[])

    def test_failed_items_are_not_fabricated(self):
        self.assertEqual(apply_sugar_guard([{'id':'missing','name':'茶'}],[])['predictions'],[])


if __name__ == '__main__':
    unittest.main()
