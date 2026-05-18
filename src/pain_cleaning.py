from __future__ import annotations

import pandas as pd


def clean_pain_scores(pain_series: pd.Series, *, log_invalid: bool = True) -> pd.Series:
    def clean_value(value):
        if pd.isna(value):
            return None

        value = str(value).lower().strip()

        if "/" in value:
            value = value.split("/")[0].strip()
        elif "-" in value:
            parts = value.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                value = str((int(parts[0]) + int(parts[1])) / 2)
            else:
                value = parts[0].strip()

        value = "".join(char for char in value if char.isdigit() or char == ".")

        try:
            numeric_value = float(value)
            if numeric_value > 10 or (0 < numeric_value < 1):
                return None
            return numeric_value
        except ValueError:
            return None

    cleaned_series = pain_series.apply(clean_value)

    if log_invalid:
        invalid_rows = pain_series[cleaned_series.isna()]
        if not invalid_rows.empty:
            print("Dropped invalid pain scores:", invalid_rows.tolist())

    return cleaned_series
