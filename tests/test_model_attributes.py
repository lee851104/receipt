"""Model attributes in the taste pipeline: None means unknown, never 'no', and the rules' own answers change nothing."""
import json
import unittest
from datetime import date
from pathlib import Path

from src.ml.fields import ATTRIBUTES, FIELDS
from src.receipt.attributes import FUN_WORDS, channel_of, describe, from_model
from src.receipt.signals import calendar_days, gather, measure
from src.receipt.traits import build_vector, explain, load_context, trait_value

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
BRANDS, WORDS = CONTEXT["brands"], CONTEXT["vocabulary"]
PERIOD = [(2026, 3), (2026, 4)]
DAYS, OFF, _ = calendar_days(PERIOD, CONTEXT["calendar"])
WORKDAYS = [day for day in DAYS if day not in OFF]
HOME = "高雄市苓雅區"


def model(**given):
    """What the model answers for one name: every one of the 23 fields unknown, except those given."""
    return {**dict.fromkeys(FIELDS), **given}


def answer(category, fields, name="測試品名", merchant="測試小店", quantity=1):
    row = {"name": name, "category": category, "merchant": merchant, "quantity": quantity}
    return from_model(row, channel_of(merchant, BRANDS, WORDS), fields, WORDS)


def bought(*groups):
    """Rows from (days, name, category, amount, merchant[, quantity]) groups; every purchase is its own invoice."""
    rows = []
    for days, name, category, amount, merchant, *quantity in groups:
        for day in days:
            rows.append({"date": day, "day": day.day, "invoice": f"M{len(rows):03}", "merchant": merchant, "district": HOME,
                         "name": name, "quantity": quantity[0] if quantity else 1, "amount": amount, "category": category,
                         "provisional": False})
    return rows


def signals_of(rows, attributes):
    return measure(rows, PERIOD, CONTEXT, attributes)["signals"]


