"""Evaluate confirmed review labels against frozen local models; aggregate console only."""
import argparse
from collections import defaultdict
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import statistics

from common import fingerprint, metrics
from dataset_split import key, prepare_real, read_rows
from fixed_split_data import load_dataset
from fixed_split_train import verify_predictions
from compare_fixed_models import model_identity, load_predictor
from prepare_data import CATEGORIES, normalize, write_json, write_jsonl


def select_confirmed(raw):
    if any(not isinstance(row, dict) for row in raw):
        raise ValueError('invalid_review_row')
    accepted = [r for r in raw if r.get('review_status') == 'human_confirmed' and r.get('category') != 10]
    rows = prepare_real(accepted)
    # prepare_real hashes component IDs; retain original match tokens separately.
    canonical = {key(row['name']): row for row in rows}
    tokens = defaultdict(set)
    for row in accepted:
        group = canonical[key(row['name'])]['group']
        tokens[group].add(key(row['name']))
        if 'group' in row:
            tokens[group].add(key(row['group']))
    for row in rows:
        row['overlap_keys'] = sorted(tokens[row['group']])
    return rows, dict(input_rows=len(raw), excluded_unconfirmed_or_unknown=len(raw)-len(accepted),
                      deduplicated_confirmed=len(accepted)-len(rows), confirmed=len(rows))


def align_saved(rows, drafts):
    by_id = {r['id']: r for r in drafts}
    if len(by_id) != len(drafts):
        raise ValueError('duplicate_draft_id')
    a, c = [], []
    for row in rows:
        saved = by_id.get(row['id'])
        if saved is None or normalize(saved['name']) != normalize(row['name']):
            raise ValueError('review_draft_mismatch')
        ac, cc = saved.get('tfidf_category'), saved.get('suggested_category')
        if any(type(v) is not int or v not in range(10) for v in (ac, cc)):
            raise ValueError('invalid_saved_prediction')
        verify_predictions([dict(category=cc, probabilities=saved['bert_probabilities'])], 1)
        a.append(ac); c.append(cc)
    return a, c


def overlap_slices(rows, parts):
    # Match normalized names or explicit group identifiers; no semantic similarity claim.
    old = {part: {key(v) for row in entries for v in (row['name'], row.get('group', row['name']))}
           for part, entries in parts.items()}
    subsets = {name: [] for name in ('all', 'train_seen', 'train_unseen', 'previously_unseen')}
    for i, row in enumerate(rows):
        identifiers = set(row.get('overlap_keys', [key(row['name']), key(row.get('group', row['name']))]))
        subsets['all'].append(i)
        subsets['train_seen' if identifiers & old['train'] else 'train_unseen'].append(i)
        if not identifiers & set.union(*old.values()):
            subsets['previously_unseen'].append(i)
    return subsets


def summarize(truth, predicted):
    if len(truth) != len(predicted) or any(type(c) is not int or c not in range(10) for c in truth + predicted):
        raise ValueError('invalid_categories')
    result = metrics(truth, predicted)
    if result is None:
        result = dict(support=0, accuracy=None, macro_f1=None, ten_class_macro_f1=None,
                      evaluated_categories=[], per_class={str(c): dict(support=0,precision=None,recall=None,f1=None) for c in range(10)},
                      confusion_matrix=[[0]*10 for _ in range(10)])
    eligible = [c for c in range(10) if result['per_class'][str(c)]['support'] >= 5]
    result['macro_f1_support_ge5'] = statistics.mean(result['per_class'][str(c)]['f1'] for c in eligible) if eligible else None
    result['macro_f1_support_ge5_categories'] = eligible
    result['low_support_categories'] = [c for c in range(10) if 0 < result['per_class'][str(c)]['support'] < 5]
    result['correct'] = sum(a == b for a, b in zip(truth, predicted))
    return result


def percentage(value):
    return 'N/A' if value is None else f'{100*value:.2f}%'


def markdown_report(report):
    counts, overlaps = report['counts'], report['overlap_counts']
    lines = ['# 三模型人工審核資料比較', '',
             f"已確認 {counts['confirmed']} 筆；原審核池 {counts['draft_total']} 筆；未納入 {counts['draft_not_in_confirmed']} 筆。", '',
             'TF-IDF 與 BERT 使用審核前保存的預測；Embedding 使用原有模型補跑，未重新訓練。', '',
             '注意：人工審核時已看到 BERT／TF-IDF 建議，這是模型輔助標註後的比較，不是盲測。排除無法辨識的品項也可能提高分數；結果只適用於此次已確認名單。', '',
             f"與舊訓練資料同名／同群組 {overlaps['train_seen']} 筆；訓練未見 {overlaps['train_unseen']} 筆；排除舊訓練、驗證及測試全部已見名稱後 {overlaps['previously_unseen']} 筆。只檢查正規化名稱及既有群組，未保證語義近似或來源完全獨立。", '',
             f"舊訓練同名標籤與此次人工答案不同：{report['training_label_conflicts']} 筆。既有模型及資料未被修改。", '',
             '混淆矩陣：列（Y 軸）為人工答案、欄（X 軸）為模型預測。對角線為答對數量。', '',
             'Macro-F1 為有真實樣本類別的 F1 平均；另外列出僅樣本數 ≥5 的類別平均。低樣本類別的逐類指標僅供描述，不代表穩定效果。', '']
    titles = {'all':'全部已確認', 'train_seen':'與舊訓練重疊', 'train_unseen':'舊訓練未見', 'previously_unseen':'舊訓練／驗證／測試皆未見'}
    for subset in titles:
        lines += [f'## {titles[subset]}（{overlaps[subset]} 筆）', '',
                  '| 模型 | 正確筆數 | Accuracy | Macro-F1 | Macro-F1（每類 ≥5 筆） |',
                  '|---|---:|---:|---:|---:|']
        for kind in ('tfidf','embedding','bert'):
            score = report['models'][kind][subset]
            lines.append(f"| {kind} | {score['correct']} | {percentage(score['accuracy'])} | {percentage(score['macro_f1'])} | {percentage(score['macro_f1_support_ge5'])} |")
        lines.append('')
    for kind in ('tfidf','embedding','bert'):
        s = report['models'][kind]['all']
        lines += [f'## {kind} 各類指標（全部已確認）', '', '| 類別 | 樣本數 | Precision | Recall | F1 |', '|---|---:|---:|---:|---:|']
        for c, label in enumerate(CATEGORIES):
            p = s['per_class'][str(c)]
            note = '（樣本不足）' if 0 < p['support'] < 5 else ''
            lines.append(f"| {c} {label}{note} | {p['support']} | {percentage(p['precision'])} | {percentage(p['recall'])} | {percentage(p['f1'])} |")
        lines += ['', '混淆矩陣計數：', '', '```text']
        lines += [' '.join(f'{n:4}' for n in row) for row in s['confusion_matrix']]
        lines += ['```', '']
    return '\n'.join(lines)


