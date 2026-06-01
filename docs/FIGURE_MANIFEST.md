# Figure and table manifest

## Main manuscript (`figures/manuscript/`)

| Fig | File | Description |
|-----|------|-------------|
| 01 | `fig01_care_pathway_dag.png` | Conceptual pathway (M4 primary; disposition/analgesia separate) |
| 02 | `fig02_cohort_flow.png` | Cohort flow |
| 03 | `fig03_table1_overview.png` | Table 1 |
| 04 | `fig04_km_reassessment_overview.png` | KM curves |
| 05 | `fig05_reassessment_rates_60min.png` | 60-min rates |
| 06 | `fig06_m4_sectional_forest.png` | **M4 primary** (ambulance only; no vitals/other arrival) |
| 07 | `fig07_year_era_reassessment_trend.png` | Unadj + M4-adj P(reassessed≤60 min) by `year_era` |
| 08 | `fig08_sequential_attenuation_key_factors.png` | Sequential **M1–M4** (race, insurance, initial pain) |
| 09 | `fig09_m4_disposition_sensitivity.png` | M4 vs M4+disposition |
| 10 | `fig10_insurance_focused_analysis.png` | Insurance package |
| 11 | `fig11_within_acuity_forests.png` | Within-ESI (race/insurance; no arrival other) |
| 12 | `fig12_severe_pain_sensitivity.png` | Pain 7–10 / 10 sensitivity |
| 13 | `fig13_post_analgesic_pathway.png` | Post-analgesic pathway |
| 14 | `fig14_pain10_esi12_subgroup.png` | Pain=10 & ESI 1–2 |
| 15 | `fig15_iptw_sensitivity.png` | IPTW weighted Cox |

`fig07_year_continuous_trend.png` is an alias of fig07 (legacy name).

## Key tables

- `tables/table07_era_reassessment_probabilities.csv` — unadjusted + M4-adjusted era probabilities
- `tables/table_year_continuous_model.csv` — Cox HR per year (supplement; not main fig07)
- `tables/table08_sequential_attenuation.csv` — disparity attenuation M1–M4
- `tables/table06_m4_sectional_forest.csv`

## Appendix

- `appendix/table_vital_sign_m4_hrs.csv`
- `appendix/table_arrival_mode_other_m4_hrs.csv` — **other vs walk-in** (not in main figures)
- `appendix/figA_sequential_workflow_attenuation.png` — workflow sequential supplement
- `appendix/fig_within_acuity_age_sex_diagnosis_pain.png`
- `appendix/figA_unadjusted_reassessment_by_era.png`
- `appendix/figA_disposition_stratified_m4_forests.png`
- `appendix/fig_iptw_balance_medicaid_private.png`

## Audit

`data/processed/analysis/figure_audit.csv` — figure name, model version, update flag (from pipeline).
