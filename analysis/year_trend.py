"""Year/temporal trend: era reassessment probabilities (fig07); continuous HR in tables."""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from lifelines import CoxPHFitter

from analysis.cox_fit import extract_terms, fit_cox
from analysis.cox_models import formula_m4
from analysis.prep_cohort import prep_analytic_cohort

NULL_CONCLUSION = (
    "No evidence of secular change in reassessment timing over the study period."
)


def formula_m4_year_continuous(df: pd.DataFrame) -> str:
    """M4 with calendar year (continuous) instead of categorical year_era."""
    parts = [p.strip() for p in formula_m4(df).split(" + ") if "year_era" not in p]
    return " + ".join(parts) + " + year"


def _era_start(era: str) -> int:
    m = re.search(r"(\d{4})", str(era))
    return int(m.group(1)) if m else 0


def fit_m4_continuous_year(df: pd.DataFrame) -> tuple[CoxPHFitter | None, pd.DataFrame, str]:
    use = df[df["year"].notna()].copy() if "year" in df.columns else pd.DataFrame()
    if len(use) < 200:
        return None, pd.DataFrame(), ""
    formula = formula_m4_year_continuous(use)
    cph = fit_cox(use, formula)
    if cph is None:
        return None, pd.DataFrame(), formula

    rows = extract_terms(cph, model="M4_year_continuous", model_label="M4 + year (continuous)", formula=formula)
    out = pd.DataFrame(rows)
    yr = out[out["term"] == "year"]
    if yr.empty:
        return cph, pd.DataFrame(), formula

    r = yr.iloc[0]
    hr1 = float(r["hazard_ratio"])
    lo1 = float(r["ci_low"])
    hi1 = float(r["ci_high"])
    summary = pd.DataFrame(
        [
            {
                "term": "year",
                "coef_log_hr": float(r["coef"]),
                "hazard_ratio_per_1_year": hr1,
                "ci_low_per_1_year": lo1,
                "ci_high_per_1_year": hi1,
                "pvalue_per_1_year": float(r["pvalue"]),
                "hazard_ratio_per_5_years": hr1**5 if hr1 > 0 else np.nan,
                "ci_low_per_5_years": lo1**5 if lo1 > 0 else np.nan,
                "ci_high_per_5_years": hi1**5 if hi1 > 0 else np.nan,
                "n": int(r["n"]),
                "n_events": int(r["n_events"]),
                "formula": formula,
            }
        ]
    )
    return cph, summary, formula


def _is_null_year_effect(summary: pd.DataFrame) -> bool:
    if summary.empty:
        return True
    r = summary.iloc[0]
    hr5 = r["hazard_ratio_per_5_years"]
    lo = r["ci_low_per_5_years"]
    hi = r["ci_high_per_5_years"]
    if not np.isfinite(hr5):
        return True
    return bool(lo <= 1 <= hi) and 0.9 <= hr5 <= 1.1


