"""Typed boundary for the isolated attribute experiment."""
import csv
import hashlib
ATTRIBUTES = ['clearance', 'sugar', 'quick', 'cooking', 'kitchen', 'sport_supply',
              'sport_gear', 'car_care', 'bulk', 'home', 'stationery', 'fun',
              'pet_food', 'pet_supply', 'species', 'alcohol']
BASIC = ['food', 'meal', 'drink', 'fresh', 'daily', 'tech', 'sport']
BOOLEAN_FIELDS = [key for key in ATTRIBUTES if key not in ('sugar', 'fun', 'species')] + BASIC


def decode_sparse(value):
    if not isinstance(value, dict) or set(value) != {'id', 'yes', 'unknown', 'sugar', 'fun', 'species'}:
        raise ValueError('Named prediction requires id, yes, unknown, sugar, fun, species')
    yes, unknown = value['yes'], value['unknown']
    if not all(isinstance(x, list) and all(isinstance(k, str) for k in x) for x in (yes, unknown)):
        raise ValueError('Labels must be string lists')
    if len(set(yes)) != len(yes) or len(set(unknown)) != len(unknown) or set(yes) & set(unknown):
        raise ValueError('Duplicate or contradictory labels')
    if not (set(yes) | set(unknown)).issubset(BOOLEAN_FIELDS):
        raise ValueError('Unsupported label')
    values = {key: None if key in unknown else key in yes for key in BOOLEAN_FIELDS}
    values.update({key: value[key] for key in ('sugar', 'fun', 'species')})
    return decode_prediction({'id': value['id'], 'attributes': [values[k] for k in ATTRIBUTES],
                              'basic': [values[k] for k in BASIC]})


def prepare(path):
    raw = path.read_bytes()
    rows, groups = [], {}
    required = {'發票日期', '發票狀態', '發票號碼', '賣方名稱', '消費明細_品名', '消費明細_數量', '消費明細_金額'}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Missing columns: ' + str(sorted(required - set(reader.fieldnames or []))))
        for line, entry in enumerate(reader, 2):
            if not entry['發票日期']:
                continue
            if entry['發票狀態'] != '開立已確認':
                raise ValueError(f'Unsupported invoice status on CSV line {line}')
            name, merchant = entry['消費明細_品名'].strip(), entry['賣方名稱'].strip()
            quantity, amount = int(entry['消費明細_數量']), int(entry['消費明細_金額'])
            # Quantity affects the bulk flag, so different quantities stay separate too.
            key = (merchant, name, quantity)
            row_id = f'r{len(rows) + 1:04}'
            if key not in groups:
                groups[key] = {'id': f'i{len(groups) + 1:04}', 'name': name,
                               'merchant': merchant, 'quantity': quantity, 'row_ids': []}
            item = groups[key]
            item['row_ids'].append(row_id)
            rows.append({'row_id': row_id, 'csv_line': line, 'item_id': item['id'],
                         'date': entry['發票日期'], 'name': name, 'merchant': merchant,
                         'quantity': quantity, 'amount': amount})
    if not rows:
        raise ValueError('No invoice rows')
    return {'schema_version': 'receipt-attributes/experiment-v1',
            'source_name': path.name, 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'total_amount': sum(r['amount'] for r in rows), 'rows': rows, 'items': list(groups.values())}


def decode_prediction(value):
    if not isinstance(value, dict) or set(value) != {'id', 'attributes', 'basic'}:
        raise ValueError('Prediction requires exactly id, attributes, basic')
    if not isinstance(value['id'], str):
        raise ValueError('Invalid id')
    arrays = (value['attributes'], value['basic'])
    if not all(isinstance(a, list) for a in arrays) or [len(a) for a in arrays] != [16, 7]:
        raise ValueError('Expected 16 attribute values and 7 basic values')
    attrs = dict(zip(ATTRIBUTES, arrays[0]))
    for key, item in attrs.items():
        if item is None:
            continue
        if key == 'sugar':
            valid = type(item) in (int, float) and item in (0, 0.2, 0.3, 0.5, 0.7, 1)
        elif key == 'fun':
            valid = item in ('movie', 'singing', 'show', 'game') and isinstance(item, str)
        elif key == 'species':
            valid = item in ('cat', 'dog') and isinstance(item, str)
        else:
            valid = type(item) is bool
        if not valid:
            raise ValueError('Invalid attribute: ' + key)
    if any(item is not None and type(item) is not bool for item in arrays[1]):
        raise ValueError('Basic values must be boolean or null')
    return {'id': value['id'], 'attributes': attrs, 'basic': dict(zip(BASIC, arrays[1])),
            'review_status': 'unreviewed_model_prediction'}


def attach(dataset, predictions):
    by_id = {p['id']: p for p in predictions}
    expected = {item['id'] for item in dataset['items']}
    if len(by_id) != len(predictions) or set(by_id) != expected:
        raise ValueError('Predictions must cover each item ID exactly once')
    return [{**row, 'prediction': by_id[row['item_id']]} for row in dataset['rows']]
