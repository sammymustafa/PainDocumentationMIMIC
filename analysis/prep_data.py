from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO_ROOT / "data/processed/modeling/final_modeling_dataset.csv"

VITAL_COLS = ["temperature_0", "heartrate_0", "resprate_0", "o2sat_0", "sbp_0", "dbp_0"]


def assign_year_era(year: pd.Series, n_eras: int = 5) -> pd.Series:
    """Bucket de-identified anchor years into ~equal-width eras."""
    y = pd.to_numeric(year, errors="coerce")
    ymin, ymax = int(y.min()), int(y.max())
    width = int(np.ceil((ymax - ymin + 1) / n_eras))
    bins = list(range(ymin, ymax + width, width))
    if bins[-1] <= ymax:
        bins.append(ymax + 1)
    labels = [f"{bins[i]}–{bins[i + 1] - 1}" for i in range(len(bins) - 1)]
    return pd.cut(y, bins=bins, labels=labels, include_lowest=True)


def load_analysis_cohort(path: Path | None = None) -> pd.DataFrame:
    path = path or DEFAULT_DATA
    df = pd.read_csv(path, low_memory=False)
    df["minutes_to_reassessment"] = df["minutes_initial_to_first_reassessment"]
    df["log_minutes_to_reassessment"] = np.log1p(df["minutes_to_reassessment"])
    for window in (60, 120, 180):
        df[f"reassessed_within_{window}"] = (df["minutes_to_reassessment"] <= window).astype(int)
    df["year_era"] = assign_year_era(df["year"])
    df["trauma_subtype"] = df["trauma_subtype"].fillna("acute_pancreatitis")
    for col in VITAL_COLS:
        if col in df.columns:
            df[f"{col}_z"] = (df[col] - df[col].mean()) / df[col].std(ddof=0)
    return df
