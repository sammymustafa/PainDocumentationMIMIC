from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = REPO_ROOT / "data/raw"
SURVIVAL_CSV = REPO_ROOT / "data/processed/analysis/survival_cohort.csv"
ANALYSIS_OUT = REPO_ROOT / "data/processed/analysis"
MANUSCRIPT_DIR = REPO_ROOT / "figures/manuscript"
MANUSCRIPT_TABLES = MANUSCRIPT_DIR / "tables"
ARCHIVE_DIR = REPO_ROOT / "figures/_archive"
EXPLORATORY_DIR = REPO_ROOT / "figures/exploratory"

DURATION_COL = "duration_minutes"
EVENT_COL = "reassessment_event"
POST_DURATION = "post_analgesic_duration_min"
POST_EVENT = "post_analgesic_event"

RACES = ["White", "Black", "Asian", "Hispanic"]
