"""Similarity, comparability and explanations on hand-made profiles."""
import json
import unittest
from pathlib import Path

from src.receipt.matching import compare, differences, eligible, overlap, ready, reasons, weighted
from src.receipt.tags import build_profile

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
NAMES = [category["name"] for category in CATEGORIES]


def profile(**changes):
    base = {"item_count": 10, "category_counts": [5, 5, 0, 0, 0, 0, 0, 0, 0, 0], "top_categories": [0, 1],
            "district_shares": {"高雄市苓雅區": 1.0}, "areas": ["高雄市苓雅區"],
            "brand_shares": {"示範茶屋": 1.0}, "frequent_brands": [("示範茶屋", 5)],
            "price_level": 0, "meat_ratio": 0.0, "flavor_items": {}, "tags": []}
    base.update(changes)
    return base


def neighbour():
    """Lives in the same district but buys entirely different things."""
    return profile(category_counts=[0, 0, 0, 0, 0, 0, 0, 0, 0, 10], top_categories=[9],
                   brand_shares={"示範數位店": 1.0}, frequent_brands=[("示範數位店", 5)], price_level=2, meat_ratio=1.0)


class MatchingTests(unittest.TestCase):
    def test_identical_profiles_score_full_marks(self):
        result = compare(profile(), profile(), SETTINGS)
        self.assertTrue(result["comparable"])
        self.assertAlmostEqual(result["taste"], 1)
        self.assertAlmostEqual(result["total"], 1)

    def test_overlap_is_histogram_intersection(self):
        self.assertAlmostEqual(overlap({"A": 0.6, "B": 0.4}, {"A": 0.3, "C": 0.7}), 0.3)
        self.assertIsNone(overlap({}, {"A": 1.0}))

    def test_missing_parts_hand_their_weight_to_the_rest(self):
        weights = SETTINGS["weights"]
        parts = {"category": 1.0, "district": None, "brand": None, "flavor": 0.0, "price": None}
        self.assertAlmostEqual(weighted(parts, weights, weights), weights["category"] / (weights["category"] + weights["flavor"]))
        self.assertIsNone(weighted(dict.fromkeys(parts), weights, weights))

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
        self.assertIsNone(result["taste"])
        self.assertIsNone(result["total"])

    def test_one_more_taste_dimension_is_required(self):
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
        self.assertIsNone(result["taste"])
        self.assertFalse(ready(sparse))

    def test_reasons_follow_contribution(self):
        me, other = profile(price_level=1), profile(price_level=1)
        parts = compare(me, other, SETTINGS)["parts"]
        self.assertEqual(reasons(me, other, parts, NAMES, SETTINGS), ["都很常買正餐", "都常在高雄市苓雅區消費", "都常去示範茶屋"])

    def test_flavor_and_price_reasons_and_fallback(self):
        me = profile(top_categories=[0], frequent_brands=[])
        other = profile(top_categories=[1], district_shares={"臺北市信義區": 1.0}, areas=["臺北市信義區"], frequent_brands=[])
        parts = compare(me, other, SETTINGS)["parts"]
        self.assertEqual(reasons(me, other, parts, NAMES, SETTINGS), ["都買比較多素食品項", "消費檔次都是小資型"])
        stranger = profile(top_categories=[9], areas=[], district_shares={}, frequent_brands=[], meat_ratio=None, price_level=2)
        parts = compare(profile(), stranger, SETTINGS)["parts"]
        self.assertEqual(reasons(profile(), stranger, parts, NAMES, SETTINGS), ["整體消費比例相近"])

    def test_differences_name_the_shared_store(self):
        veg = profile(meat_ratio=0.0, frequent_brands=[("示範水餃館", 4)], flavor_items={"示範水餃館": {"示範全素水餃": 4}})
        meat = profile(meat_ratio=1.0, frequent_brands=[("示範水餃館", 4)],
                       flavor_items={"示範水餃館": {"示範鮮蝦水餃": 3, "示範全素水餃": 1}})
        self.assertEqual(differences(veg, meat, SETTINGS), ["都常去示範水餃館，但點的不一樣（示範全素水餃／示範鮮蝦水餃）"])
        self.assertEqual(differences(veg, profile(meat_ratio=1.0), SETTINGS), ["購買紀錄不同：一位素食品項較多、一位葷食品項較多"])
        self.assertEqual(differences(veg, profile(meat_ratio=0.5), SETTINGS), [])
        self.assertEqual(differences(veg, profile(meat_ratio=None), SETTINGS), [])

    def test_eligible_keeps_the_area_band_and_sorts(self):
        candidates = [{"name": f"示範用戶 {i}", "profile": profile(price_level=i % 3)} for i in range(4)]
        candidates += [{"name": "示範鄰居", "profile": neighbour()},
                       {"name": "示範資料不足", "profile": profile(category_counts=None, top_categories=[])},
                       {"name": "示範中間", "profile": profile(brand_shares={"示範超商": 1.0}, frequent_brands=[("示範超商", 5)], meat_ratio=0.5)}]
        result = eligible(profile(), candidates, NAMES, SETTINGS)
        self.assertEqual([match["name"] for match in result], ["示範用戶 0", "示範用戶 3", "示範用戶 1", "示範用戶 2", "示範中間"])
        self.assertEqual(result[-1]["taste"], 71)
        self.assertEqual(set(result[0]), {"name", "total", "taste", "areas", "tags", "basis", "reasons", "differences"})
        self.assertEqual(result[0]["basis"], ["品類", "常消費地區", "品牌", "葷素紀錄", "消費檔次"])


if __name__ == "__main__":
    unittest.main()
