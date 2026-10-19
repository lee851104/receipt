"""Frozen diagnostic + March runs. All outputs are private and isolated."""
import argparse
import hashlib
import json
from pathlib import Path
from lab_core import decode_sparse
from run_models import ROOT, run
from download_extra import ASSET


def synthetic():
    path = ROOT / 'benchmark_cases.json'
    source = json.loads(path.read_text(encoding='utf-8'))
    items, reference = [], []
    for n, case in enumerate(source['cases'], 1):
        key = f's{n:04}'
        items.append({'id': key, 'name': case['name'], 'merchant': case['merchant'],
                      'quantity': case.get('quantity', 1), 'row_ids': []})
        prediction = decode_sparse({'id': key, 'yes': case.get('yes', []), 'unknown': [],
                                     **{f: case.get(f) for f in ('sugar','fun','species')}})
        reference.append({'id':key, 'attributes':prediction['attributes']})
    return {'schema_version':'receipt-attributes/experiment-v1',
            'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'items':items, 'rows':[], 'reference':reference, 'status':source['status']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', nargs='+', default=['0.5b','1.5b','3b','qwen3-4b'])
    parser.add_argument('--real-only', action='store_true')
    args = parser.parse_args()
    data = synthetic()
    success = True
    for name in args.models:
        if name not in ('0.5b','1.5b','3b','qwen3-4b'):
            parser.error('Unknown model')
        model = ROOT/'models'/ASSET['file'] if name == 'qwen3-4b' else None
        if not args.real_only:
            success = run(name, data, 3, 0, model_path=model, output_root=ROOT/'results/followup/synthetic') and success
        if name == 'qwen3-4b':
            real = json.loads((ROOT/'private/prepared.json').read_text(encoding='utf-8'))
            success = run(name, real, 3, 0, model_path=model, output_root=ROOT/'results/followup/real') and success
    raise SystemExit(0 if success else 1)
