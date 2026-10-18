import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_fixed_split_train import fixture, write_rows
from fixed_split_data import load_dataset
from dataset_split import key
import bert_continuation as continuation

class ContinuationDataTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.parent=fixture(self.root)
        self.parts,_,self.identity=load_dataset(self.parent)
        self.draft=self.root/'draft';self.draft.mkdir()
        self.model=self.root/'model';self.model.mkdir()
        (self.model/'classifier-manifest.json').write_text('{}')
        self.rows=[dict(id=f'new-{c}-{i}',name=f'虛構新增類{c}品{i}',category=c,source='real',review_status='human_confirmed') for c in range(10) for i in range(10)]
        for part in ('train','validation','test'):
            r=self.parts[part][0]
            self.rows.append(dict(r,id='copy-'+part,source='real',review_status='human_confirmed'))
        self.unresolved=self.parts['train'][1]
        write_rows(self.root/'gold.jsonl',self.rows)
        write_rows(self.draft/'draft-items.jsonl',self.rows+[dict(self.unresolved,id='unresolved')])
    def prepare(self,out):
        with patch.object(continuation,'verified_manifest',return_value=dict(dataset_sha256=self.identity)):
            return continuation.prepare(self.root/'gold.jsonl',self.draft,self.parent,self.model,out,parent_source=self.root/'real.jsonl')
    def test_only_new_groups_in_holdouts_and_unknown_excluded_from_replay(self):
        out=self.root/'new';self.prepare(out)
        parts,manifest,_=continuation.load(out)
        old={key(r['name']) for rows in self.parts.values() for r in rows}
        self.assertFalse({key(r['name']) for p in ('validation','test') for r in parts[p]} & old)
        self.assertFalse(any(key(r['name'])==key(self.unresolved['name']) for r in parts['train']))
        self.assertEqual(manifest['new_split_counts'],dict(train=80,validation=10,test=10))
        self.assertEqual(manifest['excluded_previously_seen'],3)
        self.assertEqual(manifest['excluded_unresolved_replay'],1)
        self.assertEqual(manifest['evaluation_status'],'previously_evaluated_round_isolated_holdout_not_blind')
    def test_unmapped_cross_version_explicit_group_is_rejected(self):
        self.rows[0]['group']='fictional-original-group-not-in-parent-manifest'
        write_rows(self.root/'gold.jsonl',self.rows)
        with self.assertRaisesRegex(ValueError,'unresolved_cross_version_group'):
            self.prepare(self.root/'unsafe-group')
        self.assertFalse((self.root/'unsafe-group').exists())

    def test_hash_tamper_and_reusing_output_rejected(self):
        out=self.root/'new';self.prepare(out)
        with self.assertRaises(FileExistsError):self.prepare(out)
        with (out/'test.jsonl').open('a',encoding='utf-8') as f:f.write('{}\n')
        with self.assertRaises(ValueError):continuation.load(out)

if __name__=='__main__':unittest.main()
