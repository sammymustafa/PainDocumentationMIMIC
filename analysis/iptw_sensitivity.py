"""IPTW sensitivity: Medicaid vs private (primary); Black vs White if feasible."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.cox_fit import DURATION_COL, EVENT_COL
from analysis.cox_models import formula_iptw_ps
from analysis.prep_cohort import prep_analytic_cohort

MIN_N = 200
MIN_EVENTS = 40


def _smd(x: pd.Series, t: pd.Series) -> float:
    g1, g0 = x[t == 1], x[t == 0]
    if len(g1) < 2 or len(g0) < 2:
        return np.nan
    v1, v0 = g1.var(), g0.var()
    pooled = np.sqrt((v1 + v0) / 2)
    if pooled == 0 or not np.isfinite(pooled):
        return 0.0
    return float((g1.mean() - g0.mean()) / pooled)


def _balance_table(df: pd.DataFrame, treat: pd.Series, covariates: list[str]) -> pd.DataFrame:
    rows = []
    for col in covariates:
        if col not in df.columns:
            continue
        use = df[[col]].copy()
        if use[col].dtype == object or str(use[col].dtype) == "category":
            dummies = pd.get_dummies(use[col], drop_first=True)
            for c in dummies.columns:
                s = dummies[c].astype(float)
                rows.append(
                    {
                        "covariate": f"{col}:{c}",
                        "smd_unweighted": _smd(s, treat),
                    }
                )
        else:
            s = pd.to_numeric(use[col], errors="coerce")
            rows.append({"covariate": col, "smd_unweighted": _smd(s, treat)})
    return pd.DataFrame(rows)


def _ps_formula(df: pd.DataFrame, *, exclude_col: str) -> str:
    base = formula_iptw_ps(df)
    return " + ".join(p for p in base.split(" + ") if exclude_col not in p)


def _run_iptw_exposure(
    df: pd.DataFrame,
    *,
    exposure_id: str,
    exposure_col: str,
    treated_value: str,
    reference_label: str,
) -> pd.DataFrame | None:
    ps_formula = _ps_formula(df, exclude_col=exposure_col)

    if exposure_col == "insurance_group":
        use = df[df["insurance_group"].isin(["Medicaid", "private"])].copy()
        use["tx"] = (use["insurance_group"] == "Medicaid").astype(int)
        p_treat = use["tx"].mean()
    else:
        use = df[df["race_ethnicity"].isin(["Black", "White"])].copy()
        use["tx"] = (use["race_ethnicity"] == "Black").astype(int)
        p_treat = use["tx"].mean()

    if len(use) < MIN_N or use["tx"].sum() < 30:
        return None

    try:
        logit = smf.logit(f"tx ~ {ps_formula}", data=use).fit(disp=0, maxiter=80)
        ps = np.clip(logit.predict(use), 0.05, 0.95)
    except Exception:
        return None

    use["sw"] = np.where(use["tx"] == 1, p_treat / ps, (1 - p_treat) / (1 - ps))
    use = use[
        use[DURATION_COL].notna()
        & (use[DURATION_COL] > 0)
        & use[EVENT_COL].notna()
        & np.isfinite(use["sw"])
    ].copy()
    use[EVENT_COL] = use[EVENT_COL].astype(int)
    use["sw"] = use["sw"].clip(0.01, 50)

    cph = CoxPHFitter()
    try:
        cph.fit(
            use,
            duration_col=DURATION_COL,
            event_col=EVENT_COL,
            weights_col="sw",
            formula="tx",
            robust=True,
        )
    except Exception:
        return None

    hr = float(np.exp(cph.params_["tx"]))
    ci = cph.confidence_intervals_.loc["tx"]
    return pd.DataFrame(
        [
            {
                "exposure": exposure_id,
                "comparison": f"{treated_value} vs {reference_label}",
                "hazard_ratio": hr,
                "ci_low": float(np.exp(ci.iloc[0])),
                "ci_high": float(np.exp(ci.iloc[1])),
                "pvalue": float(cph.summary.loc["tx", "p"]),
                "n": len(use),
                "events": int(use[EVENT_COL].sum()),
                "ps_formula": ps_formula,
            }
        ]
    )


def plot_balance(before: pd.DataFrame, path: Path, title: str) -> None:
    if before.empty:
        return
    sub = before.dropna(subset=["smd_unweighted"]).head(25)
    fig, ax = plt.subplots(figsize=(8, max(4, 0.25 * len(sub) + 1)))
    y = np.arange(len(sub))
    ax.barh(y, sub["smd_unweighted"], color="steelblue")
    ax.axvline(0.1, color="coral", ls="--", label="|SMD|=0.1")
    ax.axvline(-0.1, color="coral", ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(sub["covariate"], fontsize=6)
    ax.set_xlabel("Standardized mean difference (unweighted)")
    ax.set_title(title, fontweight="bold", fontsize=9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_iptw_results(results: pd.DataFrame, m4: pd.DataFrame, path: Path) -> None:
    if results.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 3))
    for i, (_, r) in enumerate(results.iterrows()):
        ax.errorbar(
            r["hazard_ratio"],
            i,
            xerr=[[r["hazard_ratio"] - r["ci_low"]], [r["ci_high"] - r["hazard_ratio"]]],
            fmt="o",
            capsize=3,
            label="IPTW Cox",
        )
    ax.axvline(1, color="gray", ls="--")
    ax.set_yticks(range(len(results)))
    ax.set_yticklabels(results["comparison"], fontsize=8)
    ax.set_xlabel("Hazard ratio")
    ax.set_title("IPTW-weighted Cox vs primary M4 (robustness)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run_iptw_sensitivity(df: pd.DataFrame | None = None, m4: pd.DataFrame | None = None) -> pd.DataFrame:
    df = prep_analytic_cohort() if df is None else df
    appendix_dir = MANUSCRIPT_DIR / "appendix"
    tables_dir = MANUSCRIPT_DIR / "tables"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    if m4 is None and (ANALYSIS_OUT / "m4_cox_hr.csv").exists():
        m4 = pd.read_csv(ANALYSIS_OUT / "m4_cox_hr.csv")

    use_ins = df[df["insurance_group"].isin(["Medicaid", "private"])].copy()
    treat_ins = (use_ins["insurance_group"] == "Medicaid").astype(int)
    bal_covs = [
        c
        for c in [
            "initial_pain_score",
            "triage_acuity",
            "age_group",
            "sex",
            "race_ethnicity",
            "injury_group",
            "year",
        ]
        if c in use_ins.columns
    ]
    bal = _balance_table(use_ins, treat_ins, bal_covs)
    plot_balance(
        bal,
        appendix_dir / "fig_iptw_balance_medicaid_private.png",
        "Covariate balance: Medicaid vs private (unweighted SMDs)",
    )

    rows = []
    med = _run_iptw_exposure(
        df,
        exposure_id="medicaid_private",
        exposure_col="insurance_group",
        treated_value="Medicaid",
        reference_label="private",
    )
    if med is not None:
        rows.append(med.iloc[0].to_dict())

    race = _run_iptw_exposure(
        df,
        exposure_id="black_white",
        exposure_col="race_ethnicity",
        treated_value="Black",
        reference_label="White",
    )
    if race is not None:
        rows.append(race.iloc[0].to_dict())

    out = pd.DataFrame(rows)
    out.to_csv(tables_dir / "iptw_medicaid_private_results.csv", index=False)
    out.to_csv(ANALYSIS_OUT / "iptw_results.csv", index=False)
    if not out.empty:
        plot_iptw_results(
            out,
            m4 if m4 is not None else pd.DataFrame(),
            appendix_dir / "fig_iptw_weighted_cox_results.png",
        )
        plot_iptw_results(
            out,
            m4 if m4 is not None else pd.DataFrame(),
            MANUSCRIPT_DIR / "fig15_iptw_sensitivity.png",
        )
    return out
