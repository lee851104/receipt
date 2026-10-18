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
        self.assertTrue(all(set(row) == {"day", "invoice", "merchant", "district", "name", "quantity", "amount", "category", "provisional"} for row in rows))

    def test_mixed_months_rejected(self):
        self.write_rows([[date, "開立已確認", "X", "測試商店", "測試餐盒", 1, 120] for date in ("20260301", "20260401")])
        with self.assertRaisesRegex(ValueError, "one month"):
            build_month(self.path, self.catalog)

    def test_unreviewed_invoice_rejected(self):
        self.write_rows([["20260301", "作廢", "X", "測試商店", "測試餐盒", 1, 120]])
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            build_month(self.path, self.catalog)

    def test_district_replaces_full_address_and_tax_id(self):
        fields = ["發票日期", "發票狀態", "發票號碼", "賣方名稱", "賣方地址", "賣方統一編號", "消費明細_品名", "消費明細_數量", "消費明細_金額"]
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow(dict(zip(fields, ["20260302", "開立已確認", "X1", "測試商店", "802高雄市苓雅區測試路99號", "TEST-TAX-ID", "測試餐盒", 1, 120])))
        _, month = build_month(self.path, self.catalog)
        self.assertEqual(month["rows"][0]["district"], "高雄市苓雅區")
        self.assertNotIn("測試路", str(month))
        self.assertNotIn("TEST-TAX-ID", str(month))

    def test_an_upload_skips_voided_invoices(self):
        self.write_rows([
            ["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, 120],
            ["20260503", "作廢已確認", "A2", "測試商店", "測試餐盒", 1, 120],
            ["20260504", "作廢", "A3", "測試商店", "測試餐盒", 1, 120],
        ])
        _, month = build_month(self.path, self.catalog, for_upload=True)
        self.assertEqual([row["day"] for row in month["rows"]], [2])

    def test_an_upload_skips_small_and_decimal_amounts(self):
        self.write_rows([
            ["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 2, 240],
            ["20260502", "開立已確認", "A1", "測試商店", "測試折扣", 1, -20],
            ["20260502", "開立已確認", "A1", "測試商店", "未知贈品", 1, 0],
            ["20260502", "開立已確認", "A1", "測試商店", "測試小物", 1, 9],
            ["20260502", "開立已確認", "A1", "測試商店", "測試秤重", 1, "35.5"],
            ["20260503", "開立已確認", "A2", "測試商店", "測試十元", 1, 10],
        ])
        _, month = build_month(self.path, self.catalog, for_upload=True)
        self.assertEqual([(row["name"], row["amount"]) for row in month["rows"]], [("測試餐盒", 240), ("測試十元", 10)])
        self.assertEqual([row["invoice"] for row in month["rows"]], ["2026-05-R01", "2026-05-R02"])

    def test_an_upload_skips_a_line_without_a_product_name_and_never_reads_its_quantity(self):
        # A name is blank when nothing is left after strip(): empty, spaces, a tab, the wide space of CJK text.
        wide_space = chr(0x3000)
        self.write_rows([
            ["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, 120],
            ["20260502", "開立已確認", "A1", "測試商店", "", "abc", 80],
            ["20260503", "開立已確認", "A2", "測試商店", "   ", "", 90],
            ["20260503", "開立已確認", "A2", "測試商店", f" \t{wide_space} ", "30.5", 10],
            ["20260504", "開立已確認", "A3", "測試商店", "測試餐盒", 1, 150],
        ])
        _, month = build_month(self.path, self.catalog, for_upload=True)
        # The blank-named lines are neither counted nor analysed, and a quantity that is no number does not fail the
        # upload. A2 holds only blank-named lines, so it gets no code and A3 is R02.
        self.assertEqual([(row["name"], row["amount"], row["invoice"]) for row in month["rows"]],
                         [("測試餐盒", 120, "2026-05-R01"), ("測試餐盒", 150, "2026-05-R02")])

    def test_an_upload_keeps_a_line_whose_name_is_only_padded_with_spaces(self):
        self.write_rows([["20260502", "開立已確認", "A1", "測試商店", "  測試餐盒 ", 1, 120]])
        _, month = build_month(self.path, self.catalog, for_upload=True)
        self.assertEqual([row["name"] for row in month["rows"]], ["測試餐盒"])

    def test_the_v1_reading_keeps_a_line_without_a_product_name(self):
        self.write_rows([["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, 120],
                         ["20260502", "開立已確認", "A1", "測試商店", "  ", 1, 80]])
        _, month = build_month(self.path, self.catalog)
        self.assertEqual([(row["name"], row["amount"]) for row in month["rows"]], [("測試餐盒", 120), ("", 80)])

    def test_an_upload_counts_a_decimal_quantity_as_one_and_reads_whole_numbers_written_with_a_point(self):
        self.write_rows([["20260502", "開立已確認", "A1", "測試加油站", "測試汽油", "30.5", 900],
                         ["20260502", "開立已確認", "A1", "測試加油站", "測試洗車", "2.0", "240.0"]])
        _, month = build_month(self.path, self.catalog, for_upload=True)
        self.assertEqual([(row["quantity"], row["amount"]) for row in month["rows"]], [(1, 900), (2, 240)])

    def test_an_upload_gives_codes_only_to_invoices_with_kept_lines(self):
        self.write_rows([["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, 120],
                         ["20260503", "開立已確認", "A2", "測試商店", "測試折扣", "", -20],
                         ["20260504", "開立已確認", "A3", "測試商店", "測試餐盒", 1, 120]])
        _, month = build_month(self.path, self.catalog, for_upload=True)
        # A2 holds only a discount (whose blank quantity is never read), so it gets no code and A3 is R02.
        self.assertEqual([row["invoice"] for row in month["rows"]], ["2026-05-R01", "2026-05-R02"])

    def test_an_upload_names_a_cell_that_is_no_number_and_refuses_short_lines(self):
        for amount in ("", "abc", "nan", "inf"):
            with self.subTest(amount=amount):
                self.write_rows([["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, amount]])
                with self.assertRaisesRegex(ValueError, "^Line 2: 消費明細_金額 is not a number$"):
                    build_month(self.path, self.catalog, for_upload=True)
        self.write_rows([["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, "9" * 20]])
        with self.assertRaisesRegex(ValueError, "^Line 2: 消費明細_金額 is too large$"):
            build_month(self.path, self.catalog, for_upload=True)
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            header = ",".join(["發票日期", "發票狀態", "發票號碼", "賣方名稱", "消費明細_品名", "消費明細_數量", "消費明細_金額"])
            stream.write(header + chr(10) + "20260502,開立已確認,A1" + chr(10))
        with self.assertRaisesRegex(ValueError, "fewer columns"):
            build_month(self.path, self.catalog, for_upload=True)

    def test_an_upload_points_at_the_line_and_column_of_a_bad_cell_without_repeating_it(self):
        # In a line whose columns have shifted, any cell can hold a piece of a product name, which must not reach
        # the message the page shows.
        good = ["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, 120]
        secret = "測試祕密品名"
        cases = [(0, "Line 3: 發票日期 is not a date written YYYYMMDD"),
                 (1, "Line 3: Unreviewed invoice status in 發票狀態"),
                 (5, "Line 3: 消費明細_數量 is not a number"),
                 (6, "Line 3: 消費明細_金額 is not a number")]
        for column, message in cases:
            with self.subTest(message=message):
                bad = list(good)
                bad[column] = secret
                self.write_rows([good, bad])
                with self.assertRaises(ValueError) as caught:
                    build_month(self.path, self.catalog, for_upload=True)
                self.assertEqual(str(caught.exception), message)

    def test_an_upload_still_counts_a_skipped_line_from_another_month(self):
        self.write_rows([["20260502", "開立已確認", "A1", "測試商店", "測試餐盒", 1, 120],
                         ["20260601", "開立已確認", "A2", "測試商店", "測試折扣", 1, -20]])
        with self.assertRaisesRegex(ValueError, "one month"):
            build_month(self.path, self.catalog, for_upload=True)

    def test_an_upload_names_missing_columns_and_still_refuses_unknown_statuses(self):
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            stream.write("發票日期,發票狀態,發票號碼,賣方名稱,消費明細_數量,消費明細_金額\n"
                         "20260502,開立已確認,A1,測試商店,1,120\n")
        with self.assertRaisesRegex(ValueError, "Missing column: 消費明細_品名"):
            build_month(self.path, self.catalog, for_upload=True)
        self.write_rows([["20260502", "開立待確認", "A1", "測試商店", "測試餐盒", 1, 120]])
        with self.assertRaisesRegex(ValueError, "^Line 2: Unreviewed invoice status in 發票狀態$"):
            build_month(self.path, self.catalog, for_upload=True)

    def test_an_upload_of_only_skipped_lines_has_no_records(self):
        self.write_rows([["20260502", "作廢已確認", "A1", "測試商店", "測試餐盒", 1, 120],
                         ["20260502", "開立已確認", "A2", "測試商店", "測試折扣", 1, -5]])
        with self.assertRaisesRegex(ValueError, "No invoice records"):
            build_month(self.path, self.catalog, for_upload=True)

    def test_an_upload_of_only_lines_without_a_product_name_has_no_records(self):
        self.write_rows([["20260502", "開立已確認", "A1", "測試商店", "", 1, 120],
                         ["20260503", "開立已確認", "A2", "測試商店", "   ", "abc", 80]])
        with self.assertRaisesRegex(ValueError, "No invoice records"):
            build_month(self.path, self.catalog, for_upload=True)


if __name__ == "__main__":
    unittest.main()
