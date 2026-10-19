"""Grouped, inner-stopped CV comparing synthetic ratios. Never opens the heldout test file."""
import argparse
from collections import Counter, defaultdict
from contextlib import redirect_stdout, redirect_stderr
import gc
import io
import json
import math
from pathlib import Path
import random
import statistics
import time

import numpy as np
import torch
from transformers import AutoTokenizer, BertForSequenceClassification
from bert_finetune import EarlyStopping, train_epoch, validation_loss
from bert_model import Classifier, save_bundle, verified_manifest
from common import fingerprint
from dataset_split import audit_split, grouped, read_rows, digest
from embedding_features import local_manifest
from evaluate_reviewed import summarize
from fixed_split_train import verify_predictions
from prepare_data import CATEGORIES, write_json, write_jsonl

REGIMES = ('real_only', 'synthetic_25', 'synthetic_current')


def read_development(source):
    source = Path(source).resolve()
    raw = (source/'manifest.json').read_bytes()
    manifest = json.loads(raw)
    if manifest['schema_version'] != 'bert-continuation-1':
        raise ValueError('expected_continuation_source')
    parts = {}
    hashes = {}
    # Explicit allowlist: no call to load_dataset/load_continuation or test path.
    for part in ('train', 'validation'):
        path = source/f'{part}.jsonl'
        hashes[part] = fingerprint(path)
        if hashes[part] != manifest['files_sha256'][part]:
            raise ValueError('development_source_changed')
        parts[part] = read_rows(path)
    summary = audit_split(dict(**parts, test=[]))
    if any(summary[p] != manifest['summary'][p] for p in parts):
        raise ValueError('development_summary_changed')
    real = [r for p in parts.values() for r in p if r['source'] == 'real']
    synthetic = [r for r in parts['train'] if r['source'] == 'synthetic']
    real_train = summary['train']['real']
    if not real_train or not synthetic:
        raise ValueError('missing_comparison_sources')
    identity = dict(manifest=digest(raw), files=hashes)
    return real, synthetic, len(synthetic)/real_train, identity


def make_folds(real, n=5, seed=42):
    by_class = defaultdict(list)
    for gid, rows in grouped(real):
        by_class[rows[0]['category']].append((gid, rows))
    rng = random.Random(seed)
    folds = [[] for _ in range(n)]
    for cat in range(10):
        groups = by_class[cat]
        rng.shuffle(groups)
        groups.sort(key=lambda g: -len(g[1]))
        counts = [0]*n
        for gid, rows in groups:
            ties = list(range(n)); rng.shuffle(ties)
            target = min(ties, key=lambda i: (counts[i], len(folds[i])))
            folds[target].extend(dict(r, group=gid) for r in rows)
            counts[target] += len(rows)
    if any(not rows for rows in folds):
        raise ValueError('insufficient_groups')
    result = []
    for f in range(n):
        available = [r for i, rows in enumerate(folds) if i != f for r in rows]
        cats = defaultdict(list)
        for gid, rows in grouped(available):
            cats[rows[0]['category']].append((gid, rows))
        fit, inner = [], []
        inner_rng = random.Random(seed+100+f)
        for cat in range(10):
            groups = cats[cat]; inner_rng.shuffle(groups)
            held = max(1, int(.15*len(groups))) if len(groups) >= 3 else 0
            for j, (gid, rows) in enumerate(groups):
                (inner if j < held else fit).extend(dict(r, group=gid) for r in rows)
        if not inner or not fit:
            raise ValueError('insufficient_inner_partition')
        result.append(dict(train=sorted(fit,key=lambda r:r['id']),
                           inner=sorted(inner,key=lambda r:r['id']),
                           outer=sorted(folds[f],key=lambda r:r['id'])))
    return result


def synthetic_order(rows, seed):
    # Balance classes, preserve each explicit synthetic group as an indivisible unit.
    groups = defaultdict(list)
    for gid, members in grouped(rows):
        if len(members) != 1:
            raise ValueError('synthetic_sampling_requires_singleton_groups')
        groups[members[0]['category']].append(members[0])
    rng = random.Random(seed)
    for members in groups.values(): rng.shuffle(members)
    result = []
    while any(groups.values()):
        for cat in range(10):
            if groups[cat]: result.append(groups[cat].pop())
    return result


