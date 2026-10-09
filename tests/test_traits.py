"""Taste traits on small fictional purchase sets, one behaviour at a time."""
import json
import unittest
from datetime import date
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.personas import build_friends, build_personas
from src.receipt.signals import calendar_days, category_counts
from src.receipt.traits import (between, build_vector, dated, explain, load_context, population, signal_ids, trait_parts,
                                trait_value)

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
TRAITS = CONTEXT["traits"]["traits"]
INDEX = {trait["id"]: index for index, trait in enumerate(TRAITS)}
PERIOD = [(2026, 3), (2026, 4)]
DAYS, OFF, LONG = calendar_days(PERIOD, CONTEXT["calendar"])
WORKDAYS = [day for day in DAYS if day not in OFF]
LONG_DAYS = sorted(LONG)
HOME, AWAY = "高雄市苓雅區", "屏東縣恆春鎮"


def bought(*groups):
    """Rows from (days, name, category, amount, merchant, district) groups; every purchase is its own invoice."""
    rows = []
    for days, name, category, amount, merchant, district in groups:
        for day in days:
            rows.append({"date": day, "day": day.day, "invoice": f"T{len(rows):03}", "merchant": merchant,
                         "district": district, "name": name, "quantity": 1, "amount": amount, "category": category,
                         "provisional": False})
    return rows


def lunches(count=20):
    """Plain lunches at a neighbourhood shop, to reach the 20-item minimum without saying much."""
    return (WORKDAYS[:count], "測試排骨便當", 0, 100, "測試便當店", HOME)


def trait(rows, name):
    vector = build_vector(rows, PERIOD, CONTEXT)
    return vector[INDEX[name]]


class ConfigTests(unittest.TestCase):
    def test_shipped_traits_match_the_spec(self):
        self.assertEqual(len(TRAITS), 18)
        self.assertEqual([trait["id"] for trait in TRAITS if trait["kind"] == "two_sided"],
                         ["spend", "meals", "motive", "cooking", "sweet", "routine", "travel", "stock", "days", "holiday"])
        for trait in TRAITS:
            self.assertAlmostEqual(sum(signal["weight"] for signal in trait["signals"]), 1, msg=trait["id"])
            self.assertEqual(trait["weight"], 1)
        self.assertEqual(CONTEXT["traits"]["min_items"], 20)
        self.assertEqual(CONTEXT["traits"]["similarity"], {"shrink": 0.25, "min_shared_two_sided": 5})
        self.assertEqual(CONTEXT["traits"]["match"], {"min_score": 0.3, "opposite_score": 0.1, "top": 5})
        self.assertEqual({trait["id"]: trait["habit"] for trait in TRAITS if trait["kind"] == "level"},
                         {"sport": "運動", "driving": "開車騎車", "lifestyle": "生活小物", "tech": "3C", "fun": "娛樂",
                          "pets_cat": "養貓", "pets_dog": "養狗", "alcohol": "小酌"})
        self.assertEqual(CONTEXT["calendar"]["holidays"], ["2026-04-03", "2026-04-06"])


class WordingTests(unittest.TestCase):
    def test_every_signal_has_a_label_and_a_unit_and_every_trait_its_lines(self):
        units = {"share", "sugar", "money", "money_month", "times_month", "items_month", "kinds"}
        seen = {}
        for trait in TRAITS:
            for signal in trait["signals"]:
                with self.subTest(signal=signal["id"]):
                    self.assertIn(signal["unit"], units)
                    self.assertLessEqual(len(signal["label"]), 6)
                    # A signal shared by two traits reads the same in both.
                    self.assertEqual(seen.setdefault(signal["id"], (signal["label"], signal["unit"])), (signal["label"], signal["unit"]))
            with self.subTest(trait=trait["id"]):
                if trait["kind"] == "two_sided":
                    self.assertTrue(trait["short"])
                    self.assertEqual(len(trait["lines"]["both"]), 2)
                    self.assertTrue(trait["lines"]["split"])
                else:
                    self.assertIsInstance(trait["lines"]["both"], str)
        labels = [label for label, _ in seen.values()]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(CONTEXT["traits"]["readout"], {"no_alike": "共同話題還在找。", "no_unlike": "難得這麼合拍。"})


class CalendarTests(unittest.TestCase):
    def test_spring_2026_long_weekend_and_days_off(self):
        self.assertEqual(LONG_DAYS, [date(2026, 4, 3), date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6)])
        self.assertEqual(len(OFF), 19)
        self.assertEqual(len(DAYS), 61)


