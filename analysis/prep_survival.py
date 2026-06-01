"""Build stay-level survival cohort: time from first documented pain to first reassessment."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis._paths import DATA_RAW, SURVIVAL_CSV
from analysis.prep_data import assign_year_era, collapse_sparse_year_eras
from src.cohort_filters import filter_stay_cohort, normalize_disposition

STAY_CSV = DATA_RAW / "stay_covariates.csv"
PAIN_CSV = DATA_RAW / "pain_events.csv"

RACES = ["White", "Black", "Asian", "Hispanic"]


def _injury_group(row: pd.Series) -> str:
    if row.get("diagnosis_type") == "acute_pancreatitis":
        return "acute_pancreatitis"
    sub = str(row.get("trauma_subtype") or "other_trauma")
    if sub in ("fall", "fracture_dislocation", "other_trauma"):
        return sub
    return "other_trauma"


def _pain_severity(score: float) -> str:
    if score <= 3:
        return "mild (1–3)"
    if score <= 6:
        return "moderate (4–6)"
    return "severe (7–10)"


def _arrival_mode(transport: str) -> str:
    t = str(transport or "").upper()
    if "AMBULANCE" in t:
        return "ambulance"
    if "WALK" in t:
        return "walk_in"
    if t in ("", "NAN", "NONE"):
        return "unknown"
    return "other"


def build_survival_cohort(
    stays: pd.DataFrame | None = None,
    pain: pd.DataFrame | None = None,
) -> pd.DataFrame:
    stays = stays if stays is not None else pd.read_csv(STAY_CSV, low_memory=False)
    pain = pain if pain is not None else pd.read_csv(PAIN_CSV, parse_dates=["pain_charttime"])

    stays = filter_stay_cohort(normalize_disposition(stays))
    stays["intime"] = pd.to_datetime(stays["intime"])
    stays["outtime"] = pd.to_datetime(stays["outtime"])
    if "first_analgesic_time" in stays.columns:
        stays["first_analgesic_time"] = pd.to_datetime(stays["first_analgesic_time"], errors="coerce")

    pe = pain[pain["pain_numeric"] > 0].sort_values(["stay_id", "pain_charttime"])
    first = pe.groupby("stay_id", as_index=False).first()
    second = pe.groupby("stay_id").nth(1).reset_index(drop=True)

    first = first.rename(
        columns={
            "pain_charttime": "initial_pain_time",
            "pain_numeric": "initial_pain_score",
            "heartrate": "heartrate_0",
            "resprate": "resprate_0",
            "sbp": "sbp_0",
        }
    )
    second = second[["stay_id", "pain_charttime", "pain_numeric"]].rename(
        columns={
            "pain_charttime": "first_reassessment_time",
            "pain_numeric": "first_reassessment_score",
        }
    )

    df = stays.merge(
        first[
            [
                "stay_id",
                "initial_pain_time",
                "initial_pain_score",
                "heartrate_0",
                "resprate_0",
                "sbp_0",
            ]
        ],
        on="stay_id",
        how="inner",
    )
    df = df.merge(second, on="stay_id", how="left")

    df = df[df["initial_pain_score"].notna() & (df["initial_pain_score"] > 0)]
    df = df[df["race_ethnicity"].isin(RACES)]

    df["reassessment_event"] = df["first_reassessment_time"].notna().astype(int)
    df["time_end"] = df["first_reassessment_time"].where(
        df["reassessment_event"] == 1, df["outtime"]
    )
    df["duration_minutes"] = (
        (df["time_end"] - df["initial_pain_time"]).dt.total_seconds() / 60.0
    )
    df = df[df["duration_minutes"] > 0]

    for col in ["heartrate_0", "resprate_0", "sbp_0"]:
        df[f"{col}_z"] = (df[col] - df[col].mean()) / df[col].std(ddof=0)

    df["injury_group"] = df.apply(_injury_group, axis=1)
    df["initial_pain_severity"] = df["initial_pain_score"].map(_pain_severity)
    df["year_era"] = assign_year_era(df["year"], width=5)
    df["year_era"] = collapse_sparse_year_eras(df, min_n=200)
    df["arrival_mode"] = df["arrival_transport"].map(_arrival_mode)

    # Analgesic in window: after initial pain, on/before reassessment or outtime
    if "any_analgesic_given" not in df.columns:
        df["any_analgesic_given"] = 0
    mask_rx = (
        df["first_analgesic_time"].notna()
        & (df["first_analgesic_time"] >= df["initial_pain_time"])
    )
    mask_before_end = df["first_analgesic_time"] <= df["time_end"]
    df.loc[mask_rx & mask_before_end, "any_analgesic_given"] = 1

    for w in (60, 120, 180, 240):
        df[f"reassessed_by_{w}"] = (
            (df["reassessment_event"] == 1) & (df["duration_minutes"] <= w)
        ).astype(int)

    return df.reset_index(drop=True)


def load_or_build_survival(
    path: Path | None = None,
    *,
    rebuild: bool = False,
) -> pd.DataFrame:
    path = path or SURVIVAL_CSV
    if path.exists() and not rebuild:
        return pd.read_csv(
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
    df = build_survival_cohort()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df
