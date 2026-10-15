"""Validated fixed-split snapshots and honest low-support classification scores."""
import json
from pathlib import Path

import numpy as np
from common import metrics
from dataset_split import PARTS, audit_split, check_dataset, digest


def load_dataset(folder):
    folder = Path(folder)
    manifest_bytes = (folder/'manifest.json').read_bytes()
    check_dataset(folder)
    manifest = json.loads(manifest_bytes.decode('utf-8'))
    parts = {}
    for part in PARTS:
        raw = (folder/f'{part}.jsonl').read_bytes()
        if digest(raw) != manifest['files_sha256'][part]:
            raise ValueError('dataset_changed_during_load')
        parts[part] = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    if audit_split(parts) != manifest['summary'] or (folder/'manifest.json').read_bytes() != manifest_bytes:
        raise ValueError('dataset_changed_during_load')
    return parts, manifest, digest(manifest_bytes)


def score(truth, predicted):
    if len(truth) != len(predicted) or any(type(c) is not int or not 0 <= c < 10 for c in truth + predicted):
        raise ValueError('invalid_predictions')
    result = metrics(truth, predicted)
    if result is None:
        result = dict(support=0, accuracy=None, evaluated_categories=[], macro_f1=None,
                      ten_class_macro_f1=None,
                      per_class={str(c): dict(support=0, precision=None, recall=None, f1=None) for c in range(10)},
                      confusion_matrix=[[0]*10 for _ in range(10)])
    eligible = [c for c in range(10) if result['per_class'][str(c)]['support'] >= 5]
    result['evaluated_categories'] = eligible
    result['macro_f1'] = float(np.mean([result['per_class'][str(c)]['f1'] for c in eligible])) if eligible else None
    result['ten_class_macro_f1'] = result['macro_f1'] if len(eligible) == 10 else None
    result['excluded_categories'] = []
    for c in range(10):
        row = result['per_class'][str(c)]
        row['eligible'] = c in eligible
        if c not in eligible:
            result['excluded_categories'].append(dict(category=c, count=row['support'], reason='fewer_than_5_real_items'))
            row.update(precision=None, recall=None, f1=None)
    return result
