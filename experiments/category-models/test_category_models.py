"""Synthetic fixtures only: no private names or source files."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent


def sample(item_id, name, category, **extra):
    return dict(id=item_id, name=name, category=category,
                review_status="human_confirmed", **extra)


def fixtures():
    return [sample(f"a{i}", f"測試飯糰{word}", 0)
            for i, word in enumerate("甲乙丙丁戊己")] + [
        sample(f"b{i}", f"測試紅茶{word}", 1)
        for i, word in enumerate("庚辛壬癸子丑")] + [
        sample("rare", "測試耳機", 9)]


class CategoryModelsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec(name),
                             f"Missing implementation: {name}")
        return __import__(name)

    def write_data(self, records, name="items.jsonl"):
        path = self.root / name
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                for r in records), encoding="utf-8")
        return path

    def test_loader_normalizes_deduplicates_and_preserves_context(self):
        mod = self.module("prepare_data")
        rows = mod.load_items(self.write_data([
            sample("a", " Ａ茶 ", 1),
            sample("b", "A茶", 1, name_only_context_needed=True)]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "A茶")
        self.assertTrue(rows[0]["name_only_context_needed"])

    def test_loader_rejects_unreviewed_invalid_and_conflicting_labels(self):
        mod = self.module("prepare_data")
        cases = [[sample("a", "茶", 10)],
                 [sample("a", "茶", True)],
                 [sample("a", " ", 1)],
                 [dict(id="a", name="茶", category=1)],
                 [sample("a", "茶", 1), sample("a", "飯", 0)],
                 [sample("a", "Ａ茶", 1), sample("b", "A茶", 0)],
                 [sample("a", "茶", 1, name_only_context_needed="false")]]
        for records in cases:
            with self.subTest(records=records), self.assertRaises(ValueError):
                mod.load_items(self.write_data(records))

    def test_csv_preparation_excludes_nonpositive_and_provisional(self):
        mod = self.module("prepare_data")
        path = self.root / "invoices.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["發票日期", "消費明細_品名", "消費明細_金額"])
            writer.writeheader()
            for name, amount in [("測試茶", 30), ("測試茶", 40), ("贈品", 0),
                                 ("折扣", -10), ("未知", 20)]:
                writer.writerow({"發票日期": "20260101", "消費明細_品名": name,
                                 "消費明細_金額": amount})
        catalog = self.root / "catalog.json"
        catalog.write_text(json.dumps({"測試茶": {"category": 1, "provisional": False},
                                       "未知": {"category": 10, "provisional": True}}), encoding="utf-8")
        rows, summary = mod.from_invoices([path], catalog)
        self.assertEqual([r["name"] for r in rows], ["測試茶"])
        self.assertEqual(summary["nonpositive_rows"], 2)
        self.assertEqual(summary["unconfirmed_rows"], 1)

    def test_folds_keep_variants_together_and_rare_items_training_only(self):
        mod = self.module("common")
        rows = fixtures() + [sample("variant", "測試飯糰甲大份", 0,
                                    group="測試飯糰甲")]
        folds = mod.make_folds(rows, n_splits=3, seed=42)
        self.assertEqual(folds, mod.make_folds(rows, n_splits=3, seed=42))
        seen = []
        for fold in folds:
            train, validation = fold["train"], fold["validation"]
            self.assertIn(12, train)
            self.assertNotIn(12, validation)
            self.assertEqual(0 in validation, 13 in validation)
            self.assertFalse(set(train) & set(validation))
            self.assertEqual(set(train) | set(validation), set(range(14)))
            seen.extend(validation)
        self.assertEqual(sorted(seen), [*range(12), 13])

    def test_too_few_classes_for_cv_is_explicit(self):
        mod = self.module("common")
        self.assertEqual(mod.make_folds([sample("a", "茶", 1),
                                        sample("b", "飯", 0)]), [])

    def test_metrics_count_predictions_into_unevaluated_classes_as_errors(self):
        mod = self.module("common")
        result = mod.metrics([0, 1], [9, 1])
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["macro_f1"], 0.5)
        self.assertEqual(result["confusion_matrix"][0][9], 1)
        self.assertIsNone(result["per_class"]["9"]["f1"])
        self.assertIsNone(result["ten_class_macro_f1"])

    def test_pipeline_does_not_learn_validation_only_terms(self):
        mod = self.module("tfidf_lr")
        model = mod.build_model()
        model.fit(["甲飯", "乙飯", "甲茶", "乙茶"], [0, 0, 1, 1])
        model.predict(["獨有驗證字"])
        vocab = model.named_steps["tfidf"].vocabulary_
        self.assertNotIn("獨", vocab)

    def test_roundtrip_training_predicts_ten_ordered_probabilities(self):
        mod = self.module("tfidf_lr")
        data = self.write_data(fixtures())
        out = self.root / "run"
        report = mod.train(data, out)
        self.assertEqual(report["validation"]["evaluated_items"], 12)
        self.assertEqual(report["validation"]["training_only_items"], 1)
        self.assertIsNone(report["validation"]["model"]["ten_class_macro_f1"])
        predictor = mod.Classifier.load(out / "model.joblib")
        prediction = predictor.predict(["測試紅茶庚"])[0]
        self.assertEqual(prediction["category"], 1)
        self.assertEqual(len(prediction["probabilities"]), 10)
        self.assertAlmostEqual(sum(prediction["probabilities"]), 1)
        self.assertEqual(prediction["probabilities"][8], 0)
        rows = [json.loads(line) for line in (out / "validation-predictions.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 12)
        with self.assertRaises(FileExistsError):
            mod.train(data, out)

    def test_external_evaluation_separates_training_overlap(self):
        mod = self.module("tfidf_lr")
        out = self.root / "run"
        mod.train(self.write_data(fixtures()), out)
        external = self.write_data([sample("old", "測試紅茶庚", 1),
                                    sample("new", "全新測試茶", 1)], "external.jsonl")
        report = mod.evaluate(out / "model.joblib", external, self.root / "evaluation")
        self.assertEqual(report["overlap_items"], 1)
        self.assertEqual(report["unseen_items"], 1)
        self.assertEqual(report["unseen"]["support"], 1)

    def test_cli_runs_and_keeps_names_out_of_stdout(self):
        self.module("tfidf_lr")
        data = self.write_data(fixtures())
        out = self.root / "cli"
        result = subprocess.run([sys.executable, str(HERE / "tfidf_lr.py"),
                                 "train", "--data", str(data), "--out", str(out)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("測試紅茶", result.stdout)
        self.assertEqual(json.loads(result.stdout)["items"], 13)

    def test_external_csv_command_filters_rows_and_reports_overlap(self):
        self.assertTrue((HERE / "evaluate_external.py").exists(),
                        "Missing external CSV command")
        mod = self.module("tfidf_lr")
        out = self.root / "run"
        mod.train(self.write_data(fixtures()), out)
        source = self.root / "external.csv"
        with source.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["發票日期", "消費明細_品名", "消費明細_金額"])
            writer.writerows([["20260101", "測試紅茶庚", 30],
                              ["20260101", "新測試綠茶", 40],
                              ["20260101", "新測試綠茶", 0]])
        catalog = self.root / "catalog.json"
        catalog.write_text(json.dumps({name: dict(category=1, provisional=False)
                                       for name in ["測試紅茶庚", "新測試綠茶"]}), encoding="utf-8")
        result = subprocess.run([sys.executable, str(HERE / "evaluate_external.py"),
                                 "--model", str(out / "model.joblib"),
                                 "--csv", str(source), "--catalog", str(catalog),
                                 "--out", str(self.root / "external-result")],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["overlap_items"], 1)
        self.assertEqual(report["unseen_items"], 1)
        self.assertNotIn("測試紅茶庚", result.stdout)

    def test_empty_vocabulary_prediction_is_flagged(self):
        mod = self.module("tfidf_lr")
        out = self.root / "run"
        mod.train(self.write_data(fixtures()), out)
        classifier = mod.Classifier.load(out / "model.joblib")
        self.assertTrue(classifier.predict(["ΩΨ"])[0]["out_of_vocabulary"])
        with self.assertRaises(ValueError):
            classifier.predict([""])


if __name__ == "__main__":
    unittest.main()
