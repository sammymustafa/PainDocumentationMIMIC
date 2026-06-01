"""Manuscript figures fig07–fig15 (extended analyses)."""

from __future__ import annotations

import pandas as pd

from analysis.insurance_focused import run_insurance_focused
from analysis.m4_m5_m6_attenuation import run_m4_m5_m6_attenuation
from analysis.sequential_attenuation import run_sequential_attenuation
from analysis.severe_pain_sensitivity import run_severe_pain_sensitivity
from analysis.year_trend import run_year_trend


def run_extended_figures(
    df: pd.DataFrame,
    cox: dict[str, pd.DataFrame],
) -> None:
    sequential = cox.get("sequential", pd.DataFrame())
    m4 = cox.get("m4", pd.DataFrame())
    m4_disp = cox.get("m4_disposition", cox.get("m5_pathway", cox.get("m5", pd.DataFrame())))

    print("  Fig 07 — continuous year trend (M4)...")
    run_year_trend(df)

    print("  Fig 08 — sequential attenuation M1–M4...")
    run_sequential_attenuation(sequential)

    print("  Fig 09 — M4 vs M4+disposition sensitivity...")
    run_m4_m5_m6_attenuation(m4, m4_disp)

    print("  Fig 10 — insurance-focused...")
    run_insurance_focused(df, m4=m4)

    print("  Fig 12 — severe pain sensitivity...")
    run_severe_pain_sensitivity(df)
