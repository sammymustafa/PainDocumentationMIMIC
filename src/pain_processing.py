from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.pain_cleaning import clean_pain_scores

DEFAULT_EXCLUDED_RACES = [
    "American Indian or Alaska Native",
    "Two or More Races",
    "Native Hawaiian or Other Pacific Islander",
    "Unknown",
    "Asian",
]


def process_pain_dataframe(
    df: pd.DataFrame,
    *,
    pain_score_col: str = "pain_score",
    pain_numeric_col: str = "pain_numeric",
    charttime_col: str = "pain_charttime",
    intime_col: str = "intime",
    outtime_col: str = "outtime",
    subject_col: str = "subject_id",
    stay_col: str = "stay_id",
    age_col: str = "age",
    clean_pain_fn: Callable[[pd.Series], pd.Series] = clean_pain_scores,
    language_threshold: int = 100,
    insurance_threshold: int = 150,
    exclude_races: bool = True,
    excluded_races: list[str] | None = None,
) -> pd.DataFrame:
    if excluded_races is None:
        excluded_races = DEFAULT_EXCLUDED_RACES

    df = df.copy()

    language_counts = df["language"].value_counts()
    rare_languages = language_counts[language_counts < language_threshold].index
    df["language"] = df["language"].where(
        ~df["language"].isin(rare_languages),
        other="Other",
    )
    df = df[~df["language"].isin(["Other", "Kabuverdianu"])]

    df = df[df["insurance"].notna()]
    df["insurance"] = df["insurance"].replace({"No charge": "Uninsured"})

    insurance_counts = df["insurance"].value_counts()
    rare_insurance = insurance_counts[insurance_counts < insurance_threshold].index
    df["insurance"] = df["insurance"].where(
        ~df["insurance"].isin(rare_insurance),
        other="Other",
    )
    df = df[~df["insurance"].isin(["Other"])]

    if exclude_races:
        df = df[~df["race"].isin(excluded_races)]

    bins = [0, 17, 39, 64, 120]
    labels = ["<18", "18–39", "40–64", "65+"]
    df["age_group"] = pd.cut(
        df[age_col],
        bins=bins,
        labels=labels,
        right=True,
        include_lowest=True,
    )

    df["visit_num"] = (
        df.groupby(subject_col)[intime_col]
        .rank(method="dense", ascending=True)
        .astype(int)
    )

    df[pain_numeric_col] = clean_pain_fn(df[pain_score_col])
    df = df.dropna(subset=[pain_numeric_col])

    df = df[
        (df[charttime_col] >= df[intime_col]) & (df[charttime_col] <= df[outtime_col])
    ]

    df = df.drop_duplicates(
        subset=[subject_col, stay_col, pain_numeric_col, charttime_col]
    )

    df["is_last_score"] = (
        df.groupby([subject_col, stay_col])[charttime_col].transform("max")
        == df[charttime_col]
    )
    df = df[(df[pain_numeric_col] != 0) | (df["is_last_score"])].drop(
        columns=["is_last_score"]
    )

    df = df.sort_values(by=[subject_col, stay_col, charttime_col])

    df["pain_num_instance"] = (
        df.groupby([subject_col, stay_col]).cumcount().add(1)
    )

    only_zero = (
        df.groupby([subject_col, stay_col])[pain_numeric_col]
        .apply(lambda x: (x == 0).all())
        .reset_index(name="only_zero")
    )
    df = (
        df.merge(only_zero, on=[subject_col, stay_col], how="left")
        .query("only_zero == False")
        .drop(columns=["only_zero"])
    )

    df["prev_pain"] = df.groupby([subject_col, stay_col])[pain_numeric_col].shift(1)
    df["delta_pain"] = df.groupby([subject_col, stay_col])[pain_numeric_col].diff()
    df["prop_delta_pain"] = (df[pain_numeric_col] - df["prev_pain"]) / df["prev_pain"]
    df.loc[df["prev_pain"] == 0, "prop_delta_pain"] = pd.NA

    df["is_reassessment"] = df.groupby([subject_col, stay_col]).cumcount() > 0

    df["minutes_since_intime"] = (
        (df[charttime_col] - df[intime_col]).dt.total_seconds() / 60
    )
    df["pain_within_1hr"] = df["minutes_since_intime"] <= 60
    df["pain_within_3hr"] = df["minutes_since_intime"] <= 180

    df = df.sort_values([subject_col, stay_col, charttime_col])

    df["minutes_since_prev_pain"] = (
        df.groupby([subject_col, stay_col])[charttime_col]
        .diff()
        .dt.total_seconds()
        / 60
    )
    df["minutes_since_reference"] = df["minutes_since_prev_pain"]

    mask_first = df["pain_num_instance"] == 1
    df.loc[mask_first, "minutes_since_reference"] = (
        (df.loc[mask_first, charttime_col] - df.loc[mask_first, intime_col])
        .dt.total_seconds()
        / 60
    )

    df["time_bin_30min"] = (df["minutes_since_reference"] // 30).astype("Int64")

    language_counts = df["language"].value_counts()
    top_langs = language_counts.nlargest(5).index.tolist()
    df["language_top5"] = df["language"].where(
        df["language"].isin(top_langs), other="Other"
    )

    admission_counts = df["admission_type"].value_counts()
    top_admissions = admission_counts.nlargest(5).index.tolist()
    df["admission_type_top5"] = df["admission_type"].where(
        df["admission_type"].isin(top_admissions), other="Other"
    )

    return df
