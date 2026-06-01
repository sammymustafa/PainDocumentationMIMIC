"""Appendix figures: interactions, disposition-stratified M4, within-acuity, vitals, IPTW."""

from __future__ import annotations

import pandas as pd

from analysis._paths import MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import formula_m4
from analysis.interactions import run_interactions
from analysis.iptw_sensitivity import run_iptw_sensitivity
from analysis.prep_cohort import prep_analytic_cohort
from analysis.sectional_forest import M4_SECTIONS, plot_multi_panel_sectional, prepare_sectional_rows
from analysis.vitals_appendix import export_arrival_other_appendix, export_vitals_appendix_table
from analysis.within_acuity_appendix import run_within_acuity_appendix


def run_appendix_disposition_strata(df: pd.DataFrame | None = None) -> None:
    df = prep_analytic_cohort() if df is None else df
    appendix_dir = MANUSCRIPT_DIR / "appendix"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    panels = []
    for label, mask in [("Admitted", df["is_admitted"]), ("Discharged home", df["is_home"])]:
        sub = df[mask]
        cph = fit_cox(sub, formula_m4(sub))
        if cph is None:
            continue
        rows = extract_terms(cph, model=label, formula=formula_m4(sub))
        res = pd.DataFrame(rows)
        n = int(cph.durations.shape[0])
        panels.append(
            (
                f"{label}\n(n={n:,}, events={int(cph.event_observed.sum()):,})",
                res,
                M4_SECTIONS,
            )
        )
    if panels:
        plot_multi_panel_sectional(
            panels,
            appendix_dir / "figA_disposition_stratified_m4_forests.png",
            suptitle="Appendix: M4 primary model within admitted vs discharged-home strata",
            ncol=2,
            exclude_year=True,
            exclude_arrival_other=True,
        )
        forest = pd.concat(
            [
                prepare_sectional_rows(
                    res, M4_SECTIONS, exclude_year=True, exclude_arrival_other=True
                ).assign(stratum=t.split("\n")[0])
                for t, res, _ in panels
            ],
            ignore_index=True,
        )
        forest.to_csv(appendix_dir / "tableA_disposition_stratified_m4_hrs.csv", index=False)


def run_appendix_analyses(df: pd.DataFrame, cox: dict | None = None) -> None:
    appendix_dir = MANUSCRIPT_DIR / "appendix"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    m4 = cox.get("m4") if cox else None

    run_interactions(df, out_dir=appendix_dir)
    run_appendix_disposition_strata(df)
    run_within_acuity_appendix(df)
    export_vitals_appendix_table(m4)
    export_arrival_other_appendix(m4)
    run_iptw_sensitivity(df, m4=m4)