def prepare(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    if out.exists(): raise FileExistsError('output_exists')
    if out.is_relative_to(source): raise ValueError('unsafe_output')
    real, synthetic, ratio, identity = read_development(source)
    folds = make_folds(real)
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for f, parts in enumerate(folds):
        folder = out/f'fold-{f}'; folder.mkdir()
        order = synthetic_order(synthetic, 1042+f)
        hashes = {}
        for part in ('inner', 'outer'):
            write_jsonl(folder/f'{part}.jsonl', parts[part])
            hashes[f'{part}.jsonl'] = fingerprint(folder/f'{part}.jsonl')
        counts = {}
        for regime in REGIMES:
            ratio_to_real = 0 if regime == 'real_only' else 1/3 if regime == 'synthetic_25' else ratio
            count = round(len(parts['train'])*ratio_to_real)
            if count > len(order): raise ValueError('insufficient_synthetic_pool')
            train = parts['train']+order[:count]
            audit_split(dict(train=train,validation=parts['inner'],test=parts['outer']))
            path = folder/f'{regime}.jsonl'; write_jsonl(path, train)
            hashes[path.name] = fingerprint(path)
            counts[regime] = dict(real=len(parts['train']),synthetic=count,total=len(train),
                                  synthetic_fraction=count/len(train))
        records.append(dict(fold=f,seed=42+f,files=hashes,counts=counts,
                            inner_count=len(parts['inner']),outer_count=len(parts['outer'])))
    if read_development(source)[3] != identity: raise ValueError('source_changed')
    plan = dict(schema='bert-ratio-cv-1', source=str(source), source_identity=identity,
                real_count=len(real), synthetic_pool_count=len(synthetic),
                real_per_category=dict(Counter(str(r['category']) for r in real)),
                current_synthetic_per_real=ratio, regimes=list(REGIMES), folds=records,
                protocol='5 grouped outer folds; inner real holdout selects epoch; original test never opened',
                initialization='fresh_public_encoder_per_fold_and_regime',
                metric='mean outer accuracy; report sample SD, OOF F1, paired differences')
    write_json(out/'plan.json', plan)
    for f in range(5):
        for regime in REGIMES: load_fold(out,f,regime)
    return plan


def load_fold(root, fold, regime):
    root = Path(root).resolve()
    if type(fold) is not int or not 0 <= fold < 5 or regime not in REGIMES:
        raise ValueError('invalid_cv_selection')
    plan = json.loads((root/'plan.json').read_text(encoding='utf-8'))
    if plan['schema'] != 'bert-ratio-cv-1' or plan['regimes'] != list(REGIMES) or len(plan['folds']) != 5:
        raise ValueError('invalid_plan')
    real, _, _, identity = read_development(plan['source'])
    if identity != plan['source_identity']: raise ValueError('source_changed')
    info = plan['folds'][fold]
    expected = {'inner.jsonl','outer.jsonl',*[r+'.jsonl' for r in REGIMES]}
    if set(info['files']) != expected: raise ValueError('unexpected_files')
    folder = root/f'fold-{fold}'
    for name, sha in info['files'].items():
        if fingerprint(folder/name) != sha: raise ValueError('fold_changed')
    parts = {p:read_rows(folder/name) for p,name in
             [('train',regime+'.jsonl'),('inner','inner.jsonl'),('outer','outer.jsonl')]}
    audit_split(dict(train=parts['train'],validation=parts['inner'],test=parts['outer']))
    original = {r['id']:r for r in real}
    actual = [r for p in parts.values() for r in p if r['source']=='real']
    if len(actual) != len(original) or {r['id'] for r in actual} != set(original):
        raise ValueError('real_coverage_mismatch')
    for row in actual:
        old = original[row['id']]
        if any(row[k] != old[k] for k in ('name','category','review_status','source')):
            raise ValueError('real_row_changed')
    return parts, plan


def train_fold(root, pretrained, fold, regime, device='cuda', epochs=10, progress=None, seed=None, output_root=None):
    root, pretrained = Path(root).resolve(), Path(pretrained).resolve()
    seed_override=seed
    if (seed is None)!=(output_root is None):raise ValueError('seed_override_requires_separate_output')
    if seed is not None and (type(seed) is not int or not 0<=seed<2**32):raise ValueError('invalid_seed')
    destination=root if output_root is None else Path(output_root).resolve()
    if output_root is not None and (destination.is_relative_to(root) or root.is_relative_to(destination)):
        raise ValueError('unsafe_override_output')
    if destination.is_relative_to(pretrained) or pretrained.is_relative_to(destination):raise ValueError('unsafe_model_output')
    parts, plan = load_fold(root, fold, regime)
    plan_hash = fingerprint(root/'plan.json')
    if (pretrained/'classifier-manifest.json').exists():
        raise ValueError('finetuned_initialization_forbidden')
    encoder = local_manifest(pretrained)
    config = json.loads((pretrained/'config.json').read_text(encoding='utf-8'))
    if any('SequenceClassification' in a for a in config.get('architectures', [])):
        raise ValueError('classifier_initialization_forbidden')
    if type(epochs) is not int or epochs < 1 or device not in ('cpu','cuda'):
        raise ValueError('invalid_training_settings')
    if device=='cuda' and not torch.cuda.is_available(): raise ValueError('cuda_unavailable')
    settings = dict(epochs=epochs,lr=2e-5,batch_size=16,max_length=32,weight_decay=.01,
                    patience=2,min_delta=1e-4,device=device,initialization='public_encoder',
                    encoder=encoder,plan_sha256=plan_hash)
    if seed_override is not None:settings['initialization_seed']=seed_override
    destination.mkdir(parents=True,exist_ok=True)
    common_path=destination/'training-config.json'
    if common_path.exists():
        if json.loads(common_path.read_text(encoding='utf-8')) != settings:
            raise ValueError('inconsistent_run_settings')
    else:
        with common_path.open('x',encoding='utf-8') as stream:
            json.dump(settings,stream,ensure_ascii=False,sort_keys=True)
    config_hash=fingerprint(common_path)
    run=destination/'runs'/f'{regime}-fold-{fold}'
    run.mkdir(parents=True,exist_ok=False)  # Failed attempts remain claimed.
    seed=42+fold if seed_override is None else seed_override
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    if device=='cuda':
        torch.cuda.manual_seed_all(seed); torch.backends.cudnn.benchmark=False
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    tokenizer=AutoTokenizer.from_pretrained(pretrained,local_files_only=True,trust_remote_code=False)
    model=BertForSequenceClassification.from_pretrained(pretrained,num_labels=10,
        id2label={i:n for i,n in enumerate(CATEGORIES)},label2id={n:i for i,n in enumerate(CATEGORIES)},
        local_files_only=True,trust_remote_code=False,use_safetensors=True,attn_implementation='eager').to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-5,weight_decay=.01)
    generator=torch.Generator().manual_seed(seed); stop=EarlyStopping(); history=[]
    started=time.perf_counter()
    metadata=dict(categories=list(CATEGORIES),max_length=32,dataset_sha256=plan_hash,
                  seed=seed,pretrained=encoder,cv_fold=fold,cv_regime=regime)
    for epoch in range(1,epochs+1):
        loss=train_epoch(model,tokenizer,parts['train'],optimizer,device,16,32,generator)
        inner=validation_loss(model,tokenizer,parts['inner'],device,16,32)
        history.append(dict(epoch=epoch,training_loss=loss,inner_loss=inner))
        if stop.update(inner,epoch):
            save_bundle(model,tokenizer,run/'model',dict(**metadata,best_epoch=epoch))
        if progress: progress(dict(fold=fold,regime=regime,**history[-1]))
        if stop.should_stop:break
    seconds=time.perf_counter()-started
    del model,optimizer,tokenizer;gc.collect()
    if device=='cuda':torch.cuda.empty_cache()
    if fingerprint(root/'plan.json')!=plan_hash or fingerprint(common_path)!=config_hash:
        raise ValueError('experiment_changed')
    load_fold(root,fold,regime)
    if local_manifest(pretrained)!=encoder:raise ValueError('encoder_changed')
    with (run/'outer-evaluation-claimed.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(plan_sha256=plan_hash,config_sha256=config_hash),stream)
    model=Classifier.load(run/'model',device='cpu')
    predictions=model.predict([r['name'] for r in parts['outer']])
    verify_predictions(predictions,len(parts['outer']))
    truth=[r['category'] for r in parts['outer']]
    predicted=[r['category'] for r in predictions]
    private=run/'private-outer-predictions.jsonl'
    write_jsonl(private,[dict(id=r['id'],actual=r['category'],predicted=p) for r,p in zip(parts['outer'],predicted)])
    result=dict(fold=fold,regime=regime,seed=seed,best_epoch=stop.best_epoch,
                best_inner_loss=stop.best_loss,history=history,outer=summarize(truth,predicted),
                training_counts=plan['folds'][fold]['counts'][regime],training_seconds=seconds,
                gradient_steps=sum(math.ceil(len(parts['train'])/16) for _ in history),
                plan_sha256=plan_hash,config_sha256=config_hash,
                predictions_sha256=fingerprint(private),
                model_manifest_sha256=fingerprint(run/'model/classifier-manifest.json'),
                original_test='not_opened_or_evaluated')
    if fingerprint(root/'plan.json')!=plan_hash or fingerprint(common_path)!=config_hash:
        raise ValueError('experiment_changed')
    load_fold(root,fold,regime)
    write_json(run/'report.json',result)
    return result


def summarize_runs(root):
    root=Path(root).resolve();plan_hash=fingerprint(root/'plan.json')
    config_hash=fingerprint(root/'training-config.json') if (root/'training-config.json').exists() else None
    results={}; per_regime_predictions={}
    for regime in REGIMES:
        reports=[];oof=[]
        for fold in range(5):
            parts,plan=load_fold(root,fold,regime)
            run=root/'runs'/f'{regime}-fold-{fold}'
            if not (run/'report.json').exists():raise ValueError('incomplete_cv')
            r=json.loads((run/'report.json').read_text(encoding='utf-8'))
            if (r['fold']!=fold or r['regime']!=regime or r['plan_sha256']!=plan_hash or
                    r['config_sha256']!=config_hash or r['original_test']!='not_opened_or_evaluated'):
                raise ValueError('run_identity_mismatch')
            if fingerprint(run/'private-outer-predictions.jsonl')!=r['predictions_sha256']:
                raise ValueError('predictions_changed')
            if fingerprint(run/'model/classifier-manifest.json')!=r['model_manifest_sha256']:
                raise ValueError('model_changed')
            verified_manifest(run/'model')
            predictions=read_rows(run/'private-outer-predictions.jsonl')
            if [(p['id'],p['actual']) for p in predictions]!=[(p['id'],p['category']) for p in parts['outer']]:
                raise ValueError('outer_alignment_mismatch')
            if summarize([p['actual'] for p in predictions],[p['predicted'] for p in predictions])!=r['outer']:
                raise ValueError('score_mismatch')
            reports.append(r);oof.extend(predictions)
        if len(oof)!=plan['real_count'] or len({p['id'] for p in oof})!=len(oof):
            raise ValueError('oof_coverage_mismatch')
        accuracies=[r['outer']['accuracy'] for r in reports]
        results[regime]=dict(mean_accuracy=statistics.mean(accuracies),sample_sd=statistics.stdev(accuracies),
            min_accuracy=min(accuracies),max_accuracy=max(accuracies),fold_accuracy=accuracies,
            best_epochs=[r['best_epoch'] for r in reports],
            pooled=summarize([p['actual'] for p in oof],[p['predicted'] for p in oof]),
            training_counts=[r['training_counts'] for r in reports],
            total_training_seconds=sum(r['training_seconds'] for r in reports),
            gradient_steps=sum(r['gradient_steps'] for r in reports))
        per_regime_predictions[regime]={p['id']:p for p in oof}
    paired={}
    for a,b in [('real_only','synthetic_25'),('real_only','synthetic_current'),('synthetic_25','synthetic_current')]:
        x,y=per_regime_predictions[a],per_regime_predictions[b]
        paired[a+'__to__'+b]=dict(improved=sum(x[k]['predicted']!=x[k]['actual'] and y[k]['predicted']==y[k]['actual'] for k in x),
            worsened=sum(x[k]['predicted']==x[k]['actual'] and y[k]['predicted']!=y[k]['actual'] for k in x),
            fold_delta_pp=[100*(v-u) for u,v in zip(results[a]['fold_accuracy'],results[b]['fold_accuracy'])])
    summary=dict(categories=list(CATEGORIES),development_count=plan['real_count'],results=results,
        paired=paired,plan_sha256=plan_hash,config_sha256=config_hash,original_test='not_opened_or_evaluated',
        highest_mean=max(REGIMES,key=lambda r:results[r]['mean_accuracy']),
        lowest_sd=min(REGIMES,key=lambda r:results[r]['sample_sd']),
        limitations=['Development CV selected data recipes; not independent test accuracy.',
            'Fold sample SD is descriptive, not an independent-run confidence interval.',
            'Synthetic ratios change training size and optimizer steps.',
            'Rare categories and unmarked semantic variants limit generalization.',
            'One initialization seed per fold; seed variability not separately estimated.'])
    with (root/'summary.json').open('x',encoding='utf-8') as stream:
        json.dump(summary,stream,ensure_ascii=False,indent=2)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','train','summarize'])
    parser.add_argument('--source',type=Path);parser.add_argument('--out',type=Path)
    parser.add_argument('--experiment',type=Path);parser.add_argument('--pretrained',type=Path)
    parser.add_argument('--fold',type=int);parser.add_argument('--regime',choices=REGIMES)
    parser.add_argument('--private-root',type=Path,required=True)
    args=parser.parse_args(); console=__import__('sys').stdout
    try:
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            dest=(args.out if args.command=='prepare' else args.experiment).resolve()
            if dest==args.private_root.resolve() or not dest.is_relative_to(args.private_root.resolve()):
                raise ValueError('invalid_private_output')
            if args.command=='prepare':
                result=prepare(args.source,args.out)
                result={k:result[k] for k in ('real_count','synthetic_pool_count','real_per_category','current_synthetic_per_real','folds')}
            elif args.command=='train':
                result=train_fold(args.experiment,args.pretrained,args.fold,args.regime,
                    progress=lambda row:print(json.dumps(row),file=console,flush=True))
            else:result=summarize_runs(args.experiment)
        print(json.dumps(result))
    except Exception:
        parser.exit(1,'Ratio CV failed; preserve output and inspect locally without printing private names.\n')
if __name__=='__main__':main()
