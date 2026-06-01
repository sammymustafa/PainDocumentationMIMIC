"""M4 vs M4+disposition pathway sensitivity."""

from __future__ import annotations

import pandas as pd

from analysis.m4_m5_m6_attenuation import run_m4_m5_m6_attenuation


def run_disposition_analysis(
    df: pd.DataFrame | None = None,
    *,
    m4: pd.DataFrame | None = None,
    m5: pd.DataFrame | None = None,
    m6: pd.DataFrame | None = None,
) -> pd.DataFrame:
    del df, m6
    return run_m4_m5_m6_attenuation(m4=m4, m5=m5)
