"""Fit primary sequential Cox M1–M4 and disposition pathway sensitivity."""

from __future__ import annotations

import pandas as pd

from analysis._paths import ANALYSIS_OUT
from analysis.cox_fit import fit_cox, ph_test_report
from analysis.cox_models import (
    fit_named_model,
    fit_sequential_models,
    formula_m4,
    formula_m4_disposition,
)
from analysis.model_sequence_table import export_model_sequence_table
from analysis.prep_cohort import prep_analytic_cohort


def run_primary_cox(df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    df = prep_analytic_cohort() if df is None else df
    out_dir = ANALYSIS_OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    sequential = fit_sequential_models(df)
    sequential.to_csv(out_dir / "sequential_cox_hr.csv", index=False)
    export_model_sequence_table(sequential)

    m4 = fit_named_model(df, "M4", formula_m4(df), "Primary adjusted (M4)")
    m4.to_csv(out_dir / "m4_cox_hr.csv", index=False)

    m4_disp = fit_named_model(
        df,
        "M4_disposition",
        formula_m4_disposition(df),
        "Pathway sensitivity (M4 + disposition)",
    )
    m4_disp.to_csv(out_dir / "m4_disposition_cox_hr.csv", index=False)
    m4_disp.to_csv(out_dir / "m5_pathway_cox_hr.csv", index=False)  # legacy alias
    m4_disp.to_csv(out_dir / "m5_cox_hr.csv", index=False)

    ph_lines = []
    cph = fit_cox(df, formula_m4(df))
    if cph is not None:
        ph_lines.append(ph_test_report(cph, df, formula_m4(df)))
    (out_dir / "ph_diagnostics_m4.txt").write_text("\n\n".join(ph_lines))

    return {
        "sequential": sequential,
        "m4": m4,
        "m4_disposition": m4_disp,
        "m5_pathway": m4_disp,
        "m5": m4_disp,
    }