class ConversionTests(unittest.TestCase):
    def test_the_answers_have_the_same_keys_as_the_rules(self):
        row = {"name": "測試品名", "category": 0, "merchant": "測試小店", "quantity": 1}
        self.assertEqual(from_model(row, "一般店家", model(), WORDS).keys(), describe(row, "一般店家", WORDS).keys())

    def test_a_question_only_applies_inside_its_categories(self):
        # Outside the gate the answer is a known "no" whatever the model says; inside, the model's answer stands, None too.
        gates = {"clearance": {0, 1, 2, 3}, "quick": {0}, "cooking": {3}, "kitchen": {3, 8},
                 "sport_gear": set(range(4, 10)), "car_care": set(range(4, 10)), "home": set(range(4, 10)),
                 "stationery": set(range(4, 10))}
        for category in range(11):
            self.assertEqual(answer(category, model())["food"], category in (0, 1, 2, 3))
            for key, inside in gates.items():
                for given, expected in ((True, True), (False, False), (None, None)):
                    with self.subTest(category=category, key=key, given=given):
                        self.assertEqual(answer(category, model(**{key: given}))[key], expected if category in inside else False)

    def test_the_other_questions_apply_to_any_category(self):
        for category in range(11):
            for key in ("sport_supply", "pet_food", "pet_supply", "alcohol"):
                for given in (True, False, None):
                    with self.subTest(category=category, key=key, given=given):
                        self.assertIs(answer(category, model(**{key: given}))[key], given)

    def test_sugar_is_the_models_and_a_missing_answer_falls_back_to_the_default_rules(self):
        self.assertEqual(answer(1, model(sugar=0.5), name="測試珍珠鮮奶")["sugar"], 0.5)
        # No sugar at all is a real answer, not a missing one.
        self.assertEqual(answer(1, model(sugar=0), name="測試珍珠鮮奶")["sugar"], 0)
        self.assertEqual(answer(1, model(), name="測試半糖綠茶")["sugar"], 0.5)
        self.assertEqual(answer(1, model(), name="測試鮮奶")["sugar"], 0.2)
        self.assertEqual(answer(1, model(), name="測試青茶", merchant="示範茶屋")["sugar"], 1)
        self.assertIsNone(answer(1, model(), name="測試手沖咖啡")["sugar"])
        # Only drinks are sweet.
        self.assertIsNone(answer(2, model(sugar=0.5), name="測試半糖布丁")["sugar"])
        self.assertIsNone(answer(0, model(sugar=1))["sugar"])

    def test_three_of_a_kind_are_bulk_whatever_the_model_says(self):
        self.assertIs(answer(8, model(bulk=False), quantity=3)["bulk"], True)
        self.assertIs(answer(8, model(), quantity=3)["bulk"], True)
        self.assertIs(answer(8, model(bulk=False), quantity=2)["bulk"], False)
        self.assertIsNone(answer(8, model(), quantity=2)["bulk"])
        self.assertIs(answer(8, model(bulk=True), quantity=1)["bulk"], True)

    def test_the_models_kind_of_fun_is_written_in_chinese(self):
        self.assertEqual(FUN_WORDS, {"movie": "電影", "singing": "唱歌", "show": "展演", "game": "遊樂"})
        for kind, word in FUN_WORDS.items():
            self.assertEqual(answer(5, model(fun=kind))["fun"], word)

    def test_a_kind_of_fun_is_taken_in_chinese_or_in_english(self):
        for kind, word in FUN_WORDS.items():
            with self.subTest(kind=kind):
                self.assertEqual(answer(5, model(fun=word))["fun"], word)
                self.assertEqual(answer(5, model(fun=kind))["fun"], word)
                # Either spelling beats the shop's words.
                self.assertEqual(answer(5, model(fun=word), merchant="測試影城")["fun"], word)
        # Anything else is not given: the shop's words decide, or nothing does.
        for stray in ("karaoke", "KTV", "電玩", "Movie", "", 1, True):
            with self.subTest(stray=stray):
                self.assertEqual(answer(5, model(fun=stray), merchant="測試KTV")["fun"], "唱歌")
                self.assertIsNone(answer(5, model(fun=stray), merchant="測試小店")["fun"])

    def test_without_a_kind_of_fun_the_shop_decides_but_the_name_does_not(self):
        self.assertEqual(answer(5, model(), merchant="測試影城")["fun"], "電影")
        self.assertEqual(answer(5, model(), merchant="測試KTV")["fun"], "唱歌")
        self.assertIsNone(answer(5, model(), name="測試電影票", merchant="測試小店")["fun"])
        self.assertEqual(answer(5, model(fun="game"), merchant="測試影城")["fun"], "遊樂")
        # A value outside the four kinds counts as not given.
        self.assertEqual(answer(5, model(fun="karaoke"), merchant="測試KTV")["fun"], "唱歌")
        self.assertIsNone(answer(5, model(fun="karaoke"), merchant="測試小店")["fun"])

    def test_only_cats_and_dogs_are_species(self):
        self.assertEqual(answer(8, model(species="cat"))["species"], "cat")
        self.assertEqual(answer(8, model(species="dog"))["species"], "dog")
        self.assertIsNone(answer(8, model(species="bird"))["species"])
        self.assertIsNone(answer(8, model())["species"])

    def test_a_name_still_waiting_answers_like_a_model_that_knows_nothing(self):
        for category in range(11):
            for quantity in (1, 3):
                with self.subTest(category=category, quantity=quantity):
                    self.assertEqual(answer(category, None, quantity=quantity), answer(category, model(), quantity=quantity))
        # Inside its category a question is unknown, outside it is a known no.
        meal = answer(0, None)
        self.assertEqual([meal["food"], meal["clearance"], meal["quick"], meal["cooking"], meal["kitchen"], meal["home"]],
                         [True, None, None, False, False, False])
        self.assertEqual([meal[key] for key in ("sport_supply", "pet_food", "pet_supply", "alcohol", "bulk", "fun", "species")],
                         [None] * 7)
        goods = answer(8, None)
        self.assertEqual([goods["food"], goods["clearance"], goods["kitchen"], goods["home"], goods["car_care"]],
                         [False, False, None, None, None])
        # What no model is needed for still applies.
        self.assertEqual(answer(1, None, name="測試半糖綠茶")["sugar"], 0.5)
        self.assertEqual(answer(5, None, merchant="測試影城")["fun"], "電影")
        self.assertIs(answer(8, None, quantity=3)["bulk"], True)


