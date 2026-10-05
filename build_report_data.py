"""Build local, anonymized monthly data from the supplied invoice CSV files."""

import calendar
import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATEGORIES = [
    ("正餐", "#df646b"), ("飲品", "#d9b078"),
    ("零食甜點", "#e79681"), ("生鮮食材", "#89b6ed"),
    ("運動", "#b2a0cf"), ("其他服務", "#a4b8a8"),
    ("交通", "#7fbfc5"), ("住宿", "#91a1d5"),
    ("日用品", "#b1bf83"), ("電子產品", "#c993b0"),
    ("待確認", "#b5b5b5"),
]


def build_month(path, catalog):
    rows, invoice_ids = [], {}
    month_key = None
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if not row.get("發票日期"):
                continue  # CSV export footer, not a transaction.
            if row["發票狀態"] != "開立已確認":
                raise ValueError("Unreviewed invoice status: " + row["發票狀態"])
            date = datetime.strptime(row["發票日期"], "%Y%m%d")
            key = date.strftime("%Y-%m")
            if month_key and month_key != key:
                raise ValueError("Expected one month per CSV")
            month_key = key
            name = row["消費明細_品名"].strip()
            category = catalog.get(name, {"category": 10, "provisional": True})
            original_id = row["發票號碼"]
            invoice_ids.setdefault(original_id, f"{key}-R{len(invoice_ids) + 1:02}")
            rows.append({
                "day": date.day,
                "invoice": invoice_ids[original_id],
                "merchant": row["賣方名稱"],
                "name": name,
                "quantity": int(row["消費明細_數量"]),
                "amount": int(row["消費明細_金額"]),
                **category,
            })
    if not rows:
        raise ValueError("No invoice records")
    year, month = map(int, month_key.split("-"))
    return month_key, {
        "year": year, "monthNumber": month, "month": f"{year} 年 {month} 月",
        "days": calendar.monthrange(year, month)[1], "source": path.name,
        "rows": sorted(rows, key=lambda row: row["day"]),
    }


def main():
    catalog = json.loads((ROOT / "item-categories.json").read_text(encoding="utf-8"))
    months = dict(build_month(ROOT / name, catalog)
                  for name in ("0301-0331.csv", "0401-0430.csv"))
    data = {"categories": [{"name": name, "color": color} for name, color in CATEGORIES],
            "months": months}
    (ROOT / "report-data.js").write_text(
        "'use strict';\nconst expenseReportData = "
        + json.dumps(data, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    for key, month in months.items():
        print(key, len(month["rows"]), "rows; total", sum(row["amount"] for row in month["rows"]))


if __name__ == "__main__":
    main()
