"""Local model A: train, predict, and evaluate reviewed invoice item names."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time
import warnings

import joblib
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from common import (data_digest, environment, fingerprint, make_folds, metrics,
                    peak_rss_bytes)
from prepare_data import (CATEGORIES, group_key, load_items, normalize,
                          write_json, write_jsonl)


def build_model(seed=42):
    return Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(1, 3),
                                 sublinear_tf=True, lowercase=False)),
        ("lr", LogisticRegression(C=1.0, class_weight="balanced",
                                  max_iter=2000, random_state=seed)),
    ])


def fit(model, names, categories):
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(names, categories)
    return model


class Classifier:
    def __init__(self, bundle):
        self.bundle = bundle
        self.model = bundle["pipeline"]

    @classmethod
    def load(cls, path):
        # joblib uses pickle: only load files produced locally or otherwise trusted.
        bundle = joblib.load(path)
        if bundle.get("format_version") != 1:
            raise ValueError("Unsupported model format")
        return cls(bundle)

    def predict(self, names):
        names = [normalize(name) for name in names]
        if not names:
            return []
        with threadpool_limits(limits=1):
            probabilities = self.model.predict_proba(names)
            empty = self.model.named_steps["tfidf"].transform(names).getnnz(axis=1) == 0
        predictions = []
        for values, zero in zip(probabilities, empty):
            ordered = [0.0] * 10
            for category, probability in zip(self.model.classes_, values):
                ordered[int(category)] = float(probability)
            category = int(self.model.classes_[int(np.argmax(values))])
            predictions.append(dict(category=category, category_name=CATEGORIES[category],
                                    probabilities=ordered, out_of_vocabulary=bool(zero)))
        return predictions


def train(data_path, output_dir, seed=42, n_splits=3):
    data_path, output_dir = Path(data_path), Path(output_dir)
    items = load_items(data_path)
    if len({item["category"] for item in items}) < 2:
        raise ValueError("Training requires at least two classes")
    folds = make_folds(items, n_splits, seed)
    # Exclusive directory creation avoids mixing runs or overwriting user results.
    output_dir.mkdir(parents=True, exist_ok=False)
    source_hash = fingerprint(data_path)
    started = time.perf_counter()
    predictions, assignments, fold_scores = [], [], []
    for number, fold in enumerate(folds, 1):
        training = [items[i] for i in fold["train"]]
        validation = [items[i] for i in fold["validation"]]
        model = fit(build_model(seed), [r["name"] for r in training],
                    [r["category"] for r in training])
        predictor = Classifier(dict(pipeline=model))
        results = predictor.predict([r["name"] for r in validation])
        most_frequent = min(Counter(r["category"] for r in training).items(),
                            key=lambda pair: (-pair[1], pair[0]))[0]
        for row, result in zip(validation, results):
            predictions.append(dict(id=row["id"], name=row["name"],
                                    actual=row["category"], predicted=result["category"],
                                    baseline=most_frequent, fold=number,
                                    probabilities=result["probabilities"],
                                    out_of_vocabulary=result["out_of_vocabulary"],
                                    name_only_context_needed=row["name_only_context_needed"]))
        assignments.append(dict(fold=number, train_ids=[r["id"] for r in training],
                                validation_ids=[r["id"] for r in validation]))
        fold_scores.append(dict(fold=number, train_items=len(training),
                                validation_items=len(validation),
                                model=metrics([r["category"] for r in validation],
                                              [r["category"] for r in results])))
    evaluated_ids = {r["id"] for r in predictions}
    if len(evaluated_ids) != len(predictions):
        raise ValueError("A record was validated more than once")
    cv_seconds = time.perf_counter() - started
    final_start = time.perf_counter()
    model = fit(build_model(seed), [r["name"] for r in items],
                [r["category"] for r in items])
    final_seconds = time.perf_counter() - final_start
    bundle = dict(format_version=1, pipeline=model, categories=list(CATEGORIES),
                  source_sha256=source_hash, dataset_sha256=data_digest(items),
                  training_names=[r["name"] for r in items],
                  training_groups=[r["group"] for r in items], environment=environment())
    model_path = output_dir / "model.joblib"
    joblib.dump(bundle, model_path)
    predictor = Classifier.load(model_path)
    benchmark_names = [items[i % len(items)]["name"] for i in range(1000)]
    predictor.predict(benchmark_names[:10])
    bench_start = time.perf_counter()
    predictor.predict(benchmark_names)
    inference_seconds = time.perf_counter() - bench_start

    def score(rows, key="predicted"):
        return metrics([r["actual"] for r in rows], [r[key] for r in rows])

    report = dict(
        experiment="A", evaluation_kind="development_cross_validation_no_final_test",
        items=len(items), source_sha256=source_hash, dataset_sha256=data_digest(items),
        category_counts={str(i): sum(r["category"] == i for r in items) for i in range(10)},
        settings=dict(seed=seed, folds=n_splits, analyzer="char", ngram_range=[1, 3],
                      sublinear_tf=True, C=1.0, class_weight="balanced", tuned=False),
        validation=dict(status="available" if folds else "insufficient_groups",
                        evaluated_items=len(predictions),
                        training_only_items=len(items) - len(evaluated_ids),
                        model=score(predictions), baseline=score(predictions, "baseline"),
                        context_dependent=score([r for r in predictions if r["name_only_context_needed"]]),
                        name_only=score([r for r in predictions if not r["name_only_context_needed"]]),
                        folds=fold_scores),
        cost=dict(cv_seconds=cv_seconds, final_training_seconds=final_seconds,
                  inference_1000_seconds=inference_seconds,
                  benchmark="warm pipeline, 1000 cyclic repeats of input names; not accuracy evidence",
                  peak_process_rss_bytes=peak_rss_bytes(), model_bytes=model_path.stat().st_size),
        environment=environment(),
        limitations=["Development CV only; no independent final test or parameter tuning.",
                     "Classes with fewer than three groups are training-only in default CV.",
                     "Macro F1 covers only classes represented in validation; ten-class score may be null.",
                     "Variants require explicit group annotations beyond case/whitespace normalization.",
                     "Probabilities are not calibrated accuracy guarantees.",
                     "Final model uses all confirmed items; its training accuracy is not reported."])
    if fingerprint(data_path) != source_hash:
        raise ValueError("Input changed during training")
    write_json(output_dir / "splits.json", dict(dataset_sha256=data_digest(items),
                                               seed=seed, folds=assignments,
                                               training_only_ids=[r["id"] for r in items if r["id"] not in evaluated_ids]))
    write_jsonl(output_dir / "validation-predictions.jsonl", predictions)
    write_json(output_dir / "report.json", report)
    return report


def evaluate(model_path, data_path, output_dir):
    predictor = Classifier.load(model_path)
    items = load_items(data_path)
    results = predictor.predict([r["name"] for r in items])
    known = set(predictor.bundle["training_groups"])
    known.update(group_key(name) for name in predictor.bundle["training_names"])
    rows = [dict(id=row["id"], name=row["name"], actual=row["category"],
                 overlap=(row["group"] in known or group_key(row["name"]) in known), **result)
            for row, result in zip(items, results)]
    unseen = [r for r in rows if not r["overlap"]]
    report = dict(items=len(rows), overlap_items=len(rows) - len(unseen),
                  unseen_items=len(unseen),
                  unseen=metrics([r["actual"] for r in unseen], [r["category"] for r in unseen]),
                  all_items=metrics([r["actual"] for r in rows], [r["category"] for r in rows]),
                  independent_test_verified=False,
                  note="Unseen means no matching name/group, not proven independent data collection.")
    output_dir = Path(output_dir)
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
    training.add_argument("--seed", type=int, default=42)
    training.add_argument("--folds", type=int, default=3)
    for command in ("predict", "evaluate"):
        sub = commands.add_parser(command)
        sub.add_argument("--model", required=True, type=Path)
        sub.add_argument("--data", required=True, type=Path)
        sub.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "train":
            report = train(args.data, args.out, args.seed, args.folds)
        elif args.command == "evaluate":
            report = evaluate(args.model, args.data, args.out)
        else:
            if args.out.exists():
                raise FileExistsError("Output exists")
            with args.data.open(encoding="utf-8-sig") as stream:
                rows = [json.loads(line) for line in stream if line.strip()]
            results = Classifier.load(args.model).predict([r["name"] for r in rows])
            args.out.parent.mkdir(parents=True, exist_ok=True)
            write_jsonl(args.out, [dict(name=r["name"], **result) for r, result in zip(rows, results)])
            report = dict(items=len(results), output=str(args.out))
        print(json.dumps(report, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, ConvergenceWarning):
        parser.exit(1, "Experiment failed: verify inputs, reviewed labels, model and a new output path.\n")


if __name__ == "__main__":
    main()
