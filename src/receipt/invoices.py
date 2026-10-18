"""Parse invoice exports into classified records with coded invoice IDs."""

import calendar
import csv
import math
from datetime import datetime

from .address import parse_district

REQUIRED = ("發票日期", "發票狀態", "發票號碼", "賣方名稱", "消費明細_品名", "消費明細_數量", "消費明細_金額")
MIN_AMOUNT = 10  # an uploaded line below this (a discount, a free item, small change) is not analysed
MAX_NUMBER = 10**9  # far above any receipt line, far below what a database integer holds


def whole(text, column, line):
    """The integer a CSV cell holds (12, or 12.0), or None for a true decimal such as 4.49; a cell that is no finite
    number, or one too large for any receipt, raises a ValueError naming the line and column. Never the cell itself:
    in a line whose columns have shifted it can be a piece of a product name, and the page shows the message."""
    try:
        number = float(text)
    except (TypeError, ValueError):
        number = math.nan
    if not math.isfinite(number):
        raise ValueError(f"Line {line}: {column} is not a number")
    if abs(number) > MAX_NUMBER:
        raise ValueError(f"Line {line}: {column} is too large")
    return int(number) if number.is_integer() else None


def build_month(path, catalog, for_upload=False):
    """One month of an invoice export as report rows.

    An upload (for_upload=True) follows the invoice-ingestion rules: every required column must be there, voided
    invoices (a status starting with 作廢) are skipped, lines under MIN_AMOUNT or with a decimal amount are skipped,
    so are lines whose product name is blank, and a decimal quantity (litres of fuel, weighed goods) counts as 1. Without it the v1 report reads exactly as
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
            line = reader.line_num  # an upload's errors name the line and column, never a cell (see whole)
            if for_upload and any(row.get(column) is None for column in REQUIRED):
                raise ValueError(f"Line {line} has fewer columns than the header")
            if for_upload and row["發票狀態"].startswith("作廢"):
                continue  # A voided invoice was never a purchase.
            if row["發票狀態"] != "開立已確認":
                if for_upload:
                    raise ValueError(f"Line {line}: Unreviewed invoice status in 發票狀態")
                raise ValueError(f"Unreviewed invoice status: {row['發票狀態']!r}")
            try:
                date = datetime.strptime(row["發票日期"], "%Y%m%d")
            except ValueError:
                if not for_upload:
                    raise
                raise ValueError(f"Line {line}: 發票日期 is not a date written YYYYMMDD") from None
            key = date.strftime("%Y-%m")
            if month_key and month_key != key:
                raise ValueError("Expected one month per CSV")
            month_key = key
            if for_upload:
                # The amount decides first, so a skipped line's quantity is never read and cannot spoil the upload.
                amount = whole(row["消費明細_金額"], "消費明細_金額", line)
                if amount is None or amount < MIN_AMOUNT:
                    continue
                # A line with no name is skipped the same way: nothing can be said about it, and the real category
                # model refuses an empty name, which would fail the whole month's job.
                if not row["消費明細_品名"].strip():
                    continue
                quantity = whole(row["消費明細_數量"], "消費明細_數量", line)
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
