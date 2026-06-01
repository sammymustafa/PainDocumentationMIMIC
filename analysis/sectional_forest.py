"""Sectional forest plot helpers (fig 6 style): grouped y-axis, exclude year/undocumented."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.model_domains import display_label

HR_NOTE = "HR > 1: faster reassessment  |  HR < 1: slower reassessment"

# Main figures: vitals adjusted in M3+ but not displayed (see appendix vital-sign table).
M4_SECTIONS: list[tuple[str, list[str]]] = [
    ("Clinical presentation", ["initial_pain_score"]),
    ("Demographics", ["age_group", "sex", "race_ethnicity", "language_group"]),
    ("Insurance", ["insurance_group"]),
    ("Diagnosis / injury", ["injury_group"]),
    ("Clinical severity", ["triage_acuity"]),
    (
        "ED context / workflow",
        [
            "arrival_mode",
            "arrival_shift",
            "arrival_weekend",
            "ed_arrivals_past_1hr",
            "ed_census_at_initial_pain_hour",
            "year_era",
        ],
    ),
]

M4_DISPOSITION_SECTIONS: list[tuple[str, list[str]]] = M4_SECTIONS + [
    ("Disposition pathway (sensitivity)", ["disposition_pathway"]),
]

M5_PATHWAY_SECTIONS = M4_DISPOSITION_SECTIONS

M6_PATHWAY_SECTIONS = M5_PATHWAY_SECTIONS  # legacy alias

M5_SECTIONS = M4_SECTIONS  # legacy alias

WITHIN_ACUITY_SECTIONS: list[tuple[str, list[str]]] = [
    ("Race/ethnicity", ["race_ethnicity"]),
    ("Insurance", ["insurance_group"]),
    ("Clinical presentation", ["initial_pain_score"]),
    (
        "ED context",
        [
            "arrival_shift",
            "arrival_weekend",
            "ed_arrivals_past_1hr",
            "ed_census_at_initial_pain_hour",
            "arrival_mode",
        ],
    ),
]

VITAL_SIGN_SECTIONS: list[tuple[str, list[str]]] = [
    ("Vital signs (M4-adjusted; appendix)", ["heartrate_0_z", "resprate_0_z", "sbp_0_z"]),
]

M5_NO_DISP_SECTIONS: list[tuple[str, list[str]]] = [
    ("Clinical presentation", ["initial_pain_score"]),
    ("Demographics", ["age_group", "sex", "race_ethnicity"]),
    ("Insurance", ["insurance_group"]),
    ("Diagnosis / injury", ["injury_group"]),
    ("Clinical severity", ["triage_acuity", "heartrate_0_z", "resprate_0_z", "sbp_0_z"]),
    (
        "ED workflow",
        ["arrival_shift", "arrival_weekend", "ed_arrivals_past_1hr", "ed_census_at_initial_pain_hour"],
    ),
    ("Year/policy era", ["year_era"]),
    ("Arrival mode", ["arrival_mode"]),
]

WITHIN_DISPOSITION_SECTIONS: list[tuple[str, list[str]]] = [
    ("Clinical presentation", ["initial_pain_score"]),
    ("Demographics", ["age_group", "sex", "race_ethnicity"]),
    ("Insurance", ["insurance_group"]),
    ("Diagnosis / injury", ["injury_group"]),
    ("Clinical severity", ["triage_acuity", "heartrate_0_z", "resprate_0_z", "sbp_0_z"]),
    (
        "ED workflow",
        ["arrival_shift", "arrival_weekend", "ed_arrivals_past_1hr", "ed_census_at_initial_pain_hour"],
    ),
    ("Arrival mode", ["arrival_mode"]),
]


def _term_matches(term: str, patterns: list[str]) -> bool:
    return any(p in str(term) for p in patterns)


def exclude_term(
    term: str,
    comparison: str,
    *,
    exclude_year: bool = True,
    exclude_arrival_other: bool = False,
) -> bool:
    blob = f"{term} {comparison}".lower()
    if "undocumented" in blob:
        return True
    if exclude_year and ("year_era" in blob or "other_era" in blob):
        return True
    if exclude_arrival_other and "arrival_mode" in blob:
        if "other" in blob or "[t.other]" in term.lower():
            return True
    return False


def prepare_sectional_rows(
    results: pd.DataFrame,
    sections: list[tuple[str, list[str]]],
    *,
    exclude_year: bool = True,
    exclude_arrival_other: bool = True,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for section, patterns in sections:
        sub = results[
            results["term"].apply(
                lambda t: _term_matches(t, patterns)
                and not exclude_term(
                    t, "", exclude_year=exclude_year, exclude_arrival_other=exclude_arrival_other
                )
            )
        ]
        for _, r in sub.iterrows():
            if exclude_term(
                r["term"],
                str(r.get("comparison", "")),
                exclude_year=exclude_year,
                exclude_arrival_other=exclude_arrival_other,
            ):
                continue
            rows.append(
                {
                    "section": section,
                    "term": r["term"],
                    "comparison": r["comparison"],
                    "hazard_ratio": r["hazard_ratio"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                    "pvalue": r.get("pvalue"),
                }
            )
    return pd.DataFrame(rows)


def draw_sectional_on_axes(
    ax: plt.Axes,
    plot_df: pd.DataFrame,
    *,
    title: str = "",
    xlim: tuple[float, float] | None = None,
) -> None:
    if plot_df.empty:
        ax.set_title(f"{title}\n(no estimable terms)")
        ax.axis("off")
        return

    y_labels: list[str] = []
    y_pos: list[float] = []
    hrs, ci_lo, ci_hi = [], [], []
    y = 0.0
    last_section = None

    for _, r in plot_df.iterrows():
        if r["section"] != last_section:
            if last_section is not None:
                y += 0.55
            y_labels.append(f"— {r['section']} —")
            y_pos.append(y)
            hrs.append(np.nan)
            ci_lo.append(np.nan)
            ci_hi.append(np.nan)
            y += 0.65
            last_section = r["section"]

        y_labels.append(f"  {display_label(r['term'], r['comparison'])}")
        y_pos.append(y)
        hrs.append(r["hazard_ratio"])
        ci_lo.append(r["ci_low"])
        ci_hi.append(r["ci_high"])
        y += 0.85

    y_pos = np.array(y_pos)
    for yp, hr, lo, hi, lab in zip(y_pos, hrs, ci_lo, ci_hi, y_labels):
        if lab.startswith("—"):
            ax.text(
                0.02,
                yp,
                lab.strip("— "),
                fontsize=7,
                fontweight="bold",
                va="center",
                transform=ax.get_yaxis_transform(),
            )
            continue
        if pd.notna(hr):
            ax.errorbar(
                hr,
                yp,
                xerr=[[hr - lo], [hi - hr]],
                fmt="o",
                capsize=2,
                color="steelblue",
                markersize=4,
            )

    ax.axvline(1, color="gray", ls="--", lw=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([""] * len(y_pos))
    for yp, lab in zip(y_pos, y_labels):
        if not lab.startswith("—"):
            ax.text(-0.02, yp, lab, fontsize=6, va="center", ha="right", transform=ax.get_yaxis_transform())
    ax.set_ylim(y_pos.min() - 0.5, y_pos.max() + 0.5)
    if xlim:
        ax.set_xlim(xlim)
    ax.set_xlabel(HR_NOTE, fontsize=7)
    ax.set_title(title, fontsize=9, fontweight="bold")
    ax.tick_params(axis="x", labelsize=7)


def plot_single_sectional_forest(
    results: pd.DataFrame,
    sections: list[tuple[str, list[str]]],
    path: Path,
    *,
    title: str,
    exclude_arrival_other: bool = True,
) -> pd.DataFrame:
    plot_df = prepare_sectional_rows(
        results, sections, exclude_arrival_other=exclude_arrival_other
    )
    if plot_df.empty:
        return plot_df

    fig_h = max(8, 0.28 * len(plot_df) + len(plot_df["section"].unique()) * 0.6 + 2)
    fig, ax = plt.subplots(figsize=(9, fig_h))
    draw_sectional_on_axes(ax, plot_df, title=title)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return plot_df


def plot_multi_panel_sectional(
    panels: list[tuple[str, pd.DataFrame, list[tuple[str, list[str]]]]],
    path: Path,
    *,
    suptitle: str,
    ncol: int,
    exclude_year: bool = True,
    exclude_arrival_other: bool = True,
) -> None:
    plot_dfs = [
        prepare_sectional_rows(
            res, sect, exclude_year=exclude_year, exclude_arrival_other=exclude_arrival_other
        )
        for _, res, sect in panels
    ]

    all_hr: list[float] = []
    for pdf in plot_dfs:
        if not pdf.empty:
            all_hr.extend(pdf["hazard_ratio"].tolist())
            all_hr.extend(pdf["ci_low"].tolist())
            all_hr.extend(pdf["ci_high"].tolist())
    valid = [h for h in all_hr if pd.notna(h)]
    if valid:
        lo, hi = min(valid) * 0.92, max(valid) * 1.08
        xlim = (max(0.5, lo), min(2.0, hi))
    else:
        xlim = (0.7, 1.3)

    max_rows = max((len(p) + p["section"].nunique() if len(p) else 0) for p in plot_dfs)
    fig_h = max(10, 0.22 * max_rows + 2)
    fig_w = 5.5 * ncol
    fig, axes = plt.subplots(1, ncol, figsize=(fig_w, fig_h), squeeze=False)
    axes_flat = axes.flatten()

    for ax, (ptitle, _, _), pdf in zip(axes_flat, panels, plot_dfs):
        draw_sectional_on_axes(ax, pdf, title=ptitle, xlim=xlim)

    for ax in axes_flat[len(panels) :]:
        ax.axis("off")

    fig.suptitle(suptitle, fontsize=12, fontweight="bold", y=1.01)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
