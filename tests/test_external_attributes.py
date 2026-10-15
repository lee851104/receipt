"""External model attributes stay separate from v1 keyword rules and taste defaults."""
from datetime import date
from pathlib import Path
import unittest
from src.receipt.attributes import describe, channel_of
from src.receipt.signals import gather, measure
from src.receipt.traits import load_context
from src.ml.fields import FIELDS
CONTEXT = load_context(Path(__file__).resolve().parents[1])


def row(name="示範珍珠奶茶", **changes):
    return {"name":name,"category":1,"merchant":"示範茶屋","quantity":1,"amount":60,
            "date":date(2026,3,2),"day":2,"invoice":"T1","district":None,"provisional":False,**changes}


class ExternalTests(unittest.TestCase):
    def test_external_unknowns_are_preserved_without_keyword_fallback(self):
        values = dict.fromkeys(FIELDS)
        result = describe(row(), "手搖", CONTEXT["vocabulary"], external=values)
        self.assertEqual(result, values)
        result["sugar"] = 1
        self.assertIsNone(values["sugar"])
        self.assertEqual(channel_of("示範茶屋", CONTEXT["brands"], CONTEXT["vocabulary"]), "手搖")

    def test_pending_attributes_do_not_use_keywords(self):
        result = describe(row(), "手搖", CONTEXT["vocabulary"], external=None)
        self.assertEqual(set(result), set(FIELDS))
        self.assertTrue(all(value is None for value in result.values()))
        measured = measure([row(attributes=None)], [(2026,3)], CONTEXT)
        self.assertIsNone(measured["signals"]["sugar_mean"])
        self.assertEqual(measured["counts"]["items"], 1)

    def test_taste_defaults_do_not_mutate_model_attributes(self):
        values = dict.fromkeys(FIELDS, False)
        values.update(sugar=None, fun=None, species=None, food=True, drink=True)
        for name, merchant, expected in [("示範珍珠奶茶","示範茶屋",1), ("示範冰美式","示範咖啡",0), ("示範手沖","示範小店",None)]:
            with self.subTest(name=name):
                item = row(name, merchant=merchant, attributes=values)
                self.assertEqual(measure([item],[(2026,3)],CONTEXT)["signals"]["sugar_mean"], expected)
                self.assertIsNone(values["sugar"])
        values["sugar"] = 0.5
        self.assertEqual(measure([row(attributes=values)],[(2026,3)],CONTEXT)["signals"]["sugar_mean"],0.5)

    def test_bulk_quantity_is_row_specific_and_does_not_mutate_cache(self):
        values = dict.fromkeys(FIELDS)
        lines, _ = gather([row(attributes=values,quantity=3), row(attributes=values,invoice="T2")],CONTEXT)
        self.assertIs(lines[0]["bulk"], True)
        self.assertIsNone(lines[1]["bulk"])
        self.assertIsNone(values["bulk"])

    def test_unknown_flags_are_not_counted_as_negative_evidence(self):
        unknown = dict.fromkeys(FIELDS)
        known = {**unknown, "food": True, "clearance": True, "cooking": True, "bulk": True}
        unknown_food = {**unknown, "food": True}
        rows = [row("示範便當", category=0, attributes=known), row("示範便當二",category=0,invoice="T2",attributes=unknown_food)]
        signals = measure(rows,[(2026,3)],CONTEXT)["signals"]
        self.assertEqual(signals["clearance_share"],1)
        self.assertEqual(signals["fresh_share"],1)
        self.assertIsNone(signals["sport_supplies"])
        self.assertIsNone(signals["alcohol_items"])
        self.assertIsNone(signals["weekday_quick_share"])
        self.assertIsNone(signals["pet_food_cat"])
        self.assertIsNone(signals["fun_visits"])

    def test_pending_meals_do_not_increase_known_food_ratio(self):
        attrs = dict.fromkeys(FIELDS)
        attrs.update(food=True, meal=True, cooking=False)
        ready = row("示範飯", category=0, attributes=attrs)
        pending = row("示範飯二", category=0, invoice="T2", attributes=None)
        result = measure([ready,pending],[(2026,3)],CONTEXT)
        self.assertEqual(result["signals"]["ready_meal_share"],1)
        self.assertEqual(result["counts"]["meal_items"],2)

    def test_full_sweet_vector_uses_default_without_changing_api_value(self):
        from src.receipt.traits import build_vector
        attrs = dict.fromkeys(FIELDS, False)
        attrs.update(food=True, drink=True, sugar=None, species=None, fun=None)
        rows = [row(attributes=attrs, invoice=f"S{i}") for i in range(20)]
        vector = build_vector(rows,[(2026,3)],CONTEXT)
        # Full-sugar signal contributes .8; no desserts contributes 0 out of .2.
        self.assertAlmostEqual(vector[4], 0.8)
        self.assertIsNone(attrs["sugar"])
