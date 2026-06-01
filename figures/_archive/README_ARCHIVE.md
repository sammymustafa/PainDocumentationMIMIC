# Archived figure outputs

These folders were superseded by the manuscript pipeline (`figures/manuscript/`).

| Legacy path | Superseded by |
|-------------|----------------|
| `legacy_01_kaplan_meier` | `manuscript/fig04_km_reassessment_overview.png` |
| `legacy_02_main_cox_forest` (M6) | `manuscript/fig06_m5_all_factor_forest.png` |
| `legacy_03_sequential_cox` | Removed (sequential plots no longer generated) |
| `legacy fig06a–h` | `manuscript/fig06_m5_sectional_forest.png` |
| `sequential/`, old `pain_strata/` KM & single-score | `pain_strata/forest_primary_pain_{1-3,4-6,7-10}.png` only |
| `legacy_part2` (race-only within-acuity) | `manuscript/fig09_*`, `fig10_*` |
| `legacy_tables` | `manuscript/tables/` |
| `legacy_table1_by_race.*` | `manuscript/tables/table1_cohort_overview.*` |

Regenerate primary outputs: `python scripts/run_analysis.py`