class SignalTests(unittest.TestCase):
    def test_a_name_missing_from_the_attributes_is_still_waiting(self):
        rows = bought((WORKDAYS[:2], "測試排骨便當", 0, 100, "測試便當店"))
        lines, _ = gather(rows, CONTEXT, {})
        self.assertEqual([(line["food"], line["clearance"], line["quick"]) for line in lines], [(True, None, None)] * 2)
        # Without attributes the rules answer, as before.
        lines, _ = gather(rows, CONTEXT)
        self.assertEqual([(line["clearance"], line["quick"]) for line in lines], [(False, False)] * 2)

    def test_food_still_waiting_stays_out_of_the_clearance_share_denominator(self):
        rows = bought((WORKDAYS[:10], "測試排骨便當", 0, 100, "測試便當店"),
                      (WORKDAYS[10:15], "測試即期便當", 0, 80, "測試便當店"),
                      (WORKDAYS[15:20], "測試新品便當", 0, 90, "測試便當店"))
        attributes = {"測試排骨便當": model(clearance=False), "測試即期便當": model(clearance=True), "測試新品便當": None}
        measured = measure(rows, PERIOD, CONTEXT, attributes)
        self.assertEqual(measured["signals"]["clearance_share"], 5 / 15)
        self.assertEqual(len(measured["purchases"]["clearance_share"]), 5)
        # The counts a trait requires stay totals: the waiting food counts as food.
        self.assertEqual(measured["counts"]["food_items"], 20)
        # The rules never leave a question unknown, so every item counts there.
        self.assertEqual(signals_of(rows, None)["clearance_share"], 5 / 20)

    def test_the_store_clearance_share_counts_only_store_food_with_a_known_answer(self):
        rows = bought((WORKDAYS[:5], "測試即期便當", 0, 69, "示範超商"),
                      (WORKDAYS[5:10], "測試新品便當", 0, 90, "示範超商"),
                      (WORKDAYS[10:15], "測試排骨便當", 0, 90, "示範超商"),
                      (WORKDAYS[15:25], "測試牛肉麵", 0, 150, "測試麵館"))
        attributes = {"測試即期便當": model(clearance=True), "測試新品便當": None,
                      "測試排骨便當": model(clearance=False), "測試牛肉麵": model(clearance=False)}
        signals = signals_of(rows, attributes)
        self.assertEqual(signals["store_clearance_share"], 5 / 10)
        self.assertEqual(signals["clearance_share"], 5 / 20)

    def test_the_fresh_share_counts_fresh_food_still_waiting_as_unknown_but_other_food_as_not_cooking(self):
        rows = bought((WORKDAYS[:6], "測試高麗菜", 3, 120, "測試傳統市場"),
                      (WORKDAYS[6:10], "測試新鮮蔬菜", 3, 100, "測試傳統市場"),
                      (WORKDAYS[10:20], "測試排骨便當", 0, 100, "測試便當店"))
        attributes = {"測試高麗菜": model(cooking=True), "測試新鮮蔬菜": None, "測試排骨便當": None}
        self.assertEqual(signals_of(rows, attributes)["fresh_share"], 6 / 16)

    def test_the_bulk_share_counts_daily_items_whose_answer_is_known(self):
        rows = bought((WORKDAYS[:3], "測試衛生紙箱", 8, 200, "測試量販店"),
                      (WORKDAYS[3:6], "測試牙刷", 8, 60, "測試量販店"),
                      (WORKDAYS[6:10], "測試新品日用品", 8, 90, "測試量販店"),
                      (WORKDAYS[10:12], "測試洗碗精", 8, 80, "測試量販店", 3))
        attributes = {"測試衛生紙箱": model(bulk=True), "測試牙刷": model(bulk=False), "測試新品日用品": None, "測試洗碗精": None}
        self.assertEqual(signals_of(rows, attributes)["bulk_share"], 5 / 8)

    def test_the_weekday_quick_share_counts_workdays_with_a_known_answer(self):
        rows = bought((WORKDAYS[:4], "測試鮪魚飯糰", 0, 45, "示範超商"),
                      (WORKDAYS[8:10], "測試牛肉麵", 0, 150, "測試麵館"),
                      (WORKDAYS[4:8], "測試新品套餐", 0, 120, "測試便當店"),
                      # A workday that also has a known answer is counted once.
                      (WORKDAYS[:1], "測試新品套餐", 0, 120, "測試便當店"))
        attributes = {"測試鮪魚飯糰": model(quick=True), "測試牛肉麵": model(quick=False), "測試新品套餐": None}
        self.assertEqual(signals_of(rows, attributes)["weekday_quick_share"], 4 / 6)
        self.assertEqual(signals_of(rows, None)["weekday_quick_share"], 4 / 10)

    def test_counted_signals_only_count_what_is_known_to_be_true(self):
        rows = bought((WORKDAYS[:3], "測試生啤酒", 1, 60, "示範超商"),
                      (WORKDAYS[3:6], "測試新品飲料", 1, 60, "示範超商"),
                      (WORKDAYS[6:8], "測試氣泡水", 1, 30, "示範超商"))
        attributes = {"測試生啤酒": model(alcohol=True), "測試新品飲料": None, "測試氣泡水": model(alcohol=False)}
        self.assertEqual(signals_of(rows, attributes)["alcohol_items"], 3 / 2)

    def test_names_all_still_waiting_leave_the_ratios_unmeasured(self):
        rows = bought((WORKDAYS[:12], "測試排骨便當", 0, 100, "測試便當店"), (WORKDAYS[12:24], "測試即期便當", 0, 80, "示範超商"))
        explained = explain(rows, PERIOD, CONTEXT, {"測試排骨便當": None, "測試即期便當": None})
        self.assertIsNone(explained["signals"]["clearance_share"])
        self.assertIsNone(explained["signals"]["store_clearance_share"])
        self.assertIsNone(explained["signals"]["weekday_quick_share"])
        self.assertEqual(len(explained["vector"]), 18)


