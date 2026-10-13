"""Report diagnostic agreement, rare-positive coverage, and failures without claiming ground truth."""
import json
from pathlib import Path
from lab_core import ATTRIBUTES, BASIC

ROOT = Path(__file__).resolve().parent


def evaluate(result, reference):
    if result['source_sha256'] != reference['source_sha256']:
        raise ValueError('Source mismatch')
    predicted = {r['id']: r for r in result['predictions']}
    fields = {}
    differences = []
    exact = 0
    # Old initial runs were deterministic prefix batches; newer runs record requested IDs explicitly.
    requested = set(result.get('requested_ids', [x['id'] for x in reference['items'][:result['requested_items']]]))
    missing = 0
    for expected in reference['items']:
        key = expected['id']
        if key not in requested:
            continue
        available = key in predicted
        missing += int(not available)
        same = True
        for group, names in [('attributes', ATTRIBUTES), ('basic', BASIC)]:
            for field in names:
                label = group + '.' + field
                stat = fields.setdefault(label, {'compared': 0, 'equal': 0, 'expected_true': 0,
                                                 'tp': 0, 'fp': 0, 'fn': 0, 'expected_null': 0, 'null_preserved': 0})
                want = expected[group][field]
                got = predicted[key][group][field] if available else '__MISSING_PREDICTION__'
                equal = available and type(want) is type(got) and want == got
                if available and field == 'sugar' and want is not None and got is not None:
                    equal = want == got
                stat['compared'] += 1; stat['equal'] += int(equal)
                stat['expected_true'] += int(want is True)
                stat['tp'] += int(want is True and got is True)
                stat['fp'] += int(want is not None and want is not True and got is True)
                stat['fn'] += int(want is True and got is not True)
                stat['expected_null'] += int(want is None)
                stat['null_preserved'] += int(want is None and got is None)
                if not equal:
                    same = False
                    differences.append({'id': key, 'name': expected['name'], 'field': label,
                                        'draft_expected': want, 'model': got, 'reference_notes': expected['notes']})
        exact += int(same)
    bool_fields = [fields['attributes.' + name] for name in ATTRIBUTES if name not in ('sugar','fun','species') and 'attributes.' + name in fields]
    tp, fp, fn = (sum(f[x] for f in bool_fields) for x in ('tp','fp','fn'))
    return {'model': result['model'], 'reference_status': reference['status'],
            'requested': result['requested_items'], 'valid_predictions': len(predicted), 'missing_predictions': missing, 'failed_batches': len(result['failures']),
            'exact_draft_matches': exact, 'elapsed_seconds': result['elapsed_seconds'],
            'attribute_positive_precision': tp/(tp+fp) if tp+fp else None,
            'attribute_positive_recall': tp/(tp+fn) if tp+fn else None,
            'fields': fields, 'differences': differences,
            'warning': 'These are agreements with an assistant draft, NOT user-verified accuracy.'}


def main():
    reference = json.loads((ROOT / 'private/draft-reference.json').read_text(encoding='utf-8'))
    reports = []
    for path in sorted((ROOT / 'results').glob('*/predictions.json')):
        report = evaluate(json.loads(path.read_text(encoding='utf-8')), reference)
        (path.parent / 'evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        reports.append(report)
        print(report['model'], 'valid', report['valid_predictions'], '/', report['requested'],
              'exact draft agreement', report['exact_draft_matches'], 'differences', len(report['differences']))
    (ROOT / 'results/comparison.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
