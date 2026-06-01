"""Cox interaction tests on M4 backbone (appendix)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import INSURANCE, RACE, YEAR_ERA, formula_m4
from analysis.prep_cohort import prep_analytic_cohort

INTERACTION_SPECS: list[tuple[str, str, str]] = [
    ("race_x_esi", "Race × ESI group", f'C(esi_group):{RACE}'),
    ("insurance_x_esi", "Insurance × ESI group", f'C(esi_group):{INSURANCE}'),
    ("year_x_race", "Year era × race", f'{YEAR_ERA}:{RACE}'),
    ("year_x_insurance", "Year era × insurance", f'{YEAR_ERA}:{INSURANCE}'),
]


def _flag_row(hr: float, p: float, ci_low: float, ci_high: float) -> str:
    if not np.isfinite(hr) or not np.isfinite(p):
        return "insufficient_N"
    if ci_low <= 0 or ci_high > 50 or (ci_high / max(ci_low, 1e-6) > 80):
        return "unstable"
    if p >= 0.05:
        return "weak"
    return "stable"


def run_interactions(df: pd.DataFrame | None = None, *, out_dir: Path | None = None) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    out_dir = out_dir or MANUSCRIPT_DIR / "appendix"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = formula_m4(df)
    rows: list[dict] = []

    for test_id, label, ix_term in INTERACTION_SPECS:
        formula = f"{base} + {ix_term}"
        cph = fit_cox(df, formula)
        if cph is None:
            rows.append(
                {
                    "test_id": test_id,
                    "interaction": label,
                    "term": "",
                    "comparison": "",
                    "hazard_ratio": np.nan,
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "pvalue": np.nan,
                    "flag": "insufficient_N",
                    "n": None,
                    "n_events": None,
                    "notes": "Model did not converge or N/events below threshold",
                }
            )
            continue

        terms = extract_terms(cph, model=test_id, formula=formula)
        ix_rows = [t for t in terms if ":" in t["term"]]
        if not ix_rows:
            rows.append(
                {
                    "test_id": test_id,
                    "interaction": label,
                    "term": "",
                    "comparison": "",
                    "hazard_ratio": np.nan,
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "pvalue": np.nan,
                    "flag": "unstable",
                    "n": terms[0]["n"] if terms else None,
                    "n_events": terms[0]["n_events"] if terms else None,
                    "notes": "No interaction terms estimated",
                }
            )
            continue

        for t in ix_rows:
            flag = _flag_row(t["hazard_ratio"], t["pvalue"], t["ci_low"], t["ci_high"])
            rows.append(
                {
                    "test_id": test_id,
                    "interaction": label,
                    "term": t["term"],
                    "comparison": t["comparison"],
                    "hazard_ratio": t["hazard_ratio"],
                    "ci_low": t["ci_low"],
                    "ci_high": t["ci_high"],
                    "pvalue": t["pvalue"],
                    "flag": flag,
                    "n": t["n"],
                    "n_events": t["n_events"],
                    "notes": "",
                }
            )

    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "tableA_interaction_summary.csv", index=False)
    out.to_csv(ANALYSIS_OUT / "interaction_summary.csv", index=False)
    _plot_summary(out, out_dir / "figA_interaction_summary.png")
    return out


def _plot_summary(df: pd.DataFrame, path: Path) -> None:
    if df.empty:
        return
    rank = {"stable": 0, "weak": 1, "unstable": 2, "insufficient_N": 3}

    def _worst_flag(flags: pd.Series) -> str:
        return max(flags, key=lambda x: rank.get(x, 3))

    summary = df.groupby(["test_id", "interaction"], as_index=False).agg(
        min_p=("pvalue", "min"),
        flag=("flag", _worst_flag),
        n_terms=("term", "count"),
    )
    flag_colors = {
        "stable": "#2ca02c",
        "weak": "#ff7f0e",
        "unstable": "#d62728",
        "insufficient_N": "#7f7f7f",
    }
    fig, ax = plt.subplots(figsize=(9, max(3, 0.5 * len(summary) + 1)))
    y = np.arange(len(summary))
    colors = [flag_colors.get(f, "#333") for f in summary["flag"]]
    ax.barh(y, -np.log10(summary["min_p"].clip(1e-6, 1)), color=colors, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(summary["interaction"], fontsize=9)
    ax.axvline(-np.log10(0.05), color="gray", ls="--")
    ax.set_xlabel("−log10(min interaction p-value)")
    ax.set_title("Appendix: interaction tests on M4 backbone", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
