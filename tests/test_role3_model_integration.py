"""Role-3 callers and cache isolation using the role-1 from_model interface."""
import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts import evaluate_matching
from src.ml.fields import FIELDS, FLAGS
from src.receipt.attributes import from_model
from src.receipt.personas import PERIOD, build_personas
from src.receipt.signals import gather, measure
from src.receipt.traits import build_vector, explain, load_context

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)


def row(name="示範青茶", **changes):
    return {"name": name, "category": 1, "merchant": "示範茶屋", "quantity": 1, "amount": 60,
            "date": date(2026, 3, 2), "day": 2, "invoice": "T1", "district": None,
            "provisional": False, **changes}


class ModelCacheIsolationTests(unittest.TestCase):
    def test_converted_answers_are_independent_of_the_cached_model_output(self):
        values = dict.fromkeys(FIELDS)
        before = copy.deepcopy(values)
        result = from_model(row(), "手搖", values, CONTEXT["vocabulary"])
        self.assertIsNone(result["clearance"])
        result["clearance"] = True
        result["sugar"] = 0.5
        self.assertEqual(values, before)

    def test_same_name_uses_each_rows_shop_and_quantity_without_changing_cache(self):
        values = dict.fromkeys(FIELDS)
        cache = {"示範青茶": values}
        rows = [row(quantity=3), row(merchant="示範小店", invoice="T2")]
        before_rows, before_cache = copy.deepcopy(rows), copy.deepcopy(cache)
        lines, _ = gather(rows, CONTEXT, attributes=cache)
        self.assertEqual([(item["sugar"], item["bulk"]) for item in lines], [(1, True), (None, None)])
        for calculate in (measure, explain, build_vector):
            with self.subTest(calculate=calculate.__name__):
                calculate(rows, [(2026, 3)], CONTEXT, attributes=cache)
                self.assertEqual(cache, before_cache)
                self.assertEqual(rows, before_rows)

    def test_sweet_vector_defaults_leave_raw_api_sugar_and_pending_cache_unchanged(self):
        values = dict.fromkeys(FIELDS, False)
        values.update(sugar=None, fun=None, species=None)
        rows = [row(invoice=f"S{i}") for i in range(20)]
        sweet = next(i for i, trait in enumerate(CONTEXT["traits"]["traits"]) if trait["id"] == "sweet")
        for cache in ({"示範青茶": values}, {"示範青茶": None}, {}):
            before = copy.deepcopy(cache)
            with self.subTest(pending=not cache or cache["示範青茶"] is None):
                vector = build_vector(rows, [(2026, 3)], CONTEXT, attributes=cache)
                self.assertAlmostEqual(vector[sweet], 0.8)
                self.assertEqual(cache, before)
        self.assertIsNone(values["sugar"])

    def test_basic_model_flags_do_not_change_signals_or_vectors_for_40_people(self):
        records = map(json.loads, (ROOT / "datasets/synthetic/attribute-cache.jsonl").read_text(encoding="utf-8").splitlines())
        cache = {record["name"]: record["attributes"] for record in records}
        flipped = copy.deepcopy(cache)
        for values in flipped.values():
            for flag in FLAGS:
                values[flag] = not values[flag]
        before = copy.deepcopy((cache, flipped))
        people = build_personas(CONTEXT["calendar"])
        before_people = copy.deepcopy(people)
        for person in people:
            rows = person["rows"]
            with self.subTest(person=person["name"]):
                self.assertEqual(measure(rows, PERIOD, CONTEXT, attributes=cache),
                                 measure(rows, PERIOD, CONTEXT, attributes=flipped))
                self.assertEqual(build_vector(rows, PERIOD, CONTEXT, attributes=cache),
                                 build_vector(rows, PERIOD, CONTEXT, attributes=flipped))
        self.assertEqual((cache, flipped), before)
        self.assertEqual(people, before_people)


class MatchingCallerTests(unittest.TestCase):
    def test_matching_passes_the_name_cache_to_vector_calculation(self):
        people = build_personas(CONTEXT["calendar"])[:2]
        before = copy.deepcopy(people)
        calls = []

        def calculate(rows, period, context, attributes=None):
            self.assertIsInstance(attributes, dict, "Matching must pass the model cache, not silently use v1 rules")
            self.assertTrue(all("attributes" not in item for item in rows))
            self.assertTrue(all(item["name"] in attributes for item in rows))
            calls.append(attributes)
            return build_vector(rows, period, context, attributes=attributes)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in ("datasets/synthetic/attribute-cache.jsonl", "configs/persona-opposites.json"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            with patch.object(evaluate_matching, "ROOT", root), \
                 patch.object(evaluate_matching, "load_context", return_value=CONTEXT), \
                 patch.object(evaluate_matching, "build_personas", return_value=people), \
                 patch.object(evaluate_matching, "build_vector", side_effect=calculate), redirect_stdout(io.StringIO()):
                evaluate_matching.main()
            self.assertTrue((root / "docs/results/matching.json").is_file())
        self.assertEqual(len(calls), len(people) * 2)
        self.assertTrue(all(cache is calls[0] for cache in calls))
        self.assertEqual(people, before)
