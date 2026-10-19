"""Coverage regressions using the public brief and synthetic names only."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).with_name('synthetic_names.py')
ROOT = Path(__file__).resolve().parents[2]

# Independent coverage oracle derived from the brief, not from generator metadata.
REQUIRED = {
    0: [('便當',), ('牛肉麵',), ('水餃',), ('漢堡',), ('三明治',), ('飯糰',), ('套餐',), ('白飯',), ('荷包蛋',), ('小菜',)],
    1: [('奶茶',), ('美式',), ('綠茶',), ('啤酒',), ('鮮奶','鮮乳'), ('礦泉水',)],
    2: [('洋芋片',), ('布丁',), ('可頌',), ('蛋糕',), ('冰淇淋',), ('豆花',)],
    3: [('高麗菜',), ('雞胸',), ('雞蛋',), ('白米',), ('醬油',), ('香蕉',)],
    4: [('健身房',), ('游泳',), ('重訓',), ('乳清',), ('能量膠',), ('電解質',), ('肌酸',)],
    5: [('電影',), ('KTV',), ('密室',), ('洗衣',), ('餐廳服務費',)],
    6: [('高鐵',), ('客運',), ('汽油','無鉛'), ('柴油',), ('充電',), ('換電',), ('停車',)],
    7: [('旅館',), ('民宿',), ('雙人房',)],
    8: [('衛生紙',), ('洗衣',), ('牙膏',), ('筆記本',), ('貓砂',), ('犬糧','狗飼料'), ('尿布墊',), ('逗貓棒',), ('牽繩',), ('香氛蠟燭',)],
    9: [('耳機',), ('傳輸線',), ('行動電源',), ('鍵盤',), ('滑鼠',)],
}


class SyntheticNamesTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'public reproducible synthetic generator is required')
        spec = importlib.util.spec_from_file_location('synthetic_names', MODULE)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)

    def test_each_subtype_has_ten_with_three_receipt_style_names(self):
        summary = self.m.coverage()
        self.assertEqual(set(summary), set(range(10)))
        for category, entry in summary.items():
            with self.subTest(category=category):
                self.assertEqual(entry['total'], 60)
                self.assertEqual(entry['receipt_style'], 18)
                self.assertEqual(len(entry['subtypes']), 6)
                for subtype in entry['subtypes'].values():
                    self.assertEqual(subtype, {'total': 10, 'receipt_style': 3})

    def test_brief_examples_and_missing_subtypes_are_in_exported_names(self):
        rows = self.m.build_rows()
        self.assertEqual(len(rows), 600)
        for category, requirements in REQUIRED.items():
            names = [r['name'] for r in rows if r['category'] == category]
            for alternatives in requirements:
                with self.subTest(category=category, alternatives=alternatives):
                    self.assertTrue(any(any(word in name for word in alternatives) for name in names))

    def test_uncertain_sports_equipment_excluded(self):
        forbidden = ('球鞋', '瑜伽墊', '運動鞋', '羽球拍', '籃球鞋', '運動手套')
        self.assertFalse(any(word in r['name'] for r in self.m.build_rows() for word in forbidden))

    def test_export_schema_dedup_and_checked_in_file_reproduce(self):
        from dataset_split import key, validate_synthetic
        rows = self.m.build_rows()
        self.assertEqual(len(validate_synthetic(rows)), 600)
        self.assertEqual(len({key(r['name']) for r in rows}), 600)
        self.assertTrue(all(set(r) == {'name','category','source'} and r['source'] == 'synthetic' for r in rows))
        self.assertEqual(self.m.render(), (ROOT/'datasets/synthetic/item-names.jsonl').read_bytes())

    def test_cli_roundtrip_refuses_overwrite_and_checks_staleness(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'synthetic.jsonl'
            cmd = [sys.executable, str(MODULE), '--out', str(out)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['total'], 600)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(cmd+['--check'], capture_output=True).returncode, 0)
            out.write_text('{}\n', encoding='utf-8')
            self.assertNotEqual(subprocess.run(cmd+['--check'], capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(cmd+['--force'], capture_output=True).returncode, 0)
            self.assertEqual(out.read_bytes(), self.m.render())


if __name__ == '__main__': unittest.main()
