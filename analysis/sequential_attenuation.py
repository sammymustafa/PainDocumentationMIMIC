"""Sequential M1–M4 attenuation plot (fig08) and workflow supplement (appendix)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.term_utils import pick_term_row

MODEL_ORDER = ["M1", "M2", "M3", "M4"]
MODEL_LABELS = {
    "M1": "M1 clinical",
    "M2": "M2 + social",
    "M3": "M3 + severity",
    "M4": "M4 primary",
}

# Main fig08: primary disparity variables only.
KEY_FACTORS: list[tuple[str, dict]] = [
    ("Black vs White", {"term_contains": "race_ethnicity", "level": "Black"}),
    ("Hispanic vs White", {"term_contains": "race_ethnicity", "level": "Hispanic"}),
    ("Asian vs White", {"term_contains": "race_ethnicity", "level": "Asian"}),
    ("Medicaid vs private", {"term_contains": "insurance_group", "level": "Medicaid"}),
    ("Medicare vs private", {"term_contains": "insurance_group", "level": "Medicare"}),
    ("Initial pain (per unit)", {"exact_term": "initial_pain_score"}),
]

# Appendix supplement: workflow variables across M1–M4 (M4 only for workflow terms).
WORKFLOW_FACTORS: list[tuple[str, dict]] = [
    ("Ambulance vs walk-in", {"term_contains": "arrival_mode", "level": "ambulance"}),
    ("Night vs day shift", {"term_contains": "arrival_shift", "level": "night"}),
    ("Weekend vs weekday", {"exact_term": "arrival_weekend"}),
]


def build_attenuation_table(
    sequential: pd.DataFrame,
    factors: list[tuple[str, dict]] | None = None,
) -> pd.DataFrame:
    factors = KEY_FACTORS if factors is None else factors
    rows = []
    for factor_label, kwargs in factors:
        for model in MODEL_ORDER:
            r = pick_term_row(sequential, model, **kwargs)
            if r is None:
                rows.append(
                    {
                        "factor": factor_label,
                        "model": model,
                        "model_label": MODEL_LABELS.get(model, model),
                        "term": "",
                        "comparison": "",
                        "hazard_ratio": np.nan,
                        "ci_low": np.nan,
                        "ci_high": np.nan,
                        "pvalue": np.nan,
                        "in_model": False,
                    }
                )
                continue
            rows.append(
                {
                    "factor": factor_label,
                    "model": model,
                    "model_label": MODEL_LABELS.get(model, model),
                    "term": r["term"],
                    "comparison": r.get("comparison", ""),
                    "hazard_ratio": r["hazard_ratio"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                    "pvalue": r["pvalue"],
                    "in_model": True,
                }
            )
    return pd.DataFrame(rows)


def plot_attenuation(
    table: pd.DataFrame,
    path: Path,
    *,
    suptitle: str,
    ncols: int = 3,
) -> None:
    factors = table["factor"].unique()
    n_f = len(factors)
    ncols = min(ncols, n_f) if n_f else ncols
    nrows = int(np.ceil(n_f / ncols)) if n_f else 1
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 3.2 * nrows), squeeze=False)
    x = np.arange(len(MODEL_ORDER))

    for ax, factor in zip(axes.flatten(), factors):
        sub = table[table["factor"] == factor]
        hrs, lo, hi = [], [], []
        for m in MODEL_ORDER:
            row = sub[sub["model"] == m]
            if row.empty or not row.iloc[0]["in_model"]:
                hrs.append(np.nan)
                lo.append(np.nan)
                hi.append(np.nan)
            else:
                r = row.iloc[0]
                hrs.append(r["hazard_ratio"])
                lo.append(r["ci_low"])
                hi.append(r["ci_high"])
        hrs = np.array(hrs, dtype=float)
        valid = np.isfinite(hrs)
        if valid.any():
            ax.errorbar(
                x[valid],
                hrs[valid],
                yerr=[hrs[valid] - np.array(lo)[valid], np.array(hi)[valid] - hrs[valid]],
                fmt="o-",
                capsize=3,
                color="steelblue",
            )
        ax.axhline(1, color="gray", ls="--", lw=1)
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], rotation=35, ha="right", fontsize=7)
        ax.set_title(factor, fontsize=9, fontweight="bold")
        ax.set_ylabel("HR")

    for ax in axes.flatten()[n_f:]:
        ax.axis("off")

    fig.suptitle(suptitle, fontweight="bold", fontsize=12)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run_sequential_attenuation(sequential: pd.DataFrame | None = None) -> pd.DataFrame:
    if sequential is None:
        p = ANALYSIS_OUT / "sequential_cox_hr.csv"
        if not p.exists():
            return pd.DataFrame()
        sequential = pd.read_csv(p)

    table = build_attenuation_table(sequential, KEY_FACTORS)
    workflow_table = build_attenuation_table(sequential, WORKFLOW_FACTORS)

    tables_dir = MANUSCRIPT_DIR / "tables"
    appendix_dir = MANUSCRIPT_DIR / "appendix"
    tables_dir.mkdir(parents=True, exist_ok=True)
    appendix_dir.mkdir(parents=True, exist_ok=True)

    table.to_csv(tables_dir / "table08_sequential_attenuation.csv", index=False)
    table.to_csv(ANALYSIS_OUT / "sequential_attenuation_key_factors.csv", index=False)
    workflow_table.to_csv(appendix_dir / "table_sequential_workflow_attenuation.csv", index=False)

    if not table.empty:
        plot_attenuation(
            table,
            MANUSCRIPT_DIR / "fig08_sequential_attenuation_key_factors.png",
            suptitle=(
                "Sequential attenuation M1–M4: race, insurance, and initial pain\n"
                "(HR > 1 faster reassessment; disposition analyzed separately)"
            ),
            ncols=3,
        )

    if not workflow_table.empty:
        plot_attenuation(
            workflow_table,
            appendix_dir / "figA_sequential_workflow_attenuation.png",
            suptitle="Appendix: sequential attenuation for ED workflow variables (M1–M4)",
            ncols=3,
        )

    return table
