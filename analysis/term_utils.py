"""Helpers to select Cox terms from result tables."""

from __future__ import annotations

import pandas as pd


def pick_term_row(
    df: pd.DataFrame,
    model: str,
    *,
    term_contains: str | None = None,
    level: str | None = None,
    exact_term: str | None = None,
) -> pd.Series | None:
    sub = df[df["model"] == model].copy()
    if exact_term is not None:
        hit = sub[sub["term"] == exact_term]
        return hit.iloc[0] if len(hit) else None
    if term_contains:
        sub = sub[sub["term"].astype(str).str.contains(term_contains, case=False, na=False)]
    if level:
        sub = sub[
            sub["term"].astype(str).str.contains(level, case=False, na=False)
            | sub["comparison"].astype(str).str.contains(level, case=False, na=False)
        ]
    if sub.empty:
        return None
    return sub.iloc[0]


def classify_association(
    hr: float | None,
    p: float | None,
    ci_low: float | None = None,
    ci_high: float | None = None,
) -> str:
    if hr is None or p is None or pd.isna(hr) or pd.isna(p):
        return "insufficient_data"
    if ci_low is not None and ci_high is not None and pd.notna(ci_low) and pd.notna(ci_high):
        if ci_low <= 0 or ci_high > 50 or (ci_high / max(ci_low, 1e-6) > 80):
            return "unstable"
    if p >= 0.05:
        return "null"
    return "faster" if hr > 1 else "slower"