# Per share over a pool: (category, shop, question, a name answered yes, a name answered no). The waiting names have
# no answer. In each case below the shares count 2 yes among the answered.
POOLS = {"clearance_share": (0, "測試便當店", "clearance", "測試即期便當", "測試排骨便當"),
         "store_clearance_share": (0, "示範超商", "clearance", "測試即期便當", "測試排骨便當"),
         "fresh_share": (3, "測試傳統市場", "cooking", "測試高麗菜", "測試香蕉"),
         "bulk_share": (8, "測試量販店", "bulk", "測試衛生紙箱", "測試牙刷")}


def pool_case(signal, answered, waiting):
    """Rows and attributes where `answered` lines have a known answer, the first two yes, and `waiting` lines have none."""
    category, shop, question, yes, no = POOLS[signal]
    rows = bought((WORKDAYS[:2], yes, category, 100, shop), (WORKDAYS[2:answered], no, category, 100, shop),
                  (WORKDAYS[answered:answered + waiting], "測試新品", category, 100, shop))
    return rows, {yes: model(**{question: True}), no: model(**{question: False}), "測試新品": None}


def quick_case(answered, waiting):
    """Workdays with a meal: `answered` have a known quick answer (the first three a rice ball, the rest noodles) and
    `waiting` have only a meal that still waits."""
    rows = bought((WORKDAYS[:3], "測試鮪魚飯糰", 0, 45, "示範超商"), (WORKDAYS[3:answered], "測試牛肉麵", 0, 150, "測試麵館"),
                  (WORKDAYS[answered:answered + waiting], "測試新品套餐", 0, 120, "測試便當店"))
    return rows, {"測試鮪魚飯糰": model(quick=True), "測試牛肉麵": model(quick=False), "測試新品套餐": None}


