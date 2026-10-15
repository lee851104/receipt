"""在本機評估四份人工標註；公開輸出只含彙總，不含品名、ID 或逐筆答案。"""
import argparse
import json
from pathlib import Path

from src.ml.attributes import MODEL_VERSION
from src.ml.fields import FIELDS

ROOT = Path(__file__).resolve().parents[1]
ENUMS = {'sugar': (0, .2, .3, .5, .7, 1), 'fun': ('電影', '唱歌', '展演', '遊樂'), 'species': ('cat', 'dog')}
CONFIRMED = {'human_confirmed', 'human_corrected'}


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def read_groups(folder):
    return [read_jsonl(Path(folder)/f'reviewer-{i}.jsonl') for i in range(1, 5)]


def validate_attributes(values, pending=False):
    if values is None and pending:
        return
    if not isinstance(values, dict) or set(values) != set(FIELDS):
        raise ValueError('invalid_attribute_fields')
    for key, value in values.items():
        if value is None:
            continue
        valid = (type(value) in (int, float) and value in ENUMS[key]) if key == 'sugar' else (
            type(value) is str and value in ENUMS[key] if key in ENUMS else type(value) is bool)
        if not valid:
            raise ValueError('invalid_attribute_value')


def validate_groups(groups):
    if len(groups) != 4 or any(len(rows) != 25 for rows in groups):
        raise ValueError('expected_four_groups_of_25')
    rows = [row for group in groups for row in group]
    ids, names = set(), set()
    for row in rows:
        if not isinstance(row, dict) or row.get('source') != 'real':
            raise ValueError('real_review_required')
        if type(row.get('id')) is not str or not row['id'] or type(row.get('name')) is not str or not row['name']:
            raise ValueError('invalid_review_identity')
        if row['id'] in ids or row['name'] in names:
            raise ValueError('duplicate_review_identity')
        ids.add(row['id']); names.add(row['name'])
        if row.get('review_status') not in CONFIRMED | {'pending_human_review'}:
            raise ValueError('invalid_review_status')
        validate_attributes(row.get('attributes'))
    return rows


