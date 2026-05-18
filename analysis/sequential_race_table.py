from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, FIGURES

FIGURES_TABLES = FIGURES / "tables"
SEQUENTIAL_CSV = ANALYSIS_OUT / "sequential_cox_hr.csv"
OUTPUT_CSV = FIGURES_TABLES / "sequential_cox_race_ethnicity_table.csv"
OUTPUT_PNG = FIGURES_TABLES / "sequential_cox_race_ethnicity_table.png"

MODELS = ["M2", "M3", "M4", "M5", "M6"]
RACE_ROWS = [
    ("Asian vs White", "Asian"),
    ("Black vs White", "Black"),
    ("Hispanic vs White", "Hispanic"),
]


def _fmt_p(p: float) -> str:
    if pd.isna(p):
        return ""
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def _fmt_ci(lo: float, hi: float) -> str:
    if pd.isna(lo) or pd.isna(hi):
        return ""
    return f"({lo:.2f}, {hi:.2f})"


def _interpret(hrs: list[float]) -> str:
    valid = [h for h in hrs if pd.notna(h)]
    if len(valid) < 2:
        return ""
    below = [h < 1 for h in valid]
    above = [h > 1 for h in valid]
    if any(below) and any(above):
        return "Direction changes after adjustment"
    if all(below):
        if abs(valid[-1] - 1) < abs(valid[0] - 1) - 0.01:
            return "Association attenuates after adjustment"
        return "Slower reassessment vs White"
    if all(above):
        if abs(valid[-1] - 1) < abs(valid[0] - 1) - 0.01:
            return "Association attenuates after adjustment"
        return "Faster reassessment vs White"
    return "Association attenuates after adjustment"


def _extract_race_terms(seq: pd.DataFrame) -> pd.DataFrame:
    mask = seq["term"].astype(str).str.contains("race_ethnicity", na=False) & seq[
        "term"
    ].astype(str).str.contains(r"\[T\.", na=False)
    return seq.loc[mask].copy()


def _level_from_term(term: str) -> str:
    if "[T." in term:
        return term.split("[T.")[1].rstrip("]")
    return term


def build_sequential_race_table(seq_path: Path | None = None) -> pd.DataFrame:
    """Build formatted race table from existing sequential_cox_hr.csv (no model refit)."""
    seq_path = seq_path or SEQUENTIAL_CSV
    if not seq_path.exists():
        raise FileNotFoundError(
            f"Sequential Cox results not found: {seq_path}\n"
            "Run the survival analysis pipeline first to create sequential_cox_hr.csv."
        )

    seq = pd.read_csv(seq_path)
    race = _extract_race_terms(seq)
    race["level"] = race["term"].map(_level_from_term)

    rows_out: list[dict] = []
    for row_label, level in RACE_ROWS:
        row_data: dict = {"Comparison": row_label}
        hrs: list[float] = []

        for model in MODELS:
            sub = race[(race["model"] == model) & (race["level"] == level)]
            if sub.empty:
                row_data[f"{model} HR"] = ""
                row_data[f"{model} 95% CI"] = ""
                row_data[f"{model} p-value"] = ""
                hrs.append(np.nan)
                continue

            r = sub.iloc[0]
            hr = float(r["hazard_ratio"])
            lo = float(r["ci_low"])
            hi = float(r["ci_high"])
            p = float(r["pvalue"])

            row_data[f"{model} HR"] = f"{hr:.2f}"
            row_data[f"{model} 95% CI"] = _fmt_ci(lo, hi)
            row_data[f"{model} p-value"] = _fmt_p(p)
            hrs.append(hr)

        row_data["Interpretation"] = _interpret(hrs)
        rows_out.append(row_data)

    return pd.DataFrame(rows_out)


def save_race_table_png(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    show = df.astype(str)

    nrows, ncols = show.shape
    fig_w = max(16, 1.0 + 0.55 * ncols)
    fig_h = max(4.5, 1.8 + 0.45 * nrows)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")

    tbl = ax.table(
        cellText=show.values,
        colLabels=show.columns,
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1, 1.35)

    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_text_props(fontweight="bold")
            cell.set_facecolor("#e8e8e8")
        elif col == 0:
            cell.set_text_props(fontweight="bold")
            cell.set_facecolor("#f5f5f5")

    title = (
        "Sequential Cox Models: Race/Ethnicity and Time to First Pain Reassessment"
    )
    footnote = (
        "Reference group: White. HR > 1 indicates faster reassessment; HR < 1 indicates "
        "slower reassessment. M6 includes analgesic before reassessment as a "
        "pathway/sensitivity adjustment."
    )
    fig.suptitle(title, fontsize=12, fontweight="bold", y=0.98)
    fig.text(0.5, 0.02, footnote, ha="center", va="bottom", fontsize=8, wrap=True)
    fig.tight_layout(rect=[0, 0.06, 1, 0.94])
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {path}")


def write_sequential_race_table(
    seq_path: Path | None = None,
    *,
    csv_path: Path | None = None,
    png_path: Path | None = None,
) -> pd.DataFrame:
    df = build_sequential_race_table(seq_path)
    csv_path = csv_path or OUTPUT_CSV
    png_path = png_path or OUTPUT_PNG
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"  saved {csv_path}")
    save_race_table_png(df, png_path)
    return df
