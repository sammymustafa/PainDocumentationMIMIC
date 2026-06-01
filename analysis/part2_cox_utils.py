"""Backward-compatible helpers for legacy part2 scripts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

from analysis.cox_fit import (
    DURATION_COL,
    EVENT_COL,
    MIN_EVENTS,
    MIN_N,
    extract_terms,
    fit_cox,
    fmt_p,
    ph_test_report,
)
from analysis.cox_models import formula_post_analgesic as _formula_post_analgesic
from analysis.cox_models import formula_within_acuity as _formula_within_acuity

POST_DURATION = "post_analgesic_duration_min"
POST_EVENT = "post_analgesic_event"

RACE = 'C(race_ethnicity, Treatment(reference="White"))'
INSURANCE = 'C(insurance_group, Treatment(reference="private"))'
LANGUAGE = 'C(language_group, Treatment(reference="English"))'
SEX = 'C(sex, Treatment(reference="F"))'
AGE_GROUP = 'C(age_group, Treatment(reference="40-64"))'
INJURY = 'C(injury_group, Treatment(reference="acute_pancreatitis"))'
DISPOSITION = 'C(disposition_group, Treatment(reference="HOME"))'
ARRIVAL_SHIFT = 'C(arrival_shift, Treatment(reference="day"))'


def formula_within_acuity(*, parsimonious: bool = False) -> str:
    return _formula_within_acuity()


def formula_post_analgesic() -> str:
    return _formula_post_analgesic()


def formula_interaction() -> str:
    return (
        f"initial_pain_score + {RACE} + C(esi_group) + {RACE}:C(esi_group) + "
        f"{AGE_GROUP} + {SEX} + {INSURANCE} + {LANGUAGE} + {ARRIVAL_SHIFT} + "
        f"{INJURY} + {DISPOSITION}"
    )


def extract_race_hrs(
    cph: CoxPHFitter,
    *,
    stratum: str,
    pain_stratum: str = "",
    model_label: str = "",
) -> list[dict[str, Any]]:
    rows = []
    for term in cph.params_.index:
        if "race_ethnicity" not in term or "[T." not in term:
            continue
        level = term.split("[T.")[1].rstrip("]")
        if level == "White":
            continue
        ci = cph.confidence_intervals_.loc[term]
        rows.append(
            {
                "acuity_stratum": stratum,
                "pain_stratum": pain_stratum,
                "model_label": model_label,
                "comparison": f"{level} vs White",
                "n_total": int(len(cph.durations)),
                "n_events": int(cph.event_observed.sum()),
                "hazard_ratio": float(np.exp(cph.params_[term])),
                "ci_lower": float(np.exp(ci.iloc[0])),
                "ci_upper": float(np.exp(ci.iloc[1])),
                "p_value": float(cph.summary.loc[term, "p"]),
            }
        )
    return rows


def interpret_hr_pattern(hrs: list[float]) -> str:
    valid = [h for h in hrs if pd.notna(h)]
    if not valid:
        return ""
    if any(h < 1 for h in valid) and any(h > 1 for h in valid):
        return "Direction changes across strata"
    if all(h < 1 for h in valid):
        return "Slower reassessment vs White in this stratum"
    if all(h > 1 for h in valid):
        return "Faster reassessment vs White in this stratum"
    return "Association present; magnitude varies"


def extract_all_terms(cph: CoxPHFitter, *, n: int, events: int) -> list[dict]:
    return extract_terms(cph)
