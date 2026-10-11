"""How each signal names its purchases: three at most, and never in a way that tells where someone shopped."""
import unittest
from pathlib import Path

from src.receipt.items import label, listed, place_words
from src.receipt.signals import calendar_days, measure
from src.receipt.traits import explain, load_context, signal_ids

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
PERIOD = [(2026, 3), (2026, 4)]
DAYS, OFF, _ = calendar_days(PERIOD, CONTEXT["calendar"])
WORKDAYS = [day for day in DAYS if day not in OFF]
HOME = "高雄市苓雅區"
PLACE_SIGNALS = {"away_share", "shop_focus", "new_shop_share", "holiday_trip_share"}


def bought(*groups):
    """Rows from (days, name, category, amount, merchant, district) groups; every purchase is its own invoice."""
    rows = []
    for days, name, category, amount, merchant, district in groups:
        for day in days:
            rows.append({"date": day, "day": day.day, "invoice": f"T{len(rows):03}", "merchant": merchant,
                         "district": district, "name": name, "quantity": 1, "amount": amount, "category": category,
                         "provisional": False})
    return rows


class LabelTests(unittest.TestCase):
    WORDS = place_words([{"district": HOME}, {"district": "新竹縣竹北市"}, {"district": None}], CONTEXT)

    def name(self, name, channel="一般店家", category=0, merchant="測試商店"):
        return label({"name": name, "channel": channel, "category": category, "merchant": merchant}, self.WORDS, CONTEXT)

    def test_a_hotel_is_only_a_hotel_stay(self):
        self.assertEqual(self.name("示範旅店雙人房", channel="住宿", category=7), "旅館住宿")
        self.assertEqual(self.name("墾丁測試飯店 豪華客房", channel="住宿", category=7), "旅館住宿")

    def test_a_long_trip_names_its_kind_of_ticket_and_never_a_station(self):
        cases = [("高鐵 左營-台北 標準車廂", "台灣高鐵", "高鐵票"), ("自強號 高雄→台中", "臺鐵", "臺鐵票"),
                 ("台北-基隆", "測試客運", "客運票"), ("TPE-KHH 經濟艙", "測試航空", "機票"),
                 ("示範高鐵車票", "示範高鐵", "高鐵票"), ("租車一日", "測試交通", "長途交通票")]
        for name, merchant, expected in cases:
            self.assertEqual(self.name(name, channel="長途交通", category=6, merchant=merchant), expected, name)

    def test_other_names_lose_only_their_place_names(self):
        self.assertEqual(self.name("台中油飯"), "油飯")
        self.assertEqual(self.name("臺南擔仔麵"), "擔仔麵")
        self.assertEqual(self.name("金門高粱", category=1), "高粱")
        self.assertEqual(self.name("苓雅區限定便當"), "限定便當")
        self.assertEqual(self.name("竹北肉圓"), "肉圓")
        self.assertEqual(self.name("淡水阿給"), "阿給")
        self.assertEqual(self.name("高雄市 - 鹽酥雞"), "鹽酥雞")

    def test_marks_in_a_name_stay_unless_a_removed_place_leaves_them_behind(self):
        for name in ("麥香奶茶(600ml)", "(促)統一布丁", "蛋白質20%", "維他命C+"):
            self.assertEqual(self.name(name), name)
        self.assertEqual(self.name("【台中限定】鹽酥雞"), "【限定】鹽酥雞")
        self.assertEqual(self.name("鹽酥雞（台中店）"), "鹽酥雞（店）")
        self.assertEqual(self.name("鹽酥雞（台中）"), "鹽酥雞")

    def test_a_name_that_was_only_a_place_reads_as_its_category(self):
        self.assertEqual(self.name("台中"), "正餐")
        self.assertEqual(self.name("高雄 123", category=8), "日用品")

    def test_chains_stay_and_the_demo_mark_goes(self):
        self.assertEqual(self.name("星巴克那堤", category=1), "星巴克那堤")
        self.assertEqual(self.name("示範半糖冬瓜青茶", category=1), "半糖冬瓜青茶")

    def test_a_long_name_is_cut_at_twenty_letters(self):
        self.assertEqual(self.name("測" * 20), "測" * 20)
        self.assertEqual(self.name("測" * 25), "測" * 19 + "…")

    def test_place_words_cover_cities_counties_county_cities_and_the_persons_own_districts(self):
        words = place_words([{"district": HOME}, {"district": "新竹市東區"}], CONTEXT)
        for word in ("臺北市", "臺北", "新竹縣", "竹北市", "竹北", "苓雅區", "苓雅", "東區", "淡水"):
            self.assertIn(word, words)
        # A one-letter district name would cut far too much from ordinary names.
        self.assertNotIn("東", words)
        self.assertEqual(words, sorted(words, key=lambda word: (-len(word), word)))


