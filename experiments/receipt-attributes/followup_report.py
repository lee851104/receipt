"""Recompute all four metrics from complete, matching-source experiment outputs."""
import csv
import hashlib
import json
from metrics import score, ENUMS
from run_models import ROOT
from run_followup import synthetic
from bulk_rule import apply_bulk_rule
from sugar_guard import apply_sugar_guard


def checked_score(result, reference, source_hash, prompt_hash):
    ids = {r['id'] for r in reference}
    if result['source_sha256'] != source_hash or result['prompt_sha256'] != prompt_hash:
        raise ValueError('Source or prompt mismatch')
    requested = result['requested_ids']
    if len(requested) != len(ids) or set(requested) != ids:
        raise ValueError('Partial request cannot be compared to full benchmark')
    predicted = [p['id'] for p in result['predictions']]
    failed = [key for failure in result['failures'] for key in failure['ids']]
    if len(predicted + failed) != len(ids) or set(predicted + failed) != ids:
        raise ValueError('Run incomplete or duplicate coverage')
    report = score(reference, result['predictions'])
    report.update(elapsed_seconds=result['elapsed_seconds'], failed_batches=len(result['failures']),
                  source_sha256=source_hash, prompt_sha256=prompt_hash)
    return report


def main():
    data = synthetic()
    real = json.loads((ROOT/'private/draft-reference.json').read_text(encoding='utf-8'))
    real_data = json.loads((ROOT/'private/prepared.json').read_text(encoding='utf-8'))
    if real_data['source_sha256'] != real['source_sha256']:
        raise ValueError('Real data/reference source mismatch')
    prompt_hash = hashlib.sha256((ROOT/'prompt-named-v2.txt').read_text(encoding='utf-8').encode()).hexdigest()
    reports = {}
    for name in ('0.5b','1.5b','3b','qwen3-4b'):
        reports[name] = {}
        for split in ('synthetic','real'):
            folder = ROOT/'results/followup'/split/name
            if split == 'real' and name != 'qwen3-4b':
                folder = ROOT/'results'/name
            result = json.loads((folder/'predictions.json').read_text(encoding='utf-8'))
            ref = data['reference'] if split == 'synthetic' else real['items']
            source_hash = data['source_sha256'] if split == 'synthetic' else real['source_sha256']
            report = checked_score(result, ref, source_hash, prompt_hash)
            if split == 'real':
                auxiliary = score([{'id':x['id'], 'attributes':x['basic']} for x in ref],
                                  [{'id':x['id'], 'attributes':x['basic']} for x in result['predictions']])
                report['basic_auxiliary'] = {k:v for k,v in auxiliary.items() if k not in ('exact_items','differences')}
            combined = apply_bulk_rule(data['items'] if split == 'synthetic' else real_data['items'], result['predictions'])
            hybrid = checked_score({**result, 'predictions':combined['predictions']}, ref, source_hash, prompt_hash)
            hybrid['overrides'] = combined['overrides']
            report['with_bulk_rule'] = hybrid
            (folder/'with-bulk-rule.json').write_text(json.dumps(combined,ensure_ascii=False,indent=2),encoding='utf-8')
            guarded = apply_sugar_guard(data['items'] if split == 'synthetic' else real_data['items'], combined['predictions'])
            guarded['overrides'] = combined['overrides'] + guarded['overrides']
            system = checked_score({**result, 'predictions':guarded['predictions']}, ref, source_hash, prompt_hash)
            system['overrides'] = guarded['overrides']
            system['evaluation_status'] = 'POST_HOC_DEVELOPMENT_REPLAY_NOT_INDEPENDENT_HOLDOUT'
            report['with_policy_guards'] = system
            (folder/'with-policy-guards.json').write_text(json.dumps(guarded,ensure_ascii=False,indent=2),encoding='utf-8')
            reports[name][split] = report
            (folder/'four-metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(name, split, json.dumps({k:v for k,v in report.items() if k in ('accuracy','micro','macro_f1_supported','exact_items','failed_batches')}))
    destination = ROOT/'results/followup'
    (destination/'comparison.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    baselines = {}
    for split, ref in [('synthetic',data['reference']), ('real',real['items'])]:
        negatives = [{'id':r['id'], 'attributes':{f:None if f in ENUMS else False for f in r['attributes']}} for r in ref]
        baselines[split] = score(ref, negatives)
    (destination/'baselines.json').write_text(json.dumps(baselines,ensure_ascii=False,indent=2),encoding='utf-8')
    with (destination/'metrics.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['model','split','accuracy','precision_micro','recall_micro','f1_micro','f1_macro_supported','exact_items','items','failed_batches'])
        for name, splits in reports.items():
            for split,r in splits.items():
                writer.writerow([name,split,r['accuracy'],r['micro']['precision'],r['micro']['recall'],r['micro']['f1'],r['macro_f1_supported'],r['exact_items'],r['items'],r['failed_batches']])
                h = r['with_bulk_rule']
                writer.writerow([name+'+bulk-rule',split,h['accuracy'],h['micro']['precision'],h['micro']['recall'],h['micro']['f1'],h['macro_f1_supported'],h['exact_items'],h['items'],h['failed_batches']])
                g=r['with_policy_guards']
                writer.writerow([name+'+policy-guards',split,g['accuracy'],g['micro']['precision'],g['micro']['recall'],g['micro']['f1'],g['macro_f1_supported'],g['exact_items'],g['items'],g['failed_batches']])


if __name__ == '__main__':
    main()
