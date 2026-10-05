import json
import unittest

from build_report_data import ROOT, build_month


class ReportDataTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "item-categories.json").read_text(encoding="utf-8"))

    def test_csv_footer_excluded_and_totals_reconciled(self):
        for filename, count, invoices, amount, days in [
            ("0301-0331.csv", 35, 20, 4392, 31),
            ("0401-0430.csv", 52, 33, 10817, 30),
        ]:
            key, month = build_month(ROOT / filename, self.catalog)
            rows = month["rows"]
            self.assertEqual(len(rows), count)
            self.assertEqual(len({row["invoice"] for row in rows}), invoices)
            self.assertEqual(sum(row["amount"] for row in rows), amount)
            self.assertEqual(month["days"], days)
            self.assertTrue(all(1 <= row["day"] <= days for row in rows))
            self.assertTrue(all(row["invoice"].startswith(key + "-R") for row in rows))
            self.assertTrue(all(set(row) == {"day", "invoice", "merchant", "name", "quantity", "amount", "category", "provisional"} for row in rows))

    def test_discount_and_points_are_retained(self):
        _, month = build_month(ROOT / "0401-0430.csv", self.catalog)
        adjustments = [row for row in month["rows"] if row["amount"] < 0]
        self.assertEqual(sorted(row["amount"] for row in adjustments), [-100, -42])
        self.assertTrue(all(row["category"] == 0 for row in adjustments))

    def test_same_sport_item_matches_across_months(self):
        for filename in ["0301-0331.csv", "0401-0430.csv"]:
            _, month = build_month(ROOT / filename, self.catalog)
            sport = [row for row in month["rows"] if row["category"] == 4]
            self.assertEqual(len({row["invoice"] for row in sport}), 7)
            self.assertEqual(sum(row["amount"] for row in sport), 350)


if __name__ == "__main__":
    unittest.main()
