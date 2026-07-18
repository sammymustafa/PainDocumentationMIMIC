#!/usr/bin/env python3
"""Comparison forest: key M4 HRs (race, insurance, core covariates) across the
S0–S6 cohort-selection scenarios. The decision figure: if a point estimate is
stable across scenarios, the finding is robust to the selection choice.

Input : outputs/scenario_m4_terms.csv, outputs/scenario_summary.csv
Output: figures/scenario_comparison_forest.(png|pdf)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT, FIGS = HERE / "outputs", HERE / "figures"

SCEN_ORDER = [
    "S0_baseline", "S1_race_inclusive", "S2_insurance_inclusive",
    "S3_zero_valid", "S4_text_reassessment", "S5_trauma_only", "S6_all_inclusive",
]
SCEN_LABEL = {
    "S0_baseline": "S0 baseline",
    "S1_race_inclusive": "S1 all races",
    "S2_insurance_inclusive": "S2 + undocumented ins.",
    "S3_zero_valid": "S3 pain=0 valid",
    "S4_text_reassessment": "S4 text = reassessed",
    "S5_trauma_only": "S5 trauma only",
    "S6_all_inclusive": "S6 all inclusive",
}
COLORS = ["#1b2631", "#c0392b", "#2471a3", "#1e8449", "#b7950b", "#7d3c98", "#e67e22"]

# term label -> display row (order top to bottom)
ROWS = [
    ("Black vs White", "Race: Black vs White"),
    ("Hispanic vs White", "Race: Hispanic vs White"),
    ("Asian vs White", "Race: Asian vs White"),
    ("Other vs White", "Race: Other (pooled small) vs White"),
    ("Unknown vs White", "Race: Unknown vs White"),
    ("Medicaid vs private", "Insurance: Medicaid vs private"),
    ("Medicare vs private", "Insurance: Medicare vs private"),
    ("undocumented vs private", "Insurance: undocumented vs private"),
    ("non-English vs English", "Language: non-English vs English"),
    ("initial_pain_score", "Initial pain score (per point)"),
    ("triage_acuity", "ESI acuity (per level)"),
]


def main() -> None:
    terms = pd.read_csv(OUT / "scenario_m4_terms.csv")
    summ = pd.read_csv(OUT / "scenario_summary.csv").set_index("scenario")

    label_col = "comparison"
    terms[label_col] = terms[label_col].str.replace("'", "", regex=False)
    terms = terms.rename(columns={"hazard_ratio": "hr", "ci_low": "hr_lower",
                                  "ci_high": "hr_upper"})
    fig, ax = plt.subplots(figsize=(11.5, 10))

    y = 0
    yticks, ylabels = [], []
    for key, disp in ROWS:
        block = terms[terms[label_col] == key]
        if block.empty:
            continue
        n_here = 0
        for i, sc in enumerate(SCEN_ORDER):
            r = block[block["scenario"] == sc]
            if r.empty:
                continue
            r = r.iloc[0]
            hr, lo, hi = r["hr"], r["hr_lower"], r["hr_upper"]
            yy = y - i * 0.11
            ax.errorbar([hr], [yy], xerr=[[hr - lo], [hi - hr]],
                        fmt="o", ms=4.5, lw=1.4, capsize=2.2,
                        color=COLORS[i], zorder=3)
            n_here += 1
        yticks.append(y - 0.33)
        ylabels.append(disp)
        y -= 1.0
        ax.axhline(y + 0.12, color="#d5d8dc", lw=0.7, zorder=1)

    ax.axvline(1.0, color="#95a5a6", ls="--", lw=1.2, zorder=1)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=10.5)
    ax.set_xscale("log")
    ax.set_xlabel("Hazard ratio for first pain reassessment (M4, log scale)\n"
                  "HR > 1 = faster reassessment", fontsize=11)
    ax.set_title("Key M4 estimates across cohort-selection scenarios",
                 fontsize=13.5, weight="bold", pad=12)

    handles = [plt.Line2D([0], [0], marker="o", color=COLORS[i], lw=1.4,
                          label=f"{SCEN_LABEL[sc]}  (n={summ.loc[sc,'n']:,}, "
                                f"ev={summ.loc[sc,'events']:,})")
               for i, sc in enumerate(SCEN_ORDER) if sc in summ.index]
    ax.legend(handles=handles, loc="lower right", fontsize=8.5, framealpha=0.95)
    ax.grid(axis="x", color="#eaecee", lw=0.6, zorder=0)

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"scenario_comparison_forest.{ext}", dpi=300, bbox_inches="tight")
    print(f"Wrote {FIGS/'scenario_comparison_forest.png'}")

    # console: quick robustness read-out for the two headline terms
    for key in ["Black vs White", "Medicaid vs private"]:
        block = terms[terms[label_col] == key]
        if not block.empty:
            rng = block.groupby("scenario")["hr"].first()
            print(f"{key}: HR range across scenarios "
                  f"{rng.min():.3f}–{rng.max():.3f}")


if __name__ == "__main__":
    main()
