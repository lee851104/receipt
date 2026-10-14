"""Stand-ins with the same interface as category.classify and attributes.describe_items.

The API and CI use them until the real models land, so every answer is fixed.
"""
from .fields import CATEGORY_COUNT, FIELDS

# A few words for 1 飲品, 2 零食甜點, 3 生鮮食材 and 8 日用品, so the classify box shows more than one answer;
# any other name is a weak 正餐 (0), below the default CATEGORY_MIN_PROB.
KEYWORDS = ((1, ("茶", "咖啡", "拿鐵", "可樂")), (2, ("餅乾", "蛋糕", "巧克力", "布丁")),
            (3, ("蔬菜", "雞蛋", "豬肉", "香蕉")), (8, ("衛生紙", "洗衣", "牙膏")))
SURE, UNSURE = 0.9, 0.3


def spread(category, top):
    """Ten probabilities: top on one category and the rest shared evenly, adding up to 1."""
    rest = (1 - top) / (CATEGORY_COUNT - 1)
    return [top if index == category else rest for index in range(CATEGORY_COUNT)]


def classify(names):
    """Each name's category 0-9 and the probability of every category."""
    answers = []
    for name in names:
        match = next((category for category, words in KEYWORDS if any(word in name for word in words)), None)
        if match is None:
            answers.append({"category": 0, "probs": spread(0, UNSURE)})
        else:
            answers.append({"category": match, "probs": spread(match, SURE)})
    return answers


def describe_items(names):
    """Every field unknown for every name: the shape of a real answer with nothing guessed."""
    return [dict.fromkeys(FIELDS) for _ in names]