def unadjusted_era_descriptive(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    if "year_era" not in df.columns:
        return pd.DataFrame(), {}
    tab = (
        df.groupby("year_era", observed=True)
        .agg(
            n=("reassessment_event", "size"),
            pct_reassessed_60=("reassessed_by_60", "mean"),
        )
        .reset_index()
    )
    tab["era_start"] = tab["year_era"].map(_era_start)
    tab = tab.sort_values("era_start")
    tab["unadj_pct_reassessed_60"] = tab["pct_reassessed_60"] * 100

    trend_meta: dict[str, float] = {}
    x = tab["era_start"].astype(float).values
    y = tab["unadj_pct_reassessed_60"].astype(float).values
    if len(x) >= 3:
        slope, _intercept, r_val, p_trend, _se = stats.linregress(x, y)
        trend_meta = {
            "linear_trend_slope_pct_per_year": float(slope),
            "linear_trend_r": float(r_val),
            "linear_trend_p": float(p_trend),
        }
    return tab, trend_meta


def _formula_m4_logistic_era(df: pd.DataFrame) -> str:
    """M4 covariates with categorical year_era for adjusted P(reassessed≤60)."""
    parts = [p.strip() for p in formula_m4(df).split(" + ") if "year_era" not in p]
    return 'reassessed_by_60 ~ C(Q("year_era")) + ' + " + ".join(parts)


def era_unadjusted_with_ci(df: pd.DataFrame) -> pd.DataFrame:
    if "year_era" not in df.columns:
        return pd.DataFrame()
    rows = []
    for era, grp in df.groupby("year_era", observed=True):
        n = len(grp)
        k = int(grp["reassessed_by_60"].sum()) if "reassessed_by_60" in grp.columns else 0
        pct = 100.0 * k / n if n else np.nan
        if n > 0:
            lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
            lo, hi = lo * 100, hi * 100
        else:
            lo, hi = np.nan, np.nan
        rows.append(
            {
                "year_era": era,
                "era_start": _era_start(era),
                "n": n,
                "unadj_pct": pct,
                "unadj_ci_low": lo,
                "unadj_ci_high": hi,
            }
        )
    tab = pd.DataFrame(rows).sort_values("era_start")
    return tab


def era_m4_adjusted_with_ci(df: pd.DataFrame, *, n_boot: int = 80) -> pd.DataFrame:
    """M4-adjusted marginal P(reassessed≤60) by era; bootstrap CIs (fixed coefficients)."""
    use = df[df["year_era"].notna() & df["reassessed_by_60"].notna()].copy()
    if len(use) < 300 or use["year_era"].nunique() < 2:
        return pd.DataFrame()

    formula = _formula_m4_logistic_era(use)
    try:
        model = smf.logit(formula, data=use).fit(disp=0, maxiter=150, method="bfgs")
    except Exception:
        return pd.DataFrame()

    eras = sorted(use["year_era"].unique(), key=_era_start)
    rows = []
    rng = np.random.default_rng(42)
    boot_n = min(3000, len(use))

    for era in eras:
        d = use.copy().reset_index(drop=True)
        d["year_era"] = era
        adj_pct = float(model.predict(d).mean() * 100)

        boot = []
        for _ in range(n_boot):
            idx = rng.choice(len(use), size=boot_n, replace=True)
            ds = use.iloc[idx].copy().reset_index(drop=True)
            ds["year_era"] = era
            boot.append(float(model.predict(ds).mean() * 100))
        adj_lo, adj_hi = np.percentile(boot, [2.5, 97.5])

        rows.append(
            {
                "year_era": era,
                "era_start": _era_start(era),
                "adj_pct": adj_pct,
                "adj_ci_low": float(adj_lo),
                "adj_ci_high": float(adj_hi),
            }
        )
    return pd.DataFrame(rows)


def plot_fig07_era_reassessment_trend(era_tab: pd.DataFrame, path: Path) -> None:
    """Main temporal figure: unadjusted vs M4-adjusted P(reassessed≤60 min) by era."""
    need = {"unadj_pct", "unadj_ci_low", "unadj_ci_high", "adj_pct", "adj_ci_low", "adj_ci_high"}
    if era_tab.empty or not need.issubset(era_tab.columns):
        return

    tab = era_tab.sort_values("era_start")
    x = np.arange(len(tab))
    width = 0.36

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(
        x - width / 2,
        tab["unadj_pct"],
        width,
        yerr=[
            tab["unadj_pct"] - tab["unadj_ci_low"],
            tab["unadj_ci_high"] - tab["unadj_pct"],
        ],
        label="Unadjusted % ≤60 min",
        color="coral",
        alpha=0.85,
        capsize=4,
        error_kw={"elinewidth": 1},
    )
    valid_adj = tab["adj_pct"].notna()
    if valid_adj.any():
        ax.errorbar(
            x[valid_adj] + width / 2,
            tab.loc[valid_adj, "adj_pct"],
            yerr=[
                tab.loc[valid_adj, "adj_pct"] - tab.loc[valid_adj, "adj_ci_low"],
                tab.loc[valid_adj, "adj_ci_high"] - tab.loc[valid_adj, "adj_pct"],
            ],
            fmt="o",
            color="steelblue",
            capsize=4,
            markersize=8,
            label="M4-adjusted predicted % ≤60 min",
            linestyle="none",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(tab["year_era"].astype(str), rotation=30, ha="right")
    ax.set_ylabel("% reassessed within 60 minutes")
    ymax = max(
        tab["unadj_ci_high"].max(skipna=True),
        tab["adj_ci_high"].max(skipna=True) if valid_adj.any() else 0,
    )
    ax.set_ylim(0, min(100, float(ymax) * 1.12 + 3))
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title(
        "Temporal trend in 60-minute pain reassessment by anchor-year era\n"
        "(unadjusted observed rates vs M4-adjusted predicted probabilities)",
        fontweight="bold",
        fontsize=11,
    )
    for i, (_, r) in enumerate(tab.iterrows()):
        ax.text(i - width / 2, -2.5, f"n={int(r['n']):,}", ha="center", fontsize=7, color="#555")

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_era_descriptive_appendix(
    tab: pd.DataFrame, path: Path, *, trend_meta: dict[str, float] | None = None
) -> None:
    if tab.empty:
        return
    tab = tab.sort_values("era_start")
    x = np.arange(len(tab))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x, tab["unadj_pct_reassessed_60"], color="coral", alpha=0.85, label="Unadjusted % ≤60 min")
    ax.set_xticks(x)
    ax.set_xticklabels(tab["year_era"].astype(str), rotation=30, ha="right")
    ax.set_ylabel("% reassessed ≤60 min")
    ax.set_ylim(0, min(100, tab["unadj_pct_reassessed_60"].max() * 1.15 + 5))
    p_trend = (trend_meta or {}).get("linear_trend_p", np.nan)
    subtitle = f"Linear trend across eras: p={p_trend:.3g}" if np.isfinite(p_trend) else ""
    ax.set_title(
        "Appendix: unadjusted 60-minute reassessment by policy era\n" + subtitle,
        fontweight="bold",
        fontsize=10,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _fit_spline_logistic(df: pd.DataFrame) -> tuple[object | None, bool]:
    """Restricted cubic spline (3 df) for year; return model and whether pattern is meaningful."""
    use = df[df["year"].notna() & df["reassessed_by_60"].notna()].copy()
    if len(use) < 300 or use["year"].nunique() < 4:
        return None, False

    cov = formula_m4_year_continuous(use).replace(" + year", "")
    formula_lin = f"reassessed_by_60 ~ year + {cov}"
    formula_spl = f"reassessed_by_60 ~ cr(year, df=3) + {cov}"

    try:
        m_lin = smf.logit(formula_lin, data=use).fit(disp=0, maxiter=120, method="bfgs")
        m_spl = smf.logit(formula_spl, data=use).fit(disp=0, maxiter=120, method="bfgs")
    except Exception:
        return None, False

    try:
        lr_stat = 2 * (m_spl.llf - m_lin.llf)
        lr_p = float(stats.chi2.sf(lr_stat, df=2))
    except Exception:
        lr_p = 1.0

    meaningful = lr_p < 0.05
    if meaningful:
        pred_range = _spline_prediction_range(m_spl, use)
        if pred_range < 3.0:
            meaningful = False
    return (m_spl if meaningful else None), meaningful


def _spline_prediction_range(model, df: pd.DataFrame) -> float:
    years = np.linspace(df["year"].quantile(0.05), df["year"].quantile(0.95), 50)
    grid = df.sample(min(500, len(df)), random_state=1).copy()
    preds = []
    for y in years:
        g = grid.copy()
        g["year"] = y
        try:
            preds.append(float(model.predict(g).mean()) * 100)
        except Exception:
            continue
    if len(preds) < 2:
        return 0.0
    return float(max(preds) - min(preds))


def plot_spline_appendix(model, df: pd.DataFrame, path: Path) -> None:
    years = np.linspace(df["year"].min(), df["year"].max(), 80)
    grid = df[df["year"].notna()].sample(min(800, len(df)), random_state=2).copy()
    preds = []
    for y in years:
        g = grid.copy()
        g["year"] = y
        try:
            preds.append(float(model.predict(g).mean()) * 100)
        except Exception:
            preds.append(np.nan)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(years, preds, color="steelblue", lw=2)
    ax.set_xlabel("Anchor year (de-identified)")
    ax.set_ylabel("Adjusted P(reassessed ≤60 min)")
    ax.set_title(
        "Appendix: spline-adjusted reassessment probability vs year\n"
        "(M4 covariates; restricted cubic spline, 3 df)",
        fontweight="bold",
        fontsize=10,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _write_year_summary(
    summary: pd.DataFrame,
    era_tab: pd.DataFrame,
    trend_meta: dict[str, float],
    *,
    null_effect: bool,
    spline_used: bool,
) -> None:
    lines = ["# Year trend analysis (M4 + continuous year)\n"]
    if summary.empty:
        lines.append("Continuous-year model did not converge.\n")
    else:
        r = summary.iloc[0]
        lines.append(
            f"- HR per 1-year increase: {r['hazard_ratio_per_1_year']:.4f} "
            f"(95% CI {r['ci_low_per_1_year']:.4f}–{r['ci_high_per_1_year']:.4f}); "
            f"p={r['pvalue_per_1_year']:.4g}\n"
        )
        lines.append(
            f"- HR per 5-year increase: {r['hazard_ratio_per_5_years']:.4f} "
            f"(95% CI {r['ci_low_per_5_years']:.4f}–{r['ci_high_per_5_years']:.4f})\n"
        )
        lines.append(f"- log(HR) coefficient (per year): {r['coef_log_hr']:.5f}\n")
        if null_effect:
            lines.append(f"\n**Conclusion:** {NULL_CONCLUSION}\n")
        else:
            lines.append("\n**Conclusion:** Evidence of association between year and reassessment timing (see fig07).\n")

    if trend_meta.get("linear_trend_p") is not None:
        p = trend_meta["linear_trend_p"]
        lines.append(
            f"\nUnadjusted linear trend across eras (% reassessed ≤60 min vs era start year): p={p:.4g}\n"
        )
    if spline_used:
        lines.append("\nNonlinear year pattern detected; see appendix spline figure.\n")
    else:
        lines.append("\nSpline sensitivity: linear year term adequate (spline figure not shown).\n")

    (MANUSCRIPT_DIR / "year_trend_summary.md").write_text("".join(lines))


def run_year_trend(
    df: pd.DataFrame | None = None,
    m4: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    del m4  # refit M4 with continuous year
    df = prep_analytic_cohort() if df is None else df
    tables_dir = MANUSCRIPT_DIR / "tables"
    appendix_dir = MANUSCRIPT_DIR / "appendix"
    tables_dir.mkdir(parents=True, exist_ok=True)
    appendix_dir.mkdir(parents=True, exist_ok=True)

    _cph, summary, _formula = fit_m4_continuous_year(df)
    summary.to_csv(tables_dir / "table_year_continuous_model.csv", index=False)
    summary.to_csv(ANALYSIS_OUT / "year_continuous_model.csv", index=False)

    null_effect = _is_null_year_effect(summary)

    unadj = era_unadjusted_with_ci(df)
    adj = era_m4_adjusted_with_ci(df)
    era_plot = unadj.merge(adj, on=["year_era", "era_start"], how="left") if not unadj.empty else pd.DataFrame()

    if not era_plot.empty:
        era_plot.to_csv(tables_dir / "table07_era_reassessment_probabilities.csv", index=False)
        era_plot.to_csv(ANALYSIS_OUT / "year_era_reassessment_probabilities.csv", index=False)
        plot_fig07_era_reassessment_trend(era_plot, MANUSCRIPT_DIR / "fig07_year_era_reassessment_trend.png")
        # Legacy filename alias
        plot_fig07_era_reassessment_trend(era_plot, MANUSCRIPT_DIR / "fig07_year_continuous_trend.png")

    era_tab, trend_meta = unadjusted_era_descriptive(df)
    if not era_tab.empty:
        era_export = era_tab[["year_era", "era_start", "n", "unadj_pct_reassessed_60"]].copy()
        era_export.to_csv(tables_dir / "table07_unadjusted_era_reassessment.csv", index=False)
        era_export.to_csv(ANALYSIS_OUT / "year_unadjusted_by_era.csv", index=False)
        if trend_meta:
            pd.DataFrame([trend_meta]).to_csv(tables_dir / "table07_era_linear_trend_test.csv", index=False)
        plot_era_descriptive_appendix(
            era_tab, appendix_dir / "figA_unadjusted_reassessment_by_era.png", trend_meta=trend_meta
        )

    spline_model, spline_used = _fit_spline_logistic(df)
    if spline_model is not None and spline_used:
        plot_spline_appendix(spline_model, df, appendix_dir / "figA_year_spline_reassessment_probability.png")

    _write_year_summary(
        summary, era_tab, trend_meta, null_effect=null_effect, spline_used=spline_used
    )

    return {
        "continuous": summary,
        "era_probabilities": era_plot,
        "era_descriptive": era_tab,
        "null_effect": pd.DataFrame([{"null_secular_change": null_effect}]),
    }
