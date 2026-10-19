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

    def test_nonempty_lists_are_distinct_from_predefined_type_hits(self):
        people = [{"name": "a", "type": "A"}, {"name": "b", "type": "A"}]
        matches = {"a": {"similar": ["b"], "opposite": ["b"]},
                   "b": {"similar": [], "opposite": []}}
        total = summarize_matches(people, matches, {"A": "B"})["overall"]
        self.assertEqual(total["opposite_type_hits"], 0)
        for kind in ("similar", "opposite"):
            self.assertEqual(total[f"{kind}_users_with_matches"], 1)
            self.assertEqual(total[f"{kind}_list_coverage"], 0.5)

    def test_empty_population_has_no_list_coverage(self):
        total = summarize_matches([], {}, {})["overall"]
        for kind in ("similar", "opposite"):
            self.assertEqual(total[f"{kind}_users_with_matches"], 0)
            self.assertIsNone(total[f"{kind}_list_coverage"])
