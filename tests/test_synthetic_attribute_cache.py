"""Semantic regressions from the review: fictional cache must match explicit item evidence."""
import copy
import hashlib
import json
from scripts import review_synthetic_cache as review_script
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
REVIEW_EXAMPLES={
    "示範生啤酒":{"alcohol":True},"示範精釀啤酒":{"alcohol":True},"示範調酒":{"alcohol":True},
    "示範貓飼料":{"species":"cat"},"示範貓罐頭":{"species":"cat"},
    "示範95無鉛汽油":{"car_care":False},"示範重訓課":{"fun":None},
    "示範密室逃脫":{"sport_supply":False},"示範雞蛋":{"cooking":True},
    "示範花椰菜":{"cooking":True},"示範地瓜":{"cooking":True},"示範可樂":{"food":True},
    "示範即期雞腿便當":{"clearance":True},"示範醬油":{"kitchen":True},"示範筆記本":{"stationery":True}}

class SyntheticCacheTests(unittest.TestCase):
    def test_review_examples_have_expected_attributes(self):
        cache={r["name"]:r["attributes"] for r in map(json.loads,(ROOT/"datasets/synthetic/attribute-cache.jsonl").read_text(encoding="utf-8").splitlines())}
        for name,fields in REVIEW_EXAMPLES.items():
            for field,expected in fields.items():
                with self.subTest(name=name,field=field):
                    self.assertEqual(cache[name][field],expected)

    def test_every_record_retains_original_and_rerun_predictions(self):
        rows=list(map(json.loads,(ROOT/"datasets/synthetic/attribute-cache.jsonl").read_text(encoding="utf-8").splitlines()))
        self.assertEqual(len(rows),107)
        for record in rows:
            with self.subTest(name=record["name"]):
                self.assertIn("original_model_attributes",record)
                self.assertIn("model_attributes",record)
                self.assertIn("corrections",record)
                self.assertNotEqual(record["original_model_version"],record["model_version"])
                self.assertEqual(record["reviewer"],"assistant")
                self.assertTrue(record["human_confirmed"])
                self.assertEqual(record["confirmation"]["confirmed_by"], "user")
                self.assertEqual(record["review_status"], "human_corrected" if record["corrections"] else "human_confirmed")
                changed={k for k in record["attributes"] if record["attributes"][k]!=record["model_attributes"][k]}
                self.assertEqual(set(record["corrections"]),changed)

    def test_user_confirmation_survives_rebuild_metadata(self):
        row = {"attributes": {"food": True}}
        row["confirmation"] = {"confirmed_by": "user", "date": "2026-10-15",
                               "source": "user approval of review at commit 0e98b71",
                               "attributes_sha256": hashlib.sha256(json.dumps(row["attributes"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        corrected = review_script.review_metadata(row, corrected=True)
        self.assertTrue(corrected["human_confirmed"])
        self.assertEqual(corrected["review_status"], "human_corrected")
        self.assertEqual(review_script.review_metadata(row, corrected=False)["review_status"], "human_confirmed")
        changed = copy.deepcopy(row)
        changed["attributes"]["food"] = False
        self.assertFalse(review_script.review_metadata(changed, corrected=True)["human_confirmed"])

    def test_unconfirmed_review_is_not_promoted(self):
        metadata = review_script.review_metadata({"attributes": {"food": True}}, corrected=True)
        self.assertFalse(metadata["human_confirmed"])
        self.assertEqual(metadata["review_status"], "assistant_corrected")

    def test_every_public_cache_archive_marks_synthetic_source(self):
        paths = list((ROOT / "datasets/synthetic").glob("attribute-cache*.jsonl"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 107)
            self.assertTrue(all(row.get("source") == "synthetic" for row in rows), path.name)


class PrivacyReplacementProvenanceTests(unittest.TestCase):
    def test_rebuild_preserves_label_replacement_provenance(self):
        row = {"attributes": {"food": True}, "privacy_replacement": {
            "scope": "synthetic_label_only", "model_rerun": False,
            "attributes_changed": False}}
        metadata = review_script.review_metadata(row, corrected=False)
        self.assertEqual(metadata.get("privacy_replacement"), row["privacy_replacement"])
        self.assertFalse(metadata["human_confirmed"])

    def test_public_replacements_are_consistent_across_cache_archives(self):
        replacement_names = {"示範原味無糖豆乳飲", "示範香草燉菜餐盤"}
        for filename in ("attribute-review.jsonl", "attribute-cache.jsonl",
                         "attribute-cache.model-v1.jsonl", "attribute-cache.model-v2.jsonl"):
            rows = [json.loads(line) for line in (ROOT / "datasets/synthetic" / filename).read_text(encoding="utf-8").splitlines()]
            replacements = [row for row in rows if row["name"] in replacement_names]
            self.assertEqual(len(replacements), 2, filename)
            for row in replacements:
                self.assertIs(row["privacy_replacement"]["model_rerun"], False)
                self.assertIs(row["privacy_replacement"]["attributes_changed"], False)
                self.assertEqual(row["privacy_replacement"]["confirmation_scope"], "previously approved attribute values only")
