# analysis_refinement/

Scratch workspace for refining the pain-reassessment cohort after PI feedback.
**Nothing here modifies the committed analysis** (`analysis/`, `src/`, `sql/`,
`data/processed/`, `figures/manuscript/`). It is a staging area to understand
the current data-selection workflow and to trial changes before adopting them.

## Contents
- **`DATA_SELECTION_WORKFLOW.md`** — the exact current exclusion cascade, with
  file:line references, drop counts, and who gets excluded at each step. Read
  this first.
- **`RERUN_PLAN.md`** — the PI's notes mapped to concrete code changes and a
  4-run sensitivity matrix (R0–R3) to decide what to adopt.
- **`exclusion_audit.py`** — read-only script that reproduces the cascade and
  characterizes the dropped populations. Run:
  `./.venv/bin/python analysis_refinement/exclusion_audit.py`
- **`explore_raw_pain.py`** — raw-extract audit: text pain values (taxonomy →
  `outputs/text_pain_values.csv`), same-timestamp duplicates, single-score
  stays by disposition.
- **`scenario_runs.py`** — builds each scenario cohort and fits the existing
  M4 spec verbatim; writes `outputs/scenario_summary.csv`,
  `outputs/scenario_m4_terms.csv`, `outputs/composition_*.json`.
- **`make_comparison_forest.py`** — `figures/scenario_comparison_forest.png`.
- **`make_dag_v2.py`** — decomposed DAG → `figures/dag_v2.png`.
- **`SCENARIO_RESULTS.md`** — results + recommendation. Read this second.
- **`outputs/`**, **`figures/`** — generated artifacts (all present).

## Headline findings from the baseline audit
1. **Insurance is the biggest filter:** 12,154 stays dropped solely because
   insurance was `undocumented` (40% of the raw extract). Skews the cohort
   toward admitted patients.
2. **No-pain-score drop:** 13,109 stays had no pain score > 0.
3. **Single-score patients are censored, not excluded** (6,712 = 38% of final
   cohort) — this contradicts the PI's stated assumption and is the key
   methodology decision.

## Status
All seven scenarios (S0–S6) have been run; see `SCENARIO_RESULTS.md` for the
comparison. The R0–R3 matrix in `RERUN_PLAN.md` was superseded by the
finer-grained S0–S6 scenarios. Nothing in the committed pipeline has been changed.

**Adopted (July 2026):** S6 all-inclusive is the primary cohort; S0–S5 are
sensitivity analyses. The final analysis adds Fine–Gray (structural departures
competing), E-values, absolute-scale estimates, the text-pain taxonomy table,
and missingness patterns:
- **`final_analysis.py`** → `outputs/final/` (primary M1–M4 terms, E-values,
  CIF, standardized probabilities, missingness, text taxonomy, Fine-Gray input)
- **`finegray_final.R`** → `outputs/final/finegray_shr.csv` + CIF curves
- **`make_final_figures.py`** → `figures/fig_final_{flow,forest,absolute,cox_vs_fg}.png`
- **`MANUSCRIPT.md`** — full write-up (~3,000 words) with figures and references
