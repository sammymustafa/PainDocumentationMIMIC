#!/usr/bin/env python3
"""Read-only exclusion audit for the pain-reassessment cohort.

Reproduces the EXACT current selection cascade (no edits to existing code) and,
at each step, reports how many stays are dropped AND the composition of the
dropped group. Directly answers the PI's request: "document what fraction was
excluded and who they are."

Run:  ./.venv/bin/python analysis_refinement/exclusion_audit.py
Outputs land in analysis_refinement/outputs/.

Mirrors the logic in:
  - src/cohort_filters.filter_stay_cohort         (diagnosis + small-race drops)
  - analysis/prep_survival.build_survival_cohort   (positive-pain, RACES, duration)
  - analysis/prep_cohort.prep_analytic_cohort      (ESI, insurance)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

STAY_CSV = ROOT / "data/raw/stay_covariates.csv"
PAIN_CSV = ROOT / "data/raw/pain_events.csv"

# --- constants copied verbatim from the source (documented, not imported, so
#     this script stays a transparent record of the criteria) ---
EXCLUDED_RACES = {  # src/cohort_filters.py:5
    "American Indian or Alaska Native",
    "Native Hawaiian or Other Pacific Islander",
    "Two or More Races",
}
VALID_DIAGNOSIS_TYPES = {"acute_pancreatitis", "trauma"}  # src/cohort_filters.py:11
RACES = ["White", "Black", "Asian", "Hispanic"]  # prep_survival.py:17
VALID_INSURANCE = {"private", "Medicaid", "Medicare"}  # prep_cohort.py:18

steps: list[dict] = []


def profile(df: pd.DataFrame) -> dict:
    """Composition summary of a set of stays."""
    def vc(col):
        return df[col].value_counts(dropna=False).to_dict() if col in df.columns else {}
    return {
        "n": int(len(df)),
        "by_diagnosis": vc("diagnosis_type"),
        "by_race": vc("race_ethnicity"),
        "by_insurance": vc("insurance_group"),
    }


def record(name: str, kept: pd.DataFrame, dropped: pd.DataFrame, note: str = ""):
    steps.append(
        {
            "step": name,
            "note": note,
            "n_in": int(len(kept) + len(dropped)),
            "n_dropped": int(len(dropped)),
            "n_remaining": int(len(kept)),
            "dropped_profile": profile(dropped),
        }
    )
    print(f"{name:<48} in={len(kept)+len(dropped):>7,}  drop={len(dropped):>7,}  remain={len(kept):>7,}")
    if note:
        print(f"    {note}")


def main() -> None:
    stays = pd.read_csv(STAY_CSV, low_memory=False)
    pain = pd.read_csv(PAIN_CSV, parse_dates=["pain_charttime"])
    stays["intime"] = pd.to_datetime(stays["intime"])
    stays["outtime"] = pd.to_datetime(stays["outtime"])

    print(f"\nRAW stay_covariates rows: {len(stays):,}\n" + "-" * 90)

    # Step 1 — diagnosis: keep AP or trauma only (drops 'both_ap_and_trauma')
    keep = stays[stays["diagnosis_type"].isin(VALID_DIAGNOSIS_TYPES)]
    drop = stays[~stays["diagnosis_type"].isin(VALID_DIAGNOSIS_TYPES)]
    record("1. diagnosis in {AP, trauma}", keep, drop,
           "src/cohort_filters.py:53-54 — drops mixed 'both_ap_and_trauma'")
    stays = keep

    # Step 2 — small race groups
    keep = stays[~stays["race_ethnicity"].isin(EXCLUDED_RACES)]
    drop = stays[stays["race_ethnicity"].isin(EXCLUDED_RACES)]
    record("2. drop small race groups", keep, drop,
           "src/cohort_filters.py:52 — AI/AN, NH/PI, Two-or-More")
    stays = keep

    # Step 3 — race restricted to the 4 analytic groups (drops 'Unknown', 'Other')
    keep = stays[stays["race_ethnicity"].isin(RACES)]
    drop = stays[~stays["race_ethnicity"].isin(RACES)]
    record("3. race in {White,Black,Asian,Hispanic}", keep, drop,
           "prep_survival.py:98 — drops Unknown / Other race")
    stays = keep

    # Step 4 — at least one POSITIVE pain score documented in the stay
    pos = pain[pain["pain_numeric"] > 0]
    stays_with_pos = set(pos["stay_id"].unique())
    keep = stays[stays["stay_id"].isin(stays_with_pos)]
    drop = stays[~stays["stay_id"].isin(stays_with_pos)]
    record("4. >=1 documented pain score > 0", keep, drop,
           "prep_survival.py:61,97 — pain_numeric>0; note: pain=0 rows are dropped, "
           "so patients with only 0 scores are excluded here")
    stays = keep

    # Step 5 — valid survival time (initial pain within stay, duration > 0)
    first = (pos.sort_values(["stay_id", "pain_charttime"])
                .groupby("stay_id", as_index=False).first()
                .rename(columns={"pain_charttime": "initial_pain_time"}))
    stays = stays.merge(first[["stay_id", "initial_pain_time"]], on="stay_id", how="left")
    stays["duration_to_outtime"] = (stays["outtime"] - stays["initial_pain_time"]).dt.total_seconds() / 60
    keep = stays[stays["duration_to_outtime"] > 0]
    drop = stays[~(stays["duration_to_outtime"] > 0)]
    record("5. valid survival time (duration > 0)", keep, drop,
           "prep_survival.py:107 — initial pain must precede outtime")
    stays = keep

    # Step 6 — non-missing ESI / triage acuity
    stays["triage_acuity_num"] = pd.to_numeric(stays["triage_acuity"], errors="coerce")
    keep = stays[stays["triage_acuity_num"].notna()]
    drop = stays[stays["triage_acuity_num"].isna()]
    record("6. non-missing ESI (triage acuity)", keep, drop,
           "prep_cohort.py:41-47")
    stays = keep

    # Step 7 — insurance in {private, Medicaid, Medicare}
    keep = stays[stays["insurance_group"].isin(VALID_INSURANCE)]
    drop = stays[~stays["insurance_group"].isin(VALID_INSURANCE)]
    record("7. insurance in {private,Medicaid,Medicare}", keep, drop,
           "prep_cohort.py:52-53 — drops 'undocumented' insurance")
    stays = keep

    print("-" * 90)
    print(f"FINAL analytic cohort: {len(stays):,}\n")

    # --- Single-pain-score characterization (PI's specific question) ---
    counts = pos.groupby("stay_id").size()
    final_ids = set(stays["stay_id"])
    final_counts = counts[counts.index.isin(final_ids)]
    single = int((final_counts == 1).sum())
    multi = int((final_counts >= 2).sum())
    print("Single-pain-score handling in the FINAL cohort:")
    print(f"  stays with exactly ONE positive pain score : {single:,}  "
          f"({single/len(stays)*100:.1f}%)  -> currently KEPT and censored (event=0)")
    print(f"  stays with >=2 positive pain scores         : {multi:,}  "
          f"({multi/len(stays)*100:.1f}%)")
    print("  NOTE: current code does NOT exclude single-score stays; it treats")
    print("        them as censored. The PI note assumes they were excluded.\n")

    summary = {
        "final_analytic_n": int(len(stays)),
        "single_positive_score_stays": single,
        "multi_positive_score_stays": multi,
        "single_score_pct": round(single / len(stays) * 100, 1),
        "cascade": steps,
    }
    (OUT / "exclusion_cascade.json").write_text(json.dumps(summary, indent=2, default=str))

    tbl = pd.DataFrame(
        [{"step": s["step"], "n_in": s["n_in"], "n_dropped": s["n_dropped"],
          "n_remaining": s["n_remaining"],
          "pct_of_raw_dropped": round(s["n_dropped"] / steps[0]["n_in"] * 100, 1)}
         for s in steps]
    )
    tbl.to_csv(OUT / "exclusion_cascade.csv", index=False)
    print(f"Wrote {OUT/'exclusion_cascade.csv'}")
    print(f"Wrote {OUT/'exclusion_cascade.json'}")


if __name__ == "__main__":
    main()
