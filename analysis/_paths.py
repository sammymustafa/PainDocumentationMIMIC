from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SURVIVAL_CSV = REPO_ROOT / "data/processed/analysis/survival_cohort.csv"
FIGURES = REPO_ROOT / "figures"
HEATMAP_DIR = FIGURES / "08_pain_score_heatmap"
ANALYSIS_OUT = REPO_ROOT / "data/processed/analysis"

DURATION_COL = "duration_minutes"
EVENT_COL = "reassessment_event"
