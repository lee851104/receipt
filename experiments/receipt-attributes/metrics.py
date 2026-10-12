"""Typed-field accuracy and positive-label P/R/F1, without hiding abstentions."""
ENUMS = {'sugar', 'fun', 'species'}
MISSING = object()


def prf(tp, fp, fn):
    return {'tp': tp, 'fp': fp, 'fn': fn,
            'precision': tp / (tp + fp) if tp + fp else 0,
            'recall': tp / (tp + fn) if tp + fn else 0,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0}


def score(reference, predictions):
    gold_ids = {r['id'] for r in reference}
    by_id = {p['id']: p for p in predictions}
    if len(gold_ids) != len(reference) or len(by_id) != len(predictions) or not set(by_id) <= gold_ids:
        raise ValueError('Duplicate or unexpected IDs')
    fields, exact, abstained, differences = {}, 0, 0, []
    for row in reference:
        actual = by_id.get(row['id'], {}).get('attributes', {})
        matches = True
        for field, want in row['attributes'].items():
            stat = fields.setdefault(field, {'known': 0, 'correct': 0, 'support': 0, 'tp': 0, 'fp': 0, 'fn': 0})
            if field not in ENUMS and want is None:
                continue
            got = actual.get(field, MISSING)
            equal = got is not MISSING and type(want) is type(got) and want == got
            if field == 'sugar' and type(want) in (int, float) and type(got) in (int, float):
                equal = want == got
            stat['known'] += 1
            stat['correct'] += int(equal)
            abstained += int(got is MISSING or (field not in ENUMS and got is None))
            positive_gold = want is not None if field in ENUMS else want is True
            positive_pred = got is not MISSING and (got is not None if field in ENUMS else got is True)
            stat['support'] += int(positive_gold)
            stat['tp'] += int(positive_gold and positive_pred and equal)
            stat['fp'] += int(positive_pred and not (positive_gold and equal))
            stat['fn'] += int(positive_gold and not (positive_pred and equal))
            if not equal:
                matches = False
                differences.append({'id': row['id'], 'field': field, 'expected': want,
                                    'predicted': '__MISSING__' if got is MISSING else got})
        exact += int(matches and row['id'] in by_id)
    for stat in fields.values():
        stat.update(prf(stat['tp'], stat['fp'], stat['fn']))
        stat['accuracy'] = stat['correct'] / stat['known'] if stat['known'] else None
    supported = [f for f, s in fields.items() if s['support']]
    known = sum(s['known'] for s in fields.values())
    return {'items': len(reference), 'predicted_items': len(by_id), 'known_fields': known,
            'accuracy': sum(s['correct'] for s in fields.values()) / known if known else None,
            'micro': prf(*(sum(s[k] for s in fields.values()) for k in ('tp', 'fp', 'fn'))),
            'macro_f1_supported': sum(fields[f]['f1'] for f in supported) / len(supported) if supported else None,
            'supported_attributes': supported, 'exact_items': exact, 'abstained_fields': abstained,
            'fields': fields, 'differences': differences}
