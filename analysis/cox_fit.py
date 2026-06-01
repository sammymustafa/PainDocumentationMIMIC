"""Shared Cox model fitting utilities."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.statistics import multivariate_logrank_test, proportional_hazard_test

from analysis._paths import DURATION_COL, EVENT_COL

MIN_N = 80
MIN_EVENTS = 15


def cols_from_formula(formula: str, df: pd.DataFrame) -> list[str]:
    cols: set[str] = set()
    for qm in re.findall(r'Q\("([^"]+)"\)', formula):
        if qm in df.columns:
            cols.add(qm)
    for token in re.split(r"\s*\+\s*", formula):
        token = token.strip()
        if ":" in token:
            for part in token.split(":"):
                base = part.split(",")[0].replace("C(", "").replace(")", "").strip()
                if base in df.columns:
                    cols.add(base)
        elif token in df.columns:
            cols.add(token)
        elif token.startswith("C("):
            inner = token[2:].rstrip(")")
            if inner.startswith('Q("'):
                continue
            base = inner.split(",")[0].strip()
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
    cols = cols_from_formula(formula, df)
    use = df[[duration_col, event_col, *cols]].dropna()
    if len(use) < MIN_N or use[event_col].sum() < MIN_EVENTS:
        return None
    try:
        cph = CoxPHFitter()
        cph.fit(use, duration_col=duration_col, event_col=event_col, formula=formula)
        return cph
    except Exception:
        return None


def extract_terms(
    cph: CoxPHFitter,
    *,
    model: str = "",
    model_label: str = "",
    formula: str = "",
) -> list[dict[str, Any]]:
    n = int(len(cph.durations))
    events = int(cph.event_observed.sum())
    rows: list[dict[str, Any]] = []
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
                "model": model,
                "model_label": model_label,
                "n": n,
                "n_events": events,
                "concordance": float(cph.concordance_index_),
                "formula": formula,
                "term": term,
                "comparison": label,
                "coef": float(cph.params_[term]),
                "hazard_ratio": float(np.exp(cph.params_[term])),
                "ci_low": float(np.exp(ci.iloc[0])),
                "ci_high": float(np.exp(ci.iloc[1])),
                "pvalue": float(cph.summary.loc[term, "p"]),
            }
        )
    return rows


def ph_test_report(
    cph: CoxPHFitter,
    df: pd.DataFrame,
    formula: str,
    *,
    duration_col: str = DURATION_COL,
    event_col: str = EVENT_COL,
) -> str:
    cols = cols_from_formula(formula, df)
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


def fmt_p(p: float) -> str:
    if pd.isna(p):
        return ""
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def logrank_p_by_group(
    df: pd.DataFrame,
    group_col: str,
    *,
    duration_col: str = DURATION_COL,
    event_col: str = EVENT_COL,
) -> float | None:
    groups = []
    durations = []
    events = []
    for _, sub in df.groupby(group_col):
        if len(sub) < 20:
            continue
        groups.append(sub[group_col])
        durations.append(sub[duration_col])
        events.append(sub[event_col])
    if len(groups) < 2:
        return None
    try:
        lr = multivariate_logrank_test(
            pd.concat(durations),
            pd.concat(groups),
            pd.concat(events),
        )
        return float(lr.p_value)
    except Exception:
        return None