class ThinAnswerTests(unittest.TestCase):
    def check(self, signal, case, expected):
        rows, attributes = case
        measured = measure(rows, PERIOD, CONTEXT, attributes)
        self.assertEqual(measured["signals"][signal], expected, msg=signal)
        if expected is None:
            # A share that is not measured lists no purchases.
            self.assertEqual(measured["purchases"][signal], [], msg=signal)

    def test_a_share_with_unknown_answers_needs_five_known_ones(self):
        for signal in POOLS:
            with self.subTest(signal=signal):
                self.check(signal, pool_case(signal, 4, 6), None)
                self.check(signal, pool_case(signal, 5, 6), 2 / 5)
        self.check("weekday_quick_share", quick_case(4, 6), None)
        self.check("weekday_quick_share", quick_case(5, 6), 3 / 5)

    def test_a_share_with_every_answer_known_is_measured_however_few(self):
        # What the rules give: no answer is ever unknown, and the trait's own minimum is the only one.
        for signal in POOLS:
            with self.subTest(signal=signal):
                self.check(signal, pool_case(signal, 3, 0), 2 / 3)
        self.check("weekday_quick_share", quick_case(4, 0), 3 / 4)

    def test_one_known_store_meal_among_eight_does_not_settle_the_motive_trait(self):
        motive = next(trait for trait in CONTEXT["traits"]["traits"] if trait["id"] == "motive")
        rows = bought((WORKDAYS[:1], "測試即期便當", 0, 69, "示範超商"), (WORKDAYS[1:8], "測試新品便當", 0, 90, "示範超商"))
        measured = measure(rows, PERIOD, CONTEXT, {"測試即期便當": model(clearance=True, quick=False), "測試新品便當": None})
        self.assertEqual(measured["counts"]["store_food_items"], 8)
        self.assertIsNone(measured["signals"]["store_clearance_share"])
        self.assertIsNone(trait_value(motive, measured))
        # With enough known quick answers the habit alone decides, not the single clearance meal.
        rows = bought((WORKDAYS[:6], "測試鮪魚飯糰", 0, 45, "示範超商"), (WORKDAYS[6:7], "測試即期便當", 0, 69, "示範超商"),
                      (WORKDAYS[7:9], "測試新品便當", 0, 90, "示範超商"))
        measured = measure(rows, PERIOD, CONTEXT, {"測試鮪魚飯糰": model(quick=True),
                                                   "測試即期便當": model(clearance=True), "測試新品便當": None})
        self.assertIsNone(measured["signals"]["store_clearance_share"])
        self.assertEqual(measured["signals"]["weekday_quick_share"], 6 / 6)
        self.assertEqual(trait_value(motive, measured), 1)


