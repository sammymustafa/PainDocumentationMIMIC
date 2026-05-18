#!/usr/bin/env python3
"""Sectioned pain-score heatmap using this project's survival cohort variables."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.pain_score_heatmap import generate_pain_score_heatmap  # noqa: E402


def main() -> None:
    generate_pain_score_heatmap()
    print(f"\nDone → {REPO_ROOT / 'figures' / '08_pain_score_heatmap'}")


if __name__ == "__main__":
    main()
