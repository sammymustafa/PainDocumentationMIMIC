from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis._paths import REPO_ROOT, SURVIVAL_CSV
from analysis.prep_cohort import prep_analytic_cohort

RAW_PAIN = REPO_ROOT / "data/raw/pain_events.csv"
DURATION_COL = "duration_minutes"
EVENT_COL = "reassessment_event"

RACES = ["White", "Black", "Asian", "Hispanic"]


def load_survival_cohort(path: Path | None = None) -> pd.DataFrame:
    path = path or SURVIVAL_CSV
    df = pd.read_csv(
        path,
        low_memory=False,
        parse_dates=[
            "intime",
            "outtime",
            "initial_pain_time",
            "first_reassessment_time",
            "first_analgesic_time",
        ],
    )
    return df


def prep_part2a_cohort(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Primary analytic cohort (delegates to prep_cohort)."""
    if df is None:
        df = load_survival_cohort()
    return prep_analytic_cohort(df)


def build_post_analgesic_cohort(
    survival: pd.DataFrame | None = None,
    pain_path: Path | None = None,
) -> pd.DataFrame:
    """
    Analgesic-pathway cohort: time zero = first analgesic after initial pain.
    Event = first pain score documented strictly after that analgesic time.
    """
    if survival is None:
        survival = prep_part2a_cohort(load_survival_cohort())

    pain_path = pain_path or RAW_PAIN
    pain = pd.read_csv(pain_path, parse_dates=["pain_charttime"], low_memory=False)
    pain = pain[pain["pain_numeric"] > 0].sort_values(["stay_id", "pain_charttime"])

    base = survival[
        (survival["any_analgesic_given"] == 1)
        & survival["first_analgesic_time"].notna()
        & survival["initial_pain_time"].notna()
    ].copy()
    base = base[base["first_analgesic_time"] >= base["initial_pain_time"]]
    base = base[base["race_ethnicity"].isin(RACES)]

    rows = []
    for _, stay in base.iterrows():
        sid = stay["stay_id"]
        t0 = stay["first_analgesic_time"]
        outtime = stay["outtime"]
        pe = pain[pain["stay_id"] == sid]
        post = pe[pe["pain_charttime"] > t0]
        if len(post) > 0:
            t_event = post["pain_charttime"].iloc[0]
            duration = (t_event - t0).total_seconds() / 60.0
            event = 1
            post_score = post["pain_numeric"].iloc[0]
        else:
            duration = (outtime - t0).total_seconds() / 60.0
            event = 0
            post_score = np.nan

        if duration <= 0:
            continue

        row = stay.to_dict()
        row["post_analgesic_event"] = event
        row["post_analgesic_duration_min"] = duration
        row["post_analgesic_reassessment_time"] = (
            post["pain_charttime"].iloc[0] if event else pd.NaT
        )
        row["post_analgesic_pain_score"] = post_score
        row["reassessed_within_60_post_rx"] = int(event and duration <= 60)
        row["reassessed_within_120_post_rx"] = int(event and duration <= 120)
        rows.append(row)

    return pd.DataFrame(rows).reset_index(drop=True)
