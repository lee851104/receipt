"""Parse invoice exports into classified records with coded invoice IDs."""

import calendar
import csv
import math
from datetime import datetime

from .address import parse_district

REQUIRED = ("發票日期", "發票狀態", "發票號碼", "賣方名稱", "消費明細_品名", "消費明細_數量", "消費明細_金額")
MIN_AMOUNT = 10  # an uploaded line below this (a discount, a free item, small change) is not analysed


def whole(text, column):
    """The integer a CSV cell holds (12, or 12.0), or None for a true decimal such as 4.49; a cell that is no finite
    number raises a ValueError naming the column."""
    try:
        number = float(text)
    except (TypeError, ValueError):
        number = math.nan
    if not math.isfinite(number):
        raise ValueError(f"{column} is not a number: {text!r}")
    return int(number) if number.is_integer() else None


def build_month(path, catalog, for_upload=False):
    """One month of an invoice export as report rows.

    An upload (for_upload=True) follows the invoice-ingestion rules: every required column must be there, voided
    invoices (a status starting with 作廢) are skipped, lines under MIN_AMOUNT or with a decimal amount are skipped,
    and a decimal quantity (litres of fuel, weighed goods) counts as 1. Without it the v1 report reads exactly as
    before."""
    rows, invoice_ids = [], {}
    month_key = None
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if for_upload:
            missing = [column for column in REQUIRED if column not in (reader.fieldnames or [])]
            if missing:
                raise ValueError("Missing column: " + ", ".join(missing))
        for row in reader:
            if not row.get("發票日期"):
                continue  # CSV export footer, not a transaction.
            if for_upload and any(row.get(column) is None for column in REQUIRED):
                raise ValueError("A line has fewer columns than the header")
            if for_upload and row["發票狀態"].startswith("作廢"):
                continue  # A voided invoice was never a purchase.
            if row["發票狀態"] != "開立已確認":
                raise ValueError(f"Unreviewed invoice status: {row['發票狀態']!r}")
            date = datetime.strptime(row["發票日期"], "%Y%m%d")
            key = date.strftime("%Y-%m")
            if month_key and month_key != key:
                raise ValueError("Expected one month per CSV")
            month_key = key
            if for_upload:
                # The amount decides first, so a skipped line's quantity is never read and cannot spoil the upload.
                amount = whole(row["消費明細_金額"], "消費明細_金額")
                if amount is None or amount < MIN_AMOUNT:
                    continue
                quantity = whole(row["消費明細_數量"], "消費明細_數量")
                if quantity is None:
                    quantity = 1
            else:
                amount, quantity = int(row["消費明細_金額"]), int(row["消費明細_數量"])
            name = row["消費明細_品名"].strip()
            category = catalog.get(name, {"category": 10, "provisional": True})
            original_id = row["發票號碼"]
            invoice_ids.setdefault(original_id, f"{key}-R{len(invoice_ids) + 1:02}")
            rows.append({
                "day": date.day,
                "invoice": invoice_ids[original_id],
                "merchant": row["賣方名稱"],
                "district": parse_district(row.get("賣方地址")),
                "name": name,
                "quantity": quantity,
                "amount": amount,
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
