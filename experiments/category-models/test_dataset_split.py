"""Data preparation regression tests; every item in this file is fictional."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).with_name('dataset_split.py')


def real_rows(n=20):
    return [dict(id=f'r-{c}-{i}', name=f'虛構樣本{c}號{i}', category=c,
                 source='real', review_status='human_confirmed')
            for c in range(10) for i in range(n)]


def synthetic_rows(n=50):
    return [dict(name=f'合成訓練{c}號{i}', category=c, source='synthetic')
            for c in range(10) for i in range(n)]


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'dataset_split.py must implement the data contract')
        spec = importlib.util.spec_from_file_location('dataset_split', MODULE)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)

    def test_synthetic_count_source_and_plain_category(self):
        self.assertEqual(len(self.m.validate_synthetic(synthetic_rows())), 500)
        for change in ({'source': 'real'}, {'category': True}, {'category': 10}, {'name': '  '}):
            rows = synthetic_rows()
            rows[0].update(change)
            with self.assertRaises(ValueError):
                self.m.validate_synthetic(rows)
        with self.assertRaises(ValueError):
            self.m.validate_synthetic(synthetic_rows(49))

    def test_real_requires_review_and_explicit_provenance(self):
        for change in ({'source': 'synthetic'}, {'review_status': 'pending'}, {'category': False}):
            rows = real_rows()
            rows[0].update(change)
            with self.assertRaises(ValueError):
                self.m.prepare_real(rows)
        rows = real_rows()
        for r in rows:
            del r['source']
        with self.assertRaises(ValueError):
            self.m.prepare_real(rows)
        self.assertTrue(all(r['source'] == 'real' for r in self.m.prepare_real(rows, legacy_real=True)))

    def test_duplicate_ids_and_conflicting_names_rejected(self):
        rows = real_rows()
        rows[1]['id'] = rows[0]['id']
        with self.assertRaises(ValueError):
            self.m.prepare_real(rows)
        rows = real_rows()
        rows[20]['name'] = rows[0]['name']
        with self.assertRaises(ValueError):
            self.m.prepare_real(rows)

    def test_deterministic_grouped_real_holdout_and_synthetic_train_only(self):
        rows = real_rows()
        rows[0].update(name='ＡＢＣ 茶', group='a')
        rows[1].update(name='abc茶', group='b')
        rows[2].update(group='a')
        parts = self.m.make_split(self.m.prepare_real(rows), synthetic_rows())
        again = self.m.make_split(self.m.prepare_real(rows[::-1]), synthetic_rows()[::-1])
        self.assertEqual(parts, again)
        self.m.audit_split(parts)
        locations = [p for p, values in parts.items() if any(r['id'] in ('r-0-0','r-0-1','r-0-2') for r in values)]
        self.assertEqual(len(locations), 1)
        for p in ('validation','test'):
            self.assertTrue(parts[p])
            self.assertTrue(all(r['source']=='real' and r['review_status']=='human_confirmed' for r in parts[p]))
        self.assertEqual(sum(r['source']=='synthetic' for r in parts['train']), 500)

    def test_cross_source_name_collision_removed_from_training(self):
        synth = synthetic_rows()
        rows = real_rows()
        synth[0]['name'] = rows[0]['name']
        parts = self.m.make_split(self.m.prepare_real(rows), synth)
        self.assertEqual(sum(r['source']=='synthetic' for r in parts['train']),499)
        self.m.audit_split(parts)

    def test_rare_classes_remain_training_only(self):
        parts = self.m.make_split(self.m.prepare_real(real_rows(2)), synthetic_rows())
        self.assertEqual(parts['test'], [])
        self.assertEqual(parts['validation'], [])

    def test_audit_rejects_contamination_and_group_leakage(self):
        parts = self.m.make_split(self.m.prepare_real(real_rows()), synthetic_rows())
        parts['test'].append(parts['train'][0])
        with self.assertRaises(ValueError):
            self.m.audit_split(parts)
        parts = self.m.make_split(self.m.prepare_real(real_rows()), synthetic_rows())
        parts['test'][0]['source']='synthetic'
        with self.assertRaises(ValueError):
            self.m.audit_split(parts)
        parts = self.m.make_split(self.m.prepare_real(real_rows()), synthetic_rows())
        parts['validation'][0]['group'] = parts['test'][0]['group']
        with self.assertRaises(ValueError):
            self.m.audit_split(parts)

    def test_cli_roundtrip_refuses_overwrite_and_detects_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            real=folder/'real.jsonl'; synth=folder/'synthetic.jsonl'; out=folder/'split'
            for p, rows in ((real,real_rows()),(synth,synthetic_rows())):
                p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
            cmd=[sys.executable,str(MODULE),'prepare','--real',str(real),'--synthetic',str(synth),'--out',str(out)]
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('虛構樣本',result.stdout+result.stderr)
            check=[sys.executable,str(MODULE),'check','--dataset',str(out)]
            self.assertEqual(subprocess.run(check,capture_output=True).returncode,0)
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            with (out/'test.jsonl').open('a',encoding='utf-8') as f: f.write('{}\n')
            self.assertNotEqual(subprocess.run(check,capture_output=True).returncode,0)

    def test_normalized_aliases_count_as_one_independent_item(self):
        rows = real_rows(1)
        for i in range(1, 8):
            rows.append(dict(rows[0], id=f"alias-{i}", name=" " + rows[0]['name'] + " " * i))
        prepared = self.m.prepare_real(rows)
        self.assertEqual(len(prepared), 10)
        self.assertEqual(sum(r['category'] == 0 for r in prepared), 1)
        parts = self.m.make_split(prepared, synthetic_rows())
        self.assertEqual(parts['test'], [])
        self.assertEqual(parts['validation'], [])
        duplicate = dict(parts['train'][0], id='duplicate-alias-id')
        parts['train'].append(duplicate)
        with self.assertRaises(ValueError):
            self.m.audit_split(parts)

    def test_check_requires_provenance_and_handles_nonobject_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            real=folder/'real.jsonl'; synth=folder/'synthetic.jsonl'; out=folder/'split'
            for p, rows in ((real,real_rows()),(synth,synthetic_rows())):
                p.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
            self.m.save_dataset(real,synth,out)
            manifest_path=out/'manifest.json'
            original=json.loads(manifest_path.read_text(encoding='utf-8'))
            for field in ('source_sha256','seed','evaluation_status','group_review_status','legacy_real_declared'):
                changed=dict(original);del changed[field]
                manifest_path.write_text(json.dumps(changed),encoding='utf-8')
                with self.subTest(missing=field), self.assertRaises(ValueError):
                    self.m.check_dataset(out)
            for change in ({'seed':True},{'source_sha256':{'real':'invalid','synthetic':'invalid'}},
                           {'evaluation_status':'independent_final_test'}):
                manifest_path.write_text(json.dumps(dict(original,**change)),encoding='utf-8')
                with self.subTest(change=change),self.assertRaises(ValueError):
                    self.m.check_dataset(out)
            manifest_path.write_text('[]',encoding='utf-8')
            result=subprocess.run([sys.executable,str(MODULE),'check','--dataset',str(out)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('Traceback',result.stderr)

    def test_cli_bad_private_input_is_not_echoed(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.jsonl'; p.write_text('SECRET_PRIVATE_NAME',encoding='utf-8')
            result=subprocess.run([sys.executable,str(MODULE),'prepare','--real',str(p),'--synthetic',str(p),'--out',str(Path(folder)/'out')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('SECRET_PRIVATE_NAME',result.stdout+result.stderr)


if __name__=='__main__': unittest.main()
