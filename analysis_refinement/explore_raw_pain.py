#!/usr/bin/env python3
"""Explore the RAW pain extract (before any filtering) to inform refinements.

1. Non-numeric / text pain values: what's actually there, with a proposed
   grouping into 'not_reassessed' (patient unavailable/declined) vs
   'complications' (clinically unable to report).
2. Same-timestamp duplicates: same stay+charttime with conflicting scores
   (e.g., one numeric>0 and one 0).
3. Single-pain-score stays: disposition breakdown (was there a structural
   reason no reassessment happened — ELOPED, LWBS, EXPIRED, TRANSFER...).

Read-only. Outputs → analysis_refinement/outputs/.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)

RAW = ROOT / "data/raw/pain_raw.parquet"

# Proposed taxonomy for text pain entries (editable — this is a draft mapping).
# 'complications'   = clinically unable to report (sedation, AMS, critical, intubated)
# 'not_reassessed'  = patient unavailable or declined (asleep, refused, out of dept)
COMPLICATION_PAT = re.compile(
    r"sedat|intub|unrespons|critical|letharg|obtund|nonverbal|non verbal|"
    r"unable|uta\b|uto\b|trach|vent|confus|dement|altered|ams\b|comfort",
    re.I,
)
NOT_REASSESSED_PAT = re.compile(
    r"asleep|sleep|refus|declin|denies|deny|no answer|not assess|n/?a\b|"
    r"off (unit|floor)|ct scan|xray|x-ray|left|gone",
    re.I,
)


def classify_text(v: str) -> str:
    s = str(v).strip().lower()
    if COMPLICATION_PAT.search(s):
        return "complications"
    if NOT_REASSESSED_PAT.search(s):
        return "not_reassessed"
    return "unclassified"


def main() -> None:
    df = pd.read_parquet(
        RAW,
        columns=[
            "subject_id", "stay_id", "pain_charttime", "pain_raw", "pain_numeric",
            "pain_non_numeric_reason", "disposition", "disposition_group",
        ],
    )
    df["pain_charttime"] = pd.to_datetime(df["pain_charttime"])
    print(f"raw pain rows: {len(df):,} | stays: {df['stay_id'].nunique():,}\n")

    # ---------- 1. text / non-numeric pain values ----------
    txt = df[df["pain_numeric"].isna() & df["pain_raw"].notna()].copy()
    print(f"non-numeric pain rows: {len(txt):,} "
          f"({len(txt)/len(df)*100:.1f}% of all pain rows) "
          f"across {txt['stay_id'].nunique():,} stays")
    print("\npain_non_numeric_reason (SQL's own bucket):")
    print(txt["pain_non_numeric_reason"].value_counts(dropna=False).to_string())

    txt["text_group"] = txt["pain_raw"].map(classify_text)
    print("\nproposed grouping:")
    print(txt["text_group"].value_counts().to_string())

    vc = (txt.groupby(["text_group", "pain_raw"]).size()
             .sort_values(ascending=False).reset_index(name="n"))
    vc.to_csv(OUT / "text_pain_values.csv", index=False)
    print(f"\ntop 40 raw text values:\n{vc.head(40).to_string(index=False)}")

    # ---------- 2. same-timestamp duplicates ----------
    num = df[df["pain_numeric"].notna()].copy()
    dup_grp = num.groupby(["stay_id", "pain_charttime"])["pain_numeric"].agg(["nunique", "count", "min", "max"])
    conflict = dup_grp[(dup_grp["count"] > 1) & (dup_grp["nunique"] > 1)]
    zero_vs_pos = conflict[(conflict["min"] == 0) & (conflict["max"] > 0)]
    print(f"\nsame stay+charttime rows with >1 numeric value: {len(conflict):,}")
    print(f"  of which 0 vs positive conflicts: {len(zero_vs_pos):,} "
          f"(stays affected: {zero_vs_pos.reset_index()['stay_id'].nunique():,})")
    zero_vs_pos.reset_index().to_csv(OUT / "same_time_zero_vs_positive.csv", index=False)

    exact_dupes = dup_grp[(dup_grp["count"] > 1) & (dup_grp["nunique"] == 1)]
    print(f"  exact duplicate rows (same time, same value): {len(exact_dupes):,}")

    # ---------- 3. single-score stays: disposition ----------
    pos = num[num["pain_numeric"] > 0]
    n_scores = pos.groupby("stay_id").size().rename("n_pos_scores")
    stay_disp = df.drop_duplicates("stay_id").set_index("stay_id")["disposition"]
    tab = pd.concat([n_scores, stay_disp], axis=1, join="inner")
    tab["single"] = tab["n_pos_scores"] == 1

    xt = pd.crosstab(tab["disposition"], tab["single"], margins=True)
    xt.columns = ["multi_score", "single_score", "total"]
    xt["pct_single"] = (xt["single_score"] / xt["total"] * 100).round(1)
    xt = xt.sort_values("total", ascending=False)
    print("\nsingle- vs multi-score stays by ED disposition:")
    print(xt.to_string())
    xt.to_csv(OUT / "single_score_by_disposition.csv")

    # Which single-score stays have a 'structural' censoring reason?
    STRUCTURAL = {"ELOPED", "LEFT WITHOUT BEING SEEN", "LEFT AGAINST MEDICAL ADVICE",
                  "EXPIRED", "TRANSFER"}
    singles = tab[tab["single"]]
    n_struct = singles["disposition"].str.upper().isin(STRUCTURAL).sum()
    print(f"\nsingle-score stays: {len(singles):,}")
    print(f"  with structural reason (eloped/LWBS/AMA/expired/transfer): {n_struct:,} "
          f"({n_struct/len(singles)*100:.1f}%)")
    print(f"  without (ADMITTED/HOME/OTHER — plausibly should have been reassessed): "
          f"{len(singles)-n_struct:,}")

    # Did single-score stays ALSO have text entries afterward? (i.e., a nurse
    # attempted reassessment but couldn't get a number)
    first_pos_time = pos.sort_values("pain_charttime").groupby("stay_id")["pain_charttime"].first()
    txt2 = txt.merge(first_pos_time.rename("first_pos_time"), on="stay_id", how="inner")
    txt_after = txt2[txt2["pain_charttime"] > txt2["first_pos_time"]]
    singles_with_text_after = set(txt_after["stay_id"]) & set(singles.index)
    print(f"  single-score stays with a TEXT pain entry AFTER the score "
          f"(attempted reassessment): {len(singles_with_text_after):,} "
          f"({len(singles_with_text_after)/len(singles)*100:.1f}%)")


if __name__ == "__main__":
    main()
