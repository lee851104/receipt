"""Freeze A/B/three BERT seeds, then score one shared test set exactly once."""
import argparse
from collections import Counter
from contextlib import redirect_stdout,redirect_stderr
import gc
import io
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

from common import environment,fingerprint,peak_rss_bytes
from fixed_split_data import load_dataset,score
from fixed_split_train import verify_predictions
from prepare_data import write_json,write_jsonl


def aggregate_bert(results):
    if len(results)!=3 or len({r['seed'] for r in results})!=3:raise ValueError('three_distinct_seeds_required')
    summary={}
    for metric in ('accuracy','macro_f1'):
        values=[r['metrics'][metric] for r in results]
        summary[metric+'_mean']=statistics.mean(values) if all(v is not None for v in values) else None
        summary[metric+'_std']=statistics.pstdev(values) if all(v is not None for v in values) else None
    return summary


def claim_test(dataset,identity,models,plan_sha256=None):
    dataset=Path(dataset)
    if load_dataset(dataset)[2]!=identity:raise ValueError('dataset_changed_before_claim')
    marker=dataset/'test-evaluation-claimed.json'
    with marker.open('x',encoding='utf-8') as stream:
        json.dump(dict(manifest_sha256=identity,models=models,plan_sha256=plan_sha256,policy='one final evaluation; do not delete to rerun'),stream)
    return marker


def model_identity(kind,run):
    run=Path(run)
    report=json.loads((run/'report.json').read_text(encoding='utf-8'))
    if report['model']!=kind or not report['reload_verified']:raise ValueError('unverified_training_run')
    if kind=='bert':
        from bert_model import verified_manifest
        metadata=verified_manifest(run/'model')
        if metadata['dataset_sha256']!=report['dataset']['manifest_sha256'] or metadata['seed']!=report['seed'] or metadata['best_epoch']!=report['best_epoch']:
            raise ValueError('classifier_report_mismatch')
        files={**metadata['files'],'classifier-manifest.json':fingerprint(run/'model/classifier-manifest.json')}
    else:files={'model.joblib':fingerprint(run/'model.joblib')}
    return dict(kind=kind,run=str(run.resolve()),seed=report.get('seed'),files=files,report_sha256=fingerprint(run/'report.json'),dataset_sha256=report['dataset']['manifest_sha256'])


def load_predictor(entry):
    kind,run=entry['kind'],Path(entry['run'])
    if kind=='bert':
        from bert_model import Classifier
        model=Classifier.load(run/'model')
        identity=model.metadata['dataset_sha256']
    else:
        if kind=='tfidf':from tfidf_lr import Classifier
        else:from embedding_lr import Classifier
        model=Classifier.load(run/'model.joblib')
        identity=model.bundle['dataset_sha256']
    if identity!=entry['dataset_sha256']:raise ValueError('model_dataset_mismatch')
    return model


