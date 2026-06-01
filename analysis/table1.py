"""Manuscript Table 1: analytic cohort overview (overall column)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from analysis._paths import MANUSCRIPT_TABLES
from analysis.prep_cohort import prep_analytic_cohort


def _mean_sd(s: pd.Series) -> str:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if len(x) == 0:
        return "—"
    return f"{x.mean():.1f} ({x.std():.1f})"


def _n_pct(mask: pd.Series) -> str:
    n = int(mask.sum())
    d = len(mask)
    return f"{n:,} ({100 * n / d:.1f}%)" if d else "—"


def _cat_rows(df: pd.DataFrame, col: str, label_map: dict | None = None) -> list[tuple[str, str]]:
    rows = []
    if col not in df.columns:
        return rows
    vc = df[col].fillna("missing").astype(str).value_counts()
    for cat in vc.index:
        disp = label_map.get(cat, cat) if label_map else cat
        if cat == "missing" and label_map is None:
            disp = "Missing/not recorded"
        rows.append((f"  {disp}", _n_pct(df[col].fillna("missing").astype(str) == cat)))
    return rows


def build_table1(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    n = len(df)
    rows: list[list[str]] = [["Characteristic", f"Overall\n(N={n:,})"]]

    def add_section(title: str) -> None:
        rows.append([title, "—"])

    def add_row(label: str, value: str) -> None:
        rows.append([label, value])

    add_section("Demographics")
    add_row("Age (years), mean (SD)", _mean_sd(df["age"]))
    for cat in ["<18", "18-39", "40-64", "65+"]:
        if cat in df["age_group"].astype(str).values:
            add_row(f"  Age {cat}, n (%)", _n_pct(df["age_group"].astype(str) == cat))
    if df["age"].isna().any():
        add_row("  Age missing, n (%)", _n_pct(df["age"].isna()))

    add_section("Sex")
    for cat in ["F", "M"]:
        add_row(f"  {cat}, n (%)", _n_pct(df["sex"] == cat))

    add_section("Race/ethnicity")
    for cat in df["race_ethnicity"].dropna().unique():
        add_row(f"  {cat}, n (%)", _n_pct(df["race_ethnicity"] == cat))

    add_section("Insurance (analytic cohort excludes undocumented)")
    ins_map = {
        "private": "Private",
        "Medicaid": "Medicaid",
        "Medicare": "Medicare",
    }
    for label, val in _cat_rows(df, "insurance_group", ins_map):
        add_row(label, val)

    add_section("Language")
    lang_map = {
        "undocumented": "Undocumented (missing language record)",
        "English": "English",
        "non-English": "Non-English",
    }
    for label, val in _cat_rows(df, "language_group", lang_map):
        add_row(label, val)

    add_section("Clinical")
    add_row("Triage acuity (ESI), mean (SD)", _mean_sd(df["triage_acuity"]))
    for esi in sorted(df["esi_int"].dropna().unique()):
        add_row(f"  ESI {int(esi)}, n (%)", _n_pct(df["esi_int"] == esi))
    add_row("Initial pain score, mean (SD)", _mean_sd(df["initial_pain_score"]))
    add_row("Diagnosis: acute pancreatitis, n (%)", _n_pct(df["diagnosis_type"] == "acute_pancreatitis"))
    add_row("Diagnosis: trauma, n (%)", _n_pct(df["is_trauma"]))
    for label, val in _cat_rows(df, "injury_group"):
        add_row(label, val)

    add_section("Outcomes (descriptive)")
    add_row("Any reassessment, n (%)", _n_pct(df["reassessment_event"] == 1))
    add_row("Reassessed within 60 min, n (%)", _n_pct(df["reassessed_by_60"] == 1))
    add_row("Reassessed within 120 min, n (%)", _n_pct(df["reassessed_by_120"] == 1))
    add_row("Minutes to reassessment, median (IQR)", _median_iqr(df["duration_minutes"]))

    add_section("Workflow")
    for label, val in _cat_rows(df, "arrival_shift"):
        add_row(label, val)
    add_row("Weekend arrival, n (%)", _n_pct(df["arrival_weekend"] == 1))
    add_row("ED arrivals past 1 hr, mean (SD)", _mean_sd(df["ed_arrivals_past_1hr"]))
    add_row("ED census at initial pain hour, mean (SD)", _mean_sd(df["ed_census_at_initial_pain_hour"]))
    mode_map = {
        "walk_in": "Walk-in",
        "ambulance": "Ambulance",
        "other": "Other arrival mode",
        "unknown": "Arrival mode unknown",
    }
    df_mode = df.copy()
    df_mode["arrival_mode"] = df_mode["arrival_mode"].fillna("unknown")
    for label, val in _cat_rows(df_mode, "arrival_mode", mode_map):
        add_row(label, val)

    add_section("Disposition")
    for label, val in _cat_rows(df, "disposition_group"):
        add_row(label, val)

    add_section("Treatment")
    add_row(
        "Analgesic before reassessment or ED departure, n (%)",
        _n_pct(df["any_analgesic_given"] == 1),
    )
    if "first_analgesic_class" in df.columns:
        for label, val in _cat_rows(df[df["any_analgesic_given"] == 1], "first_analgesic_class"):
            add_row(label, val)

    add_section("Year / policy era")
    add_row("De-identified year, mean (SD)", _mean_sd(df["year"]))
    for label, val in _cat_rows(df, "year_era"):
        add_row(label, val)

    return pd.DataFrame(rows, columns=["Characteristic", "Value"])


def _median_iqr(s: pd.Series) -> str:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if len(x) == 0:
        return "—"
    q1, med, q3 = x.quantile([0.25, 0.5, 0.75])
    return f"{med:.0f} ({q1:.0f}–{q3:.0f})"


def _save_png(table: pd.DataFrame, path: Path, *, title: str, max_rows: int = 45) -> None:
    sub = table.head(max_rows)
    fig_h = max(8, 0.28 * len(sub) + 1.5)
    fig, ax = plt.subplots(figsize=(10, fig_h))
    ax.axis("off")
    ax.set_title(title, fontsize=12, fontweight="bold")
    tbl = ax.table(
        cellText=sub.values.tolist(),
        colLabels=sub.columns.tolist(),
        loc="center",
        cellLoc="left",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7)
    tbl.scale(1, 1.15)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _to_markdown(table: pd.DataFrame) -> str:
    lines = [
        "# Table 1. Analytic cohort overview",
        "",
        f"N = {table.iloc[0, 1].split('=')[-1].strip(')')}" if "N=" in str(table.iloc[0, 1]) else "",
        "",
        "| Characteristic | Value |",
        "|---|---|",
    ]
    for _, row in table.iterrows():
        lines.append(f"| {row.iloc[0]} | {row.iloc[1]} |")
    lines.append("")
    lines.append(
        "Footnotes: Analytic cohort excludes stays with undocumented insurance. "
        "Language is descriptive only (excluded from Cox models). "
        "Policy eras in models use 5-year bins on de-identified MIMIC years (sparse eras collapsed)."
    )
    return "\n".join(lines)


def _to_latex(table: pd.DataFrame) -> str:
    body = []
    for _, row in table.iterrows():
        c0 = str(row.iloc[0]).replace("&", "\\&")
        c1 = str(row.iloc[1]).replace("&", "\\&")
        body.append(f"{c0} & {c1} \\\\")
    return (
        "\\begin{table}[ht]\n\\centering\n\\caption{Analytic cohort overview}\n"
        "\\begin{tabular}{ll}\n\\hline\n"
        + "\n".join(body)
        + "\n\\hline\n\\end{tabular}\n\\end{table}\n"
    )


def export_table1(df: pd.DataFrame | None = None, out_dir: Path | None = None) -> pd.DataFrame:
    out_dir = out_dir or MANUSCRIPT_TABLES
    out_dir.mkdir(parents=True, exist_ok=True)
    table = build_table1(df)
    stem = out_dir / "table1_cohort_overview"
    table.to_csv(stem.with_suffix(".csv"), index=False)
    _save_png(table, stem.with_suffix(".png"), title="Table 1. Analytic cohort overview")
    stem.with_suffix(".md").write_text(_to_markdown(table))
    stem.with_suffix(".tex").write_text(_to_latex(table))
    return table
