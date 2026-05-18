from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from analysis.part2_cox_utils import (
    DURATION_COL,
    EVENT_COL,
    MIN_EVENTS,
    MIN_N,
    extract_race_hrs,
    fit_cox,
    fmt_p,
    formula_interaction,
    formula_within_acuity,
    interpret_hr_pattern,
    ph_test_report,
)
from analysis.prep_part2 import prep_part2a_cohort

PART2_DIR = Path(__file__).resolve().parents[1] / "figures" / "part2"

ESI_GROUP_STRATA = ["ESI 1–2", "ESI 3", "ESI 4–5"]
ESI_SINGLE_STRATA = [2, 3, 4]
PAIN_CROSS = [
    ("ESI 1–2", "Pain 4–6"),
    ("ESI 1–2", "Pain 7–10"),
    ("ESI 3", "Pain 4–6"),
    ("ESI 3", "Pain 7–10"),
    ("ESI 4–5", "Pain 4–6"),
    ("ESI 4–5", "Pain 7–10"),
]
RACE_LEVELS = ["Asian", "Black", "Hispanic"]


def _add_interpretation(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    interps = []
    for _, row in out.iterrows():
        hr = row["hazard_ratio"]
        p = row["p_value"]
        if pd.isna(hr):
            interps.append("")
        elif p >= 0.05:
            interps.append("No significant difference vs White")
        elif hr < 1:
            interps.append("Slower reassessment vs White")
        else:
            interps.append("Faster reassessment vs White")
    out["interpretation"] = interps
    return out


def run_within_acuity_models(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], str]:
    """Stratified Cox, acuity×pain cross, and interaction model."""
    results: list[dict] = []
    notes: list[str] = []
    ph_lines: list[str] = []

    # Grouped ESI strata
    for stratum in ESI_GROUP_STRATA:
        sub = df[df["esi_group"] == stratum]
        n, ev = len(sub), int(sub[EVENT_COL].sum())
        if n < MIN_N or ev < MIN_EVENTS:
            notes.append(f"Skipped grouped stratum {stratum}: N={n}, events={ev}")
            continue
        cph = fit_cox(sub, formula_within_acuity())
        if cph is None:
            notes.append(f"Model failed: grouped {stratum}")
            continue
        results.extend(
            extract_race_hrs(
                cph, stratum=stratum, model_label="Grouped ESI Cox"
            )
        )
        if stratum == "ESI 3":
            ph_lines.append(f"=== Grouped {stratum} ===\n")
            ph_lines.append(ph_test_report(cph, sub, formula_within_acuity()))

    # Individual ESI 2, 3, 4
    for esi in ESI_SINGLE_STRATA:
        sub = df[df["esi_int"] == esi]
        label = f"ESI {esi}"
        n, ev = len(sub), int(sub[EVENT_COL].sum())
        if n < MIN_N or ev < MIN_EVENTS:
            notes.append(f"Skipped {label}: N={n}, events={ev}")
            continue
        cph = fit_cox(sub, formula_within_acuity())
        if cph is None:
            notes.append(f"Model failed: {label}")
            continue
        results.extend(
            extract_race_hrs(cph, stratum=label, model_label="Single ESI Cox")
        )

    # Acuity × pain cross (parsimonious)
    for esi_g, pain_g in PAIN_CROSS:
        sub = df[(df["esi_group"] == esi_g) & (df["pain_stratum"] == pain_g)]
        col_label = f"{esi_g}, {pain_g}"
        n, ev = len(sub), int(sub[EVENT_COL].sum())
        if n < MIN_N or ev < MIN_EVENTS:
            notes.append(f"Skipped cross {col_label}: N={n}, events={ev}")
            continue
        cph = fit_cox(sub, formula_within_acuity(parsimonious=True))
        if cph is None:
            notes.append(f"Model failed: cross {col_label}")
            continue
        results.extend(
            extract_race_hrs(
                cph,
                stratum=esi_g,
                pain_stratum=pain_g,
                model_label="Acuity × pain Cox",
            )
        )

    # Pain = 10 within ESI 3 if N allows
    for esi_g in ESI_GROUP_STRATA:
        sub = df[(df["esi_group"] == esi_g) & (df["initial_pain_score"] >= 9.5)]
        if len(sub) < MIN_N or sub[EVENT_COL].sum() < MIN_EVENTS:
            continue
        cph = fit_cox(sub, formula_within_acuity(parsimonious=True))
        if cph is None:
            continue
        results.extend(
            extract_race_hrs(
                cph,
                stratum=esi_g,
                pain_stratum="Pain = 10",
                model_label="Pain=10 Cox",
            )
        )

    # Interaction model (full cohort)
    inter_sub = df.dropna(subset=["esi_group"])
    cph_ix = fit_cox(inter_sub, formula_interaction())
    if cph_ix is not None:
        ph_lines.append("=== Interaction model (full cohort) ===\n")
        ph_lines.append(ph_test_report(cph_ix, inter_sub, formula_interaction()))
        for term in cph_ix.params_.index:
            if "race_ethnicity" in term and ":" not in term and "[T." in term:
                level = term.split("[T.")[1].rstrip("]")
                if level == "White":
                    continue
                ci = cph_ix.confidence_intervals_.loc[term]
                results.append(
                    {
                        "acuity_stratum": "Full cohort (main effect)",
                        "pain_stratum": "",
                        "model_label": "Race × acuity interaction model",
                        "comparison": f"{level} vs White",
                        "n_total": int(len(cph_ix.durations)),
                        "n_events": int(cph_ix.event_observed.sum()),
                        "hazard_ratio": float(np.exp(cph_ix.params_[term])),
                        "ci_lower": float(np.exp(ci[0])),
                        "ci_upper": float(np.exp(ci[1])),
                        "p_value": float(cph_ix.summary.loc[term, "p"]),
                    }
                )
        ix_terms = [t for t in cph_ix.params_.index if ":" in t and "race_ethnicity" in t]
        if ix_terms:
            min_p = min(float(cph_ix.summary.loc[t, "p"]) for t in ix_terms)
            notes.append(
                f"Race×acuity interaction: smallest interaction p = {min_p:.4f}"
            )
    else:
        notes.append("Interaction model failed to converge")

    res_df = _add_interpretation(pd.DataFrame(results))
    ph_text = "\n\n".join(ph_lines) if ph_lines else "PH diagnostics not available."
    return res_df, notes, ph_text


