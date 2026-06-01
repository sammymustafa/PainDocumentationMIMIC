"""Appendix table of vital-sign HRs from M4 (adjusted but not shown in main forests)."""

from __future__ import annotations

import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_models import VITAL_Z_TERMS
from analysis.sectional_forest import prepare_sectional_rows, VITAL_SIGN_SECTIONS


def export_vitals_appendix_table(m4: pd.DataFrame | None = None) -> pd.DataFrame:
    if m4 is None:
        p = ANALYSIS_OUT / "m4_cox_hr.csv"
        m4 = pd.read_csv(p) if p.exists() else pd.DataFrame()
    if m4.empty:
        return pd.DataFrame()

    vital_rows = m4[m4["term"].astype(str).apply(lambda t: any(v in t for v in VITAL_Z_TERMS))]
    table = prepare_sectional_rows(m4, VITAL_SIGN_SECTIONS, exclude_year=False)
    if table.empty and not vital_rows.empty:
        table = vital_rows[
            ["term", "comparison", "hazard_ratio", "ci_low", "ci_high", "pvalue"]
        ].copy()
        table.insert(0, "section", "Vital signs (M4-adjusted)")

    appendix_dir = MANUSCRIPT_DIR / "appendix"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(appendix_dir / "table_vital_sign_m4_hrs.csv", index=False)
    table.to_csv(ANALYSIS_OUT / "vitals_appendix_m4_hrs.csv", index=False)
    return table


def export_arrival_other_appendix(m4: pd.DataFrame | None = None) -> pd.DataFrame:
    """Other vs walk-in arrival mode HRs (appendix only; excluded from main forest)."""
    if m4 is None:
        p = ANALYSIS_OUT / "m4_cox_hr.csv"
        m4 = pd.read_csv(p) if p.exists() else pd.DataFrame()
    if m4.empty:
        return pd.DataFrame()
    other = m4[
        m4["term"].astype(str).str.contains("arrival_mode", na=False)
        & (
            m4["term"].astype(str).str.contains("other", case=False, na=False)
            | m4["comparison"].astype(str).str.contains("other", case=False, na=False)
        )
    ]
    appendix_dir = MANUSCRIPT_DIR / "appendix"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    other.to_csv(appendix_dir / "table_arrival_mode_other_m4_hrs.csv", index=False)
    return other
