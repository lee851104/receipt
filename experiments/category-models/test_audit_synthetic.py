"""Synthetic corpus audit regression tests (only fictional names)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE=Path(__file__).with_name('audit_synthetic.py')

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(),'audit_synthetic.py must implement privacy checks')
        spec=importlib.util.spec_from_file_location('audit_synthetic',MODULE)
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)

    def test_short_csv_row_and_empty_name_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.csv'
            p.write_text('發票日期,消費明細_品名\n2026-01-01\n2026-01-02,\n2026-01-03,ＡＢＣ 茶\n',encoding='utf-8-sig')
            self.assertEqual(self.m.private_keys([p],[],[]),{'abc茶'})

    def test_public_report_scan_returns_counts_without_echoing_private_names(self):
        import json,subprocess,sys
        from synthetic_names import build_rows
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            synthetic=folder/'synthetic.jsonl'
            synthetic.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in build_rows()),encoding='utf-8')
            reviewed=folder/'reviewed.jsonl'
            reviewed.write_text(json.dumps({'name':'虛構私密ＡＢＣ 茶'})+'\n',encoding='utf-8')
            report=folder/'report.md'
            report.write_text('\n\n公開段落內含 虛構私密abc茶 的測試文字',encoding='utf-8')
            command=[sys.executable,str(MODULE),'--synthetic',str(synthetic),'--reviewed',str(reviewed),'--public-text',str(report)]
            private_review=folder/'private-review.json'
            result=subprocess.run(command+['--local-match-report',str(private_review)],capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            details=json.loads(private_review.read_text(encoding='utf-8'))
            self.assertEqual(details[0]['matches'][0]['normalized_name'],'虛構私密abc茶')
            self.assertEqual(details[0]['matches'][0]['line_numbers'],[3])
            self.assertEqual(json.loads(result.stdout)['public_text_private_matches'],1)
            self.assertNotIn('虛構私密',result.stdout+result.stderr)
            report.write_text('只有彙總數字 7/7',encoding='utf-8')
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0)
            self.assertEqual(json.loads(result.stdout)['public_text_private_matches'],0)

    def test_invalid_csv_header_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.csv';p.write_text('wrong,column\n1,2\n',encoding='utf-8')
            with self.assertRaises(ValueError):self.m.private_keys([p],[],[])

    def test_catalog_and_reviewed_sources_compare_normalized_names(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'catalog.json';p.write_text('{"虛構茶": {"category":1}}',encoding='utf-8')
            r=Path(d)/'reviewed.jsonl';r.write_text('{"name":"ＡＢＣ 茶"}\n',encoding='utf-8')
            self.assertEqual(self.m.private_keys([],[p],[r]),{'虛構茶','abc茶'})

if __name__=='__main__':unittest.main()