class ScaleTests(unittest.TestCase):
    def test_between_climbs_and_falls(self):
        self.assertEqual(between(0, 0, 0.3, 1), -1)
        self.assertAlmostEqual(between(0.5, 0, 0.3, 1), 0.2 / 0.7)
        self.assertEqual(between(2, 0, 0.3, 1), 1)
        self.assertAlmostEqual(between(0.6, 0.7, 0.45, 0.2), -0.6)
        self.assertEqual(between(0.1, 0.7, 0.45, 0.2), 1)

    def test_both_ends_stay_reachable_and_missing_signals_hand_over_their_weight(self):
        spend = TRAITS[INDEX["spend"]]
        measured = {"counts": {"food_items": 10}, "constants": {},
                    "signals": {"meal_cost": 90, "clearance_share": 0.3, "premium_drink_share": None}}
        self.assertEqual(trait_value(spend, measured), -1)
        measured["signals"] = {"meal_cost": 300, "clearance_share": 0, "premium_drink_share": 0.5}
        self.assertEqual(trait_value(spend, measured), 1)
        measured["counts"] = {"food_items": 9}
        self.assertIsNone(trait_value(spend, measured))


class TraitTests(unittest.TestCase):
    def test_too_few_items_leave_no_vector(self):
        self.assertIsNone(build_vector([], [], CONTEXT))
        self.assertIsNone(build_vector(bought(lunches(19)), PERIOD, CONTEXT))
        self.assertIsNotNone(build_vector(bought(lunches(20)), PERIOD, CONTEXT))

    def test_clearance_lunches_at_80_dollars_mean_saving(self):
        rows = bought((WORKDAYS[:24], "測試即期雞腿便當", 0, 80, "示範超商", HOME))
        self.assertLessEqual(trait(rows, "spend"), -0.5)
        rows = bought((WORKDAYS[:12], "測試和牛定食", 0, 400, "測試定食屋", HOME),
                      (WORKDAYS[12:24], "測試精品手沖", 1, 180, "測試咖啡館", HOME))
        self.assertGreaterEqual(trait(rows, "spend"), 0.5)

    def test_daily_rice_balls_mean_quick_meals_and_shops_mean_proper_ones(self):
        rows = bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME))
        self.assertLessEqual(trait(rows, "meals"), -0.5)
        rows = bought((WORKDAYS[:24], "測試牛肉麵", 0, 150, "測試麵館", HOME))
        self.assertGreaterEqual(trait(rows, "meals"), 0.5)
        self.assertIsNone(trait(bought(lunches(7), (WORKDAYS[7:20], "測試無糖綠茶", 1, 25, "示範超商", HOME)), "meals"))

    def test_clearance_and_rice_balls_send_convenience_store_shoppers_opposite_ways(self):
        saving = bought((WORKDAYS[:24], "測試即期排骨便當", 0, 69, "示範超商", HOME))
        hurried = bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME))
        self.assertLessEqual(trait(saving, "motive"), -0.5)
        self.assertGreaterEqual(trait(hurried, "motive"), 0.5)

    def test_market_vegetables_mean_cooking_but_fruit_does_not(self):
        rows = bought((WORKDAYS[:16], "測試高麗菜", 3, 120, "測試傳統市場", HOME),
                      (WORKDAYS[16:20], "測試白米", 3, 200, "測試傳統市場", HOME),
                      (WORKDAYS[20:24], "測試醬油", 3, 90, "測試傳統市場", HOME))
        self.assertGreaterEqual(trait(rows, "cooking"), 0.5)
        rows = bought((WORKDAYS[:6], "測試香蕉", 3, 60, "測試水果攤", HOME),
                      (WORKDAYS[6:24], "測試排骨便當", 0, 100, "測試便當店", HOME))
        self.assertLessEqual(trait(rows, "cooking"), -0.5)

    def test_sugar_level_sets_light_or_sweet(self):
        rows = bought((WORKDAYS[:12], "測試冰美式", 1, 60, "測試咖啡館", HOME),
                      (WORKDAYS[12:24], "測試無糖綠茶", 1, 25, "示範超商", HOME))
        self.assertLessEqual(trait(rows, "sweet"), -0.7)
        rows = bought((WORKDAYS[:16], "測試全糖紅茶", 1, 40, "測試飲料店", HOME),
                      (WORKDAYS[16:24], "測試巧克力蛋糕", 2, 80, "測試甜點店", HOME))
        self.assertGreaterEqual(trait(rows, "sweet"), 0.7)

    def test_long_weekend_trips(self):
        base = lunches()
        rows = bought(base, (LONG_DAYS[:2], "測試海鮮套餐", 0, 600, "測試海港餐廳", AWAY))
        self.assertGreaterEqual(trait(rows, "holiday"), 0.5)
        rows = bought(base, (WORKDAYS[30:32], "測試海鮮套餐", 0, 600, "測試海港餐廳", AWAY))
        self.assertLessEqual(trait(rows, "holiday"), -0.3)
        rows = bought(base, (LONG_DAYS[:1], "測試海鮮套餐", 0, 600, "測試海港餐廳", AWAY))
        self.assertIsNone(trait(rows, "holiday"))

    def test_no_home_city_means_no_trip_days(self):
        # Six districts at a sixth each: none reaches the 20% that marks a home city, so nothing counts as away.
        districts = ["高雄市苓雅區", "高雄市新興區", "高雄市前鎮區", "高雄市左營區", "臺北市信義區", "臺北市內湖區"]
        rows = bought(*[(WORKDAYS[4 * index:4 * index + 4], "測試排骨便當", 0, 100, "測試便當店", district)
                        for index, district in enumerate(districts)])
        self.assertIsNone(trait(rows, "holiday"))

    def test_workday_only_shopping_leans_to_workdays(self):
        self.assertEqual(trait(bought(lunches(24)), "days"), -1)

    def test_entertainment_pets_and_drinks(self):
        rows = bought(lunches(),
                      (WORKDAYS[20:22], "測試電影票", 5, 300, "測試影城", HOME),
                      (WORKDAYS[22:24], "測試歡唱時段", 5, 350, "測試KTV", HOME),
                      (WORKDAYS[24:26], "測試展覽門票", 5, 250, "測試展覽館", HOME),
                      (WORKDAYS[26:28], "測試密室逃脫", 5, 500, "測試密室", HOME))
        self.assertAlmostEqual(trait(rows, "fun"), 1)
        rows = bought(lunches(),
                      (WORKDAYS[20:24], "測試貓飼料", 8, 400, "測試寵物店", HOME),
                      (WORKDAYS[24:26], "測試貓砂", 8, 300, "測試寵物店", HOME))
        self.assertAlmostEqual(trait(rows, "pets_cat"), 1)
        self.assertEqual(trait(rows, "pets_dog"), 0)
        rows = bought(lunches(),
                      (WORKDAYS[20:36], "測試生啤酒", 1, 60, "示範超商", HOME),
                      (WORKDAYS[36:44], "測試料理米酒", 3, 50, "示範超商", HOME))
        self.assertAlmostEqual(trait(rows, "alcohol"), 0.7)

    def test_dog_snacks_are_dog_food_and_pet_shop_visits_follow_pet_items(self):
        rows = bought(lunches(), (WORKDAYS[20:24], "測試狗零食", 8, 200, "測試寵物店", HOME))
        self.assertAlmostEqual(trait(rows, "pets_dog"), 0.75)
        self.assertEqual(trait(rows, "pets_cat"), 0)
        # A pet-shop bill without a pet item is split evenly, even when its name mentions a cat.
        rows = bought(lunches(), (WORKDAYS[20:22], "測試貓抓板", 8, 300, "測試寵物店", HOME))
        self.assertAlmostEqual(trait(rows, "pets_cat"), 0.075)
        self.assertAlmostEqual(trait(rows, "pets_dog"), 0.075)

    def test_a_zero_quantity_line_does_not_break_the_vector(self):
        rows = bought(lunches(), (WORKDAYS[20:22], "測試精品手沖", 1, 180, "測試咖啡館", HOME))
        rows[-1]["quantity"] = 0
        self.assertIsNotNone(build_vector(rows, PERIOD, CONTEXT))


