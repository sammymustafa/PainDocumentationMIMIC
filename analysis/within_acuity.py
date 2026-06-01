"""M4-style Cox models within ESI strata (fig11)."""

from __future__ import annotations

import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox, ph_test_report
from analysis.cox_models import formula_within_acuity
from analysis.model_domains import domain_for_term
from analysis.prep_cohort import prep_analytic_cohort
from analysis.sectional_forest import (
    WITHIN_ACUITY_SECTIONS,
    plot_multi_panel_sectional,
    prepare_sectional_rows,
)

ESI_STRATA = ["ESI 1–2", "ESI 3", "ESI 4–5"]


def run_within_acuity(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    all_rows = []
    notes = []
    panels: list[tuple[str, pd.DataFrame, list]] = []
    formula = formula_within_acuity(df)

    for esi in ESI_STRATA:
        sub = df[df["esi_group"] == esi]
        cph = fit_cox(sub, formula)
        if cph is None:
            notes.append(f"{esi}: skipped (N/events insufficient)")
            continue
        rows = extract_terms(
            cph,
            model=f"within_{esi}",
            model_label=f"Within {esi}",
            formula=formula,
        )
        for r in rows:
            r["esi_group"] = esi
            r["domain"] = domain_for_term(r["term"])
            all_rows.append(r)
        ph = ph_test_report(cph, sub, formula)
        (ANALYSIS_OUT / f"ph_within_acuity_{esi.replace(' ', '_')}.txt").write_text(ph)

        res_df = pd.DataFrame(rows)
        n = int(cph.durations.shape[0])
        panels.append(
            (
                f"{esi}\n(n={n:,}, events={int(cph.event_observed.sum()):,})",
                res_df,
                WITHIN_ACUITY_SECTIONS,
            )
        )

    out = pd.DataFrame(all_rows)
    out.to_csv(ANALYSIS_OUT / "within_acuity_cox_hr.csv", index=False)
    if notes:
        (ANALYSIS_OUT / "within_acuity_notes.txt").write_text("\n".join(notes))

    if panels:
        plot_multi_panel_sectional(
            panels,
            MANUSCRIPT_DIR / "fig11_within_acuity_forests.png",
            suptitle="Within-acuity M4-style models (race/insurance; no disposition or analgesia)",
            ncol=3,
            exclude_year=True,
            exclude_arrival_other=True,
        )
        sectional = pd.concat(
            [
                prepare_sectional_rows(
                    res, WITHIN_ACUITY_SECTIONS, exclude_year=True, exclude_arrival_other=True
                ).assign(esi_group=title.split("\n")[0])
                for title, res, _ in panels
            ],
            ignore_index=True,
        )
        sectional.to_csv(ANALYSIS_OUT / "within_acuity_key_hrs.csv", index=False)
        (MANUSCRIPT_DIR / "tables").mkdir(parents=True, exist_ok=True)
        sectional.to_csv(MANUSCRIPT_DIR / "tables" / "table11_within_acuity_key_hrs.csv", index=False)

    return out
