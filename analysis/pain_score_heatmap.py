from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from lifelines import CoxPHFitter

from analysis._paths import ANALYSIS_OUT, DURATION_COL, EVENT_COL, HEATMAP_DIR, SURVIVAL_CSV

MIN_N = 50
MIN_EVENTS = 10
P_CAP = 15.0
PAIN_LEVELS = list(range(1, 11))  # skip sparse pain 0


@dataclass(frozen=True)
class HeatmapRow:
    section: str
    label: str
    col: str
    apply: Callable[[pd.DataFrame], pd.Series] | None = None
    filter_fn: Callable[[pd.DataFrame], pd.DataFrame] | None = None


def _load_cohort(path: Path | None = None) -> pd.DataFrame:
    path = path or SURVIVAL_CSV
    df = pd.read_csv(path, low_memory=False)
    df["pain_int"] = df["initial_pain_score"].round().astype(int).clip(0, 10)
    for c in ("heartrate_0", "resprate_0", "sbp_0"):
        if c in df.columns:
            df[f"{c}_z"] = (df[c] - df[c].mean()) / df[c].std(ddof=0)
    return df


def _signed_log10_p(coef: float, p: float) -> float:
    if np.isnan(coef) or np.isnan(p):
        return np.nan
    mag = P_CAP if p <= 0 else min(-np.log10(p), P_CAP)
    return (1.0 if coef >= 0 else -1.0) * mag


def _fit_uni(sub: pd.DataFrame, col: str) -> float:
    use = sub[[DURATION_COL, EVENT_COL, col]].dropna()
    if len(use) < MIN_N or use[EVENT_COL].sum() < MIN_EVENTS:
        return np.nan
    if use[col].nunique() < 2:
        return np.nan
    try:
        cph = CoxPHFitter()
        cph.fit(use, duration_col=DURATION_COL, event_col=EVENT_COL, formula=col)
        return _signed_log10_p(float(cph.params_[col]), float(cph.summary.loc[col, "p"]))
    except Exception:
        return np.nan


def _indicator(df: pd.DataFrame, mask: pd.Series) -> pd.Series:
    return mask.astype(float)


