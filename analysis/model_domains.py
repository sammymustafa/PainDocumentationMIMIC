"""Variable → analytic domain mapping for tables and figures."""

from __future__ import annotations

import re

DOMAIN_ORDER = [
    "Clinical need",
    "Demographics",
    "Insurance",
    "Language/documentation",
    "Clinical severity",
    "Diagnosis/injury",
    "Workflow",
    "Disposition",
    "Year/policy era",
    "Treatment pathway",
]

TERM_DOMAIN: dict[str, str] = {}


def _register(pattern: str, domain: str) -> None:
    TERM_DOMAIN[pattern] = domain


_register("initial_pain_score", "Clinical need")
_register("injury_group", "Diagnosis/injury")
for p in ["race_ethnicity", "age_group", "sex"]:
    _register(p, "Demographics")
_register("insurance_group", "Insurance")
_register("language_group", "Language/documentation")
for p in ["triage_acuity", "heartrate_0_z", "resprate_0_z", "sbp_0_z", "esi_group"]:
    _register(p, "Clinical severity")
_register("arrival_shift", "Workflow")
_register("arrival_weekend", "Workflow")
_register("arrival_mode", "Workflow")
_register("ed_arrivals_past_1hr", "Workflow")
_register("ed_census_at_initial_pain_hour", "Workflow")
_register("disposition_group", "Disposition")
_register("year_era", "Year/policy era")
_register("any_analgesic_given", "Treatment pathway")


def domain_for_term(term: str) -> str:
    for key, domain in TERM_DOMAIN.items():
        if key in term:
            return domain
    if "race_ethnicity" in term:
        return "Demographics"
    if "insurance" in term:
        return "Insurance"
    if "language" in term:
        return "Language/documentation"
    if "disposition" in term:
        return "Disposition"
    if "year_era" in term:
        return "Year/policy era"
    if "arrival" in term or "ed_" in term:
        return "Workflow"
    if "injury" in term or "diagnosis" in term:
        return "Diagnosis/injury"
    if "analgesic" in term:
        return "Treatment pathway"
    return "Other"


def display_label(term: str, comparison: str = "") -> str:
    if comparison and comparison != term:
        return comparison
    if "[T." in term:
        level = term.split("[T.")[1].rstrip("]")
        ref_m = re.search(r'reference="?([^"\)]+)"?\)', term)
        ref = ref_m.group(1) if ref_m else ""
        return f"{level} vs {ref}" if ref else level
    return term.replace("_", " ")
