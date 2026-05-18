from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.cohort_filters import EXCLUDED_RACES, filter_stay_cohort

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = REPO_ROOT / "data/processed/modeling/final_modeling_dataset.csv"
DEFAULT_FIGURES_DIR = REPO_ROOT / "figures"

SUMMARY_ROWS = [
    ("Triage acuity, mean (SD)", "triage_acuity", "continuous"),
    ("Initial pain score, mean (SD)", "initial_pain_score", "continuous"),
    ("First reassessment pain score, mean (SD)", "first_reassessment_score", "continuous"),
    ("Minutes to first reassessment, mean (SD)", "minutes_initial_to_first_reassessment", "continuous"),
]

SECTIONS: list[tuple[str, list[tuple]]] = [
    ("Age", [
        ("Age (years), mean (SD)", "age", "continuous"),
        ("Age group", "age_group", "categorical"),
    ]),
    ("Sex", [("Sex", "sex", "categorical")]),
    ("Language", [("Language", "language_group", "categorical")]),
    ("Insurance", [("Insurance", "insurance_group", "categorical")]),
    ("Diagnosis type", [("Diagnosis type", "diagnosis_type", "categorical")]),
    ("Trauma subtype", [("Trauma subtype", "trauma_subtype", "categorical")]),
    ("Disposition", [("Disposition", "disposition_group", "categorical")]),
    ("Arrival time", [
        ("Arrival shift", "arrival_shift", "categorical"),
        ("Weekend arrival, n (%)", "arrival_weekend", "binary", 1),
    ]),
    ("Analgesic", [
        ("Any analgesic between initial and reassessment, n (%)", "any_analgesic_given", "binary", 1),
        ("First analgesic class", "first_analgesic_class", "categorical"),
    ]),
]

TRAUMA_SUBTYPE_ORDER = ["fall", "fracture_dislocation", "other_trauma"]
SECTION_LABELS = {s[0] for s in SECTIONS} | {"Clinical outcomes"}


def _race_order(df: pd.DataFrame) -> list[str]:
    return df["race_ethnicity"].value_counts().index.tolist()


def _col_header(race: str, n: int) -> str:
    return f"{race}\n(N={n:,})"


def _mean_sd(series: pd.Series) -> str:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return "—"
    return f"{s.mean():.1f} ({s.std():.1f})"


def _n_pct(mask: pd.Series) -> str:
    n = int(mask.sum())
    denom = len(mask)
    if denom == 0:
        return "—"
    return f"{n:,} ({100 * n / denom:.1f}%)"


def _binary_cell(sub: pd.DataFrame, col: str, value) -> str:
    if col not in sub.columns:
        return "—"
    s = sub[col]
    if pd.api.types.is_numeric_dtype(s):
        mask = s.fillna(0) == value
    else:
        mask = s.astype(str) == str(value)
    return _n_pct(mask)


def _category_order(col: str, categories: list) -> list:
    if col == "trauma_subtype":
        ordered = [c for c in TRAUMA_SUBTYPE_ORDER if c in categories]
        rest = [c for c in categories if c not in ordered and c not in {"", "nan", "None"}]
        return ordered + sorted(rest)
    return sorted(c for c in categories if c not in {"", "nan", "None"})


def build_demographic_table(df: pd.DataFrame) -> pd.DataFrame:
    """Table 1: characteristics as rows, race groups as columns (vertical layout)."""
    df = filter_stay_cohort(df)
    if "race_ethnicity" not in df.columns:
        raise ValueError("Missing column: race_ethnicity")

    races = _race_order(df)
    groups: dict[str, pd.DataFrame] = {"Overall": df}
    for race in races:
        groups[race] = df.loc[df["race_ethnicity"] == race]

    headers = ["Characteristic", _col_header("Overall", len(df))]
    headers.extend(_col_header(r, len(groups[r])) for r in races)
    rows: list[list[str]] = []

    rows.append(["Clinical outcomes", *["—"] * (len(races) + 1)])
    for label, col, kind in SUMMARY_ROWS:
        if kind == "continuous" and col in df.columns:
            row = [label]
            for gname in ["Overall", *races]:
                row.append(_mean_sd(groups[gname][col]))
            rows.append(row)

    for section_title, section_rows in SECTIONS:
        rows.append([section_title, *["—"] * (len(races) + 1)])
        for item in section_rows:
            if len(item) == 3:
                label, col, kind = item
                if kind == "continuous" and col in df.columns:
                    row = [label]
                    for gname in ["Overall", *races]:
                        row.append(_mean_sd(groups[gname][col]))
                    rows.append(row)
                elif kind == "categorical" and col in df.columns:
                    cats = groups["Overall"][col].dropna().astype(str).unique().tolist()
                    for cat in _category_order(col, cats):
                        row = [f"  {cat}, n (%)"]
                        for gname in ["Overall", *races]:
                            row.append(_binary_cell(groups[gname], col, cat))
                        rows.append(row)
            elif len(item) == 4:
                label, col, kind, value = item
                if kind == "binary" and col in df.columns:
                    row = [label]
                    for gname in ["Overall", *races]:
                        row.append(_binary_cell(groups[gname], col, value))
                    rows.append(row)

    return pd.DataFrame(rows, columns=headers)


def save_demographic_table_png(
    table: pd.DataFrame,
    output_path: Path,
    title: str = "Cohort characteristics by race/ethnicity",
) -> None:
    """Save vertical Table 1 (rows = characteristics, columns = race groups)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n_rows, n_cols = table.shape
    fig_w = max(12, 1.15 * n_cols)
    fig_h = max(6, 0.32 * n_rows + 1.2)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)

    col_widths = [0.26] + [0.12] * (n_cols - 1)
    tbl = ax.table(
        cellText=table.values.tolist(),
        colLabels=table.columns.tolist(),
        loc="center",
        cellLoc="left",
        colWidths=col_widths,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.2)

    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_text_props(fontweight="bold", fontsize=8)
            cell.set_facecolor("#e8e8e8")
        elif col == 0:
            text = cell.get_text().get_text().strip()
            if text in SECTION_LABELS:
                cell.set_text_props(fontweight="bold")
                cell.set_facecolor("#f4f4f4")

    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_demographic_table(
    data_path: Path | str | None = None,
    figures_dir: Path | str | None = None,
    csv_name: str = "table1_by_race.csv",
    png_name: str = "table1_by_race.png",
) -> pd.DataFrame:
    """
    Build Table 1 from the final modeling dataset and write CSV + PNG.

    Returns the table DataFrame. PNG uses standard vertical orientation
    (characteristics down the left, race strata across columns).
    """
    data_path = Path(data_path or DEFAULT_DATA_PATH)
    figures_dir = Path(figures_dir or DEFAULT_FIGURES_DIR)

    if not data_path.exists():
        raise FileNotFoundError(
            f"Modeling dataset not found: {data_path}\n"
            "Run build_modeling_dataset.py first, or pass --data."
        )

    df = pd.read_csv(data_path, low_memory=False)
    table = build_demographic_table(df)

    figures_dir.mkdir(parents=True, exist_ok=True)
    csv_path = figures_dir / csv_name
    png_path = figures_dir / png_name

    table.to_csv(csv_path, index=False)
    save_demographic_table_png(table, png_path)

    print(f"Table 1: {len(table)} rows x {len(table.columns)} columns (vertical layout)")
    print(f"Races: {', '.join(_race_order(filter_stay_cohort(df)))}")
    print(f"Excluded races: {', '.join(sorted(EXCLUDED_RACES))}")
    print(f"Saved CSV -> {csv_path}")
    print(f"Saved PNG -> {png_path}")
    return table
