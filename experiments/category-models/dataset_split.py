"""Offline, source-aware grouped splits. Console output never includes item names."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import unicodedata

PARTS = ('train', 'validation', 'test')


def key(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('invalid_text')
    return ''.join(unicodedata.normalize('NFKC', value).casefold().split())


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def check_category(row):
    if not isinstance(row, dict) or type(row.get('category')) is not int or not 0 <= row['category'] < 10:
        raise ValueError('invalid_category')
    key(row.get('name'))


def validate_synthetic(rows, minimum=50):
    counts, seen, result = Counter(), set(), []
    for row in rows:
        check_category(row)
        if set(row) != {'name', 'category', 'source'} or row['source'] != 'synthetic':
            raise ValueError('invalid_synthetic_source_or_fields')
        normalized = key(row['name'])
        if normalized in seen:
            raise ValueError('duplicate_synthetic_name')
        seen.add(normalized)
        counts[row['category']] += 1
        result.append(dict(name=unicodedata.normalize('NFKC', row['name']).strip(),
                           category=row['category'], source='synthetic'))
    if any(counts[c] < minimum for c in range(10)):
        raise ValueError('insufficient_synthetic_items')
    return sorted(result, key=lambda r: (r['category'], key(r['name'])))


def prepare_real(rows, legacy_real=False):
    result, ids, names = [], set(), {}
    for row in rows:
        check_category(row)
        source = row.get('source', 'real' if legacy_real else None)
        if source != 'real' or row.get('review_status') != 'human_confirmed':
            raise ValueError('unconfirmed_or_nonreal_input')
        item_id = row.get('id')
        if not isinstance(item_id, str) or not item_id.strip() or item_id in ids:
            raise ValueError('invalid_or_duplicate_id')
        ids.add(item_id)
        name = unicodedata.normalize('NFKC', row['name']).strip()
        normalized = key(name)
        if normalized in names and names[normalized] != row['category']:
            raise ValueError('conflicting_normalized_name')
        names[normalized] = row['category']
        context = row.get('name_only_context_needed', False)
        if type(context) is not bool:
            raise ValueError('invalid_context_flag')
        result.append(dict(id=item_id, name=name, category=row['category'],
                           source='real', review_status='human_confirmed',
                           group=key(row.get('group', name)), name_only_context_needed=context))
    if not result:
        raise ValueError('empty_real_dataset')
    # Resolve transitive group links before deduplication, otherwise an alias can
    # be the only bridge between two explicit groups. Count unique names, not purchases.
    unique = []
    for group_id, group in grouped(result):
        canonical = {}
        for row in sorted(group, key=lambda r: r['id']):
            normalized = key(row['name'])
            if normalized in canonical:
                canonical[normalized]['name_only_context_needed'] |= row['name_only_context_needed']
            else:
                canonical[normalized] = dict(row, group=group_id)
        unique.extend(canonical.values())
    return sorted(unique, key=lambda r: r['id'])


def grouped(rows):
    # Union both aliases and explicit groups; transitive alias links must stay together.
    parents = list(range(len(rows)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    seen = {}
    for i, row in enumerate(rows):
        for token in (('name', key(row['name'])), ('group', key(row.get('group', row['name'])))):
            if token in seen:
                parents[find(i)] = find(seen[token])
            else:
                seen[token] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row)
    result = []
    for group in groups.values():
        if len({r['category'] for r in group}) != 1:
            raise ValueError('conflicting_group_labels')
        group_id = digest('\n'.join(sorted(r['id'] for r in group)).encode('utf-8'))
        result.append((group_id, group))
    return sorted(result)


def make_split(real, synthetic, seed=42):
    real = prepare_real(real)
    synthetic = validate_synthetic(synthetic)
    by_category = defaultdict(list)
    for group_id, group in grouped(real):
        by_category[group[0]['category']].append((group_id, group))
    parts = {p: [] for p in PARTS}
    rng = random.Random(seed)
    for category in range(10):
        groups = by_category[category]
        rng.shuffle(groups)
        holdout = max(1, int(len(groups) * .15)) if len(groups) >= 3 else 0
        for i, (group_id, group) in enumerate(groups):
            part = 'test' if i < holdout else 'validation' if i < 2*holdout else 'train'
            for row in group:
                parts[part].append(dict(row, group=group_id))
    real_keys = {key(r['name']) for r in real}
    real_ids = {r['id'] for r in real}
    for row in synthetic:
        normalized = key(row['name'])
        if normalized in real_keys:
            continue
        item_id = 'synthetic-' + digest(normalized.encode('utf-8'))
        if item_id in real_ids:
            raise ValueError('synthetic_id_collision')
        parts['train'].append(dict(row, id=item_id, group=item_id, review_status='synthetic_generated'))
    for rows in parts.values():
        rows.sort(key=lambda r: r['id'])
    audit_split(parts)
    return parts


def audit_split(parts):
    if set(parts) != set(PARTS):
        raise ValueError('invalid_partitions')
    seen_ids, names, groups = set(), {}, {}
    summary = {}
    for part in PARTS:
        rows = parts[part]
        counts = Counter()
        for row in rows:
            check_category(row)
            item_id = row.get('id')
            if not isinstance(item_id, str) or not item_id.strip() or item_id in seen_ids:
                raise ValueError('invalid_or_duplicate_id')
            seen_ids.add(item_id)
            source = row.get('source')
            if source not in ('real', 'synthetic'):
                raise ValueError('invalid_source')
            expected_review = 'human_confirmed' if source == 'real' else 'synthetic_generated'
            if row.get('review_status') != expected_review:
                raise ValueError('invalid_review_status')
            if part != 'train' and source != 'real':
                raise ValueError('synthetic_in_holdout')
            if key(row['name']) in names:
                raise ValueError('duplicate_normalized_name')
            for mapping, token in ((names, key(row['name'])), (groups, key(row.get('group')))):
                previous = mapping.setdefault(token, (part, row['category'], source))
                if previous != (part, row['category'], source):
                    raise ValueError('group_or_name_leakage')
            counts[str(row['category'])] += 1
        summary[part] = dict(total=len(rows), real=sum(r['source']=='real' for r in rows),
                             synthetic=sum(r['source']=='synthetic' for r in rows),
                             per_category={str(c): counts[str(c)] for c in range(10)})
    summary['scored_categories'] = [c for c in range(10) if summary['test']['per_category'][str(c)] >= 5]
    summary['excluded_categories'] = [dict(category=c, test_count=summary['test']['per_category'][str(c)],
                                            reason='fewer_than_5_real_test_items')
                                        for c in range(10) if c not in summary['scored_categories']]
    return summary


def save_dataset(real_path, synthetic_path, out, legacy_real=False, seed=42):
    # Compute before creating the directory, so invalid input leaves no partial dataset.
    real_bytes, synthetic_bytes = real_path.read_bytes(), synthetic_path.read_bytes()
    real_raw = [json.loads(s) for s in real_bytes.decode('utf-8-sig').splitlines() if s.strip()]
    synth_raw = [json.loads(s) for s in synthetic_bytes.decode('utf-8-sig').splitlines() if s.strip()]
    real = prepare_real(real_raw, legacy_real=legacy_real)
    parts = make_split(real, synth_raw, seed=seed)
    summary = audit_split(parts)
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for part in PARTS:
        content = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in parts[part]).encode('utf-8')
        (out/f'{part}.jsonl').write_bytes(content)
        hashes[part] = digest(content)
    manifest = dict(schema_version=1, seed=seed, target_real_ratio=[.70,.15,.15],
                    allocation='stratified_groups_floor_15pct_min_one_if_at_least_three_groups',
                    legacy_real_declared=legacy_real,
                    evaluation_status='development_holdout_not_independent_final_test',
                    group_review_status='manual_semantic_group_review_required',
                    source_sha256={'real': digest(real_bytes), 'synthetic': digest(synthetic_bytes)},
                    synthetic_collisions_removed=len(synth_raw)-summary['train']['synthetic'],
                    files_sha256=hashes, summary=summary)
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary


def check_dataset(folder):
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    required = {'schema_version', 'seed', 'target_real_ratio', 'allocation',
                'legacy_real_declared', 'evaluation_status', 'group_review_status',
                'source_sha256', 'synthetic_collisions_removed', 'files_sha256', 'summary'}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError('invalid_manifest')
    if (type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or type(manifest['seed']) is not int
            or type(manifest['legacy_real_declared']) is not bool
            or manifest['target_real_ratio'] != [.70, .15, .15]
            or manifest['allocation'] != 'stratified_groups_floor_15pct_min_one_if_at_least_three_groups'
            or manifest['evaluation_status'] != 'development_holdout_not_independent_final_test'
            or manifest['group_review_status'] != 'manual_semantic_group_review_required'
            or type(manifest['synthetic_collisions_removed']) is not int
            or manifest['synthetic_collisions_removed'] < 0):
        raise ValueError('invalid_manifest_metadata')
    for field, expected in (('source_sha256', {'real', 'synthetic'}), ('files_sha256', set(PARTS))):
        hashes = manifest[field]
        if (not isinstance(hashes, dict) or set(hashes) != expected or
                any(not isinstance(h, str) or len(h) != 64 or
                    any(c not in '0123456789abcdef' for c in h) for h in hashes.values())):
            raise ValueError('invalid_manifest_fingerprints')
    parts = {}
    for part in PARTS:
        content = (folder/f'{part}.jsonl').read_bytes()
        if digest(content) != manifest['files_sha256'][part]:
            raise ValueError('dataset_fingerprint_mismatch')
        parts[part] = [json.loads(s) for s in content.decode('utf-8').splitlines() if s.strip()]
    summary = audit_split(parts)
    if summary != manifest['summary']:
        raise ValueError('dataset_summary_mismatch')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--real',type=Path,required=True)
    prepare.add_argument('--synthetic',type=Path,required=True)
    prepare.add_argument('--out',type=Path,required=True)
    prepare.add_argument('--legacy-real',action='store_true',help='Explicitly attest the legacy file is real, reviewed data; never overrides an existing source.')
    prepare.add_argument('--seed',type=int,default=42)
    check = commands.add_parser('check')
    check.add_argument('--dataset',type=Path,required=True)
    args=parser.parse_args()
    try:
        summary = (save_dataset(args.real,args.synthetic,args.out,args.legacy_real,args.seed)
                   if args.command=='prepare' else check_dataset(args.dataset))
        print(json.dumps(summary,ensure_ascii=True,sort_keys=True))
    except (ValueError, TypeError, KeyError, OSError):
        # JSON parsing and OS errors may contain private input, paths or excerpts.
        parser.exit(1,'Dataset validation failed; check input schema, provenance, fingerprints and output path.\n')


if __name__=='__main__': main()
