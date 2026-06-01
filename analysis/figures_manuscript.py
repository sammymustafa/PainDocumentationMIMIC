"""Manuscript figures fig01–fig06, fig13 (core deck)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR, RACES
from analysis.prep_cohort import compute_flow_counts, prep_analytic_cohort
from analysis.sectional_forest import M4_SECTIONS, plot_single_sectional_forest

FLOW_STEPS = [
    ("all_ed_stays_in_extract", "MIMIC-IV ED stays retrieved", "end"),
    ("ap_or_trauma_stays", "Filter acute pancreatitis or trauma (ED diagnosis)", "mid"),
    ("after_exclude_small_race_groups", "Exclude small/unknown race groups", "mid"),
    ("initial_pain_documented", "Extract initial pain scores (>0) with timestamps", "mid"),
    ("after_valid_survival_time", "Valid time from initial pain to reassessment/censor", "mid"),
    ("after_exclude_undocumented_insurance", "Exclude undocumented insurance", "mid"),
    ("after_nonmissing_esi", "Require documented ESI / triage acuity", "mid"),
    ("primary_analytic_cohort", "Primary analytic cohort", "end"),
]

COLOR_END = "#f4c4c4"
COLOR_MID = "#dce8f5"


def fig06_sectional_m4_forest(m4: pd.DataFrame, path: Path | None = None) -> None:
    title = (
        "Primary adjusted Cox model (M4): factors associated with time to first pain reassessment\n"
        "(early-encounter covariates only; vitals/comorbidity in M3; disposition separate)"
    )
    plot_df = plot_single_sectional_forest(
        m4,
        M4_SECTIONS,
        path or MANUSCRIPT_DIR / "fig06_m4_sectional_forest.png",
        title=title,
        exclude_arrival_other=True,
    )
    if not plot_df.empty:
        (MANUSCRIPT_DIR / "tables").mkdir(parents=True, exist_ok=True)
        plot_df.to_csv(MANUSCRIPT_DIR / "tables" / "table06_m4_sectional_forest.csv", index=False)


def fig01_dag(path: Path | None = None) -> None:
    path = path or MANUSCRIPT_DIR / "fig01_care_pathway_dag.png"
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    boxes = [
        (1, 4.5, "Clinical\npresentation"),
        (3.2, 4.5, "Patient /\nsocial"),
        (5.4, 4.5, "Severity /\ncomorbidity"),
        (7.6, 4.5, "ED context\n(M4 primary)"),
        (6, 2, "Pain\nreassessment"),
    ]
    for x, y, t in boxes:
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x - 0.7, y - 0.4), 1.4, 0.8, boxstyle="round", fc="#e8f4fc", ec="#333"
            )
        )
        ax.text(x, y, t, ha="center", va="center", fontsize=9)
    for (x1, y1), (x2, y2) in [
        ((1.7, 4.5), (2.5, 4.5)),
        ((3.9, 4.5), (4.7, 4.5)),
        ((6.1, 4.5), (6.9, 4.5)),
        ((7.6, 4.1), (6.5, 2.4)),
        ((3.2, 4.1), (5.2, 2.4)),
    ]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color="#555"))
    ax.text(9.2, 4.5, "Disposition\n(sensitivity)", fontsize=8, ha="center", color="#888")
    ax.text(9.2, 2.8, "Analgesia /\npost-Rx (sensitivity)", fontsize=8, ha="center", color="#888")
    ax.annotate("", xy=(8.5, 4.5), xytext=(9.2, 4.5), arrowprops=dict(arrowstyle="->", color="#aaa", ls="--"))
    ax.text(6, 0.35, "M4 = primary Cox; disposition & analgesia analyzed separately", fontsize=8, ha="center")
    ax.set_title("ED pain reassessment care pathway (conceptual DAG)", fontweight="bold")
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig02_flow(counts: dict | None = None, path: Path | None = None) -> None:
    path = path or MANUSCRIPT_DIR / "fig02_cohort_flow.png"
    if counts is None:
        p = ANALYSIS_OUT / "flow_counts.json"
        counts = json.loads(p.read_text()) if p.exists() else compute_flow_counts()

    n_steps = len(FLOW_STEPS)
    fig_h = 0.55 * n_steps + 1.5
    fig, ax = plt.subplots(figsize=(7.5, fig_h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    box_w, box_h = 0.72, 0.075
    y_top = 0.94
    y_step = box_h + 0.045
    prev_n = None

    for i, (key, label, kind) in enumerate(FLOW_STEPS):
        y = y_top - i * y_step
        yc = y - box_h / 2
        fc = COLOR_END if kind == "end" else COLOR_MID
        ax.add_patch(
            mpatches.FancyBboxPatch(
                ((1 - box_w) / 2, yc),
                box_w,
                box_h,
                boxstyle="round,pad=0.01",
                fc=fc,
                ec="#333",
                linewidth=1,
            )
        )
        n = counts.get(key, 0)
        ax.text(0.5, yc + box_h * 0.55, label, ha="center", va="center", fontsize=9, wrap=True)
        ax.text(0.5, yc + box_h * 0.2, f"N = {n:,}", ha="center", va="center", fontsize=10, fontweight="bold")
        if prev_n is not None and n is not None:
            excluded = int(prev_n) - int(n)
            if excluded > 0:
                ax.text(
                    0.5,
                    yc + box_h + 0.012,
                    f"−{excluded:,}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#555",
                )
        if i < n_steps - 1:
            ax.annotate(
                "",
                xy=(0.5, yc - 0.01),
                xytext=(0.5, yc - y_step + box_h + 0.01),
                arrowprops=dict(arrowstyle="->", color="#333", lw=1.2),
            )
        prev_n = n

    comorb = counts.get("with_any_comorbidity_flag")
    foot = (
        "Undocumented insurance excluded from Cox models. Language in Table 1 only (not in adjusted Cox). "
        "Comorbidity flags from linked hospital ICD when available."
    )
    if comorb is not None:
        foot += f" Analytic cohort with ≥1 comorbidity flag: {comorb:,}."
    ax.text(0.5, 0.02, foot, ha="center", va="bottom", fontsize=7, color="#444", wrap=True)
    ax.set_title("Fig. 2. Cohort construction and analytic sample", fontweight="bold", fontsize=11, pad=12)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fig03_table1_overview(table: pd.DataFrame, path: Path | None = None) -> None:
    from analysis.table1 import _save_png

    path = path or MANUSCRIPT_DIR / "fig03_table1_overview.png"
    _save_png(table, path, title="Table 1 overview (analytic cohort)", max_rows=50)


def fig04_km(df: pd.DataFrame, path: Path | None = None) -> None:
    path = path or MANUSCRIPT_DIR / "fig04_km_reassessment_overview.png"
    ins_levels = [x for x in ["private", "Medicaid", "Medicare"] if x in df["insurance_group"].unique()]
    panels = [
        ("race_ethnicity", RACES, "Race/ethnicity"),
        ("insurance_group", ins_levels, "Insurance"),
        ("triage_acuity", sorted(df["triage_acuity"].dropna().unique()), "ESI acuity"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, (col, levels, title) in zip(axes, panels):
        kmf = KaplanMeierFitter()
        for lev in levels:
            sub = df[df[col] == lev]
            if len(sub) < 30:
                continue
            kmf.fit(sub["duration_minutes"], sub["reassessment_event"], label=str(lev))
            kmf.plot_cumulative_density(ax=ax, ci_show=False)
        ax.set_xlim(0, 240)
        ax.set_xlabel("Minutes from initial pain")
        ax.set_ylabel("Cumulative reassessment")
        ax.set_title(title)
        ax.legend(fontsize=7)
    fig.suptitle("Time to first pain reassessment (unadjusted)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig05_rates(df: pd.DataFrame, path: Path | None = None) -> None:
    path = path or MANUSCRIPT_DIR / "fig05_reassessment_rates_60min.png"
    df = df.copy()
    df["pain_bin"] = pd.cut(
        df["initial_pain_score"],
        bins=[0, 3, 6, 10],
        labels=["1–3", "4–6", "7–10"],
    )
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, col, title in zip(axes, ["race_ethnicity", "insurance_group"], ["Race/ethnicity", "Insurance"]):
        ct = (
            df.groupby(["pain_bin", col], observed=True)["reassessed_by_60"]
            .mean()
            .mul(100)
            .unstack(fill_value=np.nan)
        )
        ct.plot(kind="bar", ax=ax, rot=0)
        ax.set_ylabel("% reassessed ≤60 min")
        ax.set_xlabel("Initial pain score group")
        ax.set_title(title)
        ax.legend(fontsize=7, title="")
    fig.suptitle("60-minute reassessment by pain severity and key groups", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def run_all_figures(
    df: pd.DataFrame | None = None,
    *,
    table1: pd.DataFrame | None = None,
    m4: pd.DataFrame | None = None,
    m5: pd.DataFrame | None = None,
    flow_counts: dict | None = None,
) -> None:
    MANUSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    (MANUSCRIPT_DIR / "tables").mkdir(exist_ok=True)
    df = prep_analytic_cohort() if df is None else df

    fig01_dag()
    fig02_flow(flow_counts)
    if table1 is not None:
        fig03_table1_overview(table1)
    fig04_km(df)
    fig05_rates(df)

    if m4 is None and (ANALYSIS_OUT / "m4_cox_hr.csv").exists():
        m4 = pd.read_csv(ANALYSIS_OUT / "m4_cox_hr.csv")

    if m4 is not None and len(m4) > 0:
        fig06_sectional_m4_forest(m4)
        m4.to_csv(MANUSCRIPT_DIR / "tables" / "table_m4_full_factor.csv", index=False)
