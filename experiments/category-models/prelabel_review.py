"""Prepare local model-assisted review. Stdout contains aggregate counts only."""
import argparse
from collections import Counter
import contextlib
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path

from prepare_data import CATEGORIES, group_key, normalize


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_invoices(paths):
    counts = Counter(files=len(paths), eligible_rows=0, excluded_footer=0,
                     excluded_void=0, excluded_amount=0)
    unique = {}
    required = {'發票日期', '發票狀態', '消費明細_品名', '消費明細_金額'}
    for path in paths:
        with Path(path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not required <= set(reader.fieldnames or []):
                raise ValueError('invalid_invoice_headers')
            for row in reader:
                if not row.get('發票日期'):
                    counts['excluded_footer'] += 1
                    continue
                if None in row or any(row.get(k) is None for k in required):
                    raise ValueError('invalid_invoice_columns')
                status = row['發票狀態'].strip()
                if status.startswith('作廢'):
                    counts['excluded_void'] += 1
                    continue
                if status != '開立已確認':
                    raise ValueError('invalid_invoice_status')
                try:
                    datetime.strptime(row['發票日期'], '%Y%m%d')
                except ValueError:
                    raise ValueError('invalid_invoice_date') from None
                try:
                    amount = float(row['消費明細_金額'])
                except (ValueError, TypeError):
                    raise ValueError('invalid_invoice_amount') from None
                if not math.isfinite(amount) or abs(amount) > 10**9:
                    raise ValueError('invalid_invoice_amount')
                if not amount.is_integer() or amount < 10:
                    counts['excluded_amount'] += 1
                    continue
                name = normalize(row['消費明細_品名'])
                if not name:
                    raise ValueError('empty_invoice_name')
                key = group_key(name)
                if key not in unique:
                    unique[key] = dict(id='new-' + hashlib.sha256(key.encode()).hexdigest()[:20],
                                       name=name, occurrences=0)
                unique[key]['occurrences'] += 1
                counts['eligible_rows'] += 1
    counts['unique_names'] = len(unique)
    if not unique:
        raise ValueError('no_eligible_names')
    return list(unique.values()), dict(counts)


def validate_predictions(predictions, size):
    if len(predictions) != size:
        raise ValueError('invalid_prediction_count')
    for result in predictions:
        category, probs = result.get('category'), result.get('probabilities', [])
        if type(category) is not int or category not in range(10) or len(probs) != 10:
            raise ValueError('invalid_prediction')
        if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in probs):
            raise ValueError('invalid_prediction')
        if abs(sum(probs) - 1) > 1e-5 or category != max(range(10), key=probs.__getitem__):
            raise ValueError('invalid_prediction')


def make_drafts(rows, bert, tfidf):
    validate_predictions(bert, len(rows))
    validate_predictions(tfidf, len(rows))
    drafts = []
    for row, primary, secondary in zip(rows, bert, tfidf):
        ranked = sorted(primary['probabilities'], reverse=True)
        reasons = []
        if primary['category'] != secondary['category']:
            reasons.append('model_disagreement')
        if ranked[0] < .8:
            reasons.append('low_score')
        if ranked[0] - ranked[1] < .25:
            reasons.append('small_margin')
        if secondary.get('out_of_vocabulary'):
            reasons.append('tfidf_out_of_vocabulary')
        drafts.append(dict(**row, source='real', category=None, review_status='model_pending',
                           name_only_context_needed=False, suggested_category=primary['category'],
                           bert_score=ranked[0], bert_probabilities=primary['probabilities'],
                           tfidf_category=secondary['category'], review_reasons=reasons))
    return sorted(drafts, key=lambda r: (not bool(r['review_reasons']), r['bert_score'], r['id']))


def render_review(payload):
    # JSON inside a script element must escape '<', even for a non-executable JSON type.
    data = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    folder = Path(__file__).parent
    template = (folder/'review_template.html').read_text(encoding='utf-8-sig')
    core = (folder/'review_core.js').read_text(encoding='utf-8-sig')
    return template.replace('/*REVIEW_CORE*/', core).replace('<!--REVIEW_DATA-->', data)


def write_review(out, payload, counts, provenance):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    rows = payload['rows']
    summary = dict(counts, pending=len(rows), human_confirmed=0,
                   prioritized=sum(bool(r['review_reasons']) for r in rows),
                   suggested_categories=dict(sorted(Counter(str(r['suggested_category']) for r in rows).items())),
                   reason_counts=dict(Counter(reason for row in rows for reason in row['review_reasons'])))
    (out/'draft-items.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
    (out/'review.html').write_text(render_review(payload), encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (out/'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--bert', type=Path, required=True)
    parser.add_argument('--tfidf', type=Path, required=True)
    args = parser.parse_args()
    out, root = args.out.resolve(), args.private_root.resolve()
    if not out.is_relative_to(root) or out == root or out.exists():
        raise ValueError('invalid_private_output')
    paths = sorted(args.input_dir.glob('*.csv'))
    sources = [dict(file=p.name, sha256=digest(p)) for p in paths]
    rows, counts = read_invoices(paths)
    bert_identity = digest(args.bert/'classifier-manifest.json')
    tfidf_identity = digest(args.tfidf)
    # Keep third-party logs private, including when tokenization/inference raises.
    logs = io.StringIO()
    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        from bert_model import Classifier as Bert
        from tfidf_lr import Classifier as Tfidf
        bert = Bert.load(args.bert, device='cpu', threads=2)
        names = [row['name'] for row in rows]
        primary = bert.predict(names)
        secondary = Tfidf.load(args.tfidf).predict(names)
    drafts = make_drafts(rows, primary, secondary)
    if any(digest(path) != source['sha256'] for path, source in zip(paths, sources)):
        raise ValueError('source_changed_during_prelabel')
    if bert_identity != digest(args.bert/'classifier-manifest.json') or tfidf_identity != digest(args.tfidf):
        raise ValueError('model_changed_during_prelabel')
    provenance = dict(sources=sources, bert_manifest_sha256=bert_identity,
                      tfidf_sha256=tfidf_identity, model='BERT seed42 + TF-IDF',
                      categories=list(CATEGORIES), review_required=True,
                      filtering='confirmed nonvoid invoices; integer line amount >= 10; normalized name deduplication')
    batch = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()[:20]
    payload = dict(batch_id=batch, categories=list(CATEGORIES), rows=drafts)
    summary = write_review(out, payload, counts, provenance)
    (out/'inference.log').write_text(logs.getvalue(), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never echo exception text or a traceback that may contain private cells.
        print('{"error":"local_prelabel_failed","private_data_not_printed":true}')
        raise SystemExit(1)