class ListTests(unittest.TestCase):
    def test_each_signal_lists_its_three_most_bought_names_counted_by_bill(self):
        rows = bought((WORKDAYS[:8], "測試排骨便當", 0, 100, "測試便當店", HOME),
                      (WORKDAYS[8:11], "測試台中油飯", 0, 70, "測試小吃店", HOME),
                      (WORKDAYS[11:14], "測試臺南油飯", 0, 70, "測試小吃店", HOME),
                      (WORKDAYS[14:19], "測試牛肉麵", 0, 150, "測試麵館", HOME),
                      (WORKDAYS[19:24], "測試滷肉飯", 0, 60, "測試小吃店", HOME),
                      (WORKDAYS[24:26], "測試旅店雙人房", 7, 2000, "測試旅宿", "屏東縣恆春鎮"))
        # Breakfast on the same hotel bill is still one stay.
        rows.append({**rows[-1], "name": "測試早餐券", "amount": 200})
        lists = listed(measure(rows, PERIOD, CONTEXT)["purchases"], rows, CONTEXT)
        self.assertEqual(set(lists), set(signal_ids(CONTEXT["traits"])))
        # Two dishes that differ only by a place are one name, and ties go by name.
        self.assertEqual(lists["shop_meal_share"], [["測試排骨便當", 8], ["測試油飯", 6], ["測試滷肉飯", 5]])
        self.assertEqual(lists["stays"], [["旅館住宿", 2]])
        self.assertEqual(lists["sugar_mean"], [])
        for key in PLACE_SIGNALS:
            self.assertIsNone(lists[key], key)

    def test_explain_hands_the_lists_on(self):
        rows = bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME))
        person = explain(rows, PERIOD, CONTEXT)
        # weekday_quick_share feeds two traits and has one list for both.
        self.assertEqual(person["items"]["weekday_quick_share"], [["測試鮪魚飯糰", 24]])
        self.assertEqual(person["items"]["store_meal_share"], [["測試鮪魚飯糰", 24]])
        self.assertIsNone(person["items"]["away_share"])


class ConfigTests(unittest.TestCase):
    def test_only_the_four_place_signals_hide_their_purchases(self):
        flags = {}
        for trait in CONTEXT["traits"]["traits"]:
            for signal in trait["signals"]:
                flags.setdefault(signal["id"], set()).add(signal.get("list_items", True))
        self.assertEqual({key for key, seen in flags.items() if False in seen}, PLACE_SIGNALS)
        # A signal shared by two traits says the same in both.
        self.assertTrue(all(len(seen) == 1 for seen in flags.values()))

    def test_the_item_words_are_configured(self):
        vocabulary = CONTEXT["vocabulary"]
        self.assertEqual([kind for kind, _ in vocabulary["transport_kinds"]], ["高鐵票", "臺鐵票", "客運票", "機票"])
        self.assertEqual(vocabulary["generic_labels"], {"住宿": "旅館住宿", "長途交通": "長途交通票"})
        self.assertIn("淡水", vocabulary["place_words"])
        self.assertEqual(CONTEXT["report"]["categories"][0]["name"], "正餐")


if __name__ == "__main__":
    unittest.main()
