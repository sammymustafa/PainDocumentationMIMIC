#!/usr/bin/env python3
"""Sensitivity scenarios for cohort-selection refinements (read-only vs committed pipeline).

One scenario per contemplated change (PI directive: remove nothing yet — run each
candidate change separately and compare):

  S0_baseline           current spec (4 races, 3 insurance groups, pain>0 only,
                        text entries ignored, AP+trauma, single-score censored)
  S1_race_inclusive     keep ALL races: small groups pooled into 'Other',
                        'Unknown' kept as its own level (nobody dropped for race)
  S2_insurance_inclusive keep 'undocumented' insurance as its own level
  S3_zero_valid         pain=0 counts as valid documentation (initial and
                        reassessment events can be 0)
  S4_text_reassessment  a TEXT pain entry after the initial score counts as a
                        reassessment event (documentation attempt occurred)
  S5_trauma_only        drop acute pancreatitis (PI's 'simpler framing' probe;
                        AP kept as ONE group everywhere else — no subtypes)
  S6_all_inclusive      S1+S2+S3+S4 combined (maximal inclusion)

Single-pain-score stays are KEPT (censored) in every scenario per PI. Each
scenario reports how many censored stays have a structural disposition reason
(ELOPED / LWBS / AMA / EXPIRED / TRANSFER) vs not.

Outputs -> analysis_refinement/outputs/ and analysis_refinement/figures/.
Model: the existing M4 spec, reused verbatim from analysis/cox_models.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.cox_fit import extract_terms, fit_cox  # noqa: E402
from analysis.cox_models import formula_m4  # noqa: E402
from analysis.prep_data import assign_year_era, collapse_sparse_year_eras  # noqa: E402
from analysis.prep_survival import _arrival_mode, _injury_group, _pain_severity  # noqa: E402
from src.cohort_filters import normalize_disposition, normalize_trauma_subtype  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs"
FIGS = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
FIGS.mkdir(exist_ok=True)

STAY_CSV = ROOT / "data/raw/stay_covariates.csv"
PAIN_RAW = ROOT / "data/raw/pain_raw.parquet"

RACES4 = ["White", "Black", "Asian", "Hispanic"]
SMALL_RACES = {
    "American Indian or Alaska Native",
    "Native Hawaiian or Other Pacific Islander",
    "Two or More Races",
    "Other",
}
VALID_INSURANCE = {"private", "Medicaid", "Medicare"}
STRUCTURAL_DISPO = {
    "ELOPED", "LEFT WITHOUT BEING SEEN", "LEFT AGAINST MEDICAL ADVICE",
    "EXPIRED", "TRANSFER",
}

# text taxonomy (same as explore_raw_pain.py)
import re  # noqa: E402

COMPLICATION_PAT = re.compile(
    r"sedat|intub|unrespons|critical|crit\b|letharg|obtund|nonverbal|non verbal|"
    r"unable|\buta\b|\buto\b|\bua\b|u/a|\butr\b|\bett\b|trach|vent|confus|dement|altered|\bams\b",
    re.I,
)
NOT_REASSESSED_PAT = re.compile(
    r"asleep|sleep|refus|declin|denies|deny|no answer|not assess|"
    r"off (unit|floor)|ct scan|xray|x-ray",
    re.I,
)

SCENARIOS: dict[str, dict] = {
    "S0_baseline": {},
    "S1_race_inclusive": {"race_policy": "inclusive"},
    "S2_insurance_inclusive": {"insurance_policy": "inclusive"},
    "S3_zero_valid": {"zero_policy": "zero_valid"},
    "S4_text_reassessment": {"text_policy": "text_event"},
    "S5_trauma_only": {"diagnosis": "trauma_only"},
    "S6_all_inclusive": {
        "race_policy": "inclusive",
        "insurance_policy": "inclusive",
        "zero_policy": "zero_valid",
        "text_policy": "text_event",
    },
}


def load_inputs():
    stays = pd.read_csv(STAY_CSV, low_memory=False)
    stays["intime"] = pd.to_datetime(stays["intime"])
    stays["outtime"] = pd.to_datetime(stays["outtime"])

    ev = pd.read_parquet(
        PAIN_RAW,
        columns=["stay_id", "pain_charttime", "pain_raw", "pain_numeric",
                 "heartrate", "resprate", "sbp", "disposition"],
    )
    ev["pain_charttime"] = pd.to_datetime(ev["pain_charttime"])
    for c in ["pain_numeric", "heartrate", "resprate", "sbp"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")  # BigQuery NUMERIC -> Decimal
    # exact-duplicate protection (audit found zero, but keep the guard)
    ev = ev.drop_duplicates(subset=["stay_id", "pain_charttime", "pain_numeric", "pain_raw"])

    is_text = ev["pain_numeric"].isna() & ev["pain_raw"].notna()
    ev["text_group"] = np.where(
        ~is_text, None,
        np.where(ev["pain_raw"].astype(str).str.contains(COMPLICATION_PAT), "complications",
        np.where(ev["pain_raw"].astype(str).str.contains(NOT_REASSESSED_PAT), "not_reassessed",
                 "unclassified")),
    )
    # fine-grained disposition per stay (stay_covariates only has grouped)
    dispo = ev.drop_duplicates("stay_id")[["stay_id", "disposition"]].rename(
        columns={"disposition": "disposition_fine"}
    )
    return stays, ev, dispo


def build_cohort(stays, ev, dispo, *, race_policy="four", insurance_policy="three",
                 zero_policy="positive_only", text_policy="ignore", diagnosis="both"):
    s = stays.copy()

    # --- diagnosis ---
    valid_dx = {"trauma"} if diagnosis == "trauma_only" else {"acute_pancreatitis", "trauma"}
    s = s[s["diagnosis_type"].isin(valid_dx)]
    s = normalize_trauma_subtype(normalize_disposition(s))

    # --- race ---
    if race_policy == "four":
        s = s[s["race_ethnicity"].isin(RACES4)]
    else:  # inclusive: pool small groups, keep Unknown
        s["race_ethnicity"] = s["race_ethnicity"].where(
            ~s["race_ethnicity"].isin(SMALL_RACES), "Other"
        )

    # --- numeric pain events ---
    num = ev[ev["pain_numeric"].notna()].copy()
    if zero_policy == "positive_only":
        num = num[num["pain_numeric"] > 0]
    num = num.sort_values(["stay_id", "pain_charttime"])

    first = num.groupby("stay_id", as_index=False).first().rename(columns={
        "pain_charttime": "initial_pain_time", "pain_numeric": "initial_pain_score",
        "heartrate": "heartrate_0", "resprate": "resprate_0", "sbp": "sbp_0",
    })[["stay_id", "initial_pain_time", "initial_pain_score",
        "heartrate_0", "resprate_0", "sbp_0"]]
    second = num.groupby("stay_id").nth(1).reset_index(drop=True)[
        ["stay_id", "pain_charttime", "pain_numeric"]
    ].rename(columns={"pain_charttime": "numeric_reassessment_time",
                      "pain_numeric": "first_reassessment_score"})

    df = s.merge(first, on="stay_id", how="inner").merge(second, on="stay_id", how="left")

    # --- text entries as reassessment events ---
    if text_policy == "text_event":
        txt = ev[ev["text_group"].notna()][["stay_id", "pain_charttime", "text_group"]]
        txt = txt.merge(first[["stay_id", "initial_pain_time"]], on="stay_id", how="inner")
        txt = txt[txt["pain_charttime"] > txt["initial_pain_time"]]
        first_txt = (txt.sort_values("pain_charttime")
                        .groupby("stay_id", as_index=False).first()
                        .rename(columns={"pain_charttime": "text_reassessment_time",
                                         "text_group": "text_reassessment_group"}))
        df = df.merge(first_txt[["stay_id", "text_reassessment_time",
                                 "text_reassessment_group"]], on="stay_id", how="left")
        df["first_reassessment_time"] = df[
            ["numeric_reassessment_time", "text_reassessment_time"]
        ].min(axis=1)
    else:
        df["first_reassessment_time"] = df["numeric_reassessment_time"]

    # --- survival construction (mirrors prep_survival) ---
    df["reassessment_event"] = df["first_reassessment_time"].notna().astype(int)
    df["time_end"] = df["first_reassessment_time"].where(
        df["reassessment_event"] == 1, df["outtime"]
    )
    df["duration_minutes"] = (df["time_end"] - df["initial_pain_time"]).dt.total_seconds() / 60
    df = df[df["duration_minutes"] > 0]

    # --- analytic filters (mirrors prep_cohort) ---
    df["triage_acuity"] = pd.to_numeric(df["triage_acuity"], errors="coerce")
    df = df[df["triage_acuity"].notna() & df["initial_pain_score"].notna()]

    if insurance_policy == "three":
        df = df[df["insurance_group"].isin(VALID_INSURANCE)]
        df.loc[df["language_group"] == "undocumented", "language_group"] = np.nan
    # inclusive: keep 'undocumented' as its own level for insurance AND language
    # (otherwise the model's complete-case drop on language would silently
    #  remove the very rows this scenario is designed to keep)

    # --- derived covariates ---
    for col in ["heartrate_0", "resprate_0", "sbp_0"]:
        df[f"{col}_z"] = (df[col] - df[col].mean()) / df[col].std(ddof=0)
    df["injury_group"] = df.apply(_injury_group, axis=1)
    df["initial_pain_severity"] = df["initial_pain_score"].map(_pain_severity)
    df["year_era"] = assign_year_era(df["year"], width=5)
    df["year_era"] = collapse_sparse_year_eras(df, min_n=200)
    df["arrival_mode"] = df["arrival_transport"].map(_arrival_mode)
    df.loc[df["arrival_mode"] == "unknown", "arrival_mode"] = np.nan
    df["comorbidity_count"] = np.nan  # flags absent from extract; matches pipeline

    df = df.merge(dispo, on="stay_id", how="left")
    return df.reset_index(drop=True)


def summarize(name, df, cph):
    censored = df[df["reassessment_event"] == 0]
    struct = censored["disposition_fine"].str.upper().isin(STRUCTURAL_DISPO)
    row = {
        "scenario": name,
        "n": len(df),
        "events": int(df["reassessment_event"].sum()),
        "event_rate_pct": round(df["reassessment_event"].mean() * 100, 1),
        "censored": len(censored),
        "censored_structural_dispo": int(struct.sum()),
        "censored_structural_pct": round(struct.mean() * 100, 1) if len(censored) else np.nan,
        "median_min_to_reassess_events": round(
            df.loc[df["reassessment_event"] == 1, "duration_minutes"].median(), 1),
        "model_n": int(len(cph.durations)) if cph is not None else np.nan,
        "model_events": int(cph.event_observed.sum()) if cph is not None else np.nan,
    }
    return row


def main() -> None:
    stays, ev, dispo = load_inputs()
    summaries, all_terms = [], []

    for name, policy in SCENARIOS.items():
        print(f"\n=== {name} {policy}")
        df = build_cohort(stays, ev, dispo, **policy)
        formula = formula_m4(df)
        if policy.get("diagnosis") == "trauma_only":
            # AP reference level doesn't exist in a trauma-only cohort
            formula = formula.replace(
                'reference="acute_pancreatitis"', 'reference="other_trauma"'
            )
        cph = fit_cox(df, formula)
        if cph is None:
            print("  !! model failed to fit")
        row = summarize(name, df, cph)
        summaries.append(row)
        print("  n={n:,} events={events:,} ({event_rate_pct}%) | "
              "censored w/ structural dispo: {censored_structural_dispo:,} "
              "({censored_structural_pct}%)".format(**row))

        if cph is not None:
            terms = pd.DataFrame(extract_terms(cph, model="M4", model_label=name, formula=formula))
            terms["scenario"] = name
            all_terms.append(terms)

        # composition snapshot
        comp = {
            "race": df["race_ethnicity"].value_counts().to_dict(),
            "insurance": df["insurance_group"].value_counts().to_dict(),
            "diagnosis": df["diagnosis_type"].value_counts().to_dict(),
        }
        (OUT / f"composition_{name}.json").write_text(json.dumps(comp, indent=2))

    pd.DataFrame(summaries).to_csv(OUT / "scenario_summary.csv", index=False)
    terms_df = pd.concat(all_terms, ignore_index=True)
    terms_df.to_csv(OUT / "scenario_m4_terms.csv", index=False)
    print(f"\nWrote {OUT/'scenario_summary.csv'}")
    print(f"Wrote {OUT/'scenario_m4_terms.csv'}")


if __name__ == "__main__":
    main()
