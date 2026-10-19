"""B uses a tiny random local BERT in tests; no downloads or private names."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from common import data_digest, make_folds
from prepare_data import load_items, write_json, write_jsonl


def records():
    return [dict(id=f"{c}-{i}", name=f"測試{word}{i}", category=c,
                 review_status="human_confirmed")
            for c, word in [(0, "飯"), (1, "茶")] for i in range(6)] + [
        dict(id="rare", name="測試耳機", category=9, review_status="human_confirmed")]


class EmbeddingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec(name), f"Missing implementation: {name}")
        return __import__(name)

    def data_and_splits(self):
        data = self.root / "items.jsonl"
        write_jsonl(data, records())
        items = load_items(data)
        folds = make_folds(items)
        evaluated = {i for fold in folds for i in fold["validation"]}
        saved = dict(dataset_sha256=data_digest(items), seed=42,
                     folds=[dict(fold=n, train_ids=[items[i]["id"] for i in f["train"]],
                                 validation_ids=[items[i]["id"] for i in f["validation"]])
                            for n, f in enumerate(folds, 1)],
                     training_only_ids=[r["id"] for i, r in enumerate(items) if i not in evaluated])
        path = self.root / "splits.json"
        write_json(path, saved)
        return data, items, path, saved

    def encoder_fixture(self):
        import torch
        from transformers import BertConfig, BertModel, BertTokenizerFast
        directory = self.root / "encoder"
        directory.mkdir(exist_ok=True)
        vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "測", "試",
                 "飯", "茶", "耳", "機", *list("0123456789")]
        (directory / "vocab.txt").write_text("\n".join(vocab) + "\n", encoding="utf-8")
        tokenizer = BertTokenizerFast(vocab_file=str(directory / "vocab.txt"))
        tokenizer.save_pretrained(directory)
        torch.manual_seed(42)
        model = BertModel(BertConfig(vocab_size=len(vocab), hidden_size=12,
                                    num_hidden_layers=1, num_attention_heads=3,
                                    intermediate_size=24, max_position_embeddings=512))
        model.save_pretrained(directory, safe_serialization=True)
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in directory.iterdir() if p.is_file()}
        write_json(directory / "encoder-manifest.json",
                   dict(repo="synthetic-test-bert", revision="0" * 40, files=files))
        return directory

    def test_saved_splits_match_and_reject_changed_data(self):
        mod = self.module("embedding_lr")
        _, items, path, saved = self.data_and_splits()
        folds, manifest = mod.load_splits(path, items)
        self.assertEqual(folds, make_folds(items))
        self.assertEqual(manifest, saved)
        items[0]["name"] += "改"
        with self.assertRaises(ValueError):
            mod.load_splits(path, items)

    def test_saved_splits_reject_leakage_missing_ids_and_repeated_validation(self):
        mod = self.module("embedding_lr")
        _, items, path, saved = self.data_and_splits()
        import copy
        malformed = []
        overlap = copy.deepcopy(saved)
        overlap["folds"][0]["train_ids"].append(overlap["folds"][0]["validation_ids"][0])
        malformed.append(overlap)
        missing = copy.deepcopy(saved)
        missing["folds"][0]["train_ids"].pop()
        malformed.append(missing)
        repeated = copy.deepcopy(saved)
        repeated["folds"][1] = copy.deepcopy(repeated["folds"][0])
        malformed.append(repeated)
        for value in malformed:
            write_json(path, value)
            with self.assertRaises(ValueError):
                mod.load_splits(path, items)

    def test_encoder_is_frozen_normalized_and_padding_independent(self):
        mod = self.module("embedding_features")
        encoder = mod.FrozenEncoder(self.encoder_fixture())
        first = encoder.encode(["測試茶"])
        padded = encoder.encode(["測試茶", "測試飯茶飯茶飯茶"])
        self.assertEqual(first.shape, (1, 12))
        np.testing.assert_allclose(np.linalg.norm(padded, axis=1), [1, 1], atol=1e-6)
        np.testing.assert_allclose(first[0], padded[0], atol=1e-6)
        self.assertFalse(encoder.model.training)
        self.assertTrue(all(not p.requires_grad for p in encoder.model.parameters()))
        self.assertEqual(encoder.encode([]).shape, (0, 12))

    def test_local_model_integrity_is_checked_before_loading(self):
        mod = self.module("embedding_features")
        directory = self.encoder_fixture()
        with (directory / "vocab.txt").open("a", encoding="utf-8") as stream:
            stream.write("changed\n")
        with self.assertRaises(ValueError):
            mod.FrozenEncoder(directory)

    def test_cache_checks_order_settings_and_array_integrity(self):
        mod = self.module("embedding_features")
        encoder = mod.FrozenEncoder(self.encoder_fixture())
        cache = self.root / "cache.npz"
        names = ["測試茶", "測試飯"]
        first, hit = mod.cached_encode(encoder, names, cache)
        self.assertFalse(hit)
        second, hit = mod.cached_encode(encoder, names, cache)
        self.assertTrue(hit)
        np.testing.assert_array_equal(first, second)
        reversed_values, hit = mod.cached_encode(encoder, names[::-1], cache)
        self.assertFalse(hit)
        np.testing.assert_allclose(reversed_values, first[::-1], atol=1e-6)
        with np.load(cache, allow_pickle=False) as saved:
            meta = saved["metadata"].copy()
            vectors = saved["vectors"].copy()
        vectors[0, 0] = np.nan
        np.savez_compressed(cache, metadata=meta, vectors=vectors)
        repaired, hit = mod.cached_encode(encoder, names[::-1], cache)
        self.assertFalse(hit)
        self.assertTrue(np.isfinite(repaired).all())
        changed = mod.FrozenEncoder(encoder.directory, max_length=64)
        _, hit = mod.cached_encode(changed, names[::-1], cache)
        self.assertFalse(hit)

    def test_truncated_cache_is_recomputed(self):
        mod = self.module("embedding_features")
        encoder = mod.FrozenEncoder(self.encoder_fixture())
        cache = self.root / "cache.npz"
        expected, _ = mod.cached_encode(encoder, ["測試茶"], cache)
        cache.write_bytes(cache.read_bytes()[:30])
        repaired, hit = mod.cached_encode(encoder, ["測試茶"], cache)
        self.assertFalse(hit)
        np.testing.assert_array_equal(repaired, expected)

    def test_cache_path_cannot_overwrite_training_inputs(self):
        mod = self.module("embedding_lr")
        data, _, splits, _ = self.data_and_splits()
        directory = self.encoder_fixture()
        for target in (data, splits, directory / "config.json"):
            original = target.read_bytes()
            with self.assertRaises(ValueError):
                mod.train(data, self.root / "run", splits, directory, target, benchmark_count=1)
            self.assertEqual(target.read_bytes(), original)

    def test_train_uses_exact_saved_folds_and_roundtrips_predictions(self):
        mod = self.module("embedding_lr")
        data, items, splits, manifest = self.data_and_splits()
        directory = self.encoder_fixture()
        out = self.root / "run"
        report = mod.train(data, out, splits, directory, self.root / "vectors.npz",
                           benchmark_count=10)
        self.assertEqual(report["validation"]["evaluated_items"], 12)
        self.assertEqual(report["validation"]["training_only_items"], 1)
        self.assertIsNone(report["validation"]["model"]["ten_class_macro_f1"])
        self.assertEqual(json.loads((out / "splits.json").read_text(encoding="utf-8")), manifest)
        model = mod.Classifier.load(out / "model.joblib")
        preds = model.predict(["測試茶0", "測試飯0"])
        again = mod.Classifier.load(out / "model.joblib").predict(["測試茶0", "測試飯0"])
        self.assertEqual(preds, again)
        for result in preds:
            self.assertEqual(len(result["probabilities"]), 10)
            self.assertAlmostEqual(sum(result["probabilities"]), 1)
            self.assertEqual(result["probabilities"][8], 0)
        self.assertGreater(report["cost"]["deployed_model_bytes"],
                           report["cost"]["classifier_bytes"])
        with self.assertRaises(FileExistsError):
            mod.train(data, out, splits, directory, self.root / "vectors.npz", benchmark_count=10)

    def test_embedding_external_evaluation_marks_training_overlap(self):
        mod = self.module("embedding_lr")
        data, _, splits, _ = self.data_and_splits()
        out = self.root / "run"
        mod.train(data, out, splits, self.encoder_fixture(), self.root / "vectors.npz",
                  benchmark_count=10)
        external = self.root / "external.jsonl"
        write_jsonl(external, [dict(id="seen", name="測試茶0", category=1, review_status="human_confirmed"),
                              dict(id="new", name="全新茶", category=1, review_status="human_confirmed")])
        report = mod.evaluate(out / "model.joblib", external, self.root / "evaluation")
        self.assertEqual(report["overlap_items"], 1)
        self.assertEqual(report["unseen_items"], 1)
        self.assertFalse(report["independent_test_verified"])


if __name__ == "__main__":
    unittest.main()