def score_field(field, gold, predicted):
    """布林看 true 正例；列舉採非 null 類別的 micro 計數，gold=null 排除。"""
    if len(gold) != len(predicted) or not gold or field not in FIELDS:
        raise ValueError('invalid_score_input')
    tp = fp = fn = 0
    for expected, actual in zip(gold, predicted):
        if expected is None:
            continue
        if field in ENUMS:
            tp += actual == expected
            fp += actual is not None and actual != expected
            fn += actual != expected
        else:
            tp += expected is True and actual is True
            fp += expected is False and actual is True
            fn += expected is True and actual is not True
    return {'known_gold': sum(v is not None for v in gold), 'tp': tp, 'fp': fp, 'fn': fn,
            'precision': tp/(tp+fp) if tp+fp else None,
            'recall': tp/(tp+fn) if tp+fn else None,
            'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            'null_ratio': sum(v is None for v in predicted)/len(predicted)}


def evaluate(groups, predictions, model_version):
    rows = validate_groups(groups)
    if len(predictions) != len(rows):
        raise ValueError('prediction_count_mismatch')
    by_id = {}
    for prediction in predictions:
        if not isinstance(prediction, dict) or prediction.get('source') != 'real':
            raise ValueError('invalid_prediction_source')
        if prediction.get('model_version') != model_version:
            raise ValueError('prediction_version_mismatch')
        ident = prediction.get('id')
        if type(ident) is not str or ident in by_id:
            raise ValueError('invalid_prediction_identity')
        validate_attributes(prediction.get('attributes'), pending=True)
        by_id[ident] = prediction
    if set(by_id) != {row['id'] for row in rows} or any(by_id[row['id']].get('name') != row['name'] for row in rows):
        raise ValueError('prediction_identity_mismatch')
    confirmed = sum(row['review_status'] in CONFIRMED for row in rows)
    predicted_items = sum(p['attributes'] is not None for p in predictions)
    status = 'pending_human_review' if confirmed != 100 else 'pending_predictions' if predicted_items != 100 else 'ready'
    result = {'status': status, 'items': len(rows), 'human_confirmed': confirmed,
              'review_groups': [{'items': len(group), 'confirmed': sum(row['review_status'] in CONFIRMED for row in group)} for group in groups],
              'predicted_items': predicted_items, 'model_version': model_version,
              'review_method': 'model_assisted' if any(row.get('review_method') == 'model_assisted' for row in rows) else 'blind'}
    if status == 'ready':
        result['metrics'] = {key: score_field(key, [row['attributes'][key] for row in rows],
                                             [by_id[row['id']]['attributes'][key] for row in rows]) for key in FIELDS}
    return result


def report_text(result):
    if result['status'] != 'ready':
        raise ValueError('review_not_complete')
    def percent(value):
        return '—' if value is None else f'{value:.2%}'
    lines = ['# 真實品名屬性人工複核', '', '100 筆、4 份各 25 筆人工確認；僅公開彙總數字。', '',
             f"模型版本：`{result['model_version']}`", '',
             '方式：模型預標後人工複核，非盲標。' if result['review_method'] == 'model_assisted' else '方式：獨立人工標註後與模型比較。', '',
             '布林欄位以 true 為正例；sugar、fun、species 以非 null 類別作 micro precision／recall／F1。',
             'gold=null 的欄位不計分；預測 null 遇到已知正例仍計漏判。分母為零的指標顯示 —，不當成滿分。',
             'null 比例分母為全部 100 筆；fun/species 的 null 可代表非娛樂或未寫物種，不等於推論失敗。', '',
             '| 欄位 | 已知人工答案 | precision | recall | F1 | null 比例 |', '|---|---:|---:|---:|---:|---:|']
    for field, score in result['metrics'].items():
        lines.append(f"| {field} | {score['known_gold']} | {percent(score['precision'])} | {percent(score['recall'])} | {percent(score['f1'])} | {percent(score['null_ratio'])} |")
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-dir', type=Path, required=True)
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/results/attributes.md')
    parser.add_argument('--status-only', action='store_true')
    parser.add_argument('--status-output', type=Path)
    args = parser.parse_args(argv)
    try:
        sources = {args.predictions.resolve(), *((args.review_dir/f'reviewer-{i}.jsonl').resolve() for i in range(1, 5))}
        if args.status_output and (args.status_output.resolve() in sources or args.status_output.resolve() in {args.output.resolve(), args.output.with_suffix('.json').resolve()}):
            raise ValueError('invalid_status_destination')
        groups = read_groups(args.review_dir)
        result = evaluate(groups, read_jsonl(args.predictions), MODEL_VERSION)
        status = {key: value for key, value in result.items() if key != 'metrics'}
        if args.status_output:
            args.status_output.write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(status, ensure_ascii=False))
        if args.status_only:
            return 0
        if result['status'] != 'ready':
            return 2
        text, encoded = report_text(result), json.dumps(result, ensure_ascii=False, indent=2)+'\n'
        # Defensive final scan: never echo the match or publish a partial report.
        if any(row['name'] in text+encoded for group in groups for row in group):
            raise ValueError('privacy_scan_failed')
        sources = {args.predictions.resolve(), *( (args.review_dir/f'reviewer-{i}.jsonl').resolve() for i in range(1, 5))}
        if args.output.suffix != '.md' or args.output.resolve() in sources or args.output.with_suffix('.json').resolve() in sources:
            raise ValueError('invalid_report_destination')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
        args.output.with_suffix('.json').write_text(encoded, encoding='utf-8')
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        # Parsing exceptions can include input fragments; do not print exceptions or tracebacks.
        print(json.dumps({'status': 'invalid_input_or_output'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