def _build_rows() -> list[HeatmapRow]:
    """Rows derived from variables in survival_cohort — not an external template."""
    rows: list[HeatmapRow] = []

    # Demographics — age
    rows += [
        HeatmapRow("Demographics — age", "Age (years)", "age"),
        HeatmapRow(
            "Demographics — age",
            "Age 18–39 vs 40–64",
            "age_18_39",
            apply=lambda d: _indicator(d, d["age_group"] == "18-39"),
            filter_fn=lambda d: d[d["age_group"].isin(["18-39", "40-64"])],
        ),
        HeatmapRow(
            "Demographics — age",
            "Age 65+ vs 40–64",
            "age_65p",
            apply=lambda d: _indicator(d, d["age_group"] == "65+"),
            filter_fn=lambda d: d[d["age_group"].isin(["65+", "40-64"])],
        ),
    ]

    # Demographics — sex & race
    rows += [
        HeatmapRow(
            "Demographics — sex",
            "Male vs female",
            "male",
            apply=lambda d: _indicator(d, d["sex"] == "M"),
        ),
    ]
    for race, lab in [
        ("Black", "Black vs White"),
        ("Asian", "Asian vs White"),
        ("Hispanic", "Hispanic vs White"),
    ]:
        rows.append(
            HeatmapRow(
                "Demographics — race",
                lab,
                f"race_{race.lower()}",
                apply=lambda d, r=race: _indicator(d, d["race_ethnicity"] == r),
                filter_fn=lambda d, r=race: d[d["race_ethnicity"].isin(["White", r])],
            )
        )

    # Insurance & language (our grouped fields)
    for ins, lab in [
        ("Medicare", "Medicare vs private"),
        ("Medicaid", "Medicaid vs private"),
        ("undocumented", "Insurance undocumented vs private"),
    ]:
        rows.append(
            HeatmapRow(
                "Insurance",
                lab,
                f"ins_{ins}",
                apply=lambda d, i=ins: _indicator(d, d["insurance_group"] == i),
                filter_fn=lambda d: d[d["insurance_group"].isin(["private", ins])],
            )
        )
    rows += [
        HeatmapRow(
            "Language",
            "Non-English vs English",
            "lang_ne",
            apply=lambda d: _indicator(d, d["language_group"] == "non-English"),
            filter_fn=lambda d: d[d["language_group"].isin(["English", "non-English"])],
        ),
        HeatmapRow(
            "Language",
            "Language undocumented vs English",
            "lang_undoc",
            apply=lambda d: _indicator(d, d["language_group"] == "undocumented"),
            filter_fn=lambda d: d[d["language_group"].isin(["English", "undocumented"])],
        ),
    ]

    # Diagnosis / injury (AP vs trauma subtypes in cohort)
    rows += [
        HeatmapRow(
            "Diagnosis",
            "Trauma vs acute pancreatitis",
            "dx_trauma",
            apply=lambda d: _indicator(d, d["diagnosis_type"] == "trauma"),
        ),
    ]
    for inj, lab in [
        ("fall", "Fall (trauma subtype)"),
        ("fracture_dislocation", "Fracture/dislocation (trauma subtype)"),
        ("other_trauma", "Other trauma (subtype)"),
    ]:
        rows.append(
            HeatmapRow(
                "Diagnosis",
                lab,
                f"inj_{inj}",
                apply=lambda d, i=inj: _indicator(d, d["injury_group"] == i),
                filter_fn=lambda d: d[d["diagnosis_type"] == "trauma"],
            )
        )

    # Clinical severity
    rows += [
        HeatmapRow("Clinical severity", "Triage acuity / ESI (per level)", "triage_acuity"),
        HeatmapRow("Clinical severity", "Heart rate at initial pain (SD)", "heartrate_0_z"),
        HeatmapRow("Clinical severity", "Respiratory rate at initial pain (SD)", "resprate_0_z"),
        HeatmapRow("Clinical severity", "Systolic BP at initial pain (SD)", "sbp_0_z"),
        HeatmapRow(
            "Clinical severity",
            "Analgesic before reassessment",
            "analgesic",
            apply=lambda d: pd.to_numeric(d["any_analgesic_given"], errors="coerce"),
        ),
    ]

    # ED workflow
    rows += [
        HeatmapRow(
            "ED workflow",
            "Evening vs day shift",
            "shift_evening",
            apply=lambda d: _indicator(d, d["arrival_shift"] == "evening"),
            filter_fn=lambda d: d[d["arrival_shift"].isin(["day", "evening"])],
        ),
        HeatmapRow(
            "ED workflow",
            "Night vs day shift",
            "shift_night",
            apply=lambda d: _indicator(d, d["arrival_shift"] == "night"),
            filter_fn=lambda d: d[d["arrival_shift"].isin(["day", "night"])],
        ),
        HeatmapRow(
            "ED workflow",
            "Weekend arrival",
            "weekend",
            apply=lambda d: pd.to_numeric(d["arrival_weekend"], errors="coerce"),
        ),
        HeatmapRow("ED workflow", "ED arrivals in past hour", "ed_arrivals_past_1hr"),
        HeatmapRow(
            "ED workflow",
            "ED census at initial pain hour",
            "ed_census_at_initial_pain_hour",
        ),
    ]

    # Disposition & arrival (exclude unknown transport)
    for disp, lab in [
        ("ADMITTED", "Admitted vs home"),
        ("TRANSFER", "Transfer vs home"),
        ("OTHER", "Other disposition vs home"),
    ]:
        rows.append(
            HeatmapRow(
                "Disposition",
                lab,
                f"disp_{disp.lower()}",
                apply=lambda d, x=disp: _indicator(d, d["disposition_group"] == x),
                filter_fn=lambda d: d[d["disposition_group"].isin(["HOME", disp])],
            )
        )
    rows += [
        HeatmapRow(
            "Arrival",
            "Ambulance vs walk-in",
            "arr_amb",
            apply=lambda d: _indicator(
                d, d["arrival_transport"].astype(str).str.upper() == "AMBULANCE"
            ),
            filter_fn=lambda d: d[
                ~d["arrival_transport"].astype(str).str.upper().eq("UNKNOWN")
            ],
        ),
    ]
    return rows


