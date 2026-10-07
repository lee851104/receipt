"""Tag rules on small fictional purchase sets."""
import json
import unittest
from pathlib import Path

from src.receipt.tags import brand_of, build_profile, flavor_of, percent

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))


def row(invoice, category=0, amount=100, name="測試品項", merchant="測試小店", district="高雄市苓雅區",
        provisional=False, quantity=1):
    return {"day": 1, "invoice": invoice, "merchant": merchant, "district": district, "name": name,
            "quantity": quantity, "amount": amount, "category": category, "provisional": provisional}


def profile_of(rows):
    return build_profile(rows, CATEGORIES, BRANDS, SETTINGS)


def texts(profile, dimension):
    return [tag["text"] for tag in profile["tags"] if tag["dimension"] == dimension]


class TagTests(unittest.TestCase):
    def test_shipped_settings_match_the_spec(self):
        self.assertAlmostEqual(sum(SETTINGS["weights"].values()), 1)
        self.assertEqual(SETTINGS["thresholds"], {"taste": 0.8, "taste_same_area": 0.7})
        self.assertEqual(SETTINGS["category_min_items"], 10)
        self.assertEqual([level["label"] for level in SETTINGS["price_levels"]], ["小資型", "均衡型", "享受型"])
        self.assertNotIn("蔬菜", SETTINGS["flavor"]["vegetarian"])
        self.assertTrue(SETTINGS["remote_sellers"])
        self.assertTrue(all(entry["brand"] and entry["keywords"] for entry in BRANDS))

    def test_percent_rounds_half_up(self):
        self.assertEqual(percent(0.805), 81)
        self.assertEqual(percent(0.8), 80)
        self.assertEqual(percent(0.7949), 79)

    def test_brand_keywords_ignore_variant_characters(self):
        self.assertEqual(brand_of("台灣高速鐵路股份有限公司", BRANDS), "台灣高鐵")
        self.assertEqual(brand_of("統一超商股份有限公司高雄示範分公司", BRANDS), "7-ELEVEN")
        self.assertIsNone(brand_of("示範巷口麵店", BRANDS))

    def test_flavor_words_prefer_explicit_vegetarian_markers(self):
        flavor = SETTINGS["flavor"]
        self.assertEqual(flavor_of("示範全素香腸", flavor), 0)
        self.assertEqual(flavor_of("示範素食雞排", flavor), 0)
        self.assertEqual(flavor_of("示範蔬食餐盒", flavor), 0)
        self.assertEqual(flavor_of("示範蔬菜豬肉水餃", flavor), 1)
        self.assertEqual(flavor_of("示範鮮蝦水餃", flavor), 1)
        self.assertIsNone(flavor_of("示範蔬菜水餃", flavor))
        self.assertIsNone(flavor_of("示範牛奶", flavor))
        self.assertIsNone(flavor_of("示範肉桂捲", flavor))

    def test_category_tags_count_confirmed_paid_items(self):
        rows = [row(f"D{i}", 1) for i in range(7)] + [row(f"M{i}", 0) for i in range(3)]
        rows += [row("E", 2, amount=-10), row("F", 2, amount=0), row("G", 3, provisional=True), row("H", 10, provisional=True)]
        profile = profile_of(rows)
        self.assertEqual(profile["item_count"], 10)
        self.assertEqual(profile["category_counts"][:4], [3, 7, 0, 0])
        self.assertEqual(texts(profile, "品類偏好"), ["常買飲品（70%）", "常買正餐（30%）"])

    def test_category_needs_ten_items(self):
        few = profile_of([row(f"D{i}", 1) for i in range(9)])
        self.assertEqual(few["item_count"], 9)
        self.assertIsNone(few["category_counts"])
        self.assertEqual(texts(few, "品類偏好"), [])

    def test_one_portion_per_item_and_invoice(self):
        rows = [row("A", 1, name="示範紅茶"), row("A", 1, name="示範紅茶"), row("B", 1, name="示範紅茶", quantity=4)]
        rows += [row(f"M{i}", 0, name="示範便當") for i in range(8)]
        profile = profile_of(rows)
        self.assertEqual(profile["item_count"], 10)
        self.assertEqual(profile["category_counts"][:2], [8, 2])

    def test_area_tags_need_enough_invoices_and_two_per_district(self):
        profile = profile_of([row("A"), row("B"), row("C", district="高雄市新興區"), row("D", district="高雄市新興區"),
                              row("E", district="臺北市信義區"), row("F", district=None)])
        self.assertEqual(texts(profile, "常消費地區"), ["高雄市新興區", "高雄市苓雅區"])
        self.assertAlmostEqual(profile["district_shares"]["高雄市苓雅區"], 0.4)
        few = profile_of([row("A"), row("B")])
        self.assertEqual(few["district_shares"], {})
        self.assertEqual(texts(few, "常消費地區"), [])

    def test_remote_sellers_do_not_count_as_places(self):
        online = [row(f"O{i}", merchant="富邦媒體科技股份有限公司", district="臺北市內湖區") for i in range(3)]
        profile = profile_of(online + [row(f"L{i}") for i in range(3)])
        self.assertEqual(profile["district_shares"], {"高雄市苓雅區": 1.0})
        self.assertEqual(texts(profile, "常消費地區"), ["高雄市苓雅區"])

    def test_frequent_brands_need_three_invoices(self):
        profile = profile_of([row(f"S{i}", merchant="統一超商股份有限公司示範門市") for i in range(3)]
                             + [row("C1", merchant="示範咖啡信義店"), row("C2", merchant="示範咖啡信義店")])
        self.assertEqual(texts(profile, "常去品牌"), ["7-ELEVEN（3 次）"])
        self.assertAlmostEqual(profile["brand_shares"]["示範咖啡"], 0.4)

    def test_price_level_uses_median_personal_invoice(self):
        cheap, middle = SETTINGS["price_levels"][0]["below"], SETTINGS["price_levels"][1]["below"]

        def level(totals):
            return texts(profile_of([row(f"I{i}", amount=total) for i, total in enumerate(totals)]), "消費檔次")

        self.assertEqual(level([cheap - 1, cheap - 1, middle + 1]), ["小資型"])
        self.assertEqual(level([cheap, cheap, middle + 1]), ["均衡型"])
        self.assertEqual(level([middle, middle, 1]), ["享受型"])
        self.assertEqual(level([middle, middle]), [])
        discounted = profile_of([row("D", amount=cheap + 10), row("D", amount=-20, name="測試折扣"),
                                 row("E", amount=cheap - 10), row("F", amount=cheap - 10)])
        self.assertEqual(texts(discounted, "消費檔次"), ["小資型"])

    def test_shared_bills_stay_out_of_price_level(self):
        cheap = SETTINGS["price_levels"][0]["below"]
        personal = [row(f"P{i}", amount=cheap - 10) for i in range(3)]
        portions = [row(f"S{i}", amount=1600, quantity=4) for i in range(3)]
        repeated = [row(f"R{i}", amount=800, name="示範火鍋") for i in range(3) for _ in range(2)]
        self.assertEqual(texts(profile_of(portions + personal), "消費檔次"), ["小資型"])
        self.assertEqual(texts(profile_of(repeated + personal), "消費檔次"), ["小資型"])
        self.assertEqual(texts(profile_of(portions + personal[:2]), "消費檔次"), [])

    def test_flavor_tag_describes_purchases(self):
        rows = [row("A", name="示範全素水餃"), row("B", name="示範全素水餃"), row("C", name="示範鮮蝦水餃", merchant="示範水餃館")]
        profile = profile_of(rows)
        self.assertEqual(texts(profile, "葷素紀錄"), ["葷素品項都有"])
        self.assertEqual(profile["flavor_items"], {"示範水餃館": {"示範鮮蝦水餃": 1}})
        self.assertEqual(texts(profile_of(rows[:2]), "葷素紀錄"), [])
        self.assertEqual(texts(profile_of([row(f"V{i}", name="示範素食便當") for i in range(3)]), "葷素紀錄"), ["素食品項較多"])
        self.assertIsNone(profile_of([row(f"V{i}", name="示範蔬菜水餃") for i in range(3)])["meat_ratio"])
        self.assertIsNone(profile_of([row(f"G{i}", category=4, name="示範雞肉造型背包") for i in range(3)])["meat_ratio"])


if __name__ == "__main__":
    unittest.main()
