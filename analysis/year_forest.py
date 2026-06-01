"""Single forest plot: policy-era HRs from M5 (5-year bins)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.model_domains import display_label

HR_NOTE = "HR > 1: faster reassessment  |  HR < 1: slower reassessment"


def plot_year_era_forest(m5: pd.DataFrame, path: Path | None = None) -> bool:
    path = path or MANUSCRIPT_DIR / "fig07_year_policy_5yr_forest.png"
    sub = m5[m5["term"].astype(str).str.contains("year_era", na=False)].copy()
    sub = sub[~sub["term"].astype(str).str.contains("other_era", na=False)]
    if sub.empty:
        return False

    sub = sub.sort_values("hazard_ratio")
    n_rows = len(sub)
    fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * n_rows + 1.5)))
    y = np.arange(n_rows)
    ax.errorbar(
        sub["hazard_ratio"],
        y,
        xerr=[sub["hazard_ratio"] - sub["ci_low"], sub["ci_high"] - sub["hazard_ratio"]],
        fmt="o",
        capsize=3,
        color="steelblue",
    )
    ax.axvline(1, color="gray", ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(
        [display_label(t, c) for t, c in zip(sub["term"], sub["comparison"])],
        fontsize=9,
    )
    ax.set_ylim(-0.5, n_rows - 0.5)
    ax.set_xlabel(HR_NOTE)
    ax.set_title(
        "Adjusted hazard ratios by 5-year policy era (M5)\n"
        "De-identified MIMIC anchor years; reference era = first level",
        fontweight="bold",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    sub.to_csv(MANUSCRIPT_DIR / "tables" / "table_year_policy_5yr_hr.csv", index=False)
    return True


def run_year_forest(m5: pd.DataFrame | None = None) -> bool:
    if m5 is None:
        p = ANALYSIS_OUT / "m5_cox_hr.csv"
        if not p.exists():
            return False
        m5 = pd.read_csv(p)
    return plot_year_era_forest(m5)
