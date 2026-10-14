"""The fake models answer in exactly the shape the real ones will."""
import unittest
from pathlib import Path

from src.ml import fakes
from src.ml.fields import ATTRIBUTES, CATEGORY_COUNT, FIELDS
from src.receipt.attributes import describe
from src.receipt.traits import load_context

ROOT = Path(__file__).resolve().parents[1]


class FakeModelTests(unittest.TestCase):
    def test_classify_gives_each_name_a_category_and_ten_probabilities(self):
        answers = fakes.classify(["鮮奶茶", "滷肉飯", "衛生紙 12 包"])
        self.assertEqual([answer["category"] for answer in answers], [1, 0, 8])
        for answer in answers:
            self.assertEqual(len(answer["probs"]), CATEGORY_COUNT)
            self.assertAlmostEqual(sum(answer["probs"]), 1.0)
            self.assertEqual(max(answer["probs"]), answer["probs"][answer["category"]])

    def test_a_name_without_keywords_is_a_weak_guess(self):
        [answer] = fakes.classify(["滷肉飯"])
        self.assertLess(answer["probs"][answer["category"]], 0.5)

    def test_describe_items_has_every_field_and_knows_none_of_them(self):
        answers = fakes.describe_items(["鮮奶茶", "滷肉飯"])
        self.assertEqual(len(answers), 2)
        for answer in answers:
            self.assertEqual(list(answer), list(FIELDS))
            self.assertTrue(all(value is None for value in answer.values()))

    def test_the_sixteen_attributes_are_what_the_rules_answer_today(self):
        vocabulary = load_context(ROOT)["vocabulary"]
        row = {"name": "鮮奶茶", "category": 1, "quantity": 1, "merchant": "飲料店"}
        # describe() answers food plus the 16 attributes; food is also one of the 7 flags.
        self.assertEqual(set(describe(row, "一般店家", vocabulary)), set(ATTRIBUTES) | {"food"})
        self.assertEqual(len(FIELDS), 23)


if __name__ == "__main__":
    unittest.main()