def _prepare_row(sub: pd.DataFrame, row: HeatmapRow) -> pd.DataFrame:
    if row.filter_fn is not None:
        sub = row.filter_fn(sub)
    out = sub.copy()
    if row.apply is not None:
        out[row.col] = row.apply(out)
    elif row.col not in out.columns:
        return out.iloc[0:0]
    return out


def compute_heatmap_matrix(df: pd.DataFrame, rows: list[HeatmapRow] | None = None) -> pd.DataFrame:
    rows = rows or _build_rows()
    pain_cols = [f"Pain {p}" for p in PAIN_LEVELS]
    records = []

    for row in rows:
        entry = {"variable": row.label, "section": row.section}
        for p in PAIN_LEVELS:
            sub = df[df["pain_int"] == p]
            sub = _prepare_row(sub, row)
            entry[f"Pain {p}"] = _fit_uni(sub, row.col)
        records.append(entry)

    mat = pd.DataFrame(records).set_index("variable")
    return mat[pain_cols]


def plot_sectioned_heatmap(
    matrix: pd.DataFrame,
    sections: list[str],
    *,
    title: str,
    output_path: Path,
) -> None:
    section_by_var = dict(zip(matrix.index, sections))
    fig_h = max(9, 0.34 * len(matrix) + 2.5)
    fig, ax = plt.subplots(figsize=(12, fig_h))

    sns.heatmap(
        matrix.astype(float),
        ax=ax,
        cmap="RdBu_r",
        center=0,
        vmin=-P_CAP,
        vmax=P_CAP,
        cbar_kws={
            "label": "Signed −log₁₀(p)\nred → faster reassessment (HR>1)\nblue → slower (HR<1)",
        },
        linewidths=0.25,
        linecolor="#f0f0f0",
    )
    ax.set_xlabel("Initial pain score at first documentation")
    ax.set_ylabel("")
    ax.set_title(title, fontweight="bold", pad=10)

    labels = list(matrix.index)
    prev_sec = None
    for i, lab in enumerate(labels):
        sec = section_by_var[lab]
        if prev_sec is not None and sec != prev_sec:
            ax.axhline(i, color="#444", lw=1.2)
        prev_sec = sec

    sec_idx: dict[str, list[int]] = {}
    for i, lab in enumerate(labels):
        sec_idx.setdefault(section_by_var[lab], []).append(i)
    for sec, idxs in sec_idx.items():
        mid = (min(idxs) + max(idxs) + 1) / 2
        fig.text(
            0.01,
            1 - mid / len(labels),
            sec,
            ha="left",
            va="center",
            fontsize=8,
            fontweight="bold",
            transform=fig.transFigure,
        )

    fig.tight_layout(rect=[0.18, 0, 1, 1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {output_path}")


def generate_pain_score_heatmap(
    df: pd.DataFrame | None = None,
    *,
    cohort_label: str = "full cohort (AP + trauma)",
) -> pd.DataFrame:
    if df is None:
        df = _load_cohort()

    rows = _build_rows()
    matrix = compute_heatmap_matrix(df, rows)
    sections = [r.section for r in rows]

    slug = "full_cohort"
    matrix.reset_index().assign(section=sections).to_csv(
        ANALYSIS_OUT / f"pain_score_heatmap_{slug}.csv", index=False
    )

    plot_sectioned_heatmap(
        matrix,
        sections,
        title=(
            f"Time to first pain reassessment — univariate Cox by initial pain score\n"
            f"{cohort_label} (N={len(df):,})"
        ),
        output_path=HEATMAP_DIR / f"fig_pain_score_heatmap_{slug}.png",
    )
    return matrix
