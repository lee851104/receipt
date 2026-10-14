"""What every category and attribute model answers, fake or real; roles 2 and 3 run their models through these."""
import math

from src.ml.fields import CATEGORY_COUNT, FIELDS

NAMES = ["鮮奶茶", "滷肉飯", "衛生紙 12 包"]
# Plain Python values only: numpy.int64, numpy.float32 or numpy.bool_ would break the JSON response.
VALUE_TYPES = (type(None), bool, float, str)


def check_classify(test, classify, names=NAMES):
    """One answer per name, in order: a plain int category 0-9 that is the most likely one,
    and ten plain float probabilities adding up to 1. Returns the answers for further checks."""
    test.assertEqual(classify([]), [])
    answers = classify(names)
    test.assertEqual(len(answers), len(names))
    for answer in answers:
        test.assertEqual(set(answer), {"category", "probs"})
        test.assertIs(type(answer["category"]), int)
        test.assertIn(answer["category"], range(CATEGORY_COUNT))
        test.assertEqual(len(answer["probs"]), CATEGORY_COUNT)
        test.assertTrue(all(type(prob) is float for prob in answer["probs"]))
        test.assertTrue(math.isclose(sum(answer["probs"]), 1.0, abs_tol=1e-6))
        test.assertEqual(max(answer["probs"]), answer["probs"][answer["category"]])
    return answers


def check_describe(test, describe_items, names=NAMES):
    """One answer per name, in order: None for a name never analysed, otherwise exactly the 23 fields
    holding plain values, where None means unknown. Returns the answers for further checks."""
    test.assertEqual(describe_items([]), [])
    answers = describe_items(names)
    test.assertEqual(len(answers), len(names))
    for answer in answers:
        if answer is not None:
            test.assertEqual(set(answer), set(FIELDS))
            test.assertTrue(all(type(value) in VALUE_TYPES for value in answer.values()))
    return answers
