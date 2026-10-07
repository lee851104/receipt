"""Scores, distances and the two tags shown for each match, on hand-made profiles."""
import json
import unittest
from pathlib import Path

from src.receipt.matching import (compare, distance, eligible, least_alike, most_alike, overlap, place_distance,
                                  ready, weighted)
from src.receipt.tags import build_profile, describe

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
NAMES = [category["name"] for category in CATEGORIES]
REGIONS = SETTINGS["regions"]


def profile(**changes):
    base = {"item_count": 10, "category_counts": [5, 5, 0, 0, 0, 0, 0, 0, 0, 0], "top_categories": [0, 1],
            "district_shares": {"高雄市苓雅區": 1.0}, "areas": ["高雄市苓雅區"],
            "brand_shares": {"示範茶屋": 1.0}, "frequent_brands": [("示範茶屋", 5)],
            "price_level": 0, "meat_ratio": 0.0}
    base.update(changes)
    base["tags"] = describe(base, NAMES, SETTINGS)
    return base


def neighbour():
    """Shops in the same district but buys entirely different things."""
    return profile(category_counts=[0, 0, 0, 0, 0, 0, 0, 0, 0, 10], top_categories=[9],
                   brand_shares={"示範數位店": 1.0}, frequent_brands=[("示範數位店", 5)], price_level=2, meat_ratio=1.0)


def tag(dimension, text):
    return {"dimension": dimension, "text": text}


class ScoreTests(unittest.TestCase):
    def test_identical_profiles_score_full_marks(self):
        result = compare(profile(), profile(), SETTINGS)
        self.assertTrue(result["comparable"])
        self.assertAlmostEqual(result["score"], 1)

    def test_area_does_not_change_the_score(self):
        far = profile(district_shares={"臺北市信義區": 1.0}, areas=["臺北市信義區"])
        result = compare(profile(), far, SETTINGS)
        self.assertAlmostEqual(result["score"], compare(profile(), profile(), SETTINGS)["score"])
        self.assertNotIn("district", result["parts"])

    def test_overlap_is_histogram_intersection(self):
        self.assertAlmostEqual(overlap({"A": 0.6, "B": 0.4}, {"A": 0.3, "C": 0.7}), 0.3)
        self.assertIsNone(overlap({}, {"A": 1.0}))

    def test_missing_parts_hand_their_weight_to_the_rest(self):
        weights = SETTINGS["weights"]
        parts = {"category": 1.0, "brand": None, "flavor": 0.0, "price": None}
        self.assertAlmostEqual(weighted(parts, weights), weights["category"] / (weights["category"] + weights["flavor"]))
        self.assertIsNone(weighted(dict.fromkeys(parts), weights))

    def test_price_and_flavor_similarity(self):
        result = compare(profile(price_level=0, meat_ratio=0.0), profile(price_level=2, meat_ratio=1.0), SETTINGS)
        self.assertEqual(result["parts"]["price"], 0)
        self.assertEqual(result["parts"]["flavor"], 0)
        result = compare(profile(price_level=1, meat_ratio=None), profile(price_level=2), SETTINGS)
        self.assertEqual(result["parts"]["price"], 0.5)
        self.assertIsNone(result["parts"]["flavor"])

    def test_category_is_required(self):
        result = compare(profile(category_counts=None, top_categories=[]), profile(), SETTINGS)
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["score"])

    def test_one_more_dimension_is_required(self):
        bare = profile(brand_shares={}, frequent_brands=[], meat_ratio=None, price_level=None)
        self.assertFalse(compare(bare, profile(), SETTINGS)["comparable"])
        self.assertFalse(ready(bare))
        self.assertTrue(ready(dict(bare, price_level=1)))
        self.assertFalse(ready(profile(category_counts=None)))

    def test_three_uncategorized_invoices_cannot_be_compared(self):
        rows = [{"day": 1, "invoice": f"U{i}", "merchant": "測試小店", "district": "高雄市苓雅區", "name": "測試未分類",
                 "quantity": 1, "amount": 120, "category": 10, "provisional": True} for i in range(3)]
        sparse = build_profile(rows, CATEGORIES, BRANDS, SETTINGS)
        result = compare(sparse, sparse, SETTINGS)
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["score"])
        self.assertFalse(ready(sparse))


