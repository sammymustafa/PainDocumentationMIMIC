"""Insurance-focused figure: KM, M4 HRs, within-ESI, by pain severity."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

from analysis._paths import ANALYSIS_OUT, DURATION_COL, EVENT_COL, MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox, logrank_p_by_group
from analysis.cox_models import formula_m4
from analysis.prep_cohort import prep_analytic_cohort
from analysis.sectional_forest import exclude_term

INS_LEVELS = ["private", "Medicaid", "Medicare", "undocumented", "uninsured"]
PAIN_BINS = [("1-3", 1, 3), ("4-6", 4, 6), ("7-10", 7, 10)]


def _insurance_m4_rows(m4: pd.DataFrame) -> pd.DataFrame:
    sub = m4[m4["term"].astype(str).str.contains("insurance_group", na=False)].copy()
    sub = sub[
        ~sub.apply(
            lambda r: exclude_term(
                r["term"], str(r.get("comparison", "")), exclude_arrival_other=True
            ),
            axis=1,
        )
    ]
    return sub.sort_values("hazard_ratio")


def _insurance_within_acuity(within: pd.DataFrame) -> pd.DataFrame:
    sub = within[within["term"].astype(str).str.contains("insurance_group", na=False)].copy()
    if "esi_group" not in sub.columns:
        return sub
    return sub.sort_values(["esi_group", "hazard_ratio"])


def _insurance_by_pain(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, lo, hi in PAIN_BINS:
        s = df["initial_pain_score"].round()
        sub = df[(s >= lo) & (s <= hi)]
        cph = fit_cox(sub, formula_m4(sub))
        if cph is None:
            continue
        for r in extract_terms(cph, model=label, formula=formula_m4(sub)):
            if "insurance_group" not in r["term"]:
                continue
            if "Medicaid" not in str(r["term"]) and "Medicaid" not in str(r.get("comparison", "")):
                if "Medicare" not in str(r["term"]) and "Medicare" not in str(r.get("comparison", "")):
                    continue
            rows.append(
                {
                    "pain_group": label,
                    "comparison": r["comparison"],
                    "hazard_ratio": r["hazard_ratio"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                    "pvalue": r["pvalue"],
                    "n": r["n"],
                    "n_events": r["n_events"],
                }
            )
    return pd.DataFrame(rows)


def _forest_panel(ax: plt.Axes, df: pd.DataFrame, title: str) -> None:
    if df.empty:
        ax.set_title(f"{title}\n(no data)")
        ax.axis("off")
        return
    n = len(df)
    y = np.arange(n)
    ax.errorbar(
        df["hazard_ratio"],
        y,
        xerr=[df["hazard_ratio"] - df["ci_low"], df["ci_high"] - df["hazard_ratio"]],
        fmt="o",
        capsize=3,
        color="steelblue",
    )
    ax.axvline(1, color="gray", ls="--")
    labels = (
        [f"{r['esi_group']}: {r['comparison']}" for _, r in df.iterrows()]
        if "esi_group" in df.columns
        else df["comparison"].tolist()
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_ylim(-0.5, n - 0.5)
    ax.set_xlabel("Hazard ratio")
    ax.set_title(title, fontweight="bold", fontsize=8)


def run_insurance_focused(
    df: pd.DataFrame | None = None,
    m4: pd.DataFrame | None = None,
    within_acuity: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    if m4 is None:
        p = ANALYSIS_OUT / "m4_cox_hr.csv"
        m4 = pd.read_csv(p) if p.exists() else pd.DataFrame()
    if within_acuity is None:
        p = ANALYSIS_OUT / "within_acuity_cox_hr.csv"
        within_acuity = pd.read_csv(p) if p.exists() else pd.DataFrame()

    by_acuity = _insurance_within_acuity(within_acuity)
    by_pain = _insurance_by_pain(df)
    (MANUSCRIPT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    by_acuity.to_csv(MANUSCRIPT_DIR / "tables" / "table10_insurance_by_acuity.csv", index=False)
    by_pain.to_csv(MANUSCRIPT_DIR / "tables" / "table10_insurance_by_pain.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    ax = axes[0, 0]
    kmf = KaplanMeierFitter()
    levels = [x for x in INS_LEVELS if x in df["insurance_group"].unique()]
    for lev in levels:
        sub = df[df["insurance_group"] == lev]
        if len(sub) < 30:
            continue
        kmf.fit(sub[DURATION_COL], sub[EVENT_COL], label=f"{lev} (n={len(sub):,})")
        kmf.plot_cumulative_density(ax=ax, ci_show=False)
    p_lr = logrank_p_by_group(df[df["insurance_group"].isin(levels)], "insurance_group")
    if p_lr is not None:
        ax.text(0.98, 0.02, f"log-rank p = {p_lr:.4f}", transform=ax.transAxes, ha="right", fontsize=7)
    ax.set_xlim(0, 240)
    ax.set_xlabel("Minutes from initial pain")
    ax.set_ylabel("Cumulative reassessment")
    ax.set_title("A. Unadjusted KM by insurance", fontweight="bold", fontsize=9)
    ax.legend(fontsize=6)

    _forest_panel(axes[0, 1], _insurance_m4_rows(m4), "B. M4: Medicaid/Medicare vs private")
    _forest_panel(axes[1, 0], by_acuity, "C. Within ESI strata")
    _forest_panel(axes[1, 1], by_pain, "D. M4 HRs by initial pain group")

    fig.suptitle(
        "Insurance and pain reassessment (documented insurance; M4 primary model)",
        fontweight="bold",
        fontsize=12,
    )
    fig.tight_layout()
    out_path = MANUSCRIPT_DIR / "fig10_insurance_focused_analysis.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return by_acuity
