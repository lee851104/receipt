"""Evaluate local invoice CSVs with a reviewed catalog; print aggregates only."""
import argparse
import json
from pathlib import Path

from prepare_data import from_invoices, write_json, write_jsonl
from tfidf_lr import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--csv", action="append", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        items, preparation = from_invoices(args.csv, args.catalog)
        args.out.mkdir(parents=True, exist_ok=False)
        prepared = args.out / "prepared.jsonl"
        write_jsonl(prepared, items)
        report = evaluate(args.model, prepared, args.out / "evaluation")
        report["preparation"] = preparation
        write_json(args.out / "report.json", report)
        print(json.dumps(report, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError):
        parser.exit(1, "Evaluation failed: check model, CSV, catalog and a new output path.\n")


if __name__ == "__main__":
    main()
