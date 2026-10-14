"""What every category and attribute model answers, fake or real. Roles 2 and 3 run their models through these
inside a unittest.TestCase method, for example check_classify(self, category.classify)."""
import math

from src.ml.fields import CATEGORY_COUNT, FIELDS

NAMES = ["鮮奶茶", "滷肉飯", "衛生紙 12 包"]
# Plain Python values only (call .tolist() on numpy results): numpy.int64, numpy.float32 or numpy.bool_
# would break the JSON response.
VALUE_TYPES = (type(None), bool, int, float, str)


def check_classify(test, classify, names=NAMES):
    """One answer per name, in order: a plain int category 0-9 that is the most likely one, and ten plain
    float probabilities from 0 to 1 adding up to 1. Returns the answers for further checks."""
    test.assertEqual(classify([]), [])
    answers = classify(names)
    test.assertEqual(len(answers), len(names))
    for name, answer in zip(names, answers):
        with test.subTest(name=name):
            test.assertEqual(set(answer), {"category", "probs"})
            category, probs = answer["category"], answer["probs"]
            test.assertIs(type(category), int)
            test.assertIn(category, range(CATEGORY_COUNT))
            test.assertEqual(len(probs), CATEGORY_COUNT)
            for prob in probs:
                test.assertIs(type(prob), float)
                test.assertTrue(0 <= prob <= 1, f"probability {prob} is outside 0-1")
            test.assertTrue(math.isclose(sum(probs), 1.0, abs_tol=1e-3), f"probabilities add up to {sum(probs)}")
            test.assertEqual(max(probs), probs[category])
    # The same names asked in the opposite order get the same categories in the opposite order.
    again = classify(names[::-1])
    test.assertEqual([answer["category"] for answer in again], [answer["category"] for answer in answers][::-1])
    return answers


def check_describe(test, describe_items, names=NAMES):
    """One answer per name, in the same order (not checked here): None for a name never analysed, otherwise
    exactly the 23 fields holding plain values, where None means unknown. Returns the answers for further checks."""
    test.assertEqual(describe_items([]), [])
    answers = describe_items(names)
    test.assertEqual(len(answers), len(names))
    for name, answer in zip(names, answers):
        with test.subTest(name=name):
            if answer is not None:
                test.assertEqual(set(answer), set(FIELDS))
                for field, value in answer.items():
                    test.assertIn(type(value), VALUE_TYPES, f"{field} is a {type(value).__name__}")
    return answers
