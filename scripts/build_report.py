"""Build the report from any working directory: python scripts/build_report.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from receipt.build import main

if __name__ == "__main__":
    main()
