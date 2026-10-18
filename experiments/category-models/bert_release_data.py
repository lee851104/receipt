"""Prepare the selected 25% recipe without opening, copying or hashing test data."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import io
import json
from pathlib import Path

from bert_ratio_cv import read_development,synthetic_order
from common import fingerprint
from dataset_split import audit_split,read_rows,digest
from prepare_data import write_json,write_jsonl


def expected_parts(source,cv):
    source,cv=Path(source).resolve(),Path(cv).resolve()
    _,synthetic,_,identity=read_development(source)
    plan_raw=(cv/'plan.json').read_bytes()
    summary_raw=(cv/'summary.json').read_bytes()
    plan,summary=json.loads(plan_raw),json.loads(summary_raw)
    if (plan.get('schema')!='bert-ratio-cv-1' or plan['source_identity']!=identity or
        summary['plan_sha256']!=digest(plan_raw) or 'synthetic_25' not in summary['results']):
        raise ValueError('cv_source_mismatch')
    real=[r for r in read_rows(source/'train.jsonl') if r['source']=='real']
    validation=read_rows(source/'validation.jsonl')
    count=round(len(real)/3)
    if count<1 or count>len(synthetic):raise ValueError('insufficient_training_sources')
    parts=dict(train=real+synthetic_order(synthetic,1042)[:count],validation=validation)
    summary_counts=audit_split(dict(**parts,test=[]))
    if not validation:raise ValueError('empty_validation')
    if read_development(source)[3]!=identity:raise ValueError('source_changed')
    provenance=dict(source_identity=identity,cv_plan_sha256=digest(plan_raw),cv_summary_sha256=digest(summary_raw))
    return parts,summary_counts,provenance


def prepare(source,cv,out):
    source,cv,out=map(lambda p:Path(p).resolve(),(source,cv,out))
    if out.exists():raise FileExistsError('output_exists')
    if out.is_relative_to(source) or out.is_relative_to(cv):raise ValueError('unsafe_output')
    parts,counts,provenance=expected_parts(source,cv)
    out.mkdir(parents=True,exist_ok=False)
    for part,rows in parts.items():write_jsonl(out/f'{part}.jsonl',rows)
    manifest=dict(schema='bert-development-recipe-1',source=str(source),cv=str(cv),
        selected_recipe='synthetic_25',synthetic_sampling_seed=1042,ratio_rounding='round(real_count/3)',
        provenance=provenance,summary=counts,
        actual_synthetic_fraction=counts['train']['synthetic']/counts['train']['total'],
        files_sha256={p:fingerprint(out/f'{p}.jsonl') for p in parts},
        source_sha256=dict(source_manifest=provenance['source_identity']['manifest'],
            source_train=provenance['source_identity']['files']['train'],
            source_validation=provenance['source_identity']['files']['validation'],
            cv_plan=provenance['cv_plan_sha256'],cv_summary=provenance['cv_summary_sha256']),
        test_policy='never_open_copy_hash_or_evaluate_test',
        evaluation_status='development_validation_used_for_prior_recipe_selection')
    write_json(out/'manifest.json',manifest)
    load(out)
    return counts


def load(folder):
    folder=Path(folder).resolve()
    raw=(folder/'manifest.json').read_bytes();manifest=json.loads(raw)
    if (manifest['schema']!='bert-development-recipe-1' or manifest['selected_recipe']!='synthetic_25' or
        manifest['test_policy']!='never_open_copy_hash_or_evaluate_test' or
        manifest['synthetic_sampling_seed']!=1042 or manifest['ratio_rounding']!='round(real_count/3)' or
        set(manifest['files_sha256'])!={'train','validation'}):
        raise ValueError('invalid_recipe_manifest')
    expected,counts,provenance=expected_parts(manifest['source'],manifest['cv'])
    if provenance!=manifest['provenance'] or counts!=manifest['summary']:
        raise ValueError('recipe_provenance_changed')
    expected_hashes=dict(source_manifest=provenance['source_identity']['manifest'],
        source_train=provenance['source_identity']['files']['train'],
        source_validation=provenance['source_identity']['files']['validation'],
        cv_plan=provenance['cv_plan_sha256'],cv_summary=provenance['cv_summary_sha256'])
    if (manifest['source_sha256']!=expected_hashes or
        manifest['actual_synthetic_fraction']!=counts['train']['synthetic']/counts['train']['total']):
        raise ValueError('recipe_description_changed')
    parts={}
    for part in ('train','validation'):
        path=folder/f'{part}.jsonl'
        if fingerprint(path)!=manifest['files_sha256'][part]:raise ValueError('recipe_file_changed')
        parts[part]=read_rows(path)
        if parts[part]!=expected[part]:raise ValueError('recipe_rows_changed')
    if (folder/'manifest.json').read_bytes()!=raw:raise ValueError('recipe_changed')
    return parts,manifest,digest(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','check'])
    for arg in ('source','cv','out','dataset','private-root'):parser.add_argument('--'+arg,type=Path)
    args=parser.parse_args()
    try:
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            if args.command=='prepare':
                if args.out.resolve()==args.private_root.resolve() or not args.out.resolve().is_relative_to(args.private_root.resolve()):
                    raise ValueError('invalid_private_output')
                report=prepare(args.source,args.cv,args.out)
            else:report=load(args.dataset)[1]['summary']
        print(json.dumps(report))
    except Exception:parser.exit(1,'Recipe preparation failed; private data was not printed.\n')
if __name__=='__main__':main()
