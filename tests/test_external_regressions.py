"""v1/v2 invariants: Qwen replaces attributes, not the category-derived signals."""
import copy
from pathlib import Path
import unittest
from src.receipt.personas import build_personas, PERIOD
from src.receipt.attributes import describe, channel_of
from src.receipt.signals import measure
from src.receipt.traits import load_context, build_vector
from src.ml.fields import FLAGS

CONTEXT = load_context(Path(__file__).resolve().parents[1])
CATEGORY_SIGNALS = "meal_cost premium_drink_share store_meal_share shop_meal_share ready_meal_share dessert_share repeat_rate shop_focus new_shop_share sport_visits fuel_visits parking_visits away_share stays long_trips convenience_share small_daily_visits select_visits tech_items tech_spend tech_visits offday_invoice_share offday_amount_share holiday_trip_share bar_visits".split()


def external_v1(row):
    channel = channel_of(row["merchant"], CONTEXT["brands"], CONTEXT["vocabulary"])
    values = describe(row, channel, CONTEXT["vocabulary"])
    values.update({key: row["category"] == cat for key, cat in
                   {"meal": 0, "drink": 1, "fresh": 3, "daily": 8, "tech": 9, "sport": 4}.items()})
    return {**row, "attributes": values}


class ExternalRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = build_personas(CONTEXT["calendar"])

    def test_pending_and_wrong_basic_flags_preserve_category_signals_for_40_people(self):
        for person in self.people:
            expected = measure(person["rows"], PERIOD, CONTEXT)
            for mode in ("pending", "wrong_basic"):
                rows = [{**row, "attributes": None} if mode == "pending" else external_v1(row) for row in person["rows"]]
                if mode == "wrong_basic":
                    for row in rows:
                        for flag in FLAGS:
                            row["attributes"][flag] = not row["attributes"][flag]
                before = copy.deepcopy(rows)
                actual = measure(rows, PERIOD, CONTEXT)
                with self.subTest(person=person["name"], mode=mode):
                    self.assertEqual({key: actual["signals"][key] for key in CATEGORY_SIGNALS},
                                     {key: expected["signals"][key] for key in CATEGORY_SIGNALS})
                    self.assertEqual(actual["counts"]["food_items"], expected["counts"]["food_items"])
                    self.assertEqual(rows, before)

    def test_v1_equivalent_external_attributes_preserve_all_40_vectors(self):
        for person in self.people:
            expected = build_vector(person["rows"], PERIOD, CONTEXT)
            actual = build_vector([external_v1(row) for row in person["rows"]], PERIOD, CONTEXT)
            with self.subTest(person=person["name"]):
                self.assertEqual(actual, expected)

    def test_fun_null_is_negative_after_analysis_but_pending_is_unknown(self):
        person = self.people[0]
        analysed = [external_v1(row) for row in person["rows"]]
        for row in analysed:
            row["attributes"]["fun"] = None
        known = measure(analysed, PERIOD, CONTEXT)["signals"]
        unknown = measure([{**row, "attributes": None} for row in person["rows"]], PERIOD, CONTEXT)["signals"]
        self.assertEqual((known["fun_visits"], known["fun_kinds"]), (0, 0))
        self.assertEqual((unknown["fun_visits"], unknown["fun_kinds"]), (None, None))

    def test_analysed_unspecified_pet_species_keeps_v1_split(self):
        row = {**self.people[0]["rows"][0], "name": "示範寵物飼料", "merchant": "示範寵物店", "category": 8}
        old = measure([row], PERIOD, CONTEXT)
        new = measure([external_v1(row)], PERIOD, CONTEXT)
        keys = [key for key in old["signals"] if key.startswith("pet_")]
        self.assertEqual({key:new["signals"][key] for key in keys}, {key:old["signals"][key] for key in keys})
        self.assertGreater(new["signals"]["pet_visits_cat"], 0)

    def test_pending_dog_owner_cannot_gain_cat_evidence(self):
        person = next(person for person in self.people if person["name"] == "家庭下廚 A")
        expected = build_vector(person["rows"], PERIOD, CONTEXT)
        pending = [{**row, "attributes": None} for row in person["rows"]]
        actual = build_vector(pending, PERIOD, CONTEXT)
        cat = next(i for i,t in enumerate(CONTEXT["traits"]["traits"]) if t["id"] == "pets_cat")
        self.assertLessEqual(actual[cat], expected[cat])
        measured = measure(pending, PERIOD, CONTEXT)
        self.assertEqual(measured["signals"]["pet_visits_cat"], 0)
        self.assertEqual(measured["signals"]["pet_visits_dog"], 0)
        self.assertEqual(measured["purchases"]["pet_visits_cat"], [])

    def test_pet_invoice_keeps_known_species_when_another_line_is_pending(self):
        base = self.people[0]["rows"][0]
        dog = external_v1({**base, "name":"示範犬用飼料", "merchant":"示範寵物店", "category":8})
        pending = {**base,"name":"示範未知品項","merchant":"示範寵物店","category":8,"attributes":None}
        measured = measure([dog,pending], PERIOD, CONTEXT)
        self.assertEqual(measured["signals"]["pet_visits_cat"],0)
        self.assertEqual(measured["signals"]["pet_visits_dog"],0.5)
