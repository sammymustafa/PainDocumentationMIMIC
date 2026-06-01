"""Severe pain (7–10 and pain=10) M4 key HR figure."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, DURATION_COL, EVENT_COL, MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import formula_m4
from analysis.model_domains import display_label
from analysis.prep_cohort import prep_analytic_cohort

HR_NOTE = "HR > 1: faster reassessment  |  HR < 1: slower reassessment"

# (term_prefix, level_or_empty for continuous)
KEY_SPECS: list[tuple[str, str | None]] = [
    ("race_ethnicity", "Black"),
    ("race_ethnicity", "Hispanic"),
    ("race_ethnicity", "Asian"),
    ("insurance_group", "Medicaid"),
    ("insurance_group", "Medicare"),
    ("language_group", "non-English"),
    ("age_group", "65+"),
    ("age_group", "18-39"),
    ("sex", "M"),
    ("injury_group", None),
    ("triage_acuity", None),
    ("arrival_shift", "night"),
    ("arrival_weekend", None),
]


def _fit_subset(df: pd.DataFrame, label: str) -> pd.DataFrame:
    cph = fit_cox(df, formula_m4(df))
    if cph is None:
        return pd.DataFrame()
    return pd.DataFrame(extract_terms(cph, model=label, formula=formula_m4(df)))


def _key_rows(res: pd.DataFrame, stratum: str) -> pd.DataFrame:
    rows = []
    for term_p, level in KEY_SPECS:
        if level is None and term_p == "injury_group":
            sub = res[res["term"].astype(str).str.contains("injury_group", na=False)]
        elif level is None and term_p == "triage_acuity":
            sub = res[res["term"].astype(str).str.contains("triage_acuity", na=False)]
        elif level is None and term_p == "arrival_weekend":
            sub = res[res["term"].astype(str).str.contains("arrival_weekend", na=False)]
        else:
            sub = res[
                res["term"].astype(str).str.contains(term_p, na=False)
                & (
                    res["term"].astype(str).str.contains(str(level), na=False)
                    | res["comparison"].astype(str).str.contains(str(level), na=False)
                )
            ]
        if len(sub):
            r = sub.iloc[0]
            rows.append(
                {
                    "stratum": stratum,
                    "comparison": display_label(r["term"], r["comparison"]),
                    "hazard_ratio": r["hazard_ratio"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                    "pvalue": r["pvalue"],
                }
            )
    return pd.DataFrame(rows)


def run_severe_pain_sensitivity(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    parts = []
    for label, lo, hi in [("Pain 7–10", 7, 10), ("Pain = 10", 10, 10)]:
        if hi == 10:
            sub = df[df["initial_pain_score"] >= 9.5]
        else:
            s = df["initial_pain_score"].round()
            sub = df[(s >= lo) & (s <= hi)]
        n, ev = len(sub), int(sub[EVENT_COL].sum()) if len(sub) else 0
        res = _fit_subset(sub, label)
        kr = _key_rows(res, f"{label}\n(n={n:,}, events={ev:,})")
        if len(kr):
            parts.append(kr)

    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    (MANUSCRIPT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    out.to_csv(MANUSCRIPT_DIR / "tables" / "table12_severe_pain_key_hrs.csv", index=False)
    out.to_csv(ANALYSIS_OUT / "severe_pain_key_hrs.csv", index=False)

    if out.empty:
        return out

    fig, ax = plt.subplots(figsize=(9, max(4, 0.45 * len(out) + 1)))
    strata = out["stratum"].unique()
    y = 0.0
    y_pos, hrs, lo, hi, labels = [], [], [], [], []
    for st in strata:
        block = out[out["stratum"] == st]
        labels.append(f"— {st.split(chr(10))[0]} —")
        y_pos.append(y)
        hrs.append(np.nan)
        lo.append(np.nan)
        hi.append(np.nan)
        y += 0.8
        for _, r in block.iterrows():
            labels.append(f"  {r['comparison']}")
            y_pos.append(y)
            hrs.append(r["hazard_ratio"])
            lo.append(r["ci_low"])
            hi.append(r["ci_high"])
            y += 0.7

    y_pos = np.array(y_pos)
    for yp, hr, l, h, lab in zip(y_pos, hrs, lo, hi, labels):
        if lab.startswith("—"):
            ax.text(0.02, yp, lab.strip("— "), fontweight="bold", fontsize=8, transform=ax.get_yaxis_transform())
        elif pd.notna(hr):
            ax.errorbar(hr, yp, xerr=[[hr - l], [h - hr]], fmt="o", capsize=2, color="steelblue")
    ax.axvline(1, color="gray", ls="--")
    ax.set_yticks([])
    for yp, lab in zip(y_pos, labels):
        if not lab.startswith("—"):
            ax.text(-0.02, yp, lab, fontsize=7, ha="right", transform=ax.get_yaxis_transform())
    ax.set_xlabel(HR_NOTE)
    ax.set_title(
        "Severe pain sensitivity: key M4 hazard ratios\n(initial pain 7–10 and pain = 10)",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(MANUSCRIPT_DIR / "fig12_severe_pain_sensitivity.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out
