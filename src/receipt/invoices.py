"""Parse invoice exports into classified records with coded invoice IDs."""

import calendar
import csv
from datetime import datetime


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
