"""Keep the documented fictional numbers consistent with the production comparison core."""
import unittest
from scripts.concepts_example import example


class ConceptsExampleTests(unittest.TestCase):
    def test_documented_summary_and_contributions(self):
        result = example()
        self.assertTrue(result["comparable"])
        self.assertEqual(result["percent"], 82)
        self.assertAlmostEqual(result["dot"], 1.88)
        self.assertAlmostEqual(result["norm_mine"] ** 2, 2.04)
        self.assertAlmostEqual(result["norm_theirs"] ** 2, 2.04)
        self.assertAlmostEqual(result["denominator"], 2.29)
        self.assertAlmostEqual(result["score"], 1.88 / 2.29)
        self.assertAlmostEqual(sum(c["part"] for c in result["cells"] if c["shared"]), result["score"])
        self.assertEqual(len(result["cells"]), 18)
        self.assertEqual(sum(c["shared"] for c in result["cells"]), 5)
        self.assertEqual(sum(c["part"] is None for c in result["cells"]), 13)
