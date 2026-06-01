#!/usr/bin/env python3
"""Deprecated: use scripts/run_analysis.py (includes within-acuity and post-analgesic)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

print("run_part2_analysis.py is deprecated. Running run_analysis.py instead...")
from scripts.run_analysis import main

if __name__ == "__main__":
    main()
