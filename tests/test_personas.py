"""The fictional population tells the taste story: types hold together, chosen differences pull apart."""
import json
import unittest
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.personas import PERIOD, build_friends, build_personas
from src.receipt.signals import measure
from src.receipt.similarity import compare
from src.receipt.traits import build_vector, dated, load_context, relative, similarity_model, typical

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
CATALOG = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
INDEX = {trait["id"]: index for index, trait in enumerate(CONTEXT["traits"]["traits"])}
MODEL = similarity_model(CONTEXT["traits"])
DOMINANT = {
    "省錢上班族": {"spend": (None, -0.8), "motive": (None, -0.8)},
    "忙碌工程師": {"meals": (None, -0.8), "motive": (0.8, None), "tech": (0.8, None)},
    "咖啡上班族": {"spend": (0.3, None), "meals": (0.8, None)},
    "手搖學生": {"meals": (0.8, None), "fun": (0.4, None)},
    "健身族": {"sport": (0.5, None), "sweet": (None, -0.8)},
    "家庭下廚": {"cooking": (0.7, None), "stock": (None, -0.8), "driving": (0.3, None)},
    "連假旅人": {"travel": (0.3, None)},
    "質感貓奴": {"lifestyle": (0.8, None), "pets_cat": (0.5, None)},
}


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = build_personas(CONTEXT["calendar"])
        cls.friends = build_friends(CONTEXT["calendar"])
        cls.raw = {person["name"]: build_vector(person["rows"], list(PERIOD), CONTEXT) for person in cls.people + cls.friends}
        centers = typical([cls.raw[person["name"]] for person in cls.people], CONTEXT["traits"])
        cls.vectors = {name: relative(vector, centers) for name, vector in cls.raw.items()}
        rows, period = dated(build_demo(CATALOG))
        cls.me = relative(build_vector(rows, period, CONTEXT), centers)
        cls.types = {}
        for person in cls.people:
            cls.types.setdefault(person["type"], []).append(person["name"])

    def score(self, a, b):
        return compare(self.vectors[a], self.vectors[b], MODEL)["score"]

    def test_forty_reproducible_fictional_people(self):
        self.assertEqual(len(self.people), 40)
        self.assertEqual(build_personas(CONTEXT["calendar"]), self.people)
        self.assertEqual(list(self.types), list(DOMINANT))
        rows = [row for person in self.people + self.friends for row in person["rows"]]
        self.assertTrue(all(row["merchant"].startswith("示範") and row["name"].startswith("示範") for row in rows))
        self.assertTrue(all((row["date"].year, row["date"].month) in PERIOD and row["day"] == row["date"].day for row in rows))
        self.assertEqual([friend["name"] for friend in self.friends], ["小安", "小宇", "小林"])
        self.assertTrue(all(self.raw[name] is not None for name in self.raw))

    def test_each_type_shares_its_dominant_traits(self):
        for kind, limits in DOMINANT.items():
            for name in self.types[kind]:
                for trait, (low, high) in limits.items():
                    value = self.raw[name][INDEX[trait]]
                    with self.subTest(name=name, trait=trait):
                        if low is not None:
                            self.assertGreaterEqual(value, low)
                        if high is not None:
                            self.assertLessEqual(value, high)

    def test_designed_splits_inside_a_type(self):
        # Two-sided splits give a negative part; level splits leave no shared credit, so teammates who share the habit score higher.
        for kind, trait in (("咖啡上班族", "sweet"), ("手搖學生", "sweet"), ("連假旅人", "holiday"), ("省錢上班族", "stock")):
            first, fourth = self.types[kind][0], self.types[kind][3]
            with self.subTest(kind=kind):
                self.assertLess(compare(self.vectors[first], self.vectors[fourth], MODEL)["parts"][INDEX[trait]], 0)
        for kind in ("忙碌工程師", "健身族", "家庭下廚", "質感貓奴"):
            first, fourth, fifth = self.types[kind][0], self.types[kind][3], self.types[kind][4]
            with self.subTest(kind=kind):
                self.assertGreater(self.score(fourth, fifth), self.score(first, fourth))

    def test_clearance_shoppers_and_rice_ball_eaters_both_live_at_the_convenience_store_but_differ(self):
        saving, hurried = self.types["省錢上班族"], self.types["忙碌工程師"]
        for name in saving + hurried:
            person = next(person for person in self.people if person["name"] == name)
            self.assertGreaterEqual(measure(person["rows"], list(PERIOD), CONTEXT)["signals"]["store_meal_share"], 0.8)
        for name in saving[:3]:
            for other in hurried:
                self.assertLess(self.score(name, other), 0, (name, other))
        for name in saving:
            best_teammate = max(self.score(name, other) for other in saving if other != name)
            self.assertLess(max(self.score(name, other) for other in hurried), best_teammate, name)

    def test_me_has_a_clear_match_and_a_clear_opposite(self):
        scored = sorted((compare(self.me, self.vectors[person["name"]], MODEL)["score"], person["type"]) for person in self.people)
        self.assertGreaterEqual(scored[-1][0], 0.5)
        self.assertEqual(scored[-1][1], "手搖學生")
        self.assertLessEqual(scored[0][0], -0.3)
        self.assertEqual(scored[0][1], "省錢上班族")

    def test_friends_an_and_yu_are_alike_except_for_sweetness(self):
        an_yu = compare(self.vectors["小安"], self.vectors["小宇"], MODEL)
        self.assertGreaterEqual(an_yu["score"], 0.3)
        self.assertLess(an_yu["parts"][INDEX["sweet"]], 0)
        self.assertLess(self.score("小安", "小林"), an_yu["score"])


if __name__ == "__main__":
    unittest.main()
