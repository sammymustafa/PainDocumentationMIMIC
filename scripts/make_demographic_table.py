#!/usr/bin/env python3
"""Deprecated: Table 1 is built by scripts/run_analysis.py (manuscript cohort overview)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.table1 import export_table1  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=REPO_ROOT / "data/processed/modeling/final_modeling_dataset.csv",
        help="Final modeling dataset CSV",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=REPO_ROOT / "figures",
        help="Output directory for table1_by_race.csv and .png",
    )
    return parser.parse_args()


def main() -> None:
    export_table1()


if __name__ == "__main__":
    main()
