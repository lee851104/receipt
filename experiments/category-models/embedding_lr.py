"""Model B: frozen local embeddings plus LR on the exact saved A partitions."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from common import data_digest, environment, fingerprint, metrics, peak_rss_bytes
from embedding_features import FrozenEncoder, cached_encode
from prepare_data import CATEGORIES, group_key, load_items, write_json, write_jsonl
from tfidf_lr import fit


def load_splits(path, items):
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest["dataset_sha256"] != data_digest(items):
        raise ValueError("Saved splits belong to different reviewed data")
    ids = {r["id"]: i for i, r in enumerate(items)}
    all_ids = set(ids)
    raw_rare = manifest["training_only_ids"]
    rare = set(raw_rare)
    if len(rare) != len(raw_rare) or not rare <= all_ids:
        raise ValueError("Invalid training-only IDs")
    folds, seen, numbers = [], set(), set()
    for entry in manifest["folds"]:
        train, held = entry["train_ids"], entry["validation_ids"]
        a, b = set(train), set(held)
        if (len(a) != len(train) or len(b) != len(held) or not b
                or a & b or a | b != all_ids or b & seen or not rare <= a
                or entry["fold"] in numbers):
            raise ValueError("Invalid or overlapping saved fold")
        if ({items[ids[i]]["group"] for i in a} & {items[ids[i]]["group"] for i in b}):
            raise ValueError("A variant group crosses the fold boundary")
        if len({items[ids[i]]["category"] for i in a}) < 2:
            raise ValueError("Fold training data has fewer than two classes")
        folds.append(dict(train=[ids[i] for i in train], validation=[ids[i] for i in held]))
        seen.update(b)
        numbers.add(entry["fold"])
    if seen != all_ids - rare or type(manifest["seed"]) is not int:
        raise ValueError("Incomplete validation coverage or invalid seed")
    return folds, manifest


def predict_vectors(model, vectors):
    if not len(vectors):
        return []
    with threadpool_limits(limits=1):
        probabilities = model.predict_proba(vectors)
    results = []
    for values in probabilities:
        ordered = [0.0] * 10
        for category, value in zip(model.classes_, values):
            ordered[int(category)] = float(value)
        category = int(model.classes_[int(np.argmax(values))])
        results.append(dict(category=category, category_name=CATEGORIES[category],
                            probabilities=ordered))
    return results


class Classifier:
    def __init__(self, bundle, encoder):
        if bundle["encoder_identity"] != encoder.identity:
            raise ValueError("Encoder files, settings or dependency versions differ from training")
        self.bundle, self.encoder, self.model = bundle, encoder, bundle["classifier"]

    @classmethod
    def load(cls, path, encoder_dir=None):
        path = Path(path).resolve()
        bundle = joblib.load(path)  # Only load trusted locally-produced files.
        if bundle.get("format_version") != "embedding-lr-1":
            raise ValueError("Unsupported embedding classifier")
        directory = Path(encoder_dir) if encoder_dir else path.parent / bundle["encoder_relative_path"]
        identity = bundle["encoder_identity"]
        encoder = FrozenEncoder(directory, batch_size=identity["batch_size"],
                                max_length=identity["max_length"], threads=identity["threads"])
        return cls(bundle, encoder)

    def predict(self, names):
        return predict_vectors(self.model, self.encoder.encode(names))


def train(data_path, output_dir, splits_path, encoder_dir, cache_path, benchmark_count=1000):
    data_path, output_dir, splits_path = Path(data_path), Path(output_dir), Path(splits_path)
    if benchmark_count < 1:
        raise ValueError("Benchmark count must be positive")
    if output_dir.exists():
        raise FileExistsError("Choose a new output directory")
    cache_path = Path(cache_path).resolve()
    protected = {data_path.resolve(), splits_path.resolve()}
    for candidate in (cache_path, cache_path.with_suffix(cache_path.suffix + ".tmp")):
        if (candidate in protected or candidate.is_relative_to(Path(encoder_dir).resolve())
                or candidate.is_relative_to(output_dir.resolve())):
            raise ValueError("Cache must be separate from inputs, encoder and output directory")
    if cache_path.suffix.lower() != ".npz":
        raise ValueError("Cache must use a dedicated .npz path")
    source_hash, splits_hash = fingerprint(data_path), fingerprint(splits_path)
    items = load_items(data_path)
    if len({r["category"] for r in items}) < 2:
        raise ValueError("Training requires at least two categories")
    folds, manifest = load_splits(splits_path, items)
    load_start = time.perf_counter()
    encoder = FrozenEncoder(encoder_dir)
    load_seconds = time.perf_counter() - load_start
    encode_start = time.perf_counter()
    vectors, cache_hit = cached_encode(encoder, [r["name"] for r in items], cache_path)
    encode_seconds = time.perf_counter() - encode_start
    output_dir.mkdir(parents=True, exist_ok=False)
    labels = np.array([r["category"] for r in items])
    predictions, fold_scores = [], []
    cv_start = time.perf_counter()

    def new_model():
        return LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000,
                                  random_state=manifest["seed"])

    for fold, saved in zip(folds, manifest["folds"]):
        train_ids, held = fold["train"], fold["validation"]
        model = fit(new_model(), vectors[train_ids], labels[train_ids])
        results = predict_vectors(model, vectors[held])
        baseline = min(Counter(labels[train_ids].tolist()).items(), key=lambda pair: (-pair[1], pair[0]))[0]
        for i, result in zip(held, results):
            row = items[i]
            predictions.append(dict(id=row["id"], name=row["name"], actual=row["category"],
                                    predicted=result["category"], probabilities=result["probabilities"],
                                    baseline=baseline, fold=saved["fold"],
                                    name_only_context_needed=row["name_only_context_needed"]))
        fold_scores.append(dict(fold=saved["fold"], train_items=len(train_ids), validation_items=len(held),
                                model=metrics(labels[held].tolist(), [r["category"] for r in results])))
    cv_seconds = time.perf_counter() - cv_start
    final_start = time.perf_counter()
    model = fit(new_model(), vectors, labels)
    final_seconds = time.perf_counter() - final_start
    bundle = dict(format_version="embedding-lr-1", classifier=model,
                  encoder_identity=encoder.identity,
                  encoder_relative_path=os.path.relpath(encoder.directory, output_dir.resolve()),
                  source_sha256=source_hash, dataset_sha256=data_digest(items),
                  training_names=[r["name"] for r in items], training_groups=[r["group"] for r in items],
                  categories=list(CATEGORIES))
    joblib.dump(bundle, output_dir / "model.joblib")
    predictor = Classifier(bundle, encoder)
    benchmark_names = [items[i % len(items)]["name"] for i in range(benchmark_count)]
    predictor.predict(benchmark_names[:10])
    started = time.perf_counter()
    predictor.predict(benchmark_names)  # No embedding cache: include encoder cost.
    inference_seconds = time.perf_counter() - started
    benchmark_vectors = vectors[np.arange(benchmark_count) % len(items)]
    started = time.perf_counter()
    predict_vectors(model, benchmark_vectors)
    classifier_seconds = time.perf_counter() - started

    def score(rows, key="predicted"):
        return metrics([r["actual"] for r in rows], [r[key] for r in rows])

    classifier_bytes = (output_dir / "model.joblib").stat().st_size
    report = dict(
        experiment="B", evaluation_kind="development_cross_validation_no_final_test", items=len(items),
        source_sha256=source_hash, dataset_sha256=data_digest(items), splits_sha256=splits_hash,
        encoder=encoder.identity,
        settings=dict(seed=manifest["seed"], folds=len(folds), C=1.0,
                      class_weight="balanced", encoder_finetuned=False, tuned=False),
        category_counts={str(i): sum(r["category"] == i for r in items) for i in range(10)},
        validation=dict(status="available" if folds else "insufficient_groups",
                        evaluated_items=len(predictions), training_only_items=len(manifest["training_only_ids"]),
                        model=score(predictions), baseline=score(predictions, "baseline"), folds=fold_scores,
                        context_dependent=score([r for r in predictions if r["name_only_context_needed"]]),
                        name_only=score([r for r in predictions if not r["name_only_context_needed"]])),
        cost=dict(encoder_load_seconds=load_seconds, embedding_seconds=encode_seconds,
                  embedding_cache_hit=cache_hit, cv_seconds=cv_seconds, final_training_seconds=final_seconds,
                  benchmark_count=benchmark_count, inference_seconds=inference_seconds,
                  classifier_only_seconds=classifier_seconds,
                  benchmark="Warm uncached encoder plus LR; cyclic repeated names; not accuracy evidence",
                  peak_process_rss_bytes=peak_rss_bytes(), classifier_bytes=classifier_bytes,
                  encoder_bytes=encoder.model_bytes, deployed_model_bytes=classifier_bytes + encoder.model_bytes),
        environment=environment(),
        limitations=["Exact A saved folds; development CV, not an independent test.",
                     "Six rare classes have no validation support in the current corpus.",
                     "Frozen pretrained encoder sees names only; no label-dependent embedding fit.",
                     "Probabilities are not calibrated; final classifier uses all reviewed items."])
    if fingerprint(data_path) != source_hash or fingerprint(splits_path) != splits_hash:
        raise ValueError("Data or splits changed during training")
    write_json(output_dir / "splits.json", manifest)
    write_jsonl(output_dir / "validation-predictions.jsonl", predictions)
    write_json(output_dir / "report.json", report)
    return report


def evaluate(model_path, data_path, output_dir, encoder_dir=None):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError("Choose a new output directory")
    predictor = Classifier.load(model_path, encoder_dir)
    items = load_items(data_path)
    results = predictor.predict([r["name"] for r in items])
    known = set(predictor.bundle["training_groups"])
    known.update(group_key(name) for name in predictor.bundle["training_names"])
    rows = [dict(id=row["id"], name=row["name"], actual=row["category"],
                 overlap=(row["group"] in known or group_key(row["name"]) in known), **result)
            for row, result in zip(items, results)]
    unseen = [r for r in rows if not r["overlap"]]
    report = dict(items=len(rows), overlap_items=len(rows) - len(unseen), unseen_items=len(unseen),
                  unseen=metrics([r["actual"] for r in unseen], [r["category"] for r in unseen]),
                  all_items=metrics([r["actual"] for r in rows], [r["category"] for r in rows]),
                  independent_test_verified=False,
                  note="Unseen name/group does not establish independent data collection.")
    output_dir.mkdir(parents=True, exist_ok=False)
    write_json(output_dir / "report.json", report)
    write_jsonl(output_dir / "predictions.jsonl", rows)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    training = commands.add_parser("train")
    training.add_argument("--data", required=True, type=Path)
    training.add_argument("--out", required=True, type=Path)
    training.add_argument("--splits", required=True, type=Path)
    training.add_argument("--encoder-dir", required=True, type=Path)
    training.add_argument("--cache", required=True, type=Path)
    for command in ("predict", "evaluate"):
        sub = commands.add_parser(command)
        sub.add_argument("--model", required=True, type=Path)
        sub.add_argument("--data", required=True, type=Path)
        sub.add_argument("--out", required=True, type=Path)
        sub.add_argument("--encoder-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "train":
            report = train(args.data, args.out, args.splits, args.encoder_dir, args.cache)
        elif args.command == "evaluate":
            report = evaluate(args.model, args.data, args.out, args.encoder_dir)
        else:
            if args.out.exists():
                raise FileExistsError("Output exists")
            with args.data.open(encoding="utf-8-sig") as stream:
                rows = [json.loads(line) for line in stream if line.strip()]
            results = Classifier.load(args.model, args.encoder_dir).predict([r["name"] for r in rows])
            args.out.parent.mkdir(parents=True, exist_ok=True)
            write_jsonl(args.out, [dict(name=row["name"], **result) for row, result in zip(rows, results)])
            report = dict(items=len(results), output=str(args.out))
        print(json.dumps(report, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError):
        parser.exit(1, "B failed: check reviewed inputs, saved A splits, local encoder and new output path.\n")


if __name__ == "__main__":
    main()
