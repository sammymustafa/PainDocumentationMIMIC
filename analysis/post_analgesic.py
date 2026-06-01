"""Post-analgesic pathway analysis (sensitivity S2)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR, POST_DURATION, POST_EVENT, RACES
from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import formula_post_analgesic
from analysis.prep_part2 import build_post_analgesic_cohort

SUMMARY_MD = MANUSCRIPT_DIR / "post_analgesic_pathway_summary.md"


def _km_by_race(df: pd.DataFrame, path: Path) -> float | None:
    fig, ax = plt.subplots(figsize=(10, 6))
    kmf = KaplanMeierFitter()
    groups, durations, events = [], [], []
    for race in RACES:
        sub = df[df["race_ethnicity"] == race]
        if len(sub) < 20:
            continue
        kmf.fit(sub[POST_DURATION], sub[POST_EVENT], label=f"{race} (n={len(sub):,})")
        kmf.plot_cumulative_density(ax=ax, ci_show=False)
        groups.append(sub["race_ethnicity"])
        durations.append(sub[POST_DURATION])
        events.append(sub[POST_EVENT])
    p_val = None
    if len(groups) >= 2:
        try:
            lr = multivariate_logrank_test(
                pd.concat(durations), pd.concat(groups), pd.concat(events)
            )
            p_val = float(lr.p_value)
            ax.text(0.98, 0.02, f"log-rank p = {p_val:.4f}", transform=ax.transAxes, ha="right")
        except Exception:
            pass
    ax.set_xlim(0, min(480, df[POST_DURATION].quantile(0.95)))
    ax.set_xlabel("Minutes after first analgesic")
    ax.set_ylabel("Cumulative post-analgesic reassessment")
    ax.set_title(
        "Pathway sensitivity: post-analgesic reassessment by race/ethnicity\n"
        "(not primary inference; time zero = first analgesic)"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p_val


def run_post_analgesic(survival: pd.DataFrame | None = None) -> pd.DataFrame:
    from analysis.prep_cohort import prep_analytic_cohort

    surv = prep_analytic_cohort(survival)
    full = build_post_analgesic_cohort(surv)
    primary = full[(full["is_trauma"]) & (full["pain_10"])].copy()
    secondary = full[full["is_trauma"]].copy()

    for label, sub in [("primary_trauma_pain10", primary), ("secondary_trauma", secondary), ("all_analgesic", full)]:
        sub.to_csv(ANALYSIS_OUT / f"post_analgesic_cohort_{label}.csv", index=False)

    _km_by_race(primary if len(primary) >= 80 else full, MANUSCRIPT_DIR / "fig13_post_analgesic_pathway.png")

    use = primary if len(primary) >= 80 else full
    post_formula = formula_post_analgesic(use)
    cph = fit_cox(use, post_formula, duration_col=POST_DURATION, event_col=POST_EVENT)
    rows = []
    if cph is not None:
        rows = extract_terms(cph, model="post_analgesic", formula=post_formula)
    out_rx = pd.DataFrame(rows)
    if out_rx.empty:
        out_rx = pd.DataFrame(
            columns=[
                "model",
                "term",
                "comparison",
                "hazard_ratio",
                "ci_low",
                "ci_high",
                "pvalue",
            ]
        )
    out_rx.to_csv(ANALYSIS_OUT / "post_analgesic_cox_hr.csv", index=False)

    SUMMARY_MD.write_text(
        "# Post-analgesic pathway analysis (sensitivity)\n\n"
        "Time zero = first analgesic after initial pain documentation. "
        "Event = first pain score documented strictly after analgesic. "
        "Censor at ED departure.\n\n"
        f"- Primary subgroup: trauma + pain=10 (N={len(primary):,})\n"
        f"- Secondary: all trauma with analgesic (N={len(secondary):,})\n"
        f"- Full analgesic cohort (N={len(full):,})\n\n"
        "**Interpretation:** This is a pathway/sensitivity analysis. It does not replace "
        "the primary initial-pain-to-reassessment analysis. Attenuation of demographic "
        "associations after analgesia suggests signals may be upstream of treatment or "
        "early clinical attention.\n"
    )
    return full
