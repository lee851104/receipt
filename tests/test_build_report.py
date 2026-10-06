"""Exercise the public build command with synthetic data, without private files."""
import csv
import json
import re
from html import unescape
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if (tag == "script" and "src" in attrs) or (tag == "link" and attrs.get("rel") == "stylesheet"):
            self.external.append(attrs)
        if tag == "script":
            self.scripts.append(attrs)


class StandaloneBuildTests(unittest.TestCase):
    def test_default_build_ignores_private_sources_and_preserves_private_html(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "project"
            project.mkdir()
            for name in ("src", "configs", "scripts"):
                shutil.copytree(ROOT / name, project / name, ignore=shutil.ignore_patterns("__pycache__"))
            private = project / "data" / "private"
            private.mkdir(parents=True)
            (private / "report.json").write_text("PRIVATE-SOURCE-MUST-NOT-BE-READ", encoding="utf-8")
            original = project / "invoice-insights-private.html"
            original.write_text("PRIVATE-HTML-UNCHANGED", encoding="utf-8")
            command = [sys.executable, str(project / "scripts" / "build_report.py")]
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (project / "invoice-insights.html").read_text(encoding="utf-8")
            self.assertIn('"isDemo": true', html)
            self.assertIn("虛構示範", html)
            self.assertNotIn("PRIVATE-", html)
            self.assertEqual(original.read_text(), "PRIVATE-HTML-UNCHANGED")
            self.assertFalse((project / "taste-comparison.html").exists())
            embedded = re.search(r'<template id="taste-page-source">(.*?)</template>', html, re.S)
            self.assertIsNotNone(embedded)
            comparison = unescape(embedded.group(1))
            compared = ResourceParser()
            compared.feed(comparison)
            self.assertEqual(compared.external, [])
            self.assertIn("receipt-taste/categories-v1", comparison)
            parsed = ResourceParser()
            parsed.feed(html)
            self.assertEqual(parsed.external, [])
            repeat = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(repeat.returncode, 0, repeat.stderr)
            self.assertEqual((project / "invoice-insights.html").read_text(encoding="utf-8"), html)

    def test_build_from_another_directory_is_self_contained_and_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "project"
            project.mkdir()
            for name in ("src", "configs", "scripts"):
                source = ROOT / name
                if source.exists():
                    shutil.copytree(source, project / name, ignore=shutil.ignore_patterns("__pycache__"))
            (project / "configs").mkdir(exist_ok=True)
            (project / "data" / "raw").mkdir(parents=True)
            categories = ["正餐", "飲品", "零食甜點", "生鮮食材", "運動", "其他服務", "交通", "住宿", "日用品", "電子產品", "待確認"]
            config = {
                "input_files": ["data/raw/march.csv", "data/raw/april.csv"],
                "category_catalog": "configs/item-categories.json",
                "categories": [{"name": name, "color": "#aabbcc"} for name in categories],
            }
            (project / "data" / "private").mkdir()
            (project / "data" / "private" / "report.json").write_text(json.dumps(config), encoding="utf-8")
            (project / "configs" / "item-categories.json").write_text('{"茶": {"category": 1, "provisional": false}}', encoding="utf-8")
            for name, date in (("march.csv", "20260301"), ("april.csv", "20260401")):
                row = {"發票日期": date, "發票狀態": "開立已確認", "發票號碼": "PRIVATE-INVOICE-001", "賣方名稱": "測試商店", "賣方地址": "PRIVATE-ADDRESS", "載具號碼": "PRIVATE-CARRIER", "消費明細_品名": "茶", "消費明細_數量": "1", "消費明細_金額": "30"}
                with (project / "data" / "raw" / name).open("w", encoding="utf-8-sig", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=row.keys())
                    writer.writeheader()
                    writer.writerow(row)
            command = [sys.executable, str(project / "scripts" / "build_report.py"), "--private"]
            first = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            report = project / "invoice-insights-private.html"
            self.assertFalse((project / "invoice-insights.html").exists())
            before = report.read_bytes()
            html = before.decode("utf-8")
            self.assertIn('"2026-03"', html)
            self.assertIn('"2026-04"', html)
            self.assertIn('"amount": 30', html)
            for private_value in ("PRIVATE-INVOICE-001", "PRIVATE-ADDRESS", "PRIVATE-CARRIER"):
                self.assertNotIn(private_value, html)
            parsed = ResourceParser()
            parsed.feed(html)
            self.assertEqual(parsed.external, [])
            self.assertEqual(len(parsed.scripts), 8)
            self.assertTrue((project / "data" / "private" / "report-data.js").is_file())
            self.assertNotIn('"PRIVATE-INVOICE-001"', (project / "src" / "web" / "invoice-insights.html").read_text(encoding="utf-8"))
            second = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(report.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
