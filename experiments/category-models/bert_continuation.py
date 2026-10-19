"""Versioned continuation splits: old exposure never enters new holdouts."""
import argparse
from collections import defaultdict
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import random

from bert_model import verified_manifest
from common import fingerprint
from dataset_split import audit_split, digest, grouped, key, read_rows
from evaluate_reviewed import select_confirmed, overlap_slices
from fixed_split_data import load_dataset
from prepare_data import write_json, write_jsonl

STATUS='previously_evaluated_round_isolated_holdout_not_blind'


def tokens(row):
    return set(row.get('overlap_keys', [key(row['name']),key(row.get('group',row['name']))]))


def prepare(reviewed,draft_dir,parent_dataset,parent_model,out,seed=42,parent_source=None):
    reviewed,draft_dir,parent_dataset,parent_model,out=map(Path,(reviewed,draft_dir,parent_dataset,parent_model,out))
    if out.exists():raise FileExistsError('output_exists')
    if type(seed) is not int:raise ValueError('invalid_seed')
    source_hash=fingerprint(reviewed)
    draft_path=draft_dir/'draft-items.jsonl';draft_hash=fingerprint(draft_path)
    raw_reviewed=read_rows(reviewed)
    accepted,_=select_confirmed(raw_reviewed)
    draft=read_rows(draft_path)
    draft_by_id={r['id']:r for r in draft}
    if len(draft_by_id)!=len(draft):raise ValueError('duplicate_draft_id')
    from prepare_data import normalize
    if any(r['id'] not in draft_by_id or normalize(r['name'])!=normalize(draft_by_id[r['id']]['name']) for r in accepted):
        raise ValueError('confirmed_draft_mismatch')
    confirmed_keys={key(r['name']):r for r in accepted}
    unresolved={key(r['name']) for r in draft if key(r['name']) not in confirmed_keys}
    old,old_manifest,parent_hash=load_dataset(parent_dataset)
    if parent_source is None:raise ValueError('parent_source_audit_required')
    parent_source=Path(parent_source)
    parent_source_hash=fingerprint(parent_source)
    if parent_source_hash!=old_manifest['source_sha256']['real']:raise ValueError('parent_source_mismatch')
    parent_rows=read_rows(parent_source)
    if any('group' in r and key(r['group'])!=key(r['name']) for r in parent_rows):
        raise ValueError('parent_original_group_mapping_required')
    known_tokens={key(v) for rows in old.values() for row in rows for v in (row['name'],row['group'])}
    # Parent splits retain hashed component IDs, not arbitrary original alias labels.
    # Refuse ambiguous cross-version mappings rather than calling them unseen.
    for row in raw_reviewed:
        if row.get('review_status')=='human_confirmed' and row.get('category')!=10 and 'group' in row:
            group=key(row['group'])
            if group!=key(row['name']) and group not in known_tokens:
                raise ValueError('unresolved_cross_version_group')
    parent_manifest=verified_manifest(parent_model)
    model_hash=fingerprint(parent_model/'classifier-manifest.json')
    if parent_manifest['dataset_sha256']!=parent_hash:raise ValueError('parent_dataset_mismatch')
    unseen=overlap_slices(accepted,old)['previously_unseen']
    new=[accepted[i] for i in unseen]
    by_category=defaultdict(list)
    for group_id,rows in grouped(new):by_category[rows[0]['category']].append((group_id,rows))
    parts={p:[] for p in ('train','validation','test')}
    rng=random.Random(seed)
    for category in range(10):
        groups=by_category[category];rng.shuffle(groups)
        held=max(1,int(len(groups)*.15)) if len(groups)>=3 else 0
        for i,(group_id,rows) in enumerate(groups):
            part='test' if i<held else 'validation' if i<2*held else 'train'
            parts[part].extend(dict(r,group=group_id) for r in rows)
    new_counts={p:len(rows) for p,rows in parts.items()}
    excluded_replay=0;corrected_replay=0
    for original in old['train']:
        name_key=key(original['name'])
        if name_key in unresolved:
            excluded_replay+=1;continue
        row=dict(original)
        if name_key in confirmed_keys:
            corrected_replay+=row['category']!=confirmed_keys[name_key]['category']
            row.update(category=confirmed_keys[name_key]['category'],source='real',review_status='human_confirmed')
        parts['train'].append(row)
    for rows in parts.values():rows.sort(key=lambda r:r['id'])
    summary=audit_split(parts)
    if not parts['validation'] or not parts['test']:raise ValueError('insufficient_new_holdouts')
    exposed={digest(key(v).encode()) for rows in old.values() for r in rows for v in (r['name'],r['group'])}
    banned={digest(v.encode()) for v in unresolved}
    if source_hash!=fingerprint(reviewed) or draft_hash!=fingerprint(draft_path) or load_dataset(parent_dataset)[2]!=parent_hash:
        raise ValueError('source_changed')
    out.mkdir(parents=True,exist_ok=False)
    for p,rows in parts.items():write_jsonl(out/f'{p}.jsonl',rows)
    write_json(out/'exposure.json',dict(previously_seen=sorted(exposed),unresolved=sorted(banned)))
    manifest=dict(schema_version='bert-continuation-1',seed=seed,evaluation_status=STATUS,
                  allocation='new_unseen_grouped_70_15_15_plus_parent_train_replay',
                  parent_dataset_sha256=parent_hash,parent_classifier_manifest_sha256=model_hash,
                  source_sha256=dict(reviewed=source_hash,draft=draft_hash,parent_dataset=parent_hash),
                  files_sha256={p:fingerprint(out/f'{p}.jsonl') for p in parts},
                  exposure_sha256=fingerprint(out/'exposure.json'),summary=summary,
                  confirmed_count=len(accepted),excluded_previously_seen=len(accepted)-len(new),
                  excluded_unresolved_count=len(unresolved),excluded_unresolved_replay=excluded_replay,
                  corrected_replay_labels=corrected_replay,new_split_counts=new_counts)
    write_json(out/'group-audit.json',dict(parent_source_fingerprint_verified=True,
        parent_source_sha256=parent_source_hash,parent_dataset_sha256=parent_hash,
        reviewed_sha256=source_hash,parent_explicit_nonname_groups=0,
        new_explicit_nonname_groups=sum('group' in r and key(r['group'])!=key(r['name']) for r in raw_reviewed)))
    write_json(out/'manifest.json',manifest)
    load(out)
    return {k:manifest[k] for k in ('summary','confirmed_count','excluded_previously_seen','excluded_unresolved_count','excluded_unresolved_replay','new_split_counts')}


