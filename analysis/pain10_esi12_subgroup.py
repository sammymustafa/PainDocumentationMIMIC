"""Pain=10 and ESI 1–2 subgroup: parsimonious Cox (no constant pain score)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import formula_pain10_esi12
from analysis.prep_cohort import prep_analytic_cohort
from analysis.sectional_forest import exclude_term

HR_XLIM = (0.5, 1.5)


def _stable_hr_row(r: pd.Series) -> bool:
    hr = r.get("hazard_ratio")
    lo = r.get("ci_low")
    hi = r.get("ci_high")
    if pd.isna(hr) or not np.isfinite(hr):
        return False
    if "initial_pain_score" in str(r.get("term", "")):
        return False
    if "triage_acuity" in str(r.get("term", "")):
        return False
    if exclude_term(str(r["term"]), str(r.get("comparison", "")), exclude_arrival_other=True):
        return False
    if pd.isna(lo) or pd.isna(hi) or not np.isfinite(lo) or not np.isfinite(hi):
        return False
    if lo <= 0 or hi <= 0:
        return False
    if hi > 5 or lo < 0.2 or (hi / max(lo, 1e-6)) > 20:
        return False
    return HR_XLIM[0] <= hr <= HR_XLIM[1] or (lo <= HR_XLIM[1] and hi >= HR_XLIM[0])


def run_pain10_esi12_subgroup(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    sub = df[(df["pain_10"]) & (df["esi_group"] == "ESI 1–2")].copy()
    note_path = MANUSCRIPT_DIR / "tables" / "pain10_esi12_subgroup_note.txt"
    tables_dir = MANUSCRIPT_DIR / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    n = len(sub)
    events = int(sub["reassessment_event"].sum()) if n else 0
    desc = sub.groupby("race_ethnicity", observed=True).agg(
        n=("reassessment_event", "size"),
        events=("reassessment_event", "sum"),
        pct_60=("reassessed_by_60", "mean"),
    )
    desc.to_csv(tables_dir / "pain10_esi12_descriptive.csv")

    out_path = MANUSCRIPT_DIR / "fig14_pain10_esi12_subgroup.png"

    if n < 80 or events < 40:
        note_path.write_text(
            f"Insufficient sample for Cox: N={n}, events={events}. Descriptive table only.\n"
        )
        _plot_descriptive(desc, out_path)
        return pd.DataFrame()

    if "arrival_mode" in sub.columns:
        sub = sub[sub["arrival_mode"].isin(["walk_in", "ambulance"])].copy()

    formula = formula_pain10_esi12(sub)
    cph = fit_cox(sub, formula)
    if cph is None:
        note_path.write_text(f"Cox failed to converge: N={len(sub)}, events={int(sub['reassessment_event'].sum())}.\n")
        return pd.DataFrame()

    rows = extract_terms(cph, model="pain10_esi12", formula=formula)
    out = pd.DataFrame(rows)
    out.to_csv(tables_dir / "pain10_esi12_subgroup_results.csv", index=False)
    out.to_csv(ANALYSIS_OUT / "pain10_esi12_subgroup_results.csv", index=False)
    note_path.write_text(
        f"Parsimonious model (no pain score; ESI 1–2 only; walk-in/ambulance): "
        f"N={len(sub):,}, events={int(sub['reassessment_event'].sum()):,}.\n"
    )

    _plot_forest(out, out_path, n=len(sub), events=int(sub["reassessment_event"].sum()))
    return out


def _plot_descriptive(desc: pd.DataFrame, path: Path) -> None:
    if desc.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(desc.index.astype(str), desc["pct_60"] * 100, color="steelblue")
    ax.set_ylabel("% reassessed ≤60 min")
    ax.set_title("Pain=10, ESI 1–2: descriptive reassessment by race\n(Cox not estimable)", fontweight="bold")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_forest(results: pd.DataFrame, path: Path, *, n: int, events: int) -> None:
    plot_rows = results[results.apply(_stable_hr_row, axis=1)]
    if plot_rows.empty:
        plot_rows = results[
            ~results.apply(
                lambda r: exclude_term(str(r["term"]), str(r.get("comparison", "")), exclude_arrival_other=True),
                axis=1,
            )
        ].head(12)
    sub = plot_rows.head(15)
    if sub.empty:
        return

    fig, ax = plt.subplots(figsize=(9, max(4, 0.35 * len(sub) + 1)))
    y = np.arange(len(sub))
    lo_err = np.clip(sub["hazard_ratio"] - sub["ci_low"], 0, None)
    hi_err = np.clip(sub["ci_high"] - sub["hazard_ratio"], 0, None)
    ax.errorbar(sub["hazard_ratio"], y, xerr=[lo_err, hi_err], fmt="o", capsize=3, color="steelblue")
    ax.axvline(1, color="gray", ls="--")
    ax.set_xlim(HR_XLIM)
    ax.set_yticks(y)
    ax.set_yticklabels(sub["comparison"].astype(str), fontsize=8)
    ax.set_xlabel("Hazard ratio")
    ax.set_title(
        f"Pain=10 & ESI 1–2: parsimonious Cox (n={n:,}, events={events:,}; pain score excluded)",
        fontweight="bold",
        fontsize=10,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
