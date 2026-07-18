#!/usr/bin/env python3
"""Table 1 (cohort characteristics) and the sequential M1-M4 HR table for the
S6 primary cohort.

Outputs -> outputs/final/table1.csv / table1.md
        -> outputs/final/model_sequence_key_terms.csv / model_sequence_key_terms.md

Run: ./.venv/bin/python analysis_refinement/make_table1.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "final"


def _npct(mask: pd.Series, n: int) -> str:
    k = int(mask.sum())
    return f"{k:,} ({k / n * 100:.1f})"


def _meansd(s: pd.Series) -> str:
    return f"{s.mean():.1f} ({s.std():.1f})"


def build_table1() -> pd.DataFrame:
    df = pd.read_csv(OUT / "primary_cohort_cc.csv", low_memory=False)
    n = len(df)
    rows: list[tuple[str, str, str]] = []  # (section, characteristic, value)

    def add(section: str, label: str, value: str) -> None:
        rows.append((section, label, value))

    add("", f"N", f"{n:,}")

    # Demographics
    add("Demographics", "Age (years), mean (SD)", _meansd(df["age"]))
    add("Demographics", "Female sex, n (%)", _npct(df["sex"] == "F", n))
    for race in ["White", "Black", "Hispanic", "Asian", "Unknown", "Other"]:
        add("Demographics", f"{race} race/ethnicity, n (%)",
            _npct(df["race_ethnicity"] == race, n))

    # Insurance / language
    for ins in ["Medicare", "private", "Medicaid", "undocumented"]:
        label = ins.capitalize() if ins != "Medicare" else ins
        add("Insurance and language", f"{label} insurance, n (%)",
            _npct(df["insurance_group"] == ins, n))
    add("Insurance and language", "Non-English preferred language, n (%)",
        _npct(df["language_group"] == "non-English", n))
    add("Insurance and language", "Undocumented language, n (%)",
        _npct(df["language_group"] == "undocumented", n))

    # Clinical
    add("Clinical", "ESI triage level, mean (SD)", _meansd(df["triage_acuity"]))
    add("Clinical", "Initial pain score, mean (SD)", _meansd(df["initial_pain_score"]))
    add("Clinical", "Initial pain score = 0, n (%)", _npct(df["initial_pain_score"] == 0, n))
    add("Clinical", "Trauma diagnosis, n (%)", _npct(df["diagnosis_type"] == "trauma", n))
    for grp, label in [("fall", "Fall"), ("fracture_dislocation", "Fracture/dislocation"),
                       ("other_trauma", "Other trauma")]:
        add("Clinical", f"  {label}, n (%)", _npct(df["injury_group"] == grp, n))
    add("Clinical", "Acute pancreatitis, n (%)",
        _npct(df["diagnosis_type"] == "acute_pancreatitis", n))
    add("Clinical", "First heart rate, mean (SD)", _meansd(df["heartrate_0"].dropna()))
    add("Clinical", "First respiratory rate, mean (SD)", _meansd(df["resprate_0"].dropna()))
    add("Clinical", "First systolic BP, mean (SD)", _meansd(df["sbp_0"].dropna()))

    # ED workflow
    add("ED workflow", "Ambulance arrival, n (%)", _npct(df["arrival_mode"] == "ambulance", n))
    add("ED workflow", "Weekend arrival, n (%)", _npct(df["arrival_weekend"] == 1, n))
    add("ED workflow", "Night shift arrival, n (%)", _npct(df["arrival_shift"] == "night", n))
    add("ED workflow", "Evening shift arrival, n (%)", _npct(df["arrival_shift"] == "evening", n))
    add("ED workflow", "ED arrivals in prior hour, mean (SD)",
        _meansd(df["ed_arrivals_past_1hr"]))

    # Outcomes
    evt = df["reassessment_event"] == 1
    add("Outcomes", "Any reassessment before ED departure, n (%)", _npct(evt, n))
    add("Outcomes", "Reassessed within 60 min, n (%)",
        _npct(evt & (df["duration_minutes"] <= 60), n))
    add("Outcomes", "Reassessed within 120 min, n (%)",
        _npct(evt & (df["duration_minutes"] <= 120), n))
    d = df.loc[evt, "duration_minutes"]
    add("Outcomes", "Time to reassessment, median (IQR), min",
        f"{d.median():.0f} ({d.quantile(.25):.0f}–{d.quantile(.75):.0f})")

    return pd.DataFrame(rows, columns=["section", "characteristic", "value"])


KEY = [
    ("Initial pain score (per point)", "initial_pain_score"),
    ("Fall vs acute pancreatitis", "fall vs 'acute_pancreatitis'"),
    ("Fracture/dislocation vs AP", "fracture_dislocation vs 'acute_pancreatitis'"),
    ("Other trauma vs AP", "other_trauma vs 'acute_pancreatitis'"),
    ("Black vs White", "Black vs 'White'"),
    ("Hispanic vs White", "Hispanic vs 'White'"),
    ("Asian vs White", "Asian vs 'White'"),
    ("Medicaid vs private", "Medicaid vs 'private'"),
    ("Medicare vs private", "Medicare vs 'private'"),
    ("Undocumented vs private", "undocumented vs 'private'"),
    ("Non-English vs English", "non-English vs 'English'"),
    ("Triage acuity (per ESI level)", "triage_acuity"),
    ("Night vs day arrival", "night vs 'day'"),
]


def build_sequence_table() -> pd.DataFrame:
    t = pd.read_csv(OUT / "primary_m1_m4_terms.csv")
    t["key"] = t["comparison"].fillna(t["term"])
    rows = []
    for label, key in KEY:
        row: dict[str, str] = {"term": label}
        for m in ("M1", "M2", "M3", "M4"):
            hit = t[(t["model"] == m) & (t["key"] == key)]
            if len(hit) == 0:
                hit = t[(t["model"] == m) & (t["term"] == key)]
            row[m] = ("—" if len(hit) == 0 else
                      f"{hit.iloc[0]['hazard_ratio']:.2f} "
                      f"({hit.iloc[0]['ci_low']:.2f}–{hit.iloc[0]['ci_high']:.2f})")
        rows.append(row)
    return pd.DataFrame(rows)


def to_markdown_table1(t1: pd.DataFrame) -> str:
    lines = ["| Characteristic | Value |", "|---|---|"]
    last_section = None
    for _, r in t1.iterrows():
        if r["section"] and r["section"] != last_section:
            lines.append(f"| **{r['section']}** | |")
            last_section = r["section"]
        lines.append(f"| {r['characteristic']} | {r['value']} |")
    return "\n".join(lines)


def main() -> None:
    t1 = build_table1()
    t1.to_csv(OUT / "table1.csv", index=False)
    (OUT / "table1.md").write_text(to_markdown_table1(t1))
    print(to_markdown_table1(t1))

    seq = build_sequence_table()
    seq.to_csv(OUT / "model_sequence_key_terms.csv", index=False)
    lines = ["| Term | M1 | M2 | M3 | M4 (primary) |", "|---|---|---|---|---|"]
    for _, r in seq.iterrows():
        lines.append(f"| {r['term']} | {r['M1']} | {r['M2']} | {r['M3']} | {r['M4']} |")
    md = "\n".join(lines)
    (OUT / "model_sequence_key_terms.md").write_text(md)
    print("\n" + md)


if __name__ == "__main__":
    main()