def evaluate_worker(plan_path,index):
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    if type(index) is not int or not 0<=index<len(plan['models']):raise ValueError('invalid_worker_index')
    entry=plan['models'][index]
    parts,_,identity=load_dataset(plan['dataset'])
    if identity!=plan['manifest_sha256'] or model_identity(entry['kind'],entry['run'])!=entry:raise ValueError('frozen_input_changed')
    claim=json.loads((Path(plan['dataset'])/'test-evaluation-claimed.json').read_text(encoding='utf-8'))
    if (claim['manifest_sha256']!=identity or claim['models']!=plan['models']
            or claim.get('plan_sha256')!=fingerprint(plan_path)):raise ValueError('claim_mismatch')
    claims=Path(plan['dataset'])/'test-evaluation-model-claims'
    claims.mkdir(exist_ok=True)
    with (claims/f'{index}.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(plan_sha256=claim['plan_sha256'],index=index),stream)
    output=Path(plan['out'])/str(index)
    output.mkdir(exist_ok=False)
    # The fixed dataset claim survives output relocation or an interrupted worker.
    started=time.perf_counter();predictor=load_predictor(entry)
    load_seconds=time.perf_counter()-started
    rows=parts['test']
    predictions=predictor.predict([r['name'] for r in rows])
    verify_predictions(predictions,len(rows))
    metrics=score([r['category'] for r in rows],[p['category'] for p in predictions])
    benchmark=[parts['train'][i%len(parts['train'])]['name'] for i in range(1000)]
    predictor.predict(benchmark[:10])
    started=time.perf_counter();predictor.predict(benchmark)
    inference_seconds=time.perf_counter()-started
    if model_identity(entry['kind'],entry['run'])!=entry or load_dataset(plan['dataset'])[2]!=identity:raise ValueError('frozen_input_changed')
    report=json.loads((Path(entry['run'])/'report.json').read_text(encoding='utf-8'))
    result=dict(kind=entry['kind'],seed=entry['seed'],metrics=metrics,
                cost=dict(load_seconds=load_seconds,inference_seconds=inference_seconds,benchmark_count=1000,
                          model_bytes=report['cost']['model_bytes'],peak_process_rss_bytes=peak_rss_bytes()),
                model_identity=entry,environment=environment())
    write_jsonl(output/'test-predictions.jsonl',[dict(id=r['id'],name=r['name'],actual=r['category'],predicted=p['category'],probabilities=p['probabilities']) for r,p in zip(rows,predictions)])
    write_json(output/'report.json',result)
    return result


def run(dataset,a_run,b_run,bert_runs,out):
    dataset,out=Path(dataset).resolve(),Path(out).resolve()
    if out.exists():raise FileExistsError('output_exists')
    if len(bert_runs)!=3:raise ValueError('three_bert_runs_required')
    protected=[dataset,Path(a_run).resolve(),Path(b_run).resolve(),*[Path(p).resolve() for p in bert_runs]]
    if any(out.is_relative_to(p) for p in protected):raise ValueError('unsafe_output')
    parts,manifest,identity=load_dataset(dataset)
    if not parts['test']:raise ValueError('empty_test')
    entries=[model_identity(k,p) for k,p in [('tfidf',a_run),('embedding',b_run),*[('bert',p) for p in bert_runs]]]
    if any(e['dataset_sha256']!=identity for e in entries):raise ValueError('different_dataset')
    if len({e['seed'] for e in entries[2:]})!=3:raise ValueError('duplicate_bert_seed')
    bert_reports=[json.loads((Path(e['run'])/'report.json').read_text(encoding='utf-8')) for e in entries[2:]]
    if len({json.dumps(r['pretrained'],sort_keys=True) for r in bert_reports})!=1:raise ValueError('different_pretrained')
    configs=[{k:v for k,v in r['settings'].items() if k!='seed'} for r in bert_reports]
    if configs[1:]!=configs[:-1]:raise ValueError('different_bert_settings')
    # Validate actual bundles and compatibility before spending the one-time test claim.
    for entry in entries:
        predictor=load_predictor(entry)
        verify_predictions(predictor.predict([parts['train'][0]['name']]),1)
        del predictor;gc.collect()
    selected=min(bert_reports,key=lambda r:(r['best_validation_loss'],r['seed']))['seed']
    out.mkdir(parents=True,exist_ok=False)
    plan=dict(dataset=str(dataset),out=str(out),manifest_sha256=identity,models=entries,selected_bert_seed=selected)
    plan_path=out/'evaluation-plan.json'
    write_json(plan_path,plan)
    claim_test(dataset,identity,entries,fingerprint(plan_path))
    results=[]
    for index in range(len(entries)):
        process=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(plan_path),'--index',str(index)],capture_output=True,text=True)
        if process.returncode:raise RuntimeError('test_worker_failed_claim_retained')
        results.append(json.loads((out/str(index)/'report.json').read_text(encoding='utf-8')))
    labels=Counter(r['category'] for r in parts['train'])
    majority=min(labels,key=lambda c:(-labels[c],c))
    summary=dict(evaluation_kind='one_time_development_holdout_not_independent',
                 dataset_sha256=identity,test_count=len(parts['test']),selected_bert_seed=selected,
                 selection_rule='minimum_validation_loss_before_test',models=results,
                 bert_summary=aggregate_bert(results[2:]),
                 baseline=score([r['category'] for r in parts['test']],[majority]*len(parts['test'])))
    if load_dataset(dataset)[2]!=identity:raise ValueError('dataset_changed_after_test')
    write_json(out/'report.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path)
    parser.add_argument('--a',type=Path)
    parser.add_argument('--b',type=Path)
    parser.add_argument('--bert',type=Path,action='append')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--index',type=int)
    args=parser.parse_args()
    try:
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            result=evaluate_worker(args.worker,args.index) if args.worker else run(args.dataset,args.a,args.b,args.bert,args.out)
        print(json.dumps(result,ensure_ascii=True))
    except Exception:
        parser.exit(1,'Comparison failed; verify frozen local inputs and one-time evaluation state. Do not delete the test claim to retry.\n')

if __name__=='__main__':main()
