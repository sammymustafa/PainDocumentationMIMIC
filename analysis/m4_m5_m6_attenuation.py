"""M4 primary vs M4+disposition pathway sensitivity (fig09)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_models import VITAL_Z_TERMS
from analysis.sectional_forest import exclude_term

FOCAL_PREFIXES = [
    "race_ethnicity",
    "insurance_group",
    "language_group",
    "age_group",
    "triage_acuity",
    "injury_group",
    "initial_pain_score",
    "arrival_mode",  # ambulance only (other excluded via _skip_term)
    "arrival_shift",
    "arrival_weekend",
    "ed_arrivals",
    "ed_census",
]


def _skip_term(term: str, comparison: str) -> bool:
    if any(v in str(term) for v in VITAL_Z_TERMS):
        return True
    if "comorbidity_count" in str(term):
        return True
    if any(ex in str(term) for ex in ["disposition", "year_era", "TRANSFER", "OTHER"]):
        return True
    return exclude_term(term, comparison, exclude_arrival_other=True)


def build_m4_disposition_table(m4: pd.DataFrame, m4_disp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in m4.iterrows():
        if _skip_term(str(r["term"]), str(r.get("comparison", ""))):
            continue
        if not any(p in str(r["term"]) for p in FOCAL_PREFIXES):
            continue
        rd = m4_disp[m4_disp["term"] == r["term"]]
        rows.append(
            {
                "term": r["term"],
                "comparison": r["comparison"],
                "hr_m4": r["hazard_ratio"],
                "ci_low_m4": r["ci_low"],
                "ci_high_m4": r["ci_high"],
                "p_m4": r["pvalue"],
                "hr_m4_disp": rd["hazard_ratio"].iloc[0] if len(rd) else np.nan,
                "ci_low_m4_disp": rd["ci_low"].iloc[0] if len(rd) else np.nan,
                "ci_high_m4_disp": rd["ci_high"].iloc[0] if len(rd) else np.nan,
                "p_m4_disp": rd["pvalue"].iloc[0] if len(rd) else np.nan,
            }
        )
    disp = m4_disp[m4_disp["term"].astype(str).str.contains("disposition_pathway", na=False)]
    for _, r in disp.iterrows():
        if "ADMITTED" not in str(r["term"]) and "ADMITTED" not in str(r.get("comparison", "")):
            continue
        rows.append(
            {
                "term": r["term"],
                "comparison": r["comparison"],
                "hr_m4": np.nan,
                "ci_low_m4": np.nan,
                "ci_high_m4": np.nan,
                "p_m4": np.nan,
                "hr_m4_disp": r["hazard_ratio"],
                "ci_low_m4_disp": r["ci_low"],
                "ci_high_m4_disp": r["ci_high"],
                "p_m4_disp": r["pvalue"],
            }
        )
    return pd.DataFrame(rows)


def plot_m4_disposition_sensitivity(table: pd.DataFrame, path: Path) -> None:
    sub = table.dropna(subset=["hr_m4"]).head(20)
    if sub.empty:
        sub = table.head(20)
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(10, max(5, 0.35 * len(sub) + 1)))
    y = np.arange(len(sub))
    ax.errorbar(
        sub["hr_m4"],
        y,
        xerr=[sub["hr_m4"] - sub["ci_low_m4"], sub["ci_high_m4"] - sub["hr_m4"]],
        fmt="o",
        color="steelblue",
        label="M4 primary",
        capsize=3,
    )
    ok = sub["hr_m4_disp"].notna()
    if ok.any():
        ax.errorbar(
            sub.loc[ok, "hr_m4_disp"],
            y[ok],
            xerr=[
                sub.loc[ok, "hr_m4_disp"] - sub.loc[ok, "ci_low_m4_disp"],
                sub.loc[ok, "ci_high_m4_disp"] - sub.loc[ok, "hr_m4_disp"],
            ],
            fmt="s",
            color="coral",
            label="M4 + disposition (sensitivity)",
            capsize=3,
        )
    ax.axvline(1, color="gray", ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(sub["comparison"].astype(str), fontsize=7)
    ax.set_xlabel("Hazard ratio (HR > 1: faster reassessment)")
    ax.set_title(
        "Pathway sensitivity: M4 primary vs M4 + admitted vs home",
        fontweight="bold",
        fontsize=10,
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run_m4_m5_m6_attenuation(
    m4: pd.DataFrame | None = None,
    m5: pd.DataFrame | None = None,
    m6: pd.DataFrame | None = None,
) -> pd.DataFrame:
    del m6
    if m4 is None:
        m4 = pd.read_csv(ANALYSIS_OUT / "m4_cox_hr.csv")
    if m5 is None:
        p = ANALYSIS_OUT / "m4_disposition_cox_hr.csv"
        m5 = pd.read_csv(p if p.exists() else ANALYSIS_OUT / "m5_pathway_cox_hr.csv")
    table = build_m4_disposition_table(m4, m5)
    tables_dir = MANUSCRIPT_DIR / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(tables_dir / "table09_m4_disposition_sensitivity.csv", index=False)
    table.to_csv(ANALYSIS_OUT / "m4_disposition_attenuation.csv", index=False)
    table.to_csv(tables_dir / "table09_m4_vs_m5_attenuation.csv", index=False)  # legacy
    if not table.empty:
        plot_m4_disposition_sensitivity(table, MANUSCRIPT_DIR / "fig09_m4_disposition_sensitivity.png")
        plot_m4_disposition_sensitivity(table, MANUSCRIPT_DIR / "fig09_m4_vs_m5_attenuation.png")
    return table


run_m4_vs_m5_attenuation = run_m4_m5_m6_attenuation
