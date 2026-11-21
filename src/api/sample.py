"""A fictional e-invoice CSV for trying an upload: forty lines in one month, twice the 20 items a taste profile needs.

The names come from the reviewed synthetic attribute cache (all start with 示範), so the demo's qwen model answers them
from the cache without a GPU, and only names holding a word the fake category model is sure of are used, so none of
them lands in 10 待確認 with CATEGORY_MODEL=fake. Nothing here comes from a real receipt. scripts/make_demo_upload.py
writes it to a file; in DEMO_MODE the dating app offers it for download (GET /api/dating/sample-invoices).
"""
import csv
import io
import json
import random
from pathlib import Path

from ..ml.fakes import KEYWORDS

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "datasets/synthetic/attribute-cache.jsonl"
COLUMNS = ["發票日期", "發票狀態", "發票號碼", "賣方名稱", "賣方地址", "消費明細_品名", "消費明細_數量", "消費明細_金額"]
SHOPS = (("示範便利商店", "臺北市大安區示範路1號"), ("示範生活超市", "臺北市信義區示範路2號"))
LINES = 40


def demo_names():
    """Reviewed fictional names the fake category model is sure of, a few per category, in a fixed order."""
    words = [(category, word) for category, group in KEYWORDS for word in group]
    names = [json.loads(line)["name"] for line in CACHE.read_text(encoding="utf-8").splitlines()]
    picked = []
    for category, _ in KEYWORDS:
        mine = [name for name in names if any(word in name for c, word in words if c == category)]
        picked.extend(mine[:4])
    return picked


def demo_rows(month="2026-06", variant=0):
    """LINES invoice lines across the month: one line per invoice, two shops, whole-dollar amounts. A variant above 0
    buys a different mix of the same names, so two people trying the sample do not get the very same taste."""
    names = demo_names()
    if variant:
        rng = random.Random(f"sample-{variant}")
        names = [name for name in names if rng.random() < 0.75] * 2 + rng.sample(names, k=len(names) // 3)
        rng.shuffle(names)
    yyyymm = month.replace("-", "")
    rows = []
    for index in range(LINES):
        shop, address = SHOPS[index % len(SHOPS)]
        invoice = f"DEMO-{yyyymm}-{index:03}"
        rows.append([f"{yyyymm}{index % 28 + 1:02}", "開立已確認", invoice, shop, address,
                     names[index % len(names)], 1, 35 + index % 6 * 15])
    return rows


def demo_csv(month="2026-06", variant=0):
    """The file's bytes: UTF-8 with a BOM, the export's columns and its footer line, like a real export."""
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    writer.writerows(demo_rows(month, variant))
    writer.writerow(["", "", "", "匯出摘要"])
    return (chr(0xFEFF) + stream.getvalue()).encode("utf-8")
