from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test, proportional_hazard_test

DURATION_COL = "duration_minutes"
EVENT_COL = "reassessment_event"
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

MIN_N = 80
MIN_EVENTS = 15


def formula_within_acuity(*, parsimonious: bool = False) -> str:
    parts = [
        "initial_pain_score",
        RACE,
        AGE_GROUP,
        SEX,
        INSURANCE,
        LANGUAGE,
        ARRIVAL_SHIFT,
    ]
    if not parsimonious:
        parts.append(INJURY)
        parts.append(DISPOSITION)
    return " + ".join(parts)


def formula_post_analgesic() -> str:
    return " + ".join(
        [
            "initial_pain_score",
            "triage_acuity",
            RACE,
            AGE_GROUP,
            SEX,
            INSURANCE,
            LANGUAGE,
            INJURY,
            ARRIVAL_SHIFT,
            DISPOSITION,
        ]
    )


def formula_interaction() -> str:
    return " + ".join(
        [
            "initial_pain_score",
            RACE,
            "C(esi_group)",
            f"{RACE}:C(esi_group)",
            AGE_GROUP,
            SEX,
            INSURANCE,
            LANGUAGE,
            ARRIVAL_SHIFT,
            INJURY,
            DISPOSITION,
        ]
    )


def _cols_from_formula(formula: str, df: pd.DataFrame) -> list[str]:
    cols = set()
    for token in re.split(r"\s*\+\s*", formula):
        token = token.strip()
        if ":" in token:
            for part in token.split(":"):
                base = part.split(",")[0].replace("C(", "").replace(")", "")
                if base in df.columns:
                    cols.add(base)
        elif token in df.columns:
            cols.add(token)
        elif token.startswith("C("):
            base = token.split(",")[0].replace("C(", "")
            if base in df.columns:
                cols.add(base)
    return list(cols)


def fit_cox(
    df: pd.DataFrame,
    formula: str,
    *,
    duration_col: str = DURATION_COL,
    event_col: str = EVENT_COL,
) -> CoxPHFitter | None:
    cols = _cols_from_formula(formula, df)
    use = df[[duration_col, event_col, *cols]].dropna()
    if len(use) < MIN_N or use[event_col].sum() < MIN_EVENTS:
        return None
    try:
        cph = CoxPHFitter()
        cph.fit(use, duration_col=duration_col, event_col=event_col, formula=formula)
        return cph
    except Exception:
        return None


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
        hr = float(np.exp(cph.params_[term]))
        p = float(cph.summary.loc[term, "p"])
        rows.append(
            {
                "acuity_stratum": stratum,
                "pain_stratum": pain_stratum,
                "model_label": model_label,
                "comparison": f"{level} vs White",
                "n_total": int(len(cph.durations)),
                "n_events": int(cph.event_observed.sum()),
                "hazard_ratio": hr,
                "ci_lower": float(np.exp(ci[0])),
                "ci_upper": float(np.exp(ci[1])),
                "p_value": p,
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


def fmt_p(p: float) -> str:
    if pd.isna(p):
        return ""
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def ph_test_report(
    cph: CoxPHFitter,
    df: pd.DataFrame,
    formula: str,
    *,
    duration_col: str = DURATION_COL,
    event_col: str = EVENT_COL,
) -> str:
    cols = _cols_from_formula(formula, df)
    sub = df[[duration_col, event_col, *cols]].dropna()
    try:
        result = proportional_hazard_test(cph, sub, time_transform="rank")
        lines = ["Proportional hazards test (Schoenfeld, rank transform)", ""]
        for term in result.summary.index:
            p = result.summary.loc[term, "p"]
            flag = " *violated*" if p < 0.05 else ""
            lines.append(f"  {term}: p = {p:.4f}{flag}")
        return "\n".join(lines)
    except Exception as exc:
        return f"PH test failed: {exc}"


def extract_all_terms(cph: CoxPHFitter, *, n: int, events: int) -> list[dict]:
    rows = []
    for term in cph.params_.index:
        ci = cph.confidence_intervals_.loc[term]
        label = term
        if "[T." in term:
            level = term.split("[T.")[1].rstrip("]")
            ref_m = re.search(r'reference="?([^"\)]+)"?\)', term)
            ref = ref_m.group(1) if ref_m else ""
            label = f"{level} vs {ref}" if ref else level
        rows.append(
            {
                "variable": term,
                "comparison": label,
                "n": n,
                "events": events,
                "hazard_ratio": float(np.exp(cph.params_[term])),
                "ci_lower": float(np.exp(ci[0])),
                "ci_upper": float(np.exp(ci[1])),
                "p_value": float(cph.summary.loc[term, "p"]),
            }
        )
    return rows
