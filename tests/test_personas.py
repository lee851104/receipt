"""The fictional population separates types at the match threshold and leaves nearby people for a distance choice."""
import json
import unittest
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.matching import compare, eligible
from src.receipt.personas import build_personas
from src.receipt.tags import build_profile, percent

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
CATALOG = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = build_personas()
        cls.profiles = {person["name"]: build_profile(person["rows"], CATEGORIES, BRANDS, SETTINGS) for person in cls.people}
        demo_rows = [row for month in build_demo(CATALOG).values() for row in month["rows"]]
        cls.me = build_profile(demo_rows, CATEGORIES, BRANDS, SETTINGS)
        candidates = [{"name": name, "profile": profile} for name, profile in cls.profiles.items()]
        cls.pool = eligible(cls.me, candidates, SETTINGS)

    def test_forty_reproducible_fictional_people(self):
        self.assertEqual(len(self.people), 40)
        self.assertEqual(build_personas(), self.people)
        self.assertEqual(len({person["type"] for person in self.people}), 8)
        self.assertTrue(all(row["merchant"].startswith("示範") and row["name"].startswith("示範")
                            for person in self.people for row in person["rows"]))

    def test_everyone_is_closest_to_their_own_type(self):
        for person in self.people:
            mine = self.profiles[person["name"]]
            best = max((other for other in self.people if other is not person),
                       key=lambda other: compare(mine, self.profiles[other["name"]], SETTINGS)["score"])
            self.assertEqual(best["type"], person["type"], person["name"])

    def test_types_separate_at_the_match_threshold(self):
        bar = percent(SETTINGS["thresholds"]["match"])
        for person in self.people:
            for other in self.people:
                if other is person:
                    continue
                score = percent(compare(self.profiles[person["name"]], self.profiles[other["name"]], SETTINGS)["score"])
                if person["type"] == other["type"]:
                    self.assertGreaterEqual(score, bar, (person["name"], other["name"]))
                else:
                    self.assertLess(score, bar, (person["name"], other["name"]))

    def test_least_alike_names_the_flavor_gap(self):
        found = next(candidate for candidate in self.pool if candidate["name"] == "手搖學生 D")
        self.assertEqual(found["unlike"], {"dimension": "葷素紀錄", "text": "葷食品項較多"})

    def test_neighbours_with_other_tastes_are_not_candidates(self):
        pool = {candidate["name"] for candidate in self.pool}
        for person in self.people:
            if person["type"] == "3C 玩家":
                self.assertTrue(set(self.profiles[person["name"]]["areas"]) & set(self.me["areas"]), person["name"])
                self.assertNotIn(person["name"], pool)

    def test_nearby_people_wait_for_a_distance_choice(self):
        high = [c["name"] for c in self.pool if c["score"] >= 80]
        band = [c for c in self.pool if 70 <= c["score"] < 80 and c["distance"] == 0]
        self.assertEqual(high, ["手搖學生 A", "手搖學生 B", "手搖學生 C", "手搖學生 D", "手搖學生 E"])
        self.assertGreaterEqual(len(band), 1)


if __name__ == "__main__":
    unittest.main()