def load(folder):
    folder=Path(folder);raw=(folder/'manifest.json').read_bytes();manifest=json.loads(raw)
    if manifest['schema_version']!='bert-continuation-1' or manifest['evaluation_status']!=STATUS:
        raise ValueError('invalid_continuation_manifest')
    if set(manifest['files_sha256'])!={'train','validation','test'}:raise ValueError('invalid_partitions')
    parts={}
    for part,expected in manifest['files_sha256'].items():
        content=(folder/f'{part}.jsonl').read_bytes()
        if digest(content)!=expected:raise ValueError('dataset_fingerprint_mismatch')
        parts[part]=[json.loads(line) for line in content.decode('utf-8').splitlines() if line.strip()]
    if audit_split(parts)!=manifest['summary']:raise ValueError('summary_mismatch')
    exposure_raw=(folder/'exposure.json').read_bytes()
    if digest(exposure_raw)!=manifest['exposure_sha256']:raise ValueError('exposure_changed')
    exposure=json.loads(exposure_raw);old=set(exposure['previously_seen']);banned=set(exposure['unresolved'])
    group_audit=json.loads((folder/'group-audit.json').read_text(encoding='utf-8'))
    if (group_audit['parent_explicit_nonname_groups']!=0 or not group_audit['parent_source_fingerprint_verified'] or
            group_audit['parent_dataset_sha256']!=manifest['parent_dataset_sha256'] or group_audit['reviewed_sha256']!=manifest['source_sha256']['reviewed']):
        raise ValueError('invalid_group_audit')
    for part,rows in parts.items():
        for row in rows:
            hashed={digest(token.encode()) for token in tokens(row)}
            if digest(key(row['name']).encode()) in banned:raise ValueError('unresolved_in_dataset')
            if part!='train' and hashed & old:raise ValueError('parent_exposure_in_holdout')
    if (folder/'manifest.json').read_bytes()!=raw:raise ValueError('manifest_changed')
    return parts,manifest,digest(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','check'))
    for flag in ('reviewed','draft-dir','parent-dataset','parent-model','out','private-root','dataset','parent-source'):
        parser.add_argument('--'+flag,type=Path)
    args=parser.parse_args()
    try:
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            if args.command=='check':result=load(args.dataset)[1]['summary']
            else:
                if args.out.resolve()==args.private_root.resolve() or not args.out.resolve().is_relative_to(args.private_root.resolve()):raise ValueError('invalid_private_output')
                result=prepare(args.reviewed,args.draft_dir,args.parent_dataset,args.parent_model,args.out,parent_source=args.parent_source)
        print(json.dumps(result))
    except Exception:parser.exit(1,'Continuation data failed; private input was not printed.\n')

if __name__=='__main__':main()
