"""Similarity on hand-made vectors; tests/fixtures/similarity-cases.json is shared with the browser version."""
import json
import unittest
from pathlib import Path

from src.receipt.similarity import compare, percent

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "similarity-cases.json").read_text(encoding="utf-8"))


class SimilarityTests(unittest.TestCase):
    def test_shared_cases(self):
        for case in FIXTURE["cases"]:
            with self.subTest(case["name"]):
                result = compare(case["mine"], case["theirs"], case.get("model", FIXTURE["model"]))
                self.assertEqual(result["comparable"], case["comparable"])
                if not case["comparable"]:
                    self.assertIsNone(result["score"])
                    self.assertIsNone(result["parts"])
                    continue
                self.assertAlmostEqual(result["score"], case["score"], places=9)
                for got, expected in zip(result["parts"], case["parts"]):
                    if expected is None:
                        self.assertIsNone(got)
                    else:
                        self.assertAlmostEqual(got, expected, places=9)

    def test_parts_add_up_to_the_score(self):
        case = FIXTURE["cases"][2]
        result = compare(case["mine"], case["theirs"], FIXTURE["model"])
        self.assertAlmostEqual(sum(part for part in result["parts"] if part is not None), result["score"])

    def test_percent_rounds_halves_up_like_the_browser(self):
        self.assertEqual(percent(0.625), 63)
        self.assertEqual(percent(-0.355), -35)
        self.assertEqual(percent(0.1234), 12)


if __name__ == "__main__":
    unittest.main()
