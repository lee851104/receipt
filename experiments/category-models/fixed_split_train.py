"""Train A/B locally on a fixed train split; validate without scoring the test split."""
import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import gc
import io
import json
import os
from pathlib import Path
import time

# Public model downloads run separately; no training input is sent over the network.
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

import tfidf_lr
import embedding_lr
from common import environment, peak_rss_bytes
from embedding_features import FrozenEncoder
from fixed_split_data import load_dataset, score
from prepare_data import CATEGORIES, write_json, write_jsonl



def verify_predictions(predictions, expected_count):
    if len(predictions) != expected_count:
        raise ValueError('prediction_length_mismatch')
    for prediction in predictions:
        category = prediction['category']
        probabilities = np.asarray(prediction['probabilities'], dtype=float)
        if (type(category) is not int or category not in range(10)
                or probabilities.shape != (10,) or not np.isfinite(probabilities).all()
                or (probabilities < 0).any() or (probabilities > 1).any()
                or not np.isclose(probabilities.sum(), 1.0)
                or category != int(probabilities.argmax())):
            raise ValueError('invalid_prediction')


def verify_roundtrip(first, reloaded, expected_count):
    verify_predictions(first, expected_count)
    verify_predictions(reloaded, expected_count)
    for before, after in zip(first, reloaded):
        if (before['category'] != after['category']
                or not np.allclose(before['probabilities'], after['probabilities'], rtol=1e-7, atol=1e-9)):
            raise ValueError('reload_prediction_mismatch')


