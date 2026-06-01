"""Sequential Cox M1–M4 (primary); disposition/analgesia are separate pathway models."""

from __future__ import annotations

from typing import Any

import pandas as pd

from analysis.cox_fit import extract_terms, fit_cox
from analysis.model_domains import domain_for_term

RACE = 'C(race_ethnicity, Treatment(reference="White"))'
INSURANCE = 'C(insurance_group, Treatment(reference="private"))'
LANGUAGE = 'C(language_group, Treatment(reference="English"))'
SEX = 'C(sex, Treatment(reference="F"))'
AGE_GROUP = 'C(age_group, Treatment(reference="40-64"))'
INJURY = 'C(injury_group, Treatment(reference="acute_pancreatitis"))'
DISPOSITION_PATHWAY = 'C(disposition_pathway, Treatment(reference="HOME"))'
ARRIVAL_SHIFT = 'C(arrival_shift, Treatment(reference="day"))'
YEAR_ERA = 'C(Q("year_era"))'
ARRIVAL_MODE = 'C(arrival_mode, Treatment(reference="walk_in"))'

COMORBIDITY_FLAGS = [
    "lung_disease_flag",
    "cardiac_disease_flag",
    "hypertension_flag",
    "diabetes_flag",
    "renal_disease_flag",
    "obesity_flag",
    "cancer_flag",
    "smoking_flag",
]

VITAL_Z_TERMS = ["heartrate_0_z", "resprate_0_z", "sbp_0_z"]

M1_CLINICAL = ["initial_pain_score", INJURY]
M2_DEMO_BASE = [RACE, AGE_GROUP, SEX, INSURANCE]
M3_SEVERITY = ["triage_acuity"] + VITAL_Z_TERMS
M3_SEVERITY_BASE = M3_SEVERITY
M4_WORKFLOW = [
    ARRIVAL_MODE,
    ARRIVAL_SHIFT,
    "arrival_weekend",
    "ed_arrivals_past_1hr",
    "ed_census_at_initial_pain_hour",
    YEAR_ERA,
]


def m2_parts(df: pd.DataFrame | None = None) -> list[str]:
    parts = list(M2_DEMO_BASE)
    if df is not None and "language_group" in df.columns:
        lang = df["language_group"].dropna()
        if len(lang) and lang.isin(["English", "non-English"]).any():
            parts = parts + [LANGUAGE]
    return parts


M2_DEMO = M2_DEMO_BASE + [LANGUAGE]


def m3_comorbidity_parts(df: pd.DataFrame) -> list[str]:
    if "comorbidity_count" in df.columns and df["comorbidity_count"].notna().any():
        return ["comorbidity_count"]
    return []


def m3_parts(df: pd.DataFrame | None = None) -> list[str]:
    return list(M3_SEVERITY) + (m3_comorbidity_parts(df) if df is not None else [])


def _through_m3(df: pd.DataFrame | None) -> list[str]:
    return M1_CLINICAL + m2_parts(df) + m3_parts(df)


def formula_m4(df: pd.DataFrame | None = None) -> str:
    """Primary adjusted model: early-encounter only (no disposition, no analgesia)."""
    return " + ".join(_through_m3(df) + M4_WORKFLOW)


def formula_m4_disposition(df: pd.DataFrame | None = None) -> str:
    """Pathway sensitivity: M4 + admitted vs home (transfer/other excluded via NA)."""
    return formula_m4(df) + " + " + DISPOSITION_PATHWAY


def formula_s_rx(df: pd.DataFrame | None = None) -> str:
    """Optional: M4 + analgesic on primary time scale (not in primary sequence)."""
    return formula_m4(df) + " + any_analgesic_given"


def formula_within_acuity(df: pd.DataFrame | None = None) -> str:
    m3 = [x for x in m3_parts(df) if x != "triage_acuity"]
    return " + ".join(["initial_pain_score"] + m2_parts(df) + [INJURY] + m3 + M4_WORKFLOW)


def formula_pain10_esi12(df: pd.DataFrame | None = None) -> str:
    parts = m2_parts(df) + [INJURY, ARRIVAL_SHIFT, ARRIVAL_MODE]
    if df is not None:
        parts = parts + m3_comorbidity_parts(df)
        if "year_era" in df.columns and df["year_era"].notna().nunique() >= 2:
            parts = parts + [YEAR_ERA]
    return " + ".join(parts)


def formula_post_analgesic(df: pd.DataFrame | None = None) -> str:
    return " + ".join(
        ["initial_pain_score"]
        + m3_parts(df)
        + m2_parts(df)
        + [INJURY]
        + [ARRIVAL_SHIFT, YEAR_ERA]
    )


def formula_severe_pain_stratum(df: pd.DataFrame | None = None) -> str:
    return formula_m4(df)


def formula_iptw_ps(df: pd.DataFrame | None = None) -> str:
    """Propensity: baseline / early-encounter only (M1–M3, no disposition/analgesic/workflow)."""
    return " + ".join(_through_m3(df))


# Legacy aliases
m4_comorbidity_parts = m3_comorbidity_parts
m5_comorbidity_parts = m3_comorbidity_parts
M5_PATHWAY = [DISPOSITION_PATHWAY]
M6_PATHWAY = M5_PATHWAY


def formula_m5_pathway(df: pd.DataFrame | None = None) -> str:
    return formula_m4_disposition(df)


def formula_m5_comorbidity(df: pd.DataFrame | None = None) -> str:
    return formula_m4(df)


def formula_m6_pathway(df: pd.DataFrame | None = None) -> str:
    return formula_m4_disposition(df)


def formula_m5(df: pd.DataFrame | None = None) -> str:
    return formula_m4_disposition(df)


def formula_m5_no_disp(df: pd.DataFrame | None = None) -> str:
    return formula_m4(df)


def formula_iptw_covariates(df: pd.DataFrame | None = None) -> str:
    return formula_iptw_ps(df)


def fit_sequential_models(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    m2 = m2_parts(df)
    m3 = m3_parts(df)
    specs: list[tuple[str, str, list[str]]] = [
        ("M1", "Clinical presentation", M1_CLINICAL),
        ("M2", "+ patient/social factors", M1_CLINICAL + m2),
        ("M3", "+ severity/illness burden", M1_CLINICAL + m2 + m3),
        ("M4", "+ ED context/workflow (primary)", M1_CLINICAL + m2 + m3 + M4_WORKFLOW),
    ]
    for model_id, label, parts in specs:
        formula = " + ".join(parts)
        cph = fit_cox(df, formula)
        if cph is None:
            continue
        for r in extract_terms(cph, model=model_id, model_label=label, formula=formula):
            r["domain"] = domain_for_term(r["term"])
            rows.append(r)
    return pd.DataFrame(rows)


def fit_named_model(df: pd.DataFrame, model_id: str, formula: str, label: str) -> pd.DataFrame:
    cph = fit_cox(df, formula)
    if cph is None:
        return pd.DataFrame()
    rows = extract_terms(cph, model=model_id, model_label=label, formula=formula)
    for r in rows:
        r["domain"] = domain_for_term(r["term"])
    return pd.DataFrame(rows)
