"""Audit manuscript figures against current M1–M4 model specification."""

from __future__ import annotations

import pandas as pd

from analysis.cox_models import (
    M1_CLINICAL,
    M2_DEMO_BASE,
    M3_SEVERITY,
    M4_WORKFLOW,
    formula_m4,
    formula_m4_disposition,
    formula_within_acuity,
    formula_pain10_esi12,
    formula_iptw_ps,
)

# model_version tag for audit log
MODEL_VERSION = "M1-M4_primary_v2"

FIGURE_REGISTRY: list[dict[str, str]] = [
    {
        "figure": "fig01_care_pathway_dag.png",
        "model": "conceptual",
        "variables": "M1–M4 blocks; disposition/analgesia downstream",
        "update": "no",
    },
    {
        "figure": "fig02_cohort_flow.png",
        "model": "cohort",
        "variables": "inclusion/exclusion counts",
        "update": "no",
    },
    {
        "figure": "fig03_table1_overview.png",
        "model": "descriptive",
        "variables": "Table 1 cohort descriptives",
        "update": "no",
    },
    {
        "figure": "fig04_km_reassessment_overview.png",
        "model": "unadjusted KM",
        "variables": "race, insurance, ESI",
        "update": "no",
    },
    {
        "figure": "fig05_reassessment_rates_60min.png",
        "model": "unadjusted",
        "variables": "pain bins × race/insurance",
        "update": "no",
    },
    {
        "figure": "fig06_m4_sectional_forest.png",
        "model": "M4 Cox",
        "variables": "formula_m4; hide vitals; exclude arrival other",
        "update": "yes",
    },
    {
        "figure": "fig07_year_era_reassessment_trend.png",
        "model": "M4 logistic (era)",
        "variables": "unadj + M4-adj P(reassessed≤60min) by year_era",
        "update": "yes",
    },
    {
        "figure": "fig08_sequential_attenuation_key_factors.png",
        "model": "sequential M1–M4",
        "variables": "race, insurance, initial pain only",
        "update": "yes",
    },
    {
        "figure": "fig09_m4_disposition_sensitivity.png",
        "model": "M4 vs M4+disposition",
        "variables": "formula_m4 / formula_m4_disposition; exclude arrival other",
        "update": "yes",
    },
    {
        "figure": "fig10_insurance_focused_analysis.png",
        "model": "M4 + within-acuity",
        "variables": "insurance HRs from formula_m4",
        "update": "no",
    },
    {
        "figure": "fig11_within_acuity_forests.png",
        "model": "formula_within_acuity",
        "variables": "race/insurance focus; exclude arrival other",
        "update": "yes",
    },
    {
        "figure": "fig12_severe_pain_sensitivity.png",
        "model": "M4 within pain strata",
        "variables": "formula_m4 key disparity HRs",
        "update": "no",
    },
    {
        "figure": "fig13_post_analgesic_pathway.png",
        "model": "post-analgesic Cox",
        "variables": "formula_post_analgesic",
        "update": "no",
    },
    {
        "figure": "fig14_pain10_esi12_subgroup.png",
        "model": "formula_pain10_esi12",
        "variables": "parsimonious subgroup model",
        "update": "no",
    },
    {
        "figure": "fig15_iptw_sensitivity.png",
        "model": "IPTW + weighted Cox",
        "variables": "formula_iptw_ps (M1–M3) + M4 outcome",
        "update": "no",
    },
    {
        "figure": "appendix/figA_disposition_stratified_m4_forests.png",
        "model": "M4 within strata",
        "variables": "formula_m4; exclude arrival other",
        "update": "yes",
    },
    {
        "figure": "appendix/figA_unadjusted_reassessment_by_era.png",
        "model": "descriptive",
        "variables": "year_era unadjusted rates",
        "update": "yes",
    },
    {
        "figure": "appendix/figA_sequential_workflow_attenuation.png",
        "model": "sequential M1–M4",
        "variables": "workflow terms only (supplement)",
        "update": "yes",
    },
    {
        "figure": "appendix/fig_within_acuity_age_sex_diagnosis_pain.png",
        "model": "formula_within_acuity",
        "variables": "appendix term heatmap",
        "update": "no",
    },
    {
        "figure": "appendix/figA_interaction_summary.png",
        "model": "M4 interactions",
        "variables": "formula_m4-based interactions",
        "update": "no",
    },
    {
        "figure": "appendix/fig_iptw_balance_medicaid_private.png",
        "model": "IPTW PS",
        "variables": "formula_iptw_ps balance",
        "update": "no",
    },
    {
        "figure": "appendix/fig_iptw_weighted_cox_results.png",
        "model": "IPTW",
        "variables": "weighted Cox vs M4",
        "update": "no",
    },
]


def _formula_summary() -> str:
    parts = {
        "M1": " + ".join(M1_CLINICAL),
        "M2": "M1 + " + " + ".join(M2_DEMO_BASE) + " [+ language]",
        "M3": "M2 + " + " + ".join(M3_SEVERITY) + " [+ comorbidity_count]",
        "M4": "M3 + " + " + ".join(M4_WORKFLOW),
    }
    return "; ".join(f"{k}: {v}" for k, v in parts.items())


def print_figure_audit(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Print audit table; return DataFrame for logging."""
    del df
    rows = []
    for entry in FIGURE_REGISTRY:
        rows.append(
            {
                "figure_name": entry["figure"],
                "model_version": MODEL_VERSION if entry["model"] != "conceptual" else "n/a",
                "model_used": entry["model"],
                "variables_included": entry["variables"],
                "requires_update": entry["update"],
            }
        )
    audit = pd.DataFrame(rows)
    print("\n" + "=" * 72)
    print("FIGURE AUDIT (current Cox specification)")
    print("=" * 72)
    print(f"Model version tag: {MODEL_VERSION}")
    print(f"Primary sequence: {_formula_summary()}")
    print(f"M4 primary formula (template): formula_m4(cohort)")
    print(f"Disposition sensitivity: formula_m4_disposition")
    print(f"Within-acuity: formula_within_acuity")
    print(f"IPTW PS: formula_iptw_ps (M1–M3 only)")
    print("-" * 72)
    print(audit.to_string(index=False))
    n_up = (audit["requires_update"] == "yes").sum()
    print("-" * 72)
    print(f"Figures flagged for regeneration: {n_up} / {len(audit)}")
    print("=" * 72 + "\n")
    return audit


def save_figure_audit(path) -> pd.DataFrame:
    from analysis._paths import ANALYSIS_OUT

    audit = print_figure_audit()
    ANALYSIS_OUT.mkdir(parents=True, exist_ok=True)
    audit.to_csv(path, index=False)
    return audit
