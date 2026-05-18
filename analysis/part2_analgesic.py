from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test

from analysis.part2_cox_utils import (
    POST_DURATION,
    POST_EVENT,
    extract_all_terms,
    extract_race_hrs,
    fit_cox,
    fmt_p,
    formula_post_analgesic,
    ph_test_report,
)
from analysis.prep_part2 import build_post_analgesic_cohort, prep_part2a_cohort

PART2_DIR = Path(__file__).resolve().parents[1] / "figures" / "part2"
RACES = ["White", "Black", "Asian", "Hispanic"]


def _km_curves_by_race(df: pd.DataFrame, path: Path) -> float | None:
    fig, ax = plt.subplots(figsize=(10, 6))
    kmf = KaplanMeierFitter()
    groups = []
    durations = []
    events = []

    for race in RACES:
        sub = df[df["race_ethnicity"] == race]
        if len(sub) < 20:
            continue
        kmf.fit(
            sub[POST_DURATION],
            sub[POST_EVENT],
            label=f"{race} (n={len(sub):,}, events={int(sub[POST_EVENT].sum()):,})",
        )
        kmf.plot_cumulative_density(ax=ax, ci_show=False)
        groups.append(sub["race_ethnicity"])
        durations.append(sub[POST_DURATION])
        events.append(sub[POST_EVENT])

    p_val = None
    if len(groups) >= 2:
        try:
            lr = multivariate_logrank_test(
                pd.concat(durations),
                pd.concat(groups),
                pd.concat(events),
            )
            p_val = float(lr.p_value)
            ax.text(0.98, 0.02, f"log-rank p = {p_val:.4f}", transform=ax.transAxes, ha="right")
        except Exception:
            pass

    ax.set_xlim(0, min(480, df[POST_DURATION].quantile(0.95)))
    ax.set_xlabel("Minutes after first analgesic administration")
    ax.set_ylabel("Cumulative probability of post-analgesic pain reassessment")
    ax.set_title(
        "Post-analgesic pain reassessment by race/ethnicity\n"
        "Time zero = first analgesic after initial pain documentation"
    )
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p_val