class ExplainTests(unittest.TestCase):
    def test_each_trait_is_the_sum_of_its_signal_pushes(self):
        catalog = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
        rows, period = dated(build_demo(catalog))
        people = [*build_personas(CONTEXT["calendar"]), *build_friends(CONTEXT["calendar"]), {"name": "我", "rows": rows}]
        for name, person in population(people, period, CONTEXT).items():
            for trait, value, pushes in zip(TRAITS, person["vector"], person["pushes"]):
                with self.subTest(name=name, trait=trait["id"]):
                    self.assertEqual(len(pushes), len(trait["signals"]))
                    if value is None:
                        self.assertEqual(pushes, [None] * len(pushes))
                    else:
                        self.assertAlmostEqual(sum(push for push in pushes if push is not None), value, delta=1e-9)

    def test_a_thin_trait_pushes_nothing_and_an_unmeasured_signal_pushes_none(self):
        person = explain(bought(lunches()), PERIOD, CONTEXT)
        self.assertIsNone(person["vector"][INDEX["holiday"]])
        self.assertEqual(person["pushes"][INDEX["holiday"]], [None])
        # Twenty lunches and no drinks: the share of premium drinks cannot be measured.
        self.assertIsNone(person["signals"]["premium_drink_share"])
        self.assertEqual(person["pushes"][INDEX["spend"]], [-0.625, 0.0, None])
        self.assertEqual(set(person["signals"]), {signal["id"] for trait in TRAITS for signal in trait["signals"]})

    def test_one_signal_pushes_two_traits(self):
        person = explain(bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME)), PERIOD, CONTEXT)
        for trait_id, sign in (("meals", -1), ("motive", 1)):
            ids = [signal["id"] for signal in TRAITS[INDEX[trait_id]]["signals"]]
            self.assertGreater(sign * person["pushes"][INDEX[trait_id]][ids.index("weekday_quick_share")], 0, trait_id)

    def test_level_traits_are_only_pushed_up(self):
        person = explain(bought(lunches(), (WORKDAYS[20:24], "測試貓飼料", 8, 400, "測試寵物店", HOME)), PERIOD, CONTEXT)
        for trait, pushes in zip(TRAITS, person["pushes"]):
            if trait["kind"] == "level":
                self.assertTrue(all(push is None or push >= 0 for push in pushes), trait["id"])
        self.assertGreater(person["vector"][INDEX["pets_cat"]], 0)

    def test_pushes_that_cancel_out_leave_the_trait_at_zero(self):
        motive = TRAITS[INDEX["motive"]]
        measured = {"counts": {"store_food_items": 8}, "constants": {},
                    "signals": {"store_clearance_share": 0.2, "weekday_quick_share": 0.3}}
        self.assertEqual(trait_parts(motive, measured), (0.0, [-0.25, 0.25]))

    def test_signals_are_listed_once_in_the_order_they_first_appear(self):
        ids = signal_ids(CONTEXT["traits"])
        self.assertEqual(len(ids), 46)
        self.assertEqual(len(set(ids)), 46)
        self.assertEqual(ids[:7], ["meal_cost", "clearance_share", "premium_drink_share", "store_meal_share",
                                   "weekday_quick_share", "shop_meal_share", "store_clearance_share"])

    def test_too_little_data_explains_nothing_and_names_must_be_unique(self):
        self.assertIsNone(explain([], [], CONTEXT))
        self.assertIsNone(explain(bought(lunches(19)), PERIOD, CONTEXT))
        people = [{"name": "測試甲", "rows": bought(lunches())}, {"name": "測試乙", "rows": bought(lunches(19))}]
        explained = population(people, PERIOD, CONTEXT)
        self.assertEqual(list(explained), ["測試甲", "測試乙"])
        self.assertEqual(explained["測試甲"]["vector"], build_vector(people[0]["rows"], PERIOD, CONTEXT))
        self.assertIsNone(explained["測試乙"])
        with self.assertRaises(ValueError):
            population([*people, {"name": "測試甲", "rows": []}], PERIOD, CONTEXT)


class CategoryCountTests(unittest.TestCase):
    def test_valid_items_per_category_once_per_bill(self):
        rows = bought((WORKDAYS[:3], "測試排骨便當", 0, 100, "測試便當店", HOME),
                      (WORKDAYS[3:5], "測試紅茶", 1, 30, "測試飲料店", HOME))
        rows.append(dict(rows[0]))                                    # the same item again on the same bill
        rows.append({**rows[0], "name": "測試贈品", "amount": 0})        # a free gift
        rows.append({**rows[0], "name": "測試未分類", "category": 10, "provisional": True})
        self.assertEqual(category_counts(rows), [3, 2, 0, 0, 0, 0, 0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