class DistanceTests(unittest.TestCase):
    def test_place_distance_steps_up_by_administrative_level(self):
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市苓雅區", REGIONS), 0)
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市前鎮區", REGIONS), 1)
        self.assertEqual(place_distance("高雄市苓雅區", "屏東縣恆春鎮", REGIONS), 2)
        self.assertEqual(place_distance("臺北市信義區", "新北市板橋區", REGIONS), 2)
        self.assertEqual(place_distance("宜蘭縣宜蘭市", "臺北市內湖區", REGIONS), 2)
        self.assertEqual(place_distance("高雄市苓雅區", "臺北市信義區", REGIONS), 3)

    def test_distance_takes_the_closest_pair_of_areas(self):
        self.assertEqual(distance(["高雄市苓雅區", "臺北市信義區"], ["新北市板橋區"], REGIONS), 2)
        self.assertEqual(distance([], ["高雄市苓雅區"], REGIONS), 3)
        self.assertEqual(distance(["高雄市苓雅區"], [], REGIONS), 3)


class TagPickTests(unittest.TestCase):
    def test_most_alike_checks_brand_flavor_price_then_category(self):
        me = profile()
        self.assertEqual(most_alike(me, profile(price_level=1, meat_ratio=1.0)), tag("常去品牌", "示範茶屋（5 次）"))
        other_store = {"brand_shares": {"示範超商": 1.0}, "frequent_brands": [("示範超商", 5)]}
        self.assertEqual(most_alike(me, profile(**other_store)), tag("葷素紀錄", "素食品項較多"))
        self.assertEqual(most_alike(me, profile(**other_store, meat_ratio=1.0)), tag("消費檔次", "小資型"))
        self.assertEqual(most_alike(me, profile(**other_store, meat_ratio=1.0, price_level=2)),
                         tag("品類偏好", "常買正餐（50%）"))

    def test_least_alike_checks_flavor_price_brand_then_category(self):
        me = profile()
        self.assertEqual(least_alike(me, profile(meat_ratio=1.0)), tag("葷素紀錄", "葷食品項較多"))
        self.assertEqual(least_alike(me, profile(price_level=2)), tag("消費檔次", "享受型"))
        self.assertEqual(least_alike(me, profile(frequent_brands=[("示範茶屋", 5), ("示範水餃館", 4)])),
                         tag("常去品牌", "示範水餃館（4 次）"))
        self.assertEqual(least_alike(me, profile(category_counts=[5, 0, 5, 0, 0, 0, 0, 0, 0, 0], top_categories=[0, 2])),
                         tag("品類偏好", "常買零食甜點（50%）"))
        self.assertIsNone(least_alike(me, profile()))

    def test_areas_never_explain_a_match(self):
        stranger = neighbour()
        self.assertEqual(stranger["areas"], profile()["areas"])
        self.assertIsNone(most_alike(profile(), stranger))
        self.assertEqual(least_alike(profile(), stranger), tag("葷素紀錄", "葷食品項較多"))

    def test_labels_i_lack_cannot_differ(self):
        me = profile(meat_ratio=None, price_level=None)
        other = profile(meat_ratio=1.0, price_level=2)
        self.assertIsNone(least_alike(me, other))
        self.assertEqual(most_alike(me, other), tag("常去品牌", "示範茶屋（5 次）"))


class EligibleTests(unittest.TestCase):
    def test_eligible_keeps_seventy_and_up_sorted_by_score(self):
        candidates = [{"name": f"示範用戶 {i}", "profile": profile(price_level=i % 3)} for i in range(4)]
        candidates += [
            {"name": "示範遠方", "profile": profile(district_shares={"臺北市信義區": 1.0}, areas=["臺北市信義區"])},
            {"name": "示範鄰居", "profile": neighbour()},
            {"name": "示範資料不足", "profile": profile(category_counts=None, top_categories=[])},
            {"name": "示範中間", "profile": profile(brand_shares={"示範超商": 1.0}, frequent_brands=[("示範超商", 5)],
                                                 meat_ratio=0.5)},
        ]
        result = eligible(profile(), candidates, SETTINGS)
        self.assertEqual([(match["name"], match["score"]) for match in result],
                         [("示範用戶 0", 100), ("示範用戶 3", 100), ("示範遠方", 100), ("示範用戶 1", 93),
                          ("示範用戶 2", 86), ("示範中間", 71)])
        self.assertEqual(set(result[0]), {"name", "score", "distance", "like", "unlike", "counts"})
        self.assertEqual([match["distance"] for match in result[:3]], [0, 0, 3])
        self.assertEqual(result[0]["counts"], [5, 5, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(result[-1]["like"], tag("消費檔次", "小資型"))
        self.assertEqual(result[-1]["unlike"], tag("葷素紀錄", "葷素品項都有"))


if __name__ == "__main__":
    unittest.main()
