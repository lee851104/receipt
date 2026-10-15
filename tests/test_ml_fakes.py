"""The fake models keep the contract every model keeps, and answer the same thing every time."""
import unittest
from pathlib import Path

from src.ml import fakes
from src.ml.fields import ATTRIBUTES, FIELDS, FLAGS
from src.receipt.attributes import describe
from src.receipt.traits import load_context
from tests.model_contract import check_classify, check_describe

ROOT = Path(__file__).resolve().parents[1]


class FakeModelTests(unittest.TestCase):
    def test_classify_keeps_the_contract_and_reads_its_keywords(self):
        answers = check_classify(self, fakes.classify)
        self.assertEqual([answer["category"] for answer in answers], [1, 0, 8])

    def test_a_name_without_keywords_is_a_weak_guess(self):
        [answer] = fakes.classify(["滷肉飯"])
        self.assertLess(answer["probs"][answer["category"]], 0.5)

    def test_describe_items_keeps_the_contract_and_knows_nothing(self):
        for answer in check_describe(self, fakes.describe_items):
            self.assertIsNotNone(answer)
            self.assertEqual(list(answer), list(FIELDS))
            self.assertTrue(all(value is None for value in answer.values()))

    def test_the_sixteen_attributes_are_what_the_rules_answer_today(self):
        vocabulary = load_context(ROOT)["vocabulary"]
        row = {"name": "鮮奶茶", "category": 1, "quantity": 1, "merchant": "飲料店"}
        # describe() answers food plus the 16 attributes; food is also one of the 7 flags.
        self.assertIn("food", FLAGS)
        self.assertEqual(set(describe(row, "一般店家", vocabulary)), set(ATTRIBUTES) | {"food"})
        self.assertEqual(len(set(FIELDS)), len(FIELDS))
        self.assertEqual(len(FIELDS), 23)


if __name__ == "__main__":
    unittest.main()
