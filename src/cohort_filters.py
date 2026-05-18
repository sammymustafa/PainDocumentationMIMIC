from __future__ import annotations

import pandas as pd

EXCLUDED_RACES = frozenset({
    "American Indian or Alaska Native",
    "Native Hawaiian or Other Pacific Islander",
    "Two or More Races",
})

VALID_DIAGNOSIS_TYPES = frozenset({"acute_pancreatitis", "trauma"})

TRAUMA_SUBTYPE_MAP = {
    "not_trauma": None,
    "penetrating": "other_trauma",
    "assault": "other_trauma",
    "assault_penetrating": "other_trauma",
    "mvc": "other_trauma",
    "burn": "other_trauma",
    "fracture": "fracture_dislocation",
    "dislocation": "fracture_dislocation",
    "laceration": "other_trauma",
    "contusion": "other_trauma",
    "blunt": "other_trauma",
    "sprain_strain": "other_trauma",
    "fall": "fall",
    "fracture_dislocation": "fracture_dislocation",
    "other_trauma": "other_trauma",
}


def normalize_trauma_subtype(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "trauma_subtype" not in out.columns:
        return out
    out["trauma_subtype"] = out["trauma_subtype"].replace(TRAUMA_SUBTYPE_MAP)
    if "diagnosis_type" in out.columns:
        out.loc[out["diagnosis_type"] == "acute_pancreatitis", "trauma_subtype"] = pd.NA
    return out


def normalize_disposition(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "disposition_group" in out.columns:
        out["disposition_group"] = out["disposition_group"].replace({"EXPIRED": "OTHER"})
    return out


def filter_stay_cohort(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "race_ethnicity" in out.columns:
        out = out[~out["race_ethnicity"].isin(EXCLUDED_RACES)]
    if "diagnosis_type" in out.columns:
        out = out[out["diagnosis_type"].isin(VALID_DIAGNOSIS_TYPES)]
    out = normalize_trauma_subtype(out)
    out = normalize_disposition(out)
    return out.reset_index(drop=True)