def run(args):
    out, root = args.out.resolve(), args.private_root.resolve()
    if out == root or not out.is_relative_to(root) or out.exists():
        raise ValueError('invalid_private_output')
    input_paths = [args.reviewed, args.draft_dir/'draft-items.jsonl', args.draft_dir/'provenance.json']
    hashes = [fingerprint(p) for p in input_paths]
    rows, counts = select_confirmed(read_rows(args.reviewed))
    drafts = read_rows(input_paths[1])
    predictions_a, predictions_c = align_saved(rows, drafts)
    counts.update(draft_total=len(drafts), draft_not_in_confirmed=len(drafts)-len(rows))
    parts, _, dataset_hash = load_dataset(args.dataset)
    entries = [model_identity(kind, path) for kind, path in [('tfidf',args.a),('embedding',args.b),('bert',args.c)]]
    if any(e['dataset_sha256'] != dataset_hash for e in entries):
        raise ValueError('different_model_training_data')
    provenance = json.loads(input_paths[2].read_text(encoding='utf-8'))
    if (entries[0]['files']['model.joblib'] != provenance['tfidf_sha256'] or
            entries[2]['files']['classifier-manifest.json'] != provenance['bert_manifest_sha256']):
        raise ValueError('prelabel_model_changed')
    out.mkdir(parents=True, exist_ok=False)
    frozen = dict(reviewed_sha256=hashes[0], draft_sha256=hashes[1], draft_provenance_sha256=hashes[2],
                  training_dataset_sha256=dataset_hash, model_identities=entries,
                  prediction_policy='saved TF-IDF/BERT predictions; frozen Embedding inference; no fitting')
    write_json(out/'evaluation-plan.json', frozen)
    # Keep a local copy of accepted gold and original export for reproducibility.
    (out/'reviewed-source.jsonl').write_bytes(args.reviewed.read_bytes())
    write_jsonl(out/'confirmed-items.jsonl', rows)
    predictor = load_predictor(entries[1])
    embedding_predictions = predictor.predict([r['name'] for r in rows])
    verify_predictions(embedding_predictions, len(rows))
    predictions = dict(tfidf=predictions_a, embedding=[p['category'] for p in embedding_predictions], bert=predictions_c)
    subsets = overlap_slices(rows, parts)
    results = {kind: {subset: summarize([rows[i]['category'] for i in ids], [values[i] for i in ids])
                      for subset, ids in subsets.items()} for kind, values in predictions.items()}
    train_labels = {key(r['name']): r['category'] for r in parts['train']}
    conflicts = sum(key(r['name']) in train_labels and r['category'] != train_labels[key(r['name'])] for r in rows)
    if hashes != [fingerprint(p) for p in input_paths] or load_dataset(args.dataset)[2] != dataset_hash:
        raise ValueError('evaluation_source_changed')
    if entries != [model_identity(e['kind'],e['run']) for e in entries]:
        raise ValueError('evaluation_model_changed')
    report = dict(evaluation_kind='human_reviewed_model_assisted_not_blind', categories=list(CATEGORIES), counts=counts,
                  overlap_counts={name:len(ids) for name,ids in subsets.items()},
                  training_label_conflicts=conflicts, models=results, provenance=frozen)
    write_jsonl(out/'private-predictions.jsonl', [dict(id=r['id'],name=r['name'],actual=r['category'],
        **{kind:values[i] for kind,values in predictions.items()}, subsets=[name for name,ids in subsets.items() if i in ids]) for i,r in enumerate(rows)])
    write_json(out/'report.json', report)
    (out/'comparison.md').write_text(markdown_report(report), encoding='utf-8')
    return dict(counts=counts, overlap_counts=report['overlap_counts'], training_label_conflicts=conflicts,
                models={kind:{part:{k:v for k,v in score.items() if k in ('support','correct','accuracy','macro_f1','macro_f1_support_ge5')}
                              for part,score in values.items()} for kind,values in results.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('reviewed','draft-dir','dataset','a','b','c','private-root','out'):
        parser.add_argument('--'+flag, required=True, type=Path)
    args = parser.parse_args()
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = run(args)
        print(json.dumps(result))
    except Exception:
        parser.exit(1, 'Local reviewed evaluation failed; private inputs and errors were not printed.\n')

if __name__ == '__main__': main()
