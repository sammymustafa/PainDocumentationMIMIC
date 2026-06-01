"""Adjusted race HR forests by initial pain group (1–3, 4–6, 7–10 only)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import DURATION_COL, EVENT_COL, MANUSCRIPT_DIR
from analysis.cox_fit import MIN_EVENTS, MIN_N, extract_terms, fit_cox
from analysis.cox_models import PARSIMONIOUS_STRATUM_FORMULA
from analysis.model_domains import display_label

PAIN_DIR = MANUSCRIPT_DIR / "pain_strata"
HR_NOTE = "HR > 1: faster reassessment  |  HR < 1: slower reassessment"

GROUPED_STRATA = [
    ("1-3", 1, 3),
    ("4-6", 4, 6),
    ("7-10", 7, 10),
]


def _subset(df: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    s = df["initial_pain_score"].round()
    return df[(s >= lo) & (s <= hi)].copy()


def _forest_race(
    df: pd.DataFrame,
    path: Path,
    title: str,
) -> pd.DataFrame:
    cph = fit_cox(df, PARSIMONIOUS_STRATUM_FORMULA)
    if cph is None:
        fig, ax = plt.subplots(figsize=(7, 2))
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            f"Insufficient N/events\n(n={len(df)}, events={int(df[EVENT_COL].sum())})",
            ha="center",
        )
        ax.set_title(title)
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return pd.DataFrame()

    terms = pd.DataFrame(extract_terms(cph))
    race = terms[terms["term"].astype(str).str.contains("race_ethnicity", na=False)].copy()
    if race.empty:
        return race

    race = race.sort_values("hazard_ratio")
    n_rows = len(race)
    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.5 * n_rows + 1.2)))
    y = np.arange(n_rows)
    ax.errorbar(
        race["hazard_ratio"],
        y,
        xerr=[race["hazard_ratio"] - race["ci_low"], race["ci_high"] - race["hazard_ratio"]],
        fmt="o",
        capsize=3,
    )
    ax.axvline(1, color="gray", ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(
        [display_label(t, c) for t, c in zip(race["term"], race["comparison"])],
        fontsize=9,
    )
    ax.set_ylim(-0.5, n_rows - 0.5)
    ax.set_xlabel(HR_NOTE)
    ax.set_title(
        f"{title}\n(adjusted: age, sex, insurance, ESI, disposition)",
        fontweight="bold",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    race["pain_group"] = title
    return race


def run_pain_strata_forests(cohort: pd.DataFrame) -> pd.DataFrame:
    """Primary outcome only: three forest plots for pain groups 1–3, 4–6, 7–10."""
    PAIN_DIR.mkdir(parents=True, exist_ok=True)
    log_rows: list[dict] = []
    hr_parts: list[pd.DataFrame] = []

    for label, lo, hi in GROUPED_STRATA:
        sub = _subset(cohort, lo, hi)
        n, ev = len(sub), int(sub[EVENT_COL].sum()) if len(sub) else 0
        path = PAIN_DIR / f"forest_primary_pain_{label}.png"
        title = f"Initial pain {label}"
        log_rows.append({"pain_group": label, "n": n, "events": ev, "path": str(path)})

        if n < MIN_N or ev < MIN_EVENTS:
            log_rows[-1]["status"] = "skipped"
            continue

        log_rows[-1]["status"] = "ok"
        hr = _forest_race(sub, path, title)
        if len(hr):
            hr_parts.append(hr)

    log = pd.DataFrame(log_rows)
    log.to_csv(PAIN_DIR / "pain_strata_run_log.csv", index=False)
    if hr_parts:
        pd.concat(hr_parts).to_csv(PAIN_DIR / "pain_strata_race_hr.csv", index=False)
    return log
