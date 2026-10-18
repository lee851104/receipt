"""Rebuild the public synthetic cache from preserved predictions and explicit review.

No model calls and no real data. Human confirmation applies only to the exact approved attribute values.
Run: python -m scripts.review_synthetic_cache
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'datasets/synthetic'


def read(name):
    return [json.loads(line) for line in (DATA / name).read_text(encoding='utf-8').splitlines()]


def review_metadata(row, corrected):
    """Preserve explicit user approval; edited values require renewed review."""
    confirmation = row.get('confirmation') or {}
    digest = hashlib.sha256(json.dumps(row['attributes'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    confirmed = (confirmation.get('confirmed_by') == 'user' and bool(confirmation.get('date'))
                 and bool(confirmation.get('source')) and confirmation.get('attributes_sha256') == digest)
    return {'reviewer': 'assistant', 'human_confirmed': confirmed,
            'review_status': ('human_corrected' if corrected else 'human_confirmed') if confirmed
                             else ('assistant_corrected' if corrected else 'assistant_reviewed'),
            **({'confirmation': dict(confirmation)} if confirmation else {})}


def main():
    old = {r['name']: r for r in read('attribute-cache.model-v1.jsonl')}
    new = {r['name']: r for r in read('attribute-cache.model-v2.jsonl')}
    review = read('attribute-review.jsonl')
    assert set(old) == set(new) == {r['name'] for r in review} and len(review) == 107
    result = []
    for row in review:
        name = row['name']
        corrections = {key: {'model': new[name]['attributes'][key], 'reviewed': value,
                             'reason': row['review_basis']}
                       for key, value in row['attributes'].items() if value != new[name]['attributes'][key]}
        result.append({'name': name, 'source': 'synthetic', 'model_version': new[name]['model_version'],
                       'original_model_version': old[name]['model_version'],
                       'original_model_attributes': old[name]['attributes'], 'model_attributes': new[name]['attributes'],
                       'attributes': row['attributes'], 'corrections': corrections,
                       **review_metadata(row, corrected=bool(corrections)), 'review_date': '2026-10-15',
                       'cache_revision': 'synthetic-review-20261015-v2'})
    (DATA / 'attribute-cache.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in result), encoding='utf-8')
    old_diffs = [sum(r['original_model_attributes'][k] != v for k, v in r['attributes'].items()) for r in result]
    changed = sum(bool(r['corrections']) for r in result)
    fields = sum(len(r['corrections']) for r in result)
    stats = {'items_reviewed': len(result), 'old_model_differing_items': sum(n > 0 for n in old_diffs),
             'old_model_differing_fields': sum(old_diffs), 'new_model_differing_items': changed,
             'new_model_differing_fields': fields, 'human_confirmed': sum(r['human_confirmed'] for r in result),
             'model_version': result[0]['model_version']}
    (ROOT / 'docs/results/synthetic-cache-review.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 假品名屬性逐筆複核', '', f"2026-10-15；107 筆全部為公開假品名。以下由助理逐欄複核，使用者已檢查並確認 {stats['human_confirmed']} 筆。確認來源為使用者對 commit 0e98b71 檢查表的核准，逐筆綁定屬性內容雜湊。這是合成集參考答案，不是私人真人發票的盲標成績。", '',
             f"舊模型與此複核有 {stats['old_model_differing_items']} 筆／{sum(old_diffs)} 欄差異；新版實際重跑後仍有 {changed} 筆／{fields} 欄差異。有效快取採下表修正，原模型與新模型輸出都獨立保留。", '',
             '## 原因對照', '',
             '同一個 4B GGUF、temperature=0、seed=42、quantity=1，重跑全部 107 筆。指定 15 個錯誤：原批次 3 筆／有前綴／空店家為 15；移除前綴 10；只補店家 13；兩者合用 10；單筆保留前綴 7；單筆去前綴 7；單筆去前綴＋新版 prompt 5。', '',
             '因此前綴、批次與 prompt 都會影響輸出，空白店家不是唯一原因。新版改成單筆、只移除開頭的「示範」、補充多標籤定義；保留原品名作快取鍵，merchant 仍空白。未加入按這 107 個名字查答案的規則。小模型仍會漏標與誤判，逐筆修正必須和模型品質分開計算。', '',
             '新版相較「單筆去前綴／舊 prompt」，指定錯誤 7→5、與助理複核不同的品項 47→46，但不同欄位 60→63；不宣稱全面改善。對照實驗見 [attribute-input-experiment.json](../../datasets/synthetic/attribute-input-experiment.json)。', '',
             '診斷實驗新版為 46 筆／63 欄差異；正式介面獨立重跑為 46 筆／70 欄、指定錯誤 4 個。相同 prompt 與 seed 仍有 7 筆／15 欄輸出不同，故這裡採正式重跑的實存輸出，不宣稱 GPU 推論逐次完全一致；離線配對則由固定快取重現。', '',
             '## 可核對的資料', '',
             '- [原版模型輸出](../../datasets/synthetic/attribute-cache.model-v1.jsonl)',
             '- [新版實際模型輸出](../../datasets/synthetic/attribute-cache.model-v2.jsonl)',
             '- [逐筆 23 欄複核](../../datasets/synthetic/attribute-review.jsonl)',
             '- [有效快取與每欄差異](../../datasets/synthetic/attribute-cache.jsonl)', '',
             f"model_version：`{stats['model_version']}`。每筆有 original_model_attributes、model_attributes、corrections；目前 review_status 為 {', '.join(sorted({r['review_status'] for r in result}))}；人工確認 {stats['human_confirmed']} 筆，原始準備者 reviewer=assistant、確認者 confirmation.confirmed_by=user 分開保留。重建會保留確認；若屬性改變，舊確認自動失效。", '',
             '## 107 筆檢查表', '',
             '「成立屬性」列出 true 與有值的三個列舉欄位；未列布林為 false，未列 sugar/fun/species 為 null。「修正欄位」是相對新版模型的差異。', '',
             '| # | 假品名 | 成立屬性 | 修正欄位 |', '|---:|---|---|---|']
    for index, row in enumerate(result, 1):
        positive = ', '.join(key if value is True else f'{key}={value}' for key, value in row['attributes'].items() if value is not False and value is not None)
        diff = ', '.join(f"{key}: {json.dumps(d['model'],ensure_ascii=False)} → {json.dumps(d['reviewed'],ensure_ascii=False)}" for key,d in row['corrections'].items())
        lines.append(f"| {index} | {row['name']} | {positive or '無'} | {diff or '無'} |")
    lines += ['', '重建有效快取及此表：`python -m scripts.review_synthetic_cache`。重建只讀公開的模型輸出與逐筆複核，不重新推論、不讀取真人品名。']
    (ROOT / 'docs/results/synthetic-cache-review.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
