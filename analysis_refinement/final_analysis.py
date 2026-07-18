#!/usr/bin/env python3
"""Final refined analysis: S6 all-inclusive cohort as PRIMARY.

Adopts the five recommendations agreed with the PI:
  1. S6-style inclusion is the primary cohort (S0 legacy spec + S1-S5 become
     sensitivity analyses; their fits already live in outputs/scenario_m4_terms.csv).
  2. Fine-Gray competing-risk check (input exported here; model fit in
     finegray_final.R with structural departures as the competing event).
  3. E-values for the key adjusted HRs.
  4. Absolute-scale estimates: Aalen-Johansen cumulative incidence of
     reassessment by 60/120 min by insurance (real-world scale, departures as
     competing events) plus Cox G-computation standardized probabilities
     (adjusted, conditional on remaining in the ED).
  5. Text-pain taxonomy descriptive table + missingness patterns by
     race/insurance (complete-case transparency).

Outputs -> analysis_refinement/outputs/final/
Run:      ./.venv/bin/python analysis_refinement/final_analysis.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.cox_fit import cols_from_formula, extract_terms, fit_cox  # noqa: E402
from analysis.cox_models import (  # noqa: E402
    M1_CLINICAL,
    M4_WORKFLOW,
    formula_m4,
    m2_parts,
    m3_parts,
)
from analysis_refinement.scenario_runs import (  # noqa: E402
    SCENARIOS,
    STRUCTURAL_DISPO,
    build_cohort,
    load_inputs,
)

OUT = Path(__file__).resolve().parent / "outputs" / "final"
OUT.mkdir(parents=True, exist_ok=True)

DUR, EVT = "duration_minutes", "reassessment_event"

KEY_TERMS = (
    "race_ethnicity",
    "insurance_group",
    "language_group",
)


def fit_sequence(df: pd.DataFrame) -> pd.DataFrame:
    """M1 -> M4 on the primary cohort, mirroring the committed ladder."""
    seq = {
        "M1": " + ".join(M1_CLINICAL),
        "M2": " + ".join(M1_CLINICAL + m2_parts(df)),
        "M3": " + ".join(M1_CLINICAL + m2_parts(df) + m3_parts(df)),
        "M4": formula_m4(df),
    }
    rows = []
    for label, formula in seq.items():
        cph = fit_cox(df, formula)
        if cph is None:
            print(f"  !! {label} failed")
            continue
        terms = pd.DataFrame(extract_terms(cph, model=label, model_label=label, formula=formula))
        rows.append(terms)
        print(f"  {label}: n={len(cph.durations):,} events={int(cph.event_observed.sum()):,} "
              f"c={cph.concordance_index_:.3f}")
    return pd.concat(rows, ignore_index=True)


def evalue(hr: float, lo: float, hi: float) -> tuple[float, float]:
    """VanderWeele & Ding (2017). Returns (E_point, E_ci_bound_nearest_null)."""
    def _e(r: float) -> float:
        r = max(r, 1.0 / r)
        return r + np.sqrt(r * (r - 1.0))

    e_pt = _e(hr)
    if lo <= 1.0 <= hi:
        e_ci = 1.0
    else:
        bound = hi if hr < 1 else lo
        e_ci = _e(bound)
    return round(e_pt, 2), round(e_ci, 2)


def add_evalues(terms: pd.DataFrame) -> pd.DataFrame:
    m4 = terms[terms["model"] == "M4"].copy()
    keep = m4[m4["term"].str.contains("|".join(KEY_TERMS))]
    out = []
    for _, r in keep.iterrows():
        e_pt, e_ci = evalue(r["hazard_ratio"], r["ci_low"], r["ci_high"])
        out.append({
            "comparison": r["comparison"],
            "hazard_ratio": round(r["hazard_ratio"], 2),
            "ci_low": round(r["ci_low"], 2),
            "ci_high": round(r["ci_high"], 2),
            "evalue_point": e_pt,
            "evalue_ci": e_ci,
        })
    return pd.DataFrame(out)


def aalen_johansen_cif(df: pd.DataFrame) -> pd.DataFrame:
    """Real-world P(reassessed by t): departures without reassessment are the
    competing event, so 'censoring' only happens administratively (never here)."""
    from lifelines import AalenJohansenFitter

    rows = []
    for group_col in ("insurance_group", "race_ethnicity"):
        for level, sub in df.groupby(group_col):
            if len(sub) < 200:
                continue
            events = np.where(sub[EVT] == 1, 1, 2)  # 2 = departed w/o reassessment
            aj = AalenJohansenFitter(calculate_variance=False)
            aj.fit(sub[DUR].to_numpy(), events, event_of_interest=1)
            cif = aj.cumulative_density_
            for t in (60, 120, 180):
                idx = cif.index[cif.index <= t]
                val = float(cif.loc[idx[-1]].iloc[0]) if len(idx) else 0.0
                rows.append({"group_var": group_col, "level": level, "n": len(sub),
                             "t_min": t, "cif_reassessed": round(val, 4)})
    return pd.DataFrame(rows)


def standardized_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    """Cox G-computation: cohort-standardized P(reassessment by 60/120 min)
    under each insurance assignment (conditional on remaining in the ED)."""
    from lifelines import CoxPHFitter

    formula = formula_m4(df)
    cols = cols_from_formula(formula, df)
    use = df[[DUR, EVT, *cols]].dropna().reset_index(drop=True)
    cph = CoxPHFitter()
    cph.fit(use, duration_col=DUR, event_col=EVT, formula=formula)

    rows = []
    for level in ("private", "Medicaid", "Medicare", "undocumented"):
        cf = use.copy()
        cf["insurance_group"] = level
        surv = cph.predict_survival_function(cf, times=[60.0, 120.0])
        for t in (60.0, 120.0):
            rows.append({
                "insurance_set_to": level,
                "t_min": int(t),
                "std_prob_reassessed": round(float(1 - surv.loc[t].mean()), 4),
            })
    wide = pd.DataFrame(rows)
    # risk differences vs private
    piv = wide.pivot(index="insurance_set_to", columns="t_min", values="std_prob_reassessed")
    for t in (60, 120):
        wide.loc[wide["t_min"] == t, "risk_diff_vs_private"] = (
            wide.loc[wide["t_min"] == t, "std_prob_reassessed"].values - piv.loc["private", t]
        ).round(4)
    return wide


def missingness_table(stays: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """Missingness of analytic requirements by race/insurance, on the widest
    eligible base (AP/trauma stays with >=1 numeric pain score, zeros valid)."""
    s = stays[stays["diagnosis_type"].isin(["acute_pancreatitis", "trauma"])].copy()
    num = ev[ev["pain_numeric"].notna()]
    first = num.sort_values(["stay_id", "pain_charttime"]).groupby("stay_id", as_index=False).first()
    s = s.merge(first[["stay_id", "pain_numeric", "heartrate", "resprate", "sbp"]],
                on="stay_id", how="inner")
    s["triage_acuity"] = pd.to_numeric(s["triage_acuity"], errors="coerce")

    def block(col: str) -> pd.DataFrame:
        g = s.groupby(col, dropna=False).agg(
            n=("stay_id", "size"),
            pct_missing_esi=("triage_acuity", lambda x: 100 * x.isna().mean()),
            pct_missing_vitals=("heartrate", lambda x: 100 * x.isna().mean()),
        ).reset_index().rename(columns={col: "level"})
        g["pct_undoc_language"] = (
            s.assign(u=s["language_group"].eq("undocumented"))
            .groupby(col, dropna=False)["u"].mean().values * 100
        )
        g["pct_undoc_insurance"] = (
            s.assign(u=s["insurance_group"].eq("undocumented"))
            .groupby(col, dropna=False)["u"].mean().values * 100
        )
        g.insert(0, "group_var", col)
        return g

    out = pd.concat([block("race_ethnicity"), block("insurance_group")], ignore_index=True)
    num_cols = [c for c in out.columns if c.startswith("pct_")]
    out[num_cols] = out[num_cols].round(1)
    return out


def text_pain_table(ev: pd.DataFrame) -> pd.DataFrame:
    txt = ev[ev["text_group"].notna()].copy()
    txt["value"] = txt["pain_raw"].astype(str).str.strip().str.lower()
    rows = []
    for grp, sub in txt.groupby("text_group"):
        top = sub["value"].value_counts().head(12)
        rows.append({
            "text_group": grp,
            "n_entries": len(sub),
            "n_stays": sub["stay_id"].nunique(),
            "top_values": "; ".join(f"{v} ({c})" for v, c in top.items()),
        })
    return pd.DataFrame(rows).sort_values("n_entries", ascending=False)


def export_finegray_input(df: pd.DataFrame) -> None:
    d = df.copy()
    struct = d["disposition_fine"].astype(str).str.upper().isin(STRUCTURAL_DISPO)
    d["fg_status"] = np.select(
        [d[EVT] == 1, (d[EVT] == 0) & struct], [1, 2], default=0
    )
    cols = [DUR, "fg_status", "initial_pain_score", "injury_group", "race_ethnicity",
            "age_group", "sex", "insurance_group", "language_group", "triage_acuity",
            "heartrate_0_z", "resprate_0_z", "sbp_0_z", "arrival_mode", "arrival_shift",
            "arrival_weekend", "ed_arrivals_past_1hr", "ed_census_at_initial_pain_hour",
            "year_era"]
    d = d[cols].dropna()
    d.to_csv(OUT / "finegray_input.csv", index=False)
    print(f"  finegray_input: n={len(d):,} "
          f"(reassessed {int((d.fg_status==1).sum()):,}, "
          f"structural departure {int((d.fg_status==2).sum()):,}, "
          f"censored {int((d.fg_status==0).sum()):,})")


def main() -> None:
    stays, ev, dispo = load_inputs()

    print("=== PRIMARY: S6 all-inclusive cohort")
    df = build_cohort(stays, ev, dispo, **SCENARIOS["S6_all_inclusive"])
    df.to_csv(OUT / "primary_cohort.csv", index=False)
    print(f"  n={len(df):,} events={int(df[EVT].sum()):,} ({df[EVT].mean()*100:.1f}%)")

    print("=== M1-M4 sequence")
    terms = fit_sequence(df)
    terms.to_csv(OUT / "primary_m1_m4_terms.csv", index=False)

    print("=== E-values")
    ev_tab = add_evalues(terms)
    ev_tab.to_csv(OUT / "evalues.csv", index=False)
    print(ev_tab.to_string(index=False))

    print("=== Aalen-Johansen CIF (absolute scale)")
    cif = aalen_johansen_cif(df)
    cif.to_csv(OUT / "cif_absolute.csv", index=False)

    print("=== Cox-standardized probabilities (insurance)")
    std = standardized_probabilities(df)
    std.to_csv(OUT / "standardized_probs.csv", index=False)
    print(std.to_string(index=False))

    print("=== Missingness patterns")
    miss = missingness_table(stays, ev)
    miss.to_csv(OUT / "missingness_by_group.csv", index=False)

    print("=== Text-pain taxonomy")
    tt = text_pain_table(ev)
    tt.to_csv(OUT / "text_pain_taxonomy.csv", index=False)

    print("=== Fine-Gray export")
    export_finegray_input(df)

    meta = {
        "primary": "S6_all_inclusive",
        "n": int(len(df)),
        "events": int(df[EVT].sum()),
        "sensitivity_source": "outputs/scenario_m4_terms.csv (S0-S5)",
    }
    (OUT / "run_meta.json").write_text(json.dumps(meta, indent=2))
    print("\nAll outputs in", OUT)


if __name__ == "__main__":
    main()