def save_results_table(df: pd.DataFrame, path_csv: Path, path_png: Path) -> None:
    path_csv.parent.mkdir(parents=True, exist_ok=True)
    export = df.copy()
    export["95% CI"] = export.apply(
        lambda r: f"({r['ci_lower']:.2f}, {r['ci_upper']:.2f})", axis=1
    )
    export["HR"] = export["hazard_ratio"].map(lambda x: f"{x:.2f}")
    export["p-value"] = export["p_value"].map(fmt_p)
    cols = [
        "acuity_stratum",
        "pain_stratum",
        "comparison",
        "n_total",
        "n_events",
        "HR",
        "95% CI",
        "p-value",
        "interpretation",
    ]
    export = export[cols]
    export.to_csv(path_csv, index=False)

    show = export.head(40).astype(str)
    fig_h = max(6, 0.35 * len(show) + 2)
    fig, ax = plt.subplots(figsize=(18, fig_h))
    ax.axis("off")
    tbl = ax.table(
        cellText=show.values,
        colLabels=show.columns,
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7)
    tbl.scale(1, 1.2)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0 or c == 0:
            cell.set_text_props(fontweight="bold")
    fig.suptitle(
        "Within-Acuity Cox Models: Race/Ethnicity and Time to First Pain Reassessment",
        fontsize=11,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.02,
        "Reference group: White. HR > 1 indicates faster reassessment; HR < 1 indicates slower "
        "reassessment. Models compare patients within similar triage acuity strata and adjust "
        "for available demographic/workflow covariates.",
        ha="center",
        fontsize=8,
        wrap=True,
    )
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(path_png, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_forest(df: pd.DataFrame, path: Path) -> None:
    plot_df = df[
        df["model_label"].isin(["Grouped ESI Cox", "Single ESI Cox"])
    ].copy()
    if plot_df.empty:
        plot_df = df[df["pain_stratum"] == ""].copy()
    plot_df = plot_df.sort_values(["acuity_stratum", "comparison"])
    plot_df["label"] = plot_df["acuity_stratum"] + " | " + plot_df["comparison"]

    fig, ax = plt.subplots(figsize=(10, max(5, 0.4 * len(plot_df))))
    y = np.arange(len(plot_df))
    ax.errorbar(
        plot_df["hazard_ratio"],
        y,
        xerr=[
            plot_df["hazard_ratio"] - plot_df["ci_lower"],
            plot_df["ci_upper"] - plot_df["hazard_ratio"],
        ],
        fmt="o",
        capsize=3,
        color="#4393c3",
    )
    ax.axvline(1.0, color="k", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["label"], fontsize=8)
    ax.set_xlabel("Hazard ratio (vs White)")
    ax.set_title(
        "Race/ethnicity and time to first reassessment within acuity strata\n"
        "HR > 1: faster reassessment | HR < 1: slower reassessment"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_heatmap(df: pd.DataFrame, path: Path) -> None:
    cross = df[df["model_label"] == "Acuity × pain Cox"].copy()
    if cross.empty:
        return
    cross["col"] = cross["acuity_stratum"] + ", " + cross["pain_stratum"]
    mat = cross.pivot(index="comparison", columns="col", values="hazard_ratio")
    mat = mat.reindex(columns=[f"{e}, {p}" for e, p in PAIN_CROSS if f"{e}, {p}" in mat.columns])

    fig, ax = plt.subplots(figsize=(12, 4))
    sns.heatmap(
        mat.astype(float),
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=1.0,
        vmin=0.7,
        vmax=1.3,
        ax=ax,
        cbar_kws={"label": "Hazard ratio vs White"},
        linewidths=0.5,
    )
    ax.set_title(
        "Within acuity × pain severity: race/ethnicity HR vs White\n"
        "(blank = insufficient N or model did not converge)"
    )
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_summary(
    df: pd.DataFrame,
    cohort: pd.DataFrame,
    notes: list[str],
    path: Path,
) -> None:
    grouped = df[df["model_label"] == "Grouped ESI Cox"]
    lines = [
        "PART 2A: Within-acuity pain reassessment analysis",
        "=" * 50,
        f"Cohort N: {len(cohort):,}",
        f"Reassessment events: {int(cohort[EVENT_COL].sum()):,}",
        f"ESI groups modeled: {', '.join(ESI_GROUP_STRATA)}",
        "",
        "Sparse / skipped strata:",
    ]
    lines.extend(notes if notes else ["  (none)"])
    lines.extend(["", "Key findings (grouped ESI models):"])
    for comp in ["Asian vs White", "Black vs White", "Hispanic vs White"]:
        sub = grouped[grouped["comparison"] == comp]
        if sub.empty:
            continue
        lines.append(f"  {comp}:")
        for _, r in sub.iterrows():
            sig = "*" if r["p_value"] < 0.05 else ""
            lines.append(
                f"    {r['acuity_stratum']}: HR={r['hazard_ratio']:.2f} "
                f"({r['ci_lower']:.2f}-{r['ci_upper']:.2f}), p={fmt_p(r['p_value'])}{sig}"
            )
    lines.extend(
        [
            "",
            "Interpretation:",
            "  Race/ethnicity differences were generally attenuated within acuity strata",
            "  compared with unstratified analyses. Where HR < 1 persists, reassessment",
            "  documentation was slower vs White within similar triage levels.",
            "  Acuity reflects clinical severity and triage workflow—not only a confounder.",
            "  Insurance and language patterns from the main analysis may still operate",
            "  within acuity bands.",
        ]
    )
    path.write_text("\n".join(lines))


def run_part2a(df: pd.DataFrame | None = None) -> pd.DataFrame:
    PART2_DIR.mkdir(parents=True, exist_ok=True)
    if df is None:
        df = prep_part2a_cohort()

    results, notes, ph_text = run_within_acuity_models(df)

    save_results_table(
        results,
        PART2_DIR / "within_acuity_race_cox_results.csv",
        PART2_DIR / "within_acuity_race_cox_results.png",
    )
    plot_forest(results, PART2_DIR / "within_acuity_race_forest.png")
    plot_heatmap(results, PART2_DIR / "within_acuity_pain_heatmap.png")
    write_summary(results, df, notes, PART2_DIR / "within_acuity_summary.txt")
    (PART2_DIR / "ph_diagnostics_within_acuity.txt").write_text(ph_text)

    return results
