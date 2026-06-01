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
PAIN_LEVELS = list(range(1, 11))


@dataclass(frozen=True)
class HeatmapRow:
    section: str
    label: str
    col: str
    apply: Callable[[pd.DataFrame], pd.Series] | None = None
    filter_fn: Callable[[pd.DataFrame], pd.DataFrame] | None = None


@dataclass(frozen=True)
class Stratification:
    """How columns of the heatmap are defined."""
    slug: str
    filename: str
    column_labels: list[str]
    xlabel: str
    title_suffix: str
    subset: Callable[[pd.DataFrame, str], pd.DataFrame]


def _load_cohort(path: Path | None = None) -> pd.DataFrame:
    path = path or SURVIVAL_CSV
    df = pd.read_csv(path, low_memory=False)
    df["pain_int"] = df["initial_pain_score"].round().astype(int).clip(0, 10)
    df["pain_severity"] = pd.cut(
        df["initial_pain_score"],
        bins=[0, 3, 6, 10],
        labels=["Mild (1–3)", "Moderate (4–6)", "Severe (7–10)"],
        include_lowest=True,
    )
    esi = pd.to_numeric(df["triage_acuity"], errors="coerce")
    df["esi_group"] = pd.Series(index=df.index, dtype=object)
    df.loc[esi.isin([1, 2]), "esi_group"] = "ESI 1–2"
    df.loc[esi == 3, "esi_group"] = "ESI 3"
    df.loc[esi.isin([4, 5]), "esi_group"] = "ESI 4–5"
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


def _fit_pain_interaction(sub: pd.DataFrame, col: str) -> float:
    """Signed −log10(p) for covariate×initial_pain interaction (effect modification)."""
    out = sub[[DURATION_COL, EVENT_COL, col, "initial_pain_score"]].dropna()
    if len(out) < MIN_N or out[EVENT_COL].sum() < MIN_EVENTS:
        return np.nan
    if out[col].nunique() < 2:
        return np.nan
    pain = out["initial_pain_score"]
    pain_c = pain - pain.mean()
    out = out.assign(pain_c=pain_c, interact=out[col] * pain_c)
    try:
        cph = CoxPHFitter()
        cph.fit(
            out,
            duration_col=DURATION_COL,
            event_col=EVENT_COL,
            formula=f"{col} + pain_c + interact",
        )
        if "interact" not in cph.params_.index:
            return np.nan
        return _signed_log10_p(
            float(cph.params_["interact"]),
            float(cph.summary.loc["interact", "p"]),
        )
    except Exception:
        return np.nan


def _indicator(df: pd.DataFrame, mask: pd.Series) -> pd.Series:
    return mask.astype(float)


def _build_rows() -> list[HeatmapRow]:
    rows: list[HeatmapRow] = []

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

    for ins, lab in [
        ("Medicare", "Medicare vs private"),
        ("Medicaid", "Medicaid vs private"),
    ]:
        rows.append(
            HeatmapRow(
                "Insurance",
                lab,
                f"ins_{ins}",
                apply=lambda d, i=ins: _indicator(d, d["insurance_group"] == i),
                filter_fn=lambda d, i=ins: d[d["insurance_group"].isin(["private", i])],
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
                filter_fn=lambda d, x=disp: d[d["disposition_group"].isin(["HOME", x])],
            )
        )
    rows.append(
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
        )
    )
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


