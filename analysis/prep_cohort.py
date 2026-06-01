"""Prepare analytic cohort with stratum flags and flow counts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, RACES, SURVIVAL_CSV
from analysis.cox_models import COMORBIDITY_FLAGS
from analysis.prep_survival import _arrival_mode, load_or_build_survival

DURATION_COL = "duration_minutes"
EVENT_COL = "reassessment_event"


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    flags = [c for c in COMORBIDITY_FLAGS if c in out.columns]
    if flags:
        out["comorbidity_count"] = out[flags].fillna(0).astype(float).sum(axis=1)
    else:
        out["comorbidity_count"] = np.nan

    out["disposition_pathway"] = pd.NA
    out.loc[out["disposition_group"] == "HOME", "disposition_pathway"] = "HOME"
    out.loc[out["disposition_group"] == "ADMITTED", "disposition_pathway"] = "ADMITTED"
    return out


def prep_analytic_cohort(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = load_or_build_survival()

    out = df.copy()
    out["triage_acuity"] = pd.to_numeric(out["triage_acuity"], errors="coerce")
    out = out[
        out["triage_acuity"].notna()
        & out["initial_pain_score"].notna()
        & out["race_ethnicity"].isin(RACES)
        & out[DURATION_COL].notna()
        & (out[DURATION_COL] > 0)
    ].copy()

    if "language_group" in out.columns:
        out.loc[out["language_group"] == "undocumented", "language_group"] = np.nan

    out = add_derived_columns(out)

    out["esi_int"] = out["triage_acuity"].astype(int)
    out["esi_group"] = pd.Series(index=out.index, dtype=object)
    out.loc[out["esi_int"].isin([1, 2]), "esi_group"] = "ESI 1–2"
    out.loc[out["esi_int"] == 3, "esi_group"] = "ESI 3"
    out.loc[out["esi_int"].isin([4, 5]), "esi_group"] = "ESI 4–5"

    out["is_trauma"] = out["diagnosis_type"] == "trauma"
    out["pain_10"] = out["initial_pain_score"] >= 9.5
    out["is_admitted"] = out["disposition_group"] == "ADMITTED"
    out["is_home"] = out["disposition_group"] == "HOME"

    if "arrival_mode" not in out.columns and "arrival_transport" in out.columns:
        out["arrival_mode"] = out["arrival_transport"].map(_arrival_mode)
    if "year" in out.columns:
        from analysis.prep_data import assign_year_era, collapse_sparse_year_eras

        out["year_era"] = assign_year_era(out["year"], width=5)
        out["year_era"] = collapse_sparse_year_eras(out, min_n=200)

    if "arrival_mode" in out.columns:
        out.loc[out["arrival_mode"] == "unknown", "arrival_mode"] = np.nan

    return out.reset_index(drop=True)


def compute_flow_counts(
    stays_path: Path | None = None,
    survival: pd.DataFrame | None = None,
) -> dict[str, Any]:
    from analysis.prep_survival import STAY_CSV, build_survival_cohort
    from src.cohort_filters import EXCLUDED_RACES, VALID_DIAGNOSIS_TYPES, filter_stay_cohort

    stays = pd.read_csv(stays_path or STAY_CSV, low_memory=False)
    n_mimic_ed = len(stays)
    n_ap_trauma = int(stays["diagnosis_type"].isin(list(VALID_DIAGNOSIS_TYPES)).sum())
    stays_dx = stays[stays["diagnosis_type"].isin(list(VALID_DIAGNOSIS_TYPES))]
    n_after_race_stay = int((~stays_dx["race_ethnicity"].isin(EXCLUDED_RACES)).sum())
    stays_f = filter_stay_cohort(stays)

    if survival is None:
        surv = build_survival_cohort(stays=stays_f)
    else:
        surv = survival

    n_pain = len(surv)

    s = surv.copy()
    s["triage_acuity"] = pd.to_numeric(s["triage_acuity"], errors="coerce")
    mask_base = (
        s["race_ethnicity"].isin(RACES)
        & s["initial_pain_score"].notna()
        & (s["initial_pain_score"] > 0)
        & s[DURATION_COL].notna()
        & (s[DURATION_COL] > 0)
    )
    n_after_duration = int(mask_base.sum())
    n_after_esi = int((mask_base & s["triage_acuity"].notna()).sum())

    cohort = prep_analytic_cohort(surv)
    n_analytic = len(cohort)

    flags = [c for c in COMORBIDITY_FLAGS if c in cohort.columns]
    n_comorbid = int((cohort[flags].sum(axis=1) > 0).sum()) if flags else None

    return {
        "all_ed_stays_in_extract": n_mimic_ed,
        "ap_or_trauma_stays": n_ap_trauma,
        "after_exclude_small_race_groups": n_after_race_stay,
        "initial_pain_documented": int(n_pain),
        "after_valid_survival_time": int(n_after_duration),
        "after_nonmissing_esi": int(n_after_esi),
        "primary_analytic_cohort": int(n_analytic),
        "reassessment_events": int(cohort[EVENT_COL].sum()),
        "with_any_comorbidity_flag": n_comorbid,
        "trauma_stays": int(cohort["is_trauma"].sum()),
        "pain_score_10": int(cohort["pain_10"].sum()),
        "analgesic_before_reassessment_or_outtime": int(cohort["any_analgesic_given"].sum()),
        "admitted": int(cohort["is_admitted"].sum()),
        "discharged_home": int(cohort["is_home"].sum()),
    }


def save_flow_counts(counts: dict[str, Any], path: Path | None = None) -> Path:
    path = path or ANALYSIS_OUT / "flow_counts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(counts, indent=2))
    return path


def load_survival_cohort(path: Path | None = None) -> pd.DataFrame:
    path = path or SURVIVAL_CSV
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
