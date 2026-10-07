"""The fictional population separates types, explains flavor gaps and respects the area rule."""
import json
import unittest
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.matching import compare, differences, eligible
from src.receipt.personas import build_personas
from src.receipt.tags import build_profile

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
CATALOG = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
NAMES = [category["name"] for category in CATEGORIES]


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = build_personas()
        cls.profiles = {person["name"]: build_profile(person["rows"], CATEGORIES, BRANDS, SETTINGS) for person in cls.people}
        demo_rows = [row for month in build_demo(CATALOG).values() for row in month["rows"]]
        cls.me = build_profile(demo_rows, CATEGORIES, BRANDS, SETTINGS)
        candidates = [{"name": name, "profile": profile} for name, profile in cls.profiles.items()]
        cls.pool = eligible(cls.me, candidates, NAMES, SETTINGS)

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
                       key=lambda other: compare(mine, self.profiles[other["name"]], SETTINGS)["total"])
            self.assertEqual(best["type"], person["type"], person["name"])

    def test_same_store_different_filling_is_explained(self):
        found = differences(self.profiles["手搖學生 A"], self.profiles["手搖學生 D"], SETTINGS)
        self.assertEqual(found, ["都常去示範餐坊，但點的不一樣（示範蔬食餐盒／示範鮮蝦餐盒）"])

    def test_neighbours_with_other_tastes_are_not_candidates(self):
        pool = {candidate["name"] for candidate in self.pool}
        for person in self.people:
            if person["type"] == "3C 玩家":
                self.assertTrue(set(self.profiles[person["name"]]["areas"]) & set(self.me["areas"]), person["name"])
                self.assertNotIn(person["name"], pool)

    def test_confirming_an_area_unlocks_more_people(self):
        high = [c for c in self.pool if c["taste"] >= 80]
        band = [c for c in self.pool if 70 <= c["taste"] < 80 and set(c["areas"]) & set(self.me["areas"])]
        self.assertGreaterEqual(len(high), 1)
        self.assertGreaterEqual(len(band), 1)
        self.assertTrue(any(candidate["differences"] for candidate in self.pool))


if __name__ == "__main__":
    unittest.main()
