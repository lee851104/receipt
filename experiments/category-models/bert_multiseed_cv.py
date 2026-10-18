"""Fixed grouped folds crossed with common initialization seeds; test stays sealed."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import io,json,statistics
from pathlib import Path
import bert_ratio_cv as cv
from bert_model import verified_manifest
from common import fingerprint
from dataset_split import grouped,read_rows
from embedding_features import local_manifest
from evaluate_reviewed import summarize
from prepare_data import CATEGORIES,write_json

REGIMES=('synthetic_25','synthetic_current')
SEEDS=(42,43,44)

def prepare(parent,out):
    parent,out=Path(parent).resolve(),Path(out).resolve()
    if out.exists():raise FileExistsError('output_exists')
    if out.is_relative_to(parent) or parent.is_relative_to(out):raise ValueError('unsafe_output')
    for f in range(5):
        for regime in REGIMES:_,plan=cv.load_fold(parent,f,regime)
    config=json.loads((parent/'training-config.json').read_text(encoding='utf-8'))
    ph=fingerprint(parent/'plan.json')
    if config['plan_sha256']!=ph:raise ValueError('parent_config_mismatch')
    real,_,_,_=cv.read_development(plan['source'])
    groups=grouped(real)
    protocol=dict(schema='bert-multiseed-cv-1',parent=str(parent),parent_plan_sha256=ph,
        parent_config_sha256=fingerprint(parent/'training-config.json'),training_config=config,
        seeds=list(SEEDS),regimes=list(REGIMES),folds=5,expected_runs=30,unique_real_items=len(real),
        groups=dict(count=len(groups),multi_item=sum(len(r)>1 for _,r in groups),maximum_size=max(len(r) for _,r in groups)),
        original_test='never_open_hash_copy_or_evaluate')
    out.mkdir(parents=True,exist_ok=False);write_json(out/'protocol.json',protocol);load(out)
    return protocol

def load(root):
    root=Path(root).resolve();raw=(root/'protocol.json').read_bytes();p=json.loads(raw)
    if (p['schema']!='bert-multiseed-cv-1' or p['seeds']!=list(SEEDS) or
        p['regimes']!=list(REGIMES) or p['folds']!=5 or p['expected_runs']!=30 or
        p['original_test']!='never_open_hash_copy_or_evaluate'):
        raise ValueError('invalid_protocol')
    parent=Path(p['parent']).resolve()
    if root.is_relative_to(parent) or parent.is_relative_to(root):raise ValueError('unsafe_output')
    if (fingerprint(parent/'plan.json')!=p['parent_plan_sha256'] or
        fingerprint(parent/'training-config.json')!=p['parent_config_sha256'] or
        json.loads((parent/'training-config.json').read_text(encoding='utf-8'))!=p['training_config']):
        raise ValueError('parent_changed')
    epochs=p['training_config']['epochs']
    if type(epochs) is not int or not 1<=epochs<=10:raise ValueError('invalid_epoch_cap')
    expected=dict(lr=2e-5,batch_size=16,max_length=32,weight_decay=.01,patience=2,min_delta=1e-4,initialization='public_encoder',plan_sha256=p['parent_plan_sha256'])
    if any(p['training_config'][k]!=v for k,v in expected.items()):raise ValueError('unexpected_recipe')
    if (root/'protocol.json').read_bytes()!=raw:raise ValueError('protocol_changed')
    return p

def train(root,pretrained,fold,regime,seed,progress=None):
    root=Path(root).resolve();p=load(root);ph=fingerprint(root/'protocol.json')
    if type(seed) is not int or seed not in p['seeds'] or regime not in REGIMES:
        raise ValueError('invalid_run_selection')
    if local_manifest(pretrained)!=p['training_config']['encoder']:raise ValueError('encoder_mismatch')
    r=cv.train_fold(p['parent'],pretrained,fold,regime,device=p['training_config']['device'],
        epochs=p['training_config']['epochs'],seed=seed,output_root=root/f'seed-{seed}',progress=progress)
    load(root)
    if fingerprint(root/'protocol.json')!=ph:raise ValueError('protocol_changed')
    return r

def summarize_runs(root):
    root=Path(root).resolve();p=load(root);ph=fingerprint(root/'protocol.json')
    results={};all_oof={};completed=0
    for regime in REGIMES:
        seed_results={};matrix=[];seconds=0;steps=0
        for seed in p['seeds']:
            sr=root/f'seed-{seed}';cfgpath=sr/'training-config.json'
            if not cfgpath.exists():raise ValueError('incomplete_runs')
            cfg=json.loads(cfgpath.read_text(encoding='utf-8'))
            if cfg!=dict(p['training_config'],initialization_seed=seed):raise ValueError('config_changed')
            ch=fingerprint(cfgpath);oof=[];reports=[]
            for fold in range(5):
                parts,plan=cv.load_fold(p['parent'],fold,regime)
                run=sr/'runs'/f'{regime}-fold-{fold}';rp=run/'report.json'
                if not rp.exists():raise ValueError('incomplete_runs')
                r=json.loads(rp.read_text(encoding='utf-8'))
                if (r['seed']!=seed or r['fold']!=fold or r['regime']!=regime or
                    r['plan_sha256']!=p['parent_plan_sha256'] or r['config_sha256']!=ch or
                    r['original_test']!='not_opened_or_evaluated' or
                    r['training_counts']!=plan['folds'][fold]['counts'][regime]):
                    raise ValueError('run_identity_mismatch')
                if fingerprint(run/'private-outer-predictions.jsonl')!=r['predictions_sha256']:
                    raise ValueError('predictions_changed')
                if fingerprint(run/'model/classifier-manifest.json')!=r['model_manifest_sha256']:
                    raise ValueError('model_changed')
                meta=verified_manifest(run/'model')
                if (meta['seed']!=seed or meta['cv_fold']!=fold or meta['cv_regime']!=regime or
                    meta['dataset_sha256']!=p['parent_plan_sha256'] or meta['pretrained']!=cfg['encoder']):
                    raise ValueError('model_identity_mismatch')
                preds=read_rows(run/'private-outer-predictions.jsonl')
                if [(r['id'],r['actual']) for r in preds]!=[(r['id'],r['category']) for r in parts['outer']]:
                    raise ValueError('outer_alignment_mismatch')
                if summarize([r['actual'] for r in preds],[r['predicted'] for r in preds])!=r['outer']:
                    raise ValueError('score_mismatch')
                oof.extend(preds);reports.append(r);completed+=1
            if len(oof)!=p['unique_real_items'] or len({r['id'] for r in oof})!=len(oof):
                raise ValueError('oof_coverage_mismatch')
            acc=[r['outer']['accuracy'] for r in reports];matrix.append(acc)
            seed_results[str(seed)]=dict(fold_accuracy=acc,fold_sample_sd=statistics.stdev(acc),
                mean_accuracy=statistics.mean(acc),pooled=summarize([r['actual'] for r in oof],[r['predicted'] for r in oof]),
                best_epochs=[r['best_epoch'] for r in reports],gradient_steps=sum(r['gradient_steps'] for r in reports))
            all_oof[regime,seed]={r['id']:r for r in oof}
            seconds+=sum(r['training_seconds'] for r in reports);steps+=sum(r['gradient_steps'] for r in reports)
        means=[r['mean_accuracy'] for r in seed_results.values()]
        fold_sds=[statistics.stdev(values) for values in zip(*matrix)]
        results[regime]=dict(seed_results=seed_results,mean_accuracy=statistics.mean(means),
            seed_mean_sd=statistics.stdev(means),fold_seed_sd=fold_sds,mean_fold_seed_sd=statistics.mean(fold_sds),
            training_seconds=seconds,gradient_steps=steps)
    paired=[];deltas=[]
    for seed in p['seeds']:
        a,b=all_oof['synthetic_25',seed],all_oof['synthetic_current',seed]
        if a.keys()!=b.keys() or any(a[k]['actual']!=b[k]['actual'] for k in a):raise ValueError('pair_mismatch')
        delta=[100*(x-y) for x,y in zip(results['synthetic_25']['seed_results'][str(seed)]['fold_accuracy'],results['synthetic_current']['seed_results'][str(seed)]['fold_accuracy'])]
        deltas.extend(delta)
        paired.append(dict(seed=seed,delta_pp=statistics.mean(delta),fold_delta_pp=delta,
            improved_25=sum(a[k]['predicted']==a[k]['actual'] and b[k]['predicted']!=b[k]['actual'] for k in a),
            worsened_25=sum(a[k]['predicted']!=a[k]['actual'] and b[k]['predicted']==b[k]['actual'] for k in a)))
    if completed!=p['expected_runs']:raise ValueError('incomplete_runs')
    load(root)
    if fingerprint(root/'protocol.json')!=ph:raise ValueError('protocol_changed')
    result=dict(categories=list(CATEGORIES),unique_real_items=p['unique_real_items'],groups=p['groups'],
        seeds=p['seeds'],completed_runs=completed,results=results,
        paired=dict(per_seed=paired,mean_delta_pp=statistics.mean(deltas),wins_25=sum(d>1e-10 for d in deltas),ties=sum(abs(d)<=1e-10 for d in deltas),losses_25=sum(d < -1e-10 for d in deltas)),
        protocol_sha256=ph,original_test='not_opened_or_evaluated',
        limitations=['Same real items repeated across seeds; no increased independent sample size.',
            'Fixed folds; seed variation estimated conditional on this split and synthetic subset.',
            'Not independent test accuracy; no consumer or semantic-family grouping guarantee.',
            'Equal epoch cap and stopping rule, unequal optimizer steps and real-item exposures.'])
    with (root/'summary.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','train','summarize'])
    for name in ('parent','out','experiment','pretrained','private-root'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--fold',type=int);parser.add_argument('--seed',type=int);parser.add_argument('--regime',choices=REGIMES)
    args=parser.parse_args();console=__import__('sys').stdout
    try:
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            dest=(args.out if args.command=='prepare' else args.experiment).resolve()
            if dest==args.private_root.resolve() or not dest.is_relative_to(args.private_root.resolve()):raise ValueError('unsafe_private_output')
            if args.command=='prepare':r=prepare(args.parent,args.out)
            elif args.command=='train':r=train(dest,args.pretrained,args.fold,args.regime,args.seed,progress=lambda x:print(json.dumps(x),file=console,flush=True))
            else:r=summarize_runs(dest)
        print(json.dumps(r))
    except Exception:parser.exit(1,'Multi-seed CV failed; preserve outputs; private records were not printed.\n')
if __name__=='__main__':main()
