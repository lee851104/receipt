"""Select by validation, freeze, then compare parent and continuation on test once."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import io
import json
import math
from pathlib import Path

from bert_continuation import load
from bert_model import Classifier
from common import fingerprint
from compare_fixed_models import model_identity
from evaluate_reviewed import summarize,percentage
from fixed_split_train import verify_predictions
from prepare_data import write_json,write_jsonl,CATEGORIES


def choose(reports):
    if len(reports)!=3 or {r['seed'] for r in reports}!={42,43,44}:
        raise ValueError('expected_three_distinct_predeclared_seeds')
    if any(not math.isfinite(r['best_validation_loss']) for r in reports):raise ValueError('invalid_validation_loss')
    return min(reports,key=lambda r:(r['best_validation_loss'],r['seed']))['seed']


def claim(dataset,plan,identity):
    if load(dataset)[2]!=identity:raise ValueError('dataset_changed_before_claim')
    if json.loads(Path(plan).read_text(encoding='utf-8'))['dataset_sha256']!=identity:raise ValueError('plan_dataset_mismatch')
    with (Path(dataset)/'test-evaluation-claimed.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(dataset_sha256=identity,plan_sha256=fingerprint(Path(plan)),policy='one final comparison; never delete to retry'),stream)


def run(dataset,parent_run,candidates,out):
    dataset,parent_run,out=map(lambda p:Path(p).resolve(),(dataset,parent_run,out))
    if out.exists() or (dataset/'test-evaluation-claimed.json').exists():raise FileExistsError('evaluation_already_exists')
    protected=[dataset,parent_run,*[Path(p).resolve() for p in candidates]]
    if any(out.is_relative_to(p) for p in protected):raise ValueError('unsafe_output')
    parts,manifest,identity=load(dataset)
    if not parts['test']:raise ValueError('empty_test')
    parent=model_identity('bert',parent_run)
    if parent['files']['classifier-manifest.json']!=manifest['parent_classifier_manifest_sha256'] or parent['dataset_sha256']!=manifest['parent_dataset_sha256']:
        raise ValueError('wrong_parent')
    entries=[model_identity('bert',p) for p in candidates]
    if any(e['dataset_sha256']!=identity for e in entries):raise ValueError('candidate_dataset_mismatch')
    reports=[json.loads((Path(e['run'])/'report.json').read_text(encoding='utf-8')) for e in entries]
    if any(r['settings']['initialization']!='verified_classifier_warm_start' or r['test_evaluation']!='not_run' for r in reports):
        raise ValueError('invalid_continuation_run')
    configurations=[{k:v for k,v in r['settings'].items() if k!='seed'} for r in reports]
    if configurations[1:]!=configurations[:-1] or any(r['pretrained']!=reports[0]['pretrained'] for r in reports):
        raise ValueError('candidate_configuration_mismatch')
    if reports[0]['pretrained']['files']!={k:v for k,v in parent['files'].items() if k!='classifier-manifest.json'}:
        raise ValueError('candidate_parent_mismatch')
    selected_seed=choose(reports)
    selected=next(e for e in entries if e['seed']==selected_seed)
    selected_report=next(r for r in reports if r['seed']==selected_seed)
    out.mkdir(parents=True,exist_ok=False)
    plan=dict(dataset_sha256=identity,group_audit_sha256=fingerprint(dataset/'group-audit.json'),parent=parent,candidates=entries,selected_seed=selected_seed,
              selected=selected,selection='minimum_validation_loss_then_seed; test not used')
    plan_path=out/'evaluation-plan.json';write_json(plan_path,plan)
    claim(dataset,plan_path,identity)
    plan_hash=fingerprint(plan_path)
    results={};predictions={}
    test=parts['test'];names=[r['name'] for r in test]
    for title,entry in (('before',parent),('after',selected)):
        model=Classifier.load(Path(entry['run'])/'model')
        predictions[title]=model.predict(names)
        verify_predictions(predictions[title],len(test))
        results[title]=summarize([r['category'] for r in test],[p['category'] for p in predictions[title]])
        del model
    if load(dataset)[2]!=identity or fingerprint(plan_path)!=plan_hash or fingerprint(dataset/'group-audit.json')!=plan['group_audit_sha256']:raise ValueError('frozen_inputs_changed')
    if parent!=model_identity('bert',parent_run) or entries!=[model_identity('bert',e['run']) for e in entries]:
        raise ValueError('frozen_models_changed')
    paired=dict(improved=0,worsened=0,both_correct=0,both_wrong=0)
    for row,a,b in zip(test,predictions['before'],predictions['after']):
        ac,bc=a['category']==row['category'],b['category']==row['category']
        paired['both_correct' if ac and bc else 'both_wrong' if not ac and not bc else 'improved' if bc else 'worsened']+=1
    report=dict(evaluation_kind=manifest['evaluation_status'],categories=list(CATEGORIES),test_count=len(test),
                selected_seed=selected_seed,selected_epoch=selected_report['best_epoch'],
                validation_candidates=[dict(seed=r['seed'],best_epoch=r['best_epoch'],loss=r['best_validation_loss'],accuracy=r['validation']['model']['accuracy']) for r in reports],
                results=results,paired=paired,accuracy_delta_pp=100*(results['after']['accuracy']-results['before']['accuracy']),
                dataset_summary=manifest['summary'],provenance=plan)
    write_json(out/'report.json',report)
    write_jsonl(out/'private-test-predictions.jsonl',[dict(id=r['id'],name=r['name'],actual=r['category'],before=a['category'],after=b['category']) for r,a,b in zip(test,predictions['before'],predictions['after'])])
    absent=[CATEGORIES[c] for c in range(10) if results['before']['per_class'][str(c)]['support']==0]
    absent_text='、'.join(absent) if absent else '無'
    lines=['# BERT 續訓保留集比較','',f"測試集 {len(test)} 筆；以 validation loss 選定 seed {selected_seed}、epoch {selected_report['best_epoch']}。",'',
           '| 模型 | 正確筆數 | Accuracy | Macro-F1（有樣本類別） | Macro-F1（每類 ≥5） |','|---|---:|---:|---:|---:|']
    for name,title in (('before','續訓前'),('after','驗證集選定候選')):
        s=results[name];lines.append(f"| {title} | {s['correct']}/{s['support']} | {percentage(s['accuracy'])} | {percentage(s['macro_f1'])} | {percentage(s['macro_f1_support_ge5'])} |")
    lines+=['',f"正確率差異 {report['accuracy_delta_pp']:+.2f} 個百分點；改善 {paired['improved']} 筆、退步 {paired['worsened']} 筆。",'',
            '此保留集沒有參與本輪梯度、早停、選種子或設定調整；但來源已參與上輪模型比較，且人工標註看過模型建議，不能稱為全新獨立盲測。',
            f'本測試集沒有樣本的類別：{absent_text}；其他低樣本類別不代表穩定表現。每多答對一筆就相差 {100/len(test):.2f} 個百分點。',
            'epoch 0 代表原有權重：若續訓未降低 validation loss，保留原模型；未將測試結果回饋調參。模型未部署，舊權重、舊切分保持不變。','']
    for name in ('before','after'):
        lines += [f'## {name} 混淆矩陣','列為人工答案、欄為模型預測；類別順序 0–9。','```text']
        lines += [' '.join(f'{v:3}' for v in row) for row in results[name]['confusion_matrix']]
        lines += ['```','']
    (out/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
    return {k:report[k] for k in ('evaluation_kind','test_count','selected_seed','selected_epoch','validation_candidates','results','paired','accuracy_delta_pp')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('dataset','parent-run','out','private-root'):parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--candidate',type=Path,action='append',required=True)
    args=parser.parse_args()
    try:
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            if args.out.resolve()==args.private_root.resolve() or not args.out.resolve().is_relative_to(args.private_root.resolve()):raise ValueError('invalid_private_output')
            report=run(args.dataset,args.parent_run,args.candidate,args.out)
        print(json.dumps(report))
    except Exception:parser.exit(1,'Frozen continuation test failed; preserve its claim and private output for local investigation.\n')

if __name__=='__main__':main()
