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
        self.assertEqual(SETTINGS["weights"], {"category": 0.35, "brand": 0.15, "flavor": 0.1, "price": 0.1})
        self.assertEqual(SETTINGS["thresholds"], {"match": 0.8, "nearby": 0.7})
        cities = [city for group in SETTINGS["regions"].values() for city in group]
        self.assertEqual(len(set(cities)), 22)
        self.assertTrue(all(len(city) == 3 for city in cities))
        self.assertEqual(SETTINGS["category_min_items"], 10)
        self.assertEqual([level["label"] for level in SETTINGS["price_levels"]], ["小資型", "均衡型", "享受型"])
        self.assertEqual([level.get("below") for level in SETTINGS["price_levels"]], [100, 300, None])
        self.assertEqual(SETTINGS["meal"], {"portion_category": "正餐", "food_categories": ["正餐", "飲品", "零食甜點"]})
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

    def test_meat_added_to_a_vegetarian_name_is_unknown(self):
        flavor = SETTINGS["flavor"]
        self.assertIsNone(flavor_of("示範素食便當加雞腿", flavor))
        self.assertIsNone(flavor_of("示範植物肉與牛肉雙拼堡", flavor))
        # A meat word right after 素 or 植物 names an imitation, not added meat.
        self.assertEqual(flavor_of("示範素肉燥飯", flavor), 0)
        self.assertEqual(flavor_of("示範植物牛肉堡", flavor), 0)

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

    def test_price_level_divides_a_meal_bill_by_its_main_dishes(self):
        # Four people, four different hotpots and four drinks on each bill: 450 a head, not 1,800 a bill.
        rows = [row(f"H{i}", 0, amount=amount, name=name) for i in range(3)
                for name, amount in (("示範牛肉鍋", 420), ("示範雞肉鍋", 380), ("示範海鮮鍋", 450), ("示範蔬菜鍋", 350))]
        rows += [row(f"H{i}", 1, amount=200, name="示範紅茶", quantity=4) for i in range(3)]
        self.assertEqual(texts(profile_of(rows), "消費檔次"), ["享受型"])
        bentos = [row(f"B{i}", 0, amount=800, name="示範便當", quantity=4) for i in range(3)]
        self.assertEqual(texts(profile_of(bentos), "消費檔次"), ["均衡型"])

    def test_price_level_uses_the_median_meal(self):
        cheap, middle = SETTINGS["price_levels"][0]["below"], SETTINGS["price_levels"][1]["below"]

        def level(amounts):
            return texts(profile_of([row(f"I{i}", 0, amount=amount) for i, amount in enumerate(amounts)]), "消費檔次")

        self.assertEqual(level([cheap - 1, cheap - 1, middle + 1]), ["小資型"])
        self.assertEqual(level([cheap, cheap, middle + 1]), ["均衡型"])
        self.assertEqual(level([middle, middle, 1]), ["享受型"])
        self.assertEqual(level([middle, middle]), [])

    def test_drinks_and_discounts_on_a_meal_bill_count(self):
        # With the drink, D is 120 and the median is 120; without it the median would fall to 80.
        drinks = [row("D", 0, amount=80, name="示範便當"), row("D", 1, amount=40, name="示範紅茶"),
                  row("E", 0, amount=120), row("F", 0, amount=50)]
        self.assertEqual(texts(profile_of(drinks), "消費檔次"), ["均衡型"])
        # With the discount, G is 90 and the median is 95; without it the median would rise to 110.
        discounts = [row("G", 0, amount=110, name="示範便當"), row("G", 0, amount=-20, name="示範折扣"),
                     row("H", 0, amount=95), row("I", 0, amount=300)]
        self.assertEqual(texts(profile_of(discounts), "消費檔次"), ["小資型"])

    def test_bills_without_a_main_dish_stay_out_of_price_level(self):
        drinks = [row(f"T{i}", 1, amount=60, name="示範紅茶") for i in range(3)]
        gadgets = [row(f"G{i}", 9, amount=2000, name="示範耳機") for i in range(3)]
        self.assertEqual(texts(profile_of(drinks + gadgets), "消費檔次"), [])
        meals = [row(f"M{i}", 0, amount=120) for i in range(3)]
        self.assertEqual(texts(profile_of(drinks + gadgets + meals), "消費檔次"), ["均衡型"])
        unreviewed = [row(f"P{i}", 10, amount=120, provisional=True) for i in range(3)]
        self.assertEqual(texts(profile_of(unreviewed), "消費檔次"), [])

    def test_tags_carry_comparison_keys(self):
        rows = [row(f"S{i}", 0, merchant="統一超商股份有限公司示範門市", name="示範素食便當") for i in range(10)]
        keys = {(tag["dimension"], tag["key"]) for tag in profile_of(rows)["tags"]}
        self.assertEqual(keys, {("品類偏好", "正餐"), ("常消費地區", "高雄市苓雅區"), ("常去品牌", "7-ELEVEN"),
                                ("消費檔次", "均衡型"), ("葷素紀錄", "素食品項較多")})

    def test_flavor_tag_describes_purchases(self):
        rows = [row("A", name="示範全素水餃"), row("B", name="示範全素水餃"), row("C", name="示範鮮蝦水餃", merchant="示範水餃館")]
        profile = profile_of(rows)
        self.assertEqual(texts(profile, "葷素紀錄"), ["葷素品項都有"])
        self.assertEqual(texts(profile_of(rows[:2]), "葷素紀錄"), [])
        self.assertEqual(texts(profile_of([row(f"V{i}", name="示範素食便當") for i in range(3)]), "葷素紀錄"), ["素食品項較多"])
        self.assertIsNone(profile_of([row(f"V{i}", name="示範蔬菜水餃") for i in range(3)])["meat_ratio"])
        self.assertIsNone(profile_of([row(f"G{i}", category=4, name="示範雞肉造型背包") for i in range(3)])["meat_ratio"])


if __name__ == "__main__":
    unittest.main()
