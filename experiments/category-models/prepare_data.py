"""Validate reviewed labels or prepare them from invoice CSVs and a catalog."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import unicodedata


CATEGORIES = ("正餐", "飲品", "零食甜點", "生鮮食材", "運動", "其他服務",
              "交通", "住宿", "日用品", "電子產品")


def normalize(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Expected a nonempty item name")
    return unicodedata.normalize("NFKC", name).strip()


def group_key(name):
    return "".join(normalize(name).casefold().split())


def validate_items(records):
    """Keep only fields allowed in this experiment; never infer missing reviews."""
    by_name, seen_ids = {}, set()
    for number, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {number}: expected an object")
        item_id = record.get("id")
        category = record.get("category")
        context = record.get("name_only_context_needed", False)
        if not isinstance(item_id, str) or not item_id.strip() or item_id in seen_ids:
            raise ValueError(f"Record {number}: missing or duplicate ID")
        seen_ids.add(item_id)
        if type(category) is not int or not 0 <= category < 10:
            raise ValueError(f"Record {number}: category must be an integer 0–9")
        if record.get("review_status") != "human_confirmed":
            raise ValueError(f"Record {number}: label is not human-confirmed")
        if type(context) is not bool:
            raise ValueError(f"Record {number}: context flag must be boolean")
        name = normalize(record.get("name"))
        group = group_key(record.get("group", name))
        item = dict(id=item_id, name=name, category=category, group=group,
                    name_only_context_needed=context, review_status="human_confirmed")
        if name in by_name:
            old = by_name[name]
            if old["category"] != category or old["group"] != group:
                raise ValueError(f"Record {number}: conflicting duplicate name")
            old["name_only_context_needed"] |= context
        else:
            by_name[name] = item
    if not by_name:
        raise ValueError("No confirmed items")
    group_labels = {}
    for item in by_name.values():
        group = item["group"]
        if group in group_labels and group_labels[group] != item["category"]:
            raise ValueError("A variant group has conflicting labels")
        group_labels[group] = item["category"]
    return sorted(by_name.values(), key=lambda item: (item["name"], item["id"]))


def load_items(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        records = [json.loads(line) for line in stream if line.strip()]
    return validate_items(records)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                  for row in rows), encoding="utf-8")


def from_invoices(paths, catalog_path):
    """The caller supplies a human-reviewed catalog; amounts only filter rows."""
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8-sig"))
    normalized = {}
    for name, label in catalog.items():
        key = normalize(name)
        if key in normalized and normalized[key] != label:
            raise ValueError("Catalog has conflicting normalized names")
        normalized[key] = label
    records = []
    summary = dict(source_rows=0, nonpositive_rows=0, unconfirmed_rows=0)
    for path in paths:
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"發票日期", "消費明細_品名", "消費明細_金額"}
            if not required <= set(reader.fieldnames or []):
                raise ValueError("CSV is missing required invoice columns")
            for row in reader:
                if not row.get("發票日期"):
                    continue
                summary["source_rows"] += 1
                if int(row["消費明細_金額"]) <= 0:
                    summary["nonpositive_rows"] += 1
                    continue
                name = normalize(row["消費明細_品名"])
                label = normalized.get(name, {})
                category = label.get("category")
                if (label.get("provisional") is not False or
                        type(category) is not int or not 0 <= category < 10):
                    summary["unconfirmed_rows"] += 1
                    continue
                records.append(dict(id=f"row-{len(records)}", name=name,
                                    category=category, review_status="human_confirmed"))
    items = validate_items(records)
    for item in items:
        item["id"] = hashlib.sha256(item["name"].encode("utf-8")).hexdigest()[:16]
    summary["unique_items"] = len(items)
    return items, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", action="append", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output already exists; choose a new path")
    try:
        items, summary = from_invoices(args.csv, args.catalog)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(args.out, items)
        print(json.dumps(summary))
    except (ValueError, KeyError, TypeError, OSError):
        parser.exit(1, "Preparation failed: check CSV columns and reviewed catalog.\n")


if __name__ == "__main__":
    main()