def a_month_of_everything():
    """Fictional rows touching every question the signals ask, each name with one category and one shop."""
    return bought((WORKDAYS[:12], "測試排骨便當", 0, 100, "測試便當店"),
                  (WORKDAYS[12:20], "測試即期雞腿便當", 0, 80, "示範超商"),
                  (WORKDAYS[20:26], "測試鮪魚飯糰", 0, 45, "示範超商"),
                  (WORKDAYS[26:28], "測試即期蛋糕", 2, 40, "示範超商"),
                  (WORKDAYS[:8], "測試全糖紅茶", 1, 40, "測試飲料店"),
                  (WORKDAYS[8:14], "測試無糖綠茶", 1, 25, "示範超商"),
                  (WORKDAYS[14:20], "測試手沖咖啡", 1, 180, "測試咖啡館"),
                  (WORKDAYS[20:24], "測試半糖布丁", 2, 60, "測試甜點店"),
                  (WORKDAYS[:8], "測試高麗菜", 3, 120, "測試傳統市場"),
                  (WORKDAYS[8:12], "測試香蕉", 3, 60, "測試水果攤"),
                  (WORKDAYS[12:16], "測試醬油", 3, 90, "測試傳統市場"),
                  (WORKDAYS[:6], "測試衛生紙箱", 8, 200, "測試量販店"),
                  (WORKDAYS[6:9], "測試洗碗精", 8, 80, "測試量販店", 3),
                  (WORKDAYS[9:13], "測試牙刷", 8, 60, "示範超商"),
                  (WORKDAYS[13:16], "測試香氛蠟燭", 8, 250, "測試量販店"),
                  (WORKDAYS[16:19], "測試手帳", 8, 150, "測試文具店"),
                  (WORKDAYS[:3], "測試乳清蛋白", 4, 900, "測試運動店"),
                  (WORKDAYS[3:5], "測試運動鞋", 4, 2000, "測試運動店"),
                  (WORKDAYS[5:7], "測試洗車", 5, 300, "測試洗車場"),
                  (WORKDAYS[7:9], "測試藍牙耳機", 9, 1500, "測試3C店"),
                  (WORKDAYS[20:22], "測試電影票", 5, 300, "測試影城"),
                  (WORKDAYS[22:24], "測試歡唱時段", 5, 350, "測試KTV"),
                  (WORKDAYS[24:26], "測試展覽門票", 5, 250, "測試展覽館"),
                  (WORKDAYS[26:28], "測試密室逃脫", 5, 500, "測試密室"),
                  (WORKDAYS[28:31], "測試貓砂", 8, 300, "測試寵物店"),
                  (WORKDAYS[31:34], "測試狗零食", 8, 200, "測試寵物店"),
                  (WORKDAYS[34:36], "測試寵物罐頭", 8, 100, "測試寵物店"),
                  (WORKDAYS[28:34], "測試生啤酒", 1, 60, "示範超商"),
                  (WORKDAYS[34:38], "測試料理米酒", 3, 50, "示範超商"),
                  (sorted(OFF)[:4], "測試排骨便當", 0, 100, "測試便當店"))


def rules_as_model_answers(rows):
    """Each name's attributes the way a model would write down the rules' own answers for it."""
    by_kind = {word: kind for kind, word in FUN_WORDS.items()}
    attributes = {}
    for row in rows:
        answers = describe(row, channel_of(row["merchant"], BRANDS, WORDS), WORDS)
        attributes[row["name"]] = model(**{key: answers[key] for key in ATTRIBUTES if key != "fun"},
                                        fun=by_kind.get(answers["fun"]))
    return attributes


class SameAnswersTests(unittest.TestCase):
    def test_attributes_with_the_rules_answers_give_the_same_taste(self):
        rows = a_month_of_everything()
        attributes = rules_as_model_answers(rows)
        before = explain(rows, PERIOD, CONTEXT)
        # The data must say something, or the comparison proves nothing.
        self.assertGreaterEqual(sum(value is not None for value in before["vector"]), 12)
        self.assertGreaterEqual(sum(value is not None for value in before["signals"].values()), 30)
        self.assertEqual(explain(rows, PERIOD, CONTEXT, attributes), before)
        self.assertEqual(build_vector(rows, PERIOD, CONTEXT, attributes), before["vector"])

    def test_the_rules_leave_only_sugar_fun_and_species_unanswered(self):
        rows = a_month_of_everything()
        for row in rows:
            answers = describe(row, channel_of(row["merchant"], BRANDS, WORDS), WORDS)
            for key, value in answers.items():
                if key not in ("sugar", "fun", "species"):
                    self.assertIsNotNone(value, msg=(row["name"], key))


if __name__ == "__main__":
    unittest.main()