def run(kind, dataset_dir, output_dir, encoder_dir=None, benchmark_count=1000):
    if kind not in ('tfidf', 'embedding'):
        raise ValueError('unsupported_fixed_split_model')
    if type(benchmark_count) is not int or benchmark_count < 1:
        raise ValueError('invalid_benchmark_count')
    dataset_dir, output_dir = Path(dataset_dir).resolve(), Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError('output_exists')
    if output_dir.is_relative_to(dataset_dir):
        raise ValueError('output_must_not_be_inside_dataset')
    if encoder_dir is not None:
        encoder_dir = Path(encoder_dir).resolve()
        if output_dir.is_relative_to(encoder_dir):
            raise ValueError('output_must_not_be_inside_encoder')
    parts, manifest, identity = load_dataset(dataset_dir)
    training, validation = parts['train'], parts['validation']
    if not training or len({r['category'] for r in training}) < 2:
        raise ValueError('insufficient_training_classes')
    names = [r['name'] for r in training]
    labels = [r['category'] for r in training]
    validation_names = [r['name'] for r in validation]
    training_sources = dict(Counter(r['source'] for r in training))
    seed = manifest['seed']
    # Keep a standard model bundle so existing trusted local loaders can reload it.
    bundle = dict(categories=list(CATEGORIES), training_names=names,
                  training_groups=[r['group'] for r in training], training_sources=training_sources,
                  source_sha256=manifest['files_sha256']['train'], dataset_sha256=identity,
                  evaluation_kind='fixed_split_development_validation_no_test_scoring', environment=environment())
    load_seconds, encode_seconds, encoder_bytes, encoder_identity = 0.0, 0.0, 0, None
    if kind == 'tfidf':
        model = tfidf_lr.build_model(seed)
        started = time.perf_counter()
        tfidf_lr.fit(model, names, labels)
        fit_seconds = time.perf_counter()-started
        bundle.update(format_version=1, pipeline=model)
        predictor = tfidf_lr.Classifier(bundle)
    else:
        if encoder_dir is None:
            raise ValueError('local_encoder_required')
        started = time.perf_counter()
        encoder = FrozenEncoder(encoder_dir)
        load_seconds = time.perf_counter()-started
        encoder_bytes, encoder_identity = encoder.model_bytes, encoder.identity
        started = time.perf_counter()
        vectors = encoder.encode(names)
        encode_seconds = time.perf_counter()-started
        model = LogisticRegression(C=1.0, class_weight='balanced', max_iter=2000, random_state=seed)
        started = time.perf_counter()
        tfidf_lr.fit(model, vectors, labels)
        fit_seconds = time.perf_counter()-started
        bundle.update(format_version='embedding-lr-1', classifier=model,
                      encoder_identity=encoder_identity,
                      encoder_relative_path=os.path.relpath(encoder_dir, output_dir))
        predictor = embedding_lr.Classifier(bundle, encoder)
        del vectors
    started = time.perf_counter()
    predictions = predictor.predict(validation_names)
    validation_seconds = time.perf_counter()-started
    probe_names = names[:10]
    probe_predictions = predictor.predict(probe_names)
    verify_predictions(predictions, len(validation))
    verify_predictions(probe_predictions, len(probe_names))
    # Reject an altered input before publishing model or results; never silently refit.
    _, _, after = load_dataset(dataset_dir)
    if after != identity:
        raise ValueError('dataset_changed_during_training')
    output_dir.mkdir(parents=True, exist_ok=False)
    model_path = output_dir/'model.joblib'
    joblib.dump(bundle, model_path)
    del predictor, model, bundle
    if kind == 'embedding':
        del encoder
    gc.collect()
    started = time.perf_counter()
    predictor = (tfidf_lr.Classifier.load(model_path) if kind == 'tfidf'
                 else embedding_lr.Classifier.load(model_path, encoder_dir))
    reload_seconds = time.perf_counter()-started
    again = predictor.predict(validation_names)
    verify_roundtrip(predictions, again, len(validation))
    verify_roundtrip(probe_predictions, predictor.predict(probe_names), len(probe_names))
    benchmark_names = [names[i % len(names)] for i in range(benchmark_count)]
    predictor.predict(benchmark_names[:10])
    started = time.perf_counter()
    predictor.predict(benchmark_names)
    inference_seconds = time.perf_counter()-started
    most_frequent = min(Counter(labels).items(), key=lambda pair:(-pair[1],pair[0]))[0]
    actual = [r['category'] for r in validation]
    report = dict(
        experiment='A' if kind=='tfidf' else 'B', model=kind,
        evaluation_kind='fixed_split_development_validation_no_test_scoring',
        test_evaluation='not_run', reload_verified=True, reload_probe_items=len(probe_names),
        dataset=dict(manifest_sha256=identity, files_sha256=manifest['files_sha256'],
                     source_sha256=manifest['source_sha256'], summary=manifest['summary']),
        training_sources=training_sources,
        settings=dict(seed=seed, C=1.0, class_weight='balanced', max_iter=2000, tuned=False),
        validation=dict(model=score(actual,[r['category'] for r in predictions]),
                        baseline=score(actual,[most_frequent]*len(actual))),
        cost=dict(initial_encoder_load_seconds=load_seconds, training_encode_seconds=encode_seconds,
                  fit_seconds=fit_seconds, validation_seconds=validation_seconds,
                  reload_seconds=reload_seconds, inference_seconds=inference_seconds,
                  benchmark_count=benchmark_count,
                  benchmark='warm full CPU pipeline; cyclic training names; no embedding cache; not accuracy evidence',
                  classifier_bytes=model_path.stat().st_size, encoder_bytes=encoder_bytes,
                  model_bytes=model_path.stat().st_size+encoder_bytes, peak_process_rss_bytes=peak_rss_bytes()),
        environment=environment(), encoder_identity=encoder_identity,
        limitations=['Development validation only. The test split has not been scored.',
                     'Real names were used in earlier development CV; not independent final test data.',
                     'Synthetic training data dominate. No generalization claim from these scores.',
                     'Classes with fewer than five validation names are excluded from macro F1.',
                     'Semantic variant groups still require human review.',
                     'Probabilities are not calibrated correctness guarantees.'])
    if kind=='tfidf':
        report['settings'].update(analyzer='char', ngram_range=[1,3], sublinear_tf=True, lowercase=False)
    _, _, after = load_dataset(dataset_dir)
    if after != identity:
        raise ValueError('dataset_changed_during_training')
    private_predictions = [dict(id=row['id'], name=row['name'], actual=row['category'],
                                predicted=prediction['category'], probabilities=prediction['probabilities'])
                           for row,prediction in zip(validation,predictions)]
    write_jsonl(output_dir/'validation-predictions.jsonl',private_predictions)
    write_json(output_dir/'report.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=('tfidf','embedding'),required=True)
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--encoder-dir',type=Path)
    args=parser.parse_args()
    try:
        # Suppress third-party progress/errors that could contain an input value.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            report=run(args.model,args.dataset,args.out,args.encoder_dir)
        print(json.dumps(report,ensure_ascii=True))
    except Exception:
        parser.exit(1,'Fixed-split training failed; verify local inputs, dependencies, encoder and a new output directory.\n')


if __name__=='__main__':main()