def get_stratifications() -> list[Stratification]:
    def by_pain_score(df: pd.DataFrame, label: str) -> pd.DataFrame:
        p = int(label.replace("Pain ", ""))
        return df[df["pain_int"] == p]

    def by_severity(df: pd.DataFrame, label: str) -> pd.DataFrame:
        return df[df["pain_severity"] == label]

    def overall(df: pd.DataFrame, label: str) -> pd.DataFrame:
        return df

    def by_esi(df: pd.DataFrame, label: str) -> pd.DataFrame:
        return df[df["esi_group"] == label]

    def by_dx(df: pd.DataFrame, label: str) -> pd.DataFrame:
        key = "trauma" if "Trauma" in label else "acute_pancreatitis"
        return df[df["diagnosis_type"] == key]

    def interaction(df: pd.DataFrame, label: str) -> pd.DataFrame:
        return df

    return [
        Stratification(
            slug="by_pain_score",
            filename="fig_heatmap_by_pain_score.png",
            column_labels=[f"Pain {p}" for p in PAIN_LEVELS],
            xlabel="Initial pain score (integer)",
            title_suffix="stratified by initial pain score",
            subset=by_pain_score,
        ),
        Stratification(
            slug="by_pain_severity",
            filename="fig_heatmap_by_pain_severity.png",
            column_labels=["Mild (1–3)", "Moderate (4–6)", "Severe (7–10)"],
            xlabel="Initial pain severity group",
            title_suffix="stratified by pain severity (mild / moderate / severe)",
            subset=by_severity,
        ),
        Stratification(
            slug="overall_pooled",
            filename="fig_heatmap_overall_pooled.png",
            column_labels=["All stays"],
            xlabel="",
            title_suffix="pooled across all initial pain scores",
            subset=overall,
        ),
        Stratification(
            slug="by_esi_acuity",
            filename="fig_heatmap_by_esi_acuity.png",
            column_labels=["ESI 1–2", "ESI 3", "ESI 4–5"],
            xlabel="Triage acuity group",
            title_suffix="stratified by triage acuity (ESI)",
            subset=by_esi,
        ),
        Stratification(
            slug="by_diagnosis",
            filename="fig_heatmap_by_diagnosis.png",
            column_labels=["Trauma", "Acute pancreatitis"],
            xlabel="Diagnosis group",
            title_suffix="stratified by diagnosis",
            subset=by_dx,
        ),
        Stratification(
            slug="pain_interaction",
            filename="fig_heatmap_pain_interaction.png",
            column_labels=["Pain × factor interaction"],
            xlabel="Effect modification by initial pain (continuous)",
            title_suffix="covariate × initial pain interaction (not stratified slices)",
            subset=interaction,
        ),
    ]


def compute_matrix(
    df: pd.DataFrame,
    strat: Stratification,
    rows: list[HeatmapRow] | None = None,
    *,
    use_interaction: bool = False,
) -> pd.DataFrame:
    rows = rows or _build_rows()
    records = []
    for row in rows:
        entry = {"variable": row.label, "section": row.section}
        for col_label in strat.column_labels:
            sub = strat.subset(df, col_label)
            sub = _prepare_row(sub, row)
            if use_interaction:
                entry[col_label] = _fit_pain_interaction(sub, row.col)
            else:
                entry[col_label] = _fit_uni(sub, row.col)
        records.append(entry)
    mat = pd.DataFrame(records).set_index("variable")
    return mat[strat.column_labels]


def plot_sectioned_heatmap(
    matrix: pd.DataFrame,
    sections: list[str],
    *,
    title: str,
    xlabel: str,
    output_path: Path,
) -> None:
    section_by_var = dict(zip(matrix.index, sections))
    fig_w = max(6, 1.1 + 0.65 * matrix.shape[1])
    fig_h = max(9, 0.34 * len(matrix) + 2.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    sns.heatmap(
        matrix.astype(float),
        ax=ax,
        cmap="RdBu_r",
        center=0,
        vmin=-P_CAP,
        vmax=P_CAP,
        annot=matrix.shape[1] <= 4,
        fmt=".1f",
        annot_kws={"fontsize": 7},
        cbar_kws={
            "label": "Signed −log₁₀(p)\nred → faster reassessment\nblue → slower",
        },
        linewidths=0.25,
        linecolor="#f0f0f0",
    )
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    ax.set_title(title, fontweight="bold", pad=10, fontsize=11)

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


def generate_all_heatmaps(
    df: pd.DataFrame | None = None,
    *,
    cohort_label: str = "full cohort (AP + trauma)",
) -> None:
    if df is None:
        df = _load_cohort()

    rows = _build_rows()
    sections = [r.section for r in rows]

    for strat in get_stratifications():
        use_ix = strat.slug == "pain_interaction"
        matrix = compute_matrix(df, strat, rows, use_interaction=use_ix)
        matrix.reset_index().assign(section=sections).to_csv(
            ANALYSIS_OUT / f"heatmap_{strat.slug}.csv", index=False
        )
        plot_sectioned_heatmap(
            matrix,
            sections,
            title=(
                f"Time to first pain reassessment — univariate Cox\n"
                f"{strat.title_suffix} · {cohort_label} (N={len(df):,})"
            ),
            xlabel=strat.xlabel,
            output_path=HEATMAP_DIR / strat.filename,
        )


def generate_pain_score_heatmap(df: pd.DataFrame | None = None, **kwargs) -> pd.DataFrame:
    """Backward-compatible: run all variants."""
    generate_all_heatmaps(df, **kwargs)
    strat = get_stratifications()[0]
    return compute_matrix(df or _load_cohort(), strat, _build_rows())
