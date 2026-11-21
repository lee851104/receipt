"""Write a fictional e-invoice CSV to upload in a demo, so a new account's profile is ready and it gets matches.

    .venv/Scripts/python.exe -m scripts.make_demo_upload [--month 2026-06] [--out demo-upload-2026-06.csv]

The names come from the reviewed synthetic attribute cache (all start with 示範), so the demo's qwen model answers them
from the cache without a GPU, and only names holding a word the fake category model is sure of are used, so none of
them lands in 10 待確認 when start.bat runs with CATEGORY_MODEL=fake. Forty lines in one month is twice the 20 items a
profile needs. Nothing here comes from a real receipt; *.csv is ignored by git, so the file is never committed.
"""
import argparse
from pathlib import Path

from src.api.sample import CACHE, COLUMNS, LINES, SHOPS, demo_csv, demo_names, demo_rows  # noqa: F401  (re-exported)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--month", default="2026-06", help="YYYY-MM (default 2026-06)")
    parser.add_argument("--out", type=Path, help="where to write (default demo-upload-<month>.csv here)")
    args = parser.parse_args(argv)
    out = args.out or Path(f"demo-upload-{args.month}.csv")
    out.write_bytes(demo_csv(args.month))
    print(f"wrote {out} ({LINES} fictional lines for {args.month})")


if __name__ == "__main__":
    main()