def _logistic_windows(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for race in RACES:
        sub = df[df["race_ethnicity"] == race]
        row = {
            "race_ethnicity": race,
            "n_analgesic_recipients": len(sub),
            "pct_reassessed_60min": 100 * sub["reassessed_within_60_post_rx"].mean(),
            "pct_reassessed_120min": 100 * sub["reassessed_within_120_post_rx"].mean(),
        }
        rows.append(row)

    out = pd.DataFrame(rows)
    formula_base = (
        "outcome ~ C(race_ethnicity, Treatment(reference='White')) + initial_pain_score "
        "+ triage_acuity + C(age_group) + C(sex) + C(insurance_group) + C(language_group)"
    )
    for window, col in [(60, "reassessed_within_60_post_rx"), (120, "reassessed_within_120_post_rx")]:
        sub = df.dropna(
            subset=[
                col,
                "race_ethnicity",
                "initial_pain_score",
                "triage_acuity",
                "age_group",
                "sex",
                "insurance_group",
                "language_group",
            ]
        ).copy()
        sub["outcome"] = sub[col]
        try:
            res = smf.logit(formula_base, data=sub).fit(disp=0, method="lbfgs", maxiter=200)
            for term in res.params.index:
                if "race_ethnicity" in term and "[T." in term:
                    lvl = term.split("[T.")[1].rstrip("]")
                    ci = res.conf_int().loc[term]
                    key = f"adj_or_{window}min_{lvl}"
                    out.loc[out["race_ethnicity"] == lvl, f"adj_or_{window}min"] = np.exp(
                        res.params[term]
                    )
                    out.loc[out["race_ethnicity"] == lvl, f"adj_or_{window}min_ci"] = (
                        f"({np.exp(ci[0]):.2f}, {np.exp(ci[1]):.2f})"
                    )
        except Exception:
            out[f"adj_or_{window}min"] = np.nan

    return out


def save_cox_table(rows: list[dict], path_csv: Path, path_png: Path) -> None:
    df = pd.DataFrame(rows)
    export = df.copy()
    export["HR"] = export["hazard_ratio"].map(lambda x: f"{x:.2f}")
    export["95% CI"] = export.apply(
        lambda r: f"({r['ci_lower']:.2f}, {r['ci_upper']:.2f})", axis=1
    )
    export["p-value"] = export["p_value"].map(fmt_p)
    interp = []
    for _, r in export.iterrows():
        if "race_ethnicity" not in str(r.get("variable", "")):
            interp.append("")
        elif r["p_value"] < 0.05 and r["hazard_ratio"] < 1:
            interp.append("Slower post-analgesic reassessment")
        elif r["p_value"] < 0.05 and r["hazard_ratio"] > 1:
            interp.append("Faster post-analgesic reassessment")
        elif r["p_value"] >= 0.05:
            interp.append("Not significant")
        else:
            interp.append("")
    export["interpretation"] = interp
    cols = ["variable", "comparison", "n", "events", "HR", "95% CI", "p-value", "interpretation"]
    export[cols].to_csv(path_csv, index=False)

    show = export[cols].head(25).astype(str)
    fig, ax = plt.subplots(figsize=(14, max(4, 0.35 * len(show) + 1.5)))
    ax.axis("off")
    tbl = ax.table(cellText=show.values, colLabels=cols, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    fig.suptitle(
        "Post-Analgesic Pain Reassessment: Cox Model Results",
        fontsize=11,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.02,
        "Time zero is first analgesic administration. Event is first subsequent pain "
        "reassessment. HR > 1 indicates faster post-analgesic reassessment.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=[0, 0.06, 1, 0.92])
    fig.savefig(path_png, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_post_forest(rows: list[dict], path: Path) -> None:
    df = pd.DataFrame(rows)
    race_sub = df[df["variable"].astype(str).str.contains("race_ethnicity", na=False)]
    if race_sub.empty:
        race_sub = df.head(8)
    race_sub = race_sub.sort_values("hazard_ratio")
    fig, ax = plt.subplots(figsize=(9, max(4, 0.4 * len(race_sub))))
    y = np.arange(len(race_sub))
    ax.errorbar(
        race_sub["hazard_ratio"],
        y,
        xerr=[
            race_sub["hazard_ratio"] - race_sub["ci_lower"],
            race_sub["ci_upper"] - race_sub["hazard_ratio"],
        ],
        fmt="o",
        capsize=3,
    )
    ax.axvline(1.0, color="k")
    ax.set_yticks(y)
    ax.set_yticklabels(race_sub["comparison"], fontsize=9)
    ax.set_xlabel("Adjusted hazard ratio")
    ax.set_title("Post-analgesic reassessment — key predictors")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_analgesic_summary(df: pd.DataFrame, cph_rows: list[dict], path: Path) -> None:
    med = df.loc[df[POST_EVENT] == 1, POST_DURATION].median()
    race_lines = []
    for race in RACES:
        sub = df[df["race_ethnicity"] == race]
        race_lines.append(
            f"  {race}: N={len(sub):,}, post-analgesic reassessment "
            f"{100*sub[POST_EVENT].mean():.1f}%, median time {sub.loc[sub[POST_EVENT]==1, POST_DURATION].median():.0f} min"
            if sub[POST_EVENT].sum() > 0
            else f"  {race}: N={len(sub):,}, post-analgesic reassessment {100*sub[POST_EVENT].mean():.1f}%"
        )
    race_hr = [r for r in cph_rows if "race_ethnicity" in str(r.get("variable", ""))]
    lines = [
        "PART 2B: Analgesic-pathway analysis",
        "=" * 50,
        f"Analgesic recipients (after initial pain): N={len(df):,}",
        f"Post-analgesic reassessment events: {int(df[POST_EVENT].sum()):,}",
        f"Median time analgesic → reassessment (among events): {med:.0f} min",
        "",
        "Rule: first pain score strictly after first analgesic time; censor at ED outtime.",
        "Excluded analgesic before initial pain; reassessment at/before analgesic not counted.",
        "",
        "By race/ethnicity:",
        *race_lines,
        "",
        "Cox model (race vs White):",
    ]
    for r in race_hr:
        lines.append(
            f"  {r['comparison']}: HR={r['hazard_ratio']:.2f} "
            f"({r['ci_lower']:.2f}-{r['ci_upper']:.2f}), p={fmt_p(r['p_value'])}"
        )
    lines.extend(
        [
            "",
            "Caveats:",
            "  Analgesic administration is a treatment pathway/mediator, not a standard confounder.",
            "  This analysis describes documentation behavior after treatment, not causal effect of analgesia.",
            "  Patients without post-analgesic scores are censored at discharge.",
        ]
    )
    path.write_text("\n".join(lines))


def run_part2b(survival: pd.DataFrame | None = None) -> pd.DataFrame:
    PART2_DIR.mkdir(parents=True, exist_ok=True)
    if survival is None:
        survival = prep_part2a_cohort()

    df = build_post_analgesic_cohort(survival)
    logrank_p = _km_curves_by_race(df, PART2_DIR / "post_analgesic_reassessment_curves_by_race.png")

    formula = formula_post_analgesic()
    cph = fit_cox(df, formula, duration_col=POST_DURATION, event_col=POST_EVENT)
    cph_rows: list[dict] = []
    if cph is not None:
        n, ev = int(len(cph.durations)), int(cph.event_observed.sum())
        cph_rows = extract_all_terms(cph, n=n, events=ev)
        ph_text = ph_test_report(cph, df, formula, duration_col=POST_DURATION, event_col=POST_EVENT)
    else:
        ph_text = "Post-analgesic Cox model failed to converge."
        race_only = fit_cox(
            df,
            "initial_pain_score + triage_acuity + C(race_ethnicity, Treatment(reference=\"White\"))",
            duration_col=POST_DURATION,
            event_col=POST_EVENT,
        )
        if race_only:
            cph_rows = extract_all_terms(
                race_only,
                n=len(race_only.durations),
                events=int(race_only.event_observed.sum()),
            )

    save_cox_table(
        cph_rows,
        PART2_DIR / "post_analgesic_reassessment_cox_results.csv",
        PART2_DIR / "post_analgesic_reassessment_cox_results.png",
    )
    plot_post_forest(cph_rows, PART2_DIR / "post_analgesic_reassessment_forest.png")

    win_df = _logistic_windows(df)
    win_df.to_csv(PART2_DIR / "post_analgesic_reassessment_60_120min.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(win_df))
    w = 0.35
    ax.bar(x - w / 2, win_df["pct_reassessed_60min"], width=w, label="≤60 min")
    ax.bar(x + w / 2, win_df["pct_reassessed_120min"], width=w, label="≤120 min")
    ax.set_xticks(x)
    ax.set_xticklabels(win_df["race_ethnicity"])
    ax.set_ylabel("% reassessed after analgesic")
    ax.set_title("Post-analgesic reassessment windows by race/ethnicity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        PART2_DIR / "post_analgesic_reassessment_60_120min.png",
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

    # Analgesic class descriptives
    if "first_analgesic_class" in df.columns:
        cls = (
            df.groupby("first_analgesic_class")
            .agg(n=("stay_id", "count"), events=(POST_EVENT, "sum"))
            .reset_index()
        )
        cls.to_csv(PART2_DIR / "post_analgesic_by_class_counts.csv", index=False)

    write_analgesic_summary(df, cph_rows, PART2_DIR / "post_analgesic_pathway_summary.txt")
    ph_path = PART2_DIR / "ph_diagnostics_post_analgesic.txt"
    ph_lines = [ph_text]
    if logrank_p is not None:
        ph_lines.insert(0, f"KM log-rank p (race): {logrank_p:.4f}\n")
    ph_path.write_text("\n".join(ph_lines))

    return df
