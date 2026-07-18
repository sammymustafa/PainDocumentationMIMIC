#!/usr/bin/env python3
"""Merge the complete-case requirement into cohort eligibility.

New convention (user decision 2026-07-18): the primary analytic cohort IS the
complete-case population (n = 42,076), so descriptives and models share one n.
The 329 stays missing a model covariate (318 first vitals, 11 age) move from a
modeling footnote into the last eligibility step of the flow diagram.

Outputs:
  outputs/final/primary_cohort_cc.csv        the canonical cohort (42,076)
  outputs/final/primary_m1_m4_terms.csv      OVERWRITTEN with refits on cc
                                             (old file kept as *_v42405.csv)
  outputs/final/cif_absolute.csv             OVERWRITTEN with cc AJ estimates
  outputs/final/cc_descriptives.json         every number the draft text needs
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.cox_fit import cols_from_formula  # noqa: E402
from analysis.cox_models import formula_m4  # noqa: E402
from analysis_refinement.final_analysis import (  # noqa: E402
    aalen_johansen_cif,
    fit_sequence,
)
from analysis_refinement.scenario_runs import STRUCTURAL_DISPO  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs" / "final"
DUR, EVT = "duration_minutes", "reassessment_event"


def main() -> None:
    df = pd.read_csv(OUT / "primary_cohort.csv", low_memory=False)
    cols = cols_from_formula(formula_m4(df), df)
    cc = df.dropna(subset=cols).reset_index(drop=True)
    print(f"cohort {len(df):,} -> complete-case {len(cc):,}")
    cc.to_csv(OUT / "primary_cohort_cc.csv", index=False)

    d = {"n": len(cc)}
    evt = cc[EVT] == 1
    d["events"] = int(evt.sum())
    d["event_pct"] = round(evt.mean() * 100, 1)
    dur_evt = cc.loc[evt, DUR]
    d["median_iqr"] = [round(dur_evt.median()), round(dur_evt.quantile(.25)),
                       round(dur_evt.quantile(.75))]
    for w in (60, 120):
        k = int((evt & (cc[DUR] <= w)).sum())
        d[f"by{w}"] = [k, round(k / len(cc) * 100, 1)]
    cens = cc[~evt]
    d["censored"] = len(cens)
    struct = cens["disposition_fine"].astype(str).str.upper().isin(STRUCTURAL_DISPO)
    d["censored_structural"] = [int(struct.sum()),
                                round(struct.mean() * 100, 1),
                                round(struct.sum() / len(cc) * 100, 1)]

    # single-NUMERIC-score stays by fine disposition
    single = cc["numeric_reassessment_time"].isna()
    for dispo, key in [("HOME", "home"), ("LEFT WITHOUT BEING SEEN", "lwbs"),
                       ("ELOPED", "eloped")]:
        m = cc["disposition_fine"].astype(str).str.upper() == dispo
        d[f"single_{key}"] = round((single & m).sum() / max(m.sum(), 1) * 100, 1)

    # Table-1-adjacent text numbers
    d["trauma"] = int((cc["diagnosis_type"] == "trauma").sum())
    d["ap"] = int((cc["diagnosis_type"] == "acute_pancreatitis").sum())
    for g in ("fall", "fracture_dislocation", "other_trauma"):
        k = int((cc["injury_group"] == g).sum())
        d[f"inj_{g}"] = [k, round(k / len(cc) * 100, 1)]
    d["age_mean_sd"] = [round(cc["age"].mean(), 1), round(cc["age"].std(), 1)]
    d["female_pct"] = round((cc["sex"] == "F").mean() * 100, 1)
    for r in ("White", "Black", "Hispanic", "Asian", "Unknown", "Other"):
        k = int((cc["race_ethnicity"] == r).sum())
        d[f"race_{r}"] = [k, round(k / len(cc) * 100, 1)]
    for i in ("undocumented", "Medicare", "private", "Medicaid"):
        k = int((cc["insurance_group"] == i).sum())
        d[f"ins_{i}"] = [k, round(k / len(cc) * 100, 1)]
    d["pain_mean_sd"] = [round(cc["initial_pain_score"].mean(), 1),
                         round(cc["initial_pain_score"].std(), 1)]
    k = int((cc["initial_pain_score"] == 0).sum())
    d["pain0"] = [k, round(k / len(cc) * 100, 1)]

    # absolute-scale AJ CIF on the cc cohort
    shutil.copy(OUT / "cif_absolute.csv", OUT / "cif_absolute_v42405.csv")
    cif = aalen_johansen_cif(cc)
    cif.to_csv(OUT / "cif_absolute.csv", index=False)
    ins = cif[cif["group_var"] == "insurance_group"]
    d["cif"] = {f"{r.level}_{r.t_min}": round(r.cif_reassessed * 100, 1)
                for r in ins.itertuples()}

    # refit M1-M4 on the cc cohort so every model shares the same rows
    shutil.copy(OUT / "primary_m1_m4_terms.csv", OUT / "primary_m1_m4_terms_v42405.csv")
    terms = fit_sequence(cc)
    terms.to_csv(OUT / "primary_m1_m4_terms.csv", index=False)

    (OUT / "cc_descriptives.json").write_text(json.dumps(d, indent=2))
    print(json.dumps(d, indent=2))


if __name__ == "__main__":
    main()
