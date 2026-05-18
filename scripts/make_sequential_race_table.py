#!/usr/bin/env python3
"""Build sequential Cox race/ethnicity table from existing sequential_cox_hr.csv."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.sequential_race_table import write_sequential_race_table  # noqa: E402


def main() -> None:
    print("Building sequential Cox race/ethnicity table (M2–M6, ref White)...")
    write_sequential_race_table()
    print(f"\nDone → {REPO_ROOT / 'figures' / 'tables'}")


if __name__ == "__main__":
    main()
