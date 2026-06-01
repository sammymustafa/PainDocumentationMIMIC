"""Appendix within-acuity HRs for sex, age, diagnosis, pain, race, insurance, language."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import formula_within_acuity
from analysis.prep_cohort import prep_analytic_cohort
from analysis.term_utils import classify_association
from analysis.within_acuity import ESI_STRATA

APPENDIX_TERM_SPECS: list[tuple[str, str, dict]] = [
    ("Sex", "sex", {"term_contains": "sex"}),
    ("Age group", "age_group", {"term_contains": "age_group"}),
    ("Diagnosis/injury", "injury_group", {"term_contains": "injury_group"}),
    ("Initial pain", "initial_pain_score", {"exact_term": "initial_pain_score"}),
    ("Race/ethnicity", "race_ethnicity", {"term_contains": "race_ethnicity"}),
    ("Insurance", "insurance_group", {"term_contains": "insurance_group"}),
    ("Language", "language_group", {"term_contains": "language_group"}),
]


def _pick_terms(rows: pd.DataFrame, domain: str, kwargs: dict) -> pd.DataFrame:
    if kwargs.get("exact_term"):
        r = rows[rows["term"] == kwargs["exact_term"]]
        return r
    sub = rows[rows["term"].astype(str).str.contains(kwargs.get("term_contains", domain), na=False)]
    if "level" in kwargs:
        sub = sub[
            sub["term"].astype(str).str.contains(kwargs["level"], na=False)
            | sub["comparison"].astype(str).str.contains(kwargs["level"], na=False)
        ]
    return sub


def run_within_acuity_appendix(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    formula = formula_within_acuity(df)
    all_rows: list[dict] = []

    for esi in ESI_STRATA:
        sub = df[df["esi_group"] == esi]
        cph = fit_cox(sub, formula)
        n = len(sub)
        events = int(sub["reassessment_event"].sum()) if n else 0
        if cph is None:
            for label, domain, kwargs in APPENDIX_TERM_SPECS:
                all_rows.append(
                    {
                        "esi_group": esi,
                        "domain": label,
                        "n": n,
                        "events": events,
                        "comparison": "",
                        "hazard_ratio": np.nan,
                        "ci_low": np.nan,
                        "ci_high": np.nan,
                        "pvalue": np.nan,
                        "stability": "insufficient_N",
                    }
                )
            continue

        rows = pd.DataFrame(extract_terms(cph, model=f"within_{esi}", formula=formula))
        for label, domain, kwargs in APPENDIX_TERM_SPECS:
            hits = _pick_terms(rows, domain, kwargs)
            if hits.empty:
                all_rows.append(
                    {
                        "esi_group": esi,
                        "domain": label,
                        "n": n,
                        "events": events,
                        "comparison": "",
                        "hazard_ratio": np.nan,
                        "ci_low": np.nan,
                        "ci_high": np.nan,
                        "pvalue": np.nan,
                        "stability": "not_in_model",
                    }
                )
                continue
            for _, r in hits.iterrows():
                stab = classify_association(
                    r["hazard_ratio"],
                    r.get("pvalue"),
                    r.get("ci_low"),
                    r.get("ci_high"),
                )
                all_rows.append(
                    {
                        "esi_group": esi,
                        "domain": label,
                        "n": n,
                        "events": events,
                        "comparison": r.get("comparison", r["term"]),
                        "hazard_ratio": r["hazard_ratio"],
                        "ci_low": r["ci_low"],
                        "ci_high": r["ci_high"],
                        "pvalue": r.get("pvalue"),
                        "stability": stab,
                    }
                )

    out = pd.DataFrame(all_rows)
    appendix_dir = MANUSCRIPT_DIR / "appendix"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(appendix_dir / "table_within_acuity_appendix_hrs.csv", index=False)
    out.to_csv(ANALYSIS_OUT / "within_acuity_appendix_hrs.csv", index=False)
    _plot_appendix_heatmap(out, appendix_dir / "fig_within_acuity_age_sex_diagnosis_pain.png")
    return out


def _plot_appendix_heatmap(table: pd.DataFrame, path) -> None:
    if table.empty:
        return
    domains = table["domain"].unique()
    esis = list(ESI_STRATA)
    fig, axes = plt.subplots(1, len(esis), figsize=(5 * len(esis), max(4, len(domains) * 0.35)), squeeze=False)

    for ax, esi in zip(axes.flatten(), esis):
        sub = table[table["esi_group"] == esi]
        ylabels = []
        colors = []
        for dom in domains:
            dsub = sub[sub["domain"] == dom]
            if dsub.empty:
                ylabels.append(f"{dom}\n(n/a)")
                colors.append("lightgray")
                continue
            r = dsub.iloc[0]
            stab = r.get("stability", "")
            if stab in ("insufficient_N", "not_in_model"):
                ylabels.append(f"{dom}\n[{stab}]")
                colors.append("lightgray")
            else:
                hr = r["hazard_ratio"]
                ylabels.append(f"{dom}\nHR={hr:.2f} ({stab})")
                colors.append("steelblue" if stab == "faster" else "coral" if stab == "slower" else "gray")

        ax.barh(range(len(ylabels)), [1] * len(ylabels), color=colors)
        ax.set_yticks(range(len(ylabels)))
        ax.set_yticklabels(ylabels, fontsize=6)
        ax.set_xticks([])
        n_row = sub[["n", "events"]].drop_duplicates().head(1)
        nn = int(n_row["n"].iloc[0]) if len(n_row) else 0
        ev = int(n_row["events"].iloc[0]) if len(n_row) else 0
        ax.set_title(f"{esi}\nN={nn:,}, events={ev:,}", fontsize=9, fontweight="bold")

    fig.suptitle(
        "Appendix: within-acuity M4-style associations (stability flags; sparse ESI 4–5 interpret cautiously)",
        fontweight="bold",
        fontsize=11,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
