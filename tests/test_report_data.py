"""Verify CSV parsing with fictional records only."""
import csv
import tempfile
import unittest
from pathlib import Path
from src.receipt.invoices import build_month


class ReportDataTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "fixture.csv"
        self.catalog = {"測試餐盒": {"category": 0, "provisional": False}, "測試折扣": {"category": 0, "provisional": False}}

    def write_rows(self, rows):
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["發票日期", "發票狀態", "發票號碼", "賣方名稱", "消費明細_品名", "消費明細_數量", "消費明細_金額"])
            writer.writeheader()
            for values in rows:
                writer.writerow(dict(zip(writer.fieldnames, values)))
            writer.writerow({"賣方名稱": "匯出摘要"})

    def test_footer_discount_free_item_and_private_id(self):
        self.write_rows([
            ["20260302", "開立已確認", "PRIVATE-ID", "測試商店", "測試餐盒", 2, 240],
            ["20260302", "開立已確認", "PRIVATE-ID", "測試商店", "測試折扣", 1, -20],
            ["20260305", "開立已確認", "PRIVATE-ID-2", "測試商店", "未知贈品", 1, 0],
        ])
        key, month = build_month(self.path, self.catalog)
        self.assertEqual(key, "2026-03")
        self.assertEqual(month["days"], 31)
        rows = month["rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(row["amount"] for row in rows), 220)
        self.assertEqual(len({row["invoice"] for row in rows}), 2)
        self.assertEqual(rows[0]["quantity"], 2)
        self.assertEqual(rows[1]["category"], 0)
        self.assertEqual(rows[2]["category"], 10)
        self.assertTrue(rows[2]["provisional"])
        self.assertNotIn("PRIVATE-ID", str(rows))
        self.assertTrue(all(set(row) == {"day", "invoice", "merchant", "name", "quantity", "amount", "category", "provisional"} for row in rows))

    def test_mixed_months_rejected(self):
        self.write_rows([[date, "開立已確認", "X", "測試商店", "測試餐盒", 1, 120] for date in ("20260301", "20260401")])
        with self.assertRaisesRegex(ValueError, "one month"):
            build_month(self.path, self.catalog)

    def test_unreviewed_invoice_rejected(self):
        self.write_rows([["20260301", "作廢", "X", "測試商店", "測試餐盒", 1, 120]])
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            build_month(self.path, self.catalog)


if __name__ == "__main__":
    unittest.main()
