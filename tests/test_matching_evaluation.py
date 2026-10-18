import unittest
from src.receipt.evaluation import summarize_matches

class EvaluationTests(unittest.TestCase):
    def test_exact_counts_missing_slots_and_mutual_hits(self):
        people=[{"name":"a","type":"A"},{"name":"b","type":"A"},{"name":"c","type":"B"}]
        matches={"a":{"similar":["b"],"opposite":["c"]},"b":{"similar":["a"],"opposite":[]},"c":{"similar":[],"opposite":["a"]}}
        result=summarize_matches(people,matches,{"A":"B","B":"A"})
        total=result["overall"]
        self.assertEqual(total["users"],3)
        self.assertEqual(total["same_type_hits"],2)
        self.assertEqual(total["similar_slots"],2)
        self.assertAlmostEqual(total["same_type_precision_at_5"],2/15)
        self.assertAlmostEqual(total["same_type_user_hit_rate"],2/3)
        self.assertAlmostEqual(total["same_type_mutual_user_hit_rate"],2/3)
        self.assertEqual(total["opposite_type_hits"],2)
        self.assertAlmostEqual(total["opposite_type_precision_at_5"],2/15)
        self.assertEqual(result["by_type"]["A"]["users"],2)
