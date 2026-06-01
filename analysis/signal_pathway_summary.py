"""Synthesis matrix: where reassessment associations persist across analysis stages."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import formula_m5
from analysis.prep_cohort import prep_analytic_cohort
from analysis.term_utils import classify_association, pick_term_row

STAGES = [
    ("overall_m5", "Overall M5"),
    ("pain_7_10", "Pain 7–10 (M5)"),
    ("within_acuity", "Within acuity"),
    ("post_analgesic", "Post-analgesic"),
]

DOMAINS: list[tuple[str, str, str | None]] = [
    ("race/ethnicity", "race_ethnicity", "Black"),
    ("insurance", "insurance_group", "Medicaid"),
    ("language", "", None),
    ("age", "age_group", "65+"),
    ("diagnosis", "injury_group", "other_trauma"),
    ("ESI/acuity", "triage_acuity", None),
    ("disposition", "disposition_group", "ADMITTED"),
    ("workflow", "arrival_shift", "night"),
    ("year", "year_era", None),
    ("analgesic pathway", "any_analgesic_given", None),
]

CODE_MAP = {
    "faster": 2,
    "slower": 0,
    "null": 1,
    "unstable": -1,
    "insufficient_data": -2,
    "not_in_cox": -3,
}
CODE_COLORS = {
    2: "#2166ac",
    0: "#b2182b",
    1: "#f7f7f7",
    -1: "#fdae61",
    -2: "#d9d9d9",
    -3: "#e0e0e0",
}


def _hr_from_df(
    df: pd.DataFrame,
    *,
    model: str | None = None,
    term_contains: str,
    level: str | None = None,
    exact_term: str | None = None,
) -> tuple[float | None, float | None, float | None, float | None]:
    if df is None or df.empty:
        return None, None, None, None
    if model:
        r = pick_term_row(df, model, term_contains=term_contains or None, level=level, exact_term=exact_term)
    else:
        sub = df[df["term"].astype(str).str.contains(term_contains, case=False, na=False)]
        if level:
            sub = sub[
                sub["term"].astype(str).str.contains(level, case=False, na=False)
                | sub["comparison"].astype(str).str.contains(level, case=False, na=False)
            ]
        if exact_term:
            sub = sub[sub["term"] == exact_term]
        r = sub.iloc[0] if len(sub) else None
    if r is None:
        return None, None, None, None
    return r["hazard_ratio"], r["pvalue"], r["ci_low"], r["ci_high"]


def _cell_code(hr, p, lo, hi, *, not_modeled: bool = False) -> str:
    if not_modeled:
        return "not_in_cox"
    return classify_association(hr, p, lo, hi)


def _fit_pain_710(df: pd.DataFrame) -> pd.DataFrame:
    sub = df[df["initial_pain_score"] >= 7].copy()
    cph = fit_cox(sub, formula_m5())
    if cph is None:
        return pd.DataFrame()
    return pd.DataFrame(extract_terms(cph, model="pain_7_10", formula=formula_m5()))


def build_signal_matrix(
    df: pd.DataFrame,
    m5: pd.DataFrame,
    within_acuity: pd.DataFrame,
    post_rx: pd.DataFrame,
    s_rx: pd.DataFrame,
) -> pd.DataFrame:
    pain710 = _fit_pain_710(df)

    m5_use = m5.copy()
    if len(m5_use) and "model" not in m5_use.columns:
        m5_use["model"] = "M5"

    stage_dfs: dict[str, pd.DataFrame | None] = {
        "overall_m5": m5_use,
        "pain_7_10": pain710,
        "within_acuity": within_acuity,
        "post_analgesic": post_rx,
    }

    rows = []
    for domain, term_key, level in DOMAINS:
        for stage_id, stage_label in STAGES:
            not_cox = domain == "language"
            analgesic_s_rx = domain == "analgesic pathway" and stage_id == "overall_m5"
            if analgesic_s_rx and len(s_rx):
                hr, p, lo, hi = _hr_from_df(s_rx, model="S_rx", term_contains="any_analgesic_given")
            elif domain == "analgesic pathway" and stage_id == "post_analgesic":
                hr, p, lo, hi = _hr_from_df(
                    post_rx,
                    model="post_analgesic",
                    term_contains="race_ethnicity",
                    level="Black",
                )
            elif not_cox:
                hr, p, lo, hi = None, None, None, None
            else:
                sdf = stage_dfs.get(stage_id)
                model = "M5" if stage_id == "overall_m5" else None
                exact = term_key if level is None and term_key in ("triage_acuity", "initial_pain_score", "any_analgesic_given") else None
                hr, p, lo, hi = _hr_from_df(
                    sdf if sdf is not None else pd.DataFrame(),
                    model=model,
                    term_contains=term_key,
                    level=level,
                    exact_term=exact,
                )
                if stage_id == "within_acuity" and hr is None and level:
                    # try any ESI stratum
                    for esi in ["ESI 1–2", "ESI 3", "ESI 4–5"]:
                        if "esi_group" in (sdf.columns if sdf is not None else []):
                            sub = sdf[sdf["esi_group"] == esi]
                            hr, p, lo, hi = _hr_from_df(sub, term_contains=term_key, level=level)
                            if hr is not None:
                                break
            code = _cell_code(hr, p, lo, hi, not_modeled=not_cox)
            rows.append(
                {
                    "domain": domain,
                    "stage": stage_label,
                    "stage_id": stage_id,
                    "code": code,
                    "hazard_ratio": hr,
                    "pvalue": p,
                    "ci_low": lo,
                    "ci_high": hi,
                }
            )
    return pd.DataFrame(rows)


def plot_signal_matrix(matrix: pd.DataFrame, path) -> None:
    domains = [d[0] for d in DOMAINS]
    stages = [s[1] for s in STAGES]
    grid = np.full((len(domains), len(stages)), -2)
    for i, dom in enumerate(domains):
        for j, st in enumerate(stages):
            cell = matrix[(matrix["domain"] == dom) & (matrix["stage"] == st)]
            if len(cell):
                grid[i, j] = CODE_MAP.get(cell.iloc[0]["code"], -2)

    fig, ax = plt.subplots(figsize=(12, 7))
    display = np.zeros_like(grid, dtype=float)
    remap = {0: 0, 1: 1, 2: 2, -1: 3, -2: 4, -3: 5}
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            display[i, j] = remap.get(int(grid[i, j]), 4)
    cmap = plt.matplotlib.colors.ListedColormap(
        [CODE_COLORS[0], CODE_COLORS[1], CODE_COLORS[2], CODE_COLORS[-1], CODE_COLORS[-2], CODE_COLORS[-3]]
    )
    ax.imshow(display, aspect="auto", cmap=cmap, vmin=0, vmax=5)

    ax.set_xticks(np.arange(len(stages)))
    ax.set_xticklabels(stages, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(domains)))
    ax.set_yticklabels(domains)

    labels = {
        2: "Faster",
        0: "Slower",
        1: "Null",
        -1: "Unstable",
        -2: "N insuff.",
        -3: "Not in Cox",
    }
    for i in range(len(domains)):
        for j in range(len(stages)):
            v = int(grid[i, j])
            ax.text(j, i, labels.get(v, ""), ha="center", va="center", fontsize=7, color="#222")

    ax.set_title(
        "Where does the signal live? Reassessment associations across pathway stages",
        fontweight="bold",
        pad=12,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run_signal_pathway_summary(
    df: pd.DataFrame | None = None,
    m5: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df

    def _load(name: str) -> pd.DataFrame:
        p = ANALYSIS_OUT / name
        if not p.exists() or p.stat().st_size == 0:
            return pd.DataFrame()
        try:
            return pd.read_csv(p)
        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    m5 = m5 if m5 is not None else _load("m5_cox_hr.csv")
    within_acuity = _load("within_acuity_cox_hr.csv")
    post_rx = _load("post_analgesic_cox_hr.csv")
    s_rx = _load("s_rx_cox_hr.csv")

    matrix = build_signal_matrix(df, m5, within_acuity, post_rx, s_rx)
    (MANUSCRIPT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    matrix.to_csv(MANUSCRIPT_DIR / "tables" / "table15_where_signal_lives.csv", index=False)
    matrix.to_csv(ANALYSIS_OUT / "where_signal_lives.csv", index=False)
    if not matrix.empty:
        plot_signal_matrix(matrix, MANUSCRIPT_DIR / "fig15_where_signal_lives.png")
    return matrix
