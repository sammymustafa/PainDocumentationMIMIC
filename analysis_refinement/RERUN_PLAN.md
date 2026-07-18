# Rerun plan — mapping PI notes to concrete changes

Goal: rerun the **entire** analysis (models + figures) under candidate
refinements to decide whether to adopt them. Nothing here is applied yet — this
is the decision menu. Each item lists the exact file/line to change and how to
regenerate outputs into `analysis_refinement/` instead of overwriting the
committed results.

## How the rerun will be isolated
- All new outputs → `analysis_refinement/outputs/` and `analysis_refinement/figures/`.
- The existing pipeline writes to `data/processed/` and `figures/manuscript/`
  via `analysis/_paths.py`. The rerun driver (to be written once refinements are
  chosen) will point those paths at the new folder so the committed manuscript
  results are untouched until you approve.
- Baseline is already captured: `outputs/exclusion_cascade.{csv,json}`.

## PI note → change map

### A. Exclusions: document fraction + who (DONE, baseline)
- Delivered by `exclusion_audit.py` → `outputs/exclusion_cascade.{csv,json}`.
- For the manuscript: add the per-step drop counts + dropped-group composition
  (race/insurance/diagnosis) as a STROBE-style supplement. The current
  `flow_counts.json` reports counts but **not** who was dropped.

### B. Single-pain-score patients (the key methodology fix)
- **Current behavior:** kept and censored at outtime (`prep_survival.py:100-103`).
  6,712 stays (38.3% of final cohort).
- **PI expectation:** exclude them (no way to assess reassessment potential).
- **Change:** after building the cohort in `build_survival_cohort`, add an
  optional filter dropping stays where `reassessment_event == 0 AND` only one
  positive pain score exists. Recommend running it as a **sensitivity analysis**
  (primary = censored, sensitivity = excluded) so the reviewer sees both.
- **Impact to check:** event count, median time-to-reassessment, and whether HRs
  move. Losing 38% of stays will widen CIs — quantify.

### C. Pancreatitis vs. trauma framing
- **Option C1 (PI-preferred simple):** frame as **trauma-only**. Drop AP
  entirely. Change `VALID_DIAGNOSIS_TYPES` (`cohort_filters.py:11`) to
  `{"trauma"}` and remove AP arms from figures. Cleanest; AP is only ~4% of the
  pool and adds heterogeneity.
- **Option C2 (sensitivity):** AP subtype split — alcohol-use-disorder vs
  gallstone pancreatitis. Requires new ICD logic in `pain_phenotypes.sql`
  (`ed_diagnoses` CTE) to flag `K85.2` (alcohol) vs `K85.1` (biliary/gallstone).
  **Caveat the PI flagged:** AP n≈1,962 raw and far fewer after the cascade, so
  subtype CIs will likely be too wide to interpret. Recommend computing the
  subtype n's first; only run models if each arm has adequate events.
- **Decision needed from you:** trauma-only (C1) as primary, with AP as an
  appendix sensitivity? Or keep the current AP+trauma pooled primary?

### D. DAG: improve + decompose
- Current DAG source: `docs/manuscript/` (and `figures/manuscript/`). Rebuild
  with finer nodes — separate the collider/mediator structure (disposition,
  analgesia are downstream), split "ED workflow" into crowding / shift / arrival
  mode, and show the insurance→admission→documentation path that the exclusion
  audit exposes.
- This is a figure task; will regenerate into `analysis_refinement/figures/`.

### E. Pain=0 handling (surfaced by the audit, not in PI notes)
- Decide whether a documented pain of 0 should count as a valid reassessment
  (currently discarded, `prep_survival.py:61`). If a return-to-0 is a legitimate
  reassessment, this changes both the event definition and step-4 exclusions.

## Suggested rerun matrix

| Run | Single-score | Diagnosis | Purpose |
|-----|-------------|-----------|---------|
| R0 (baseline) | censored | AP + trauma | reproduce current manuscript |
| R1 | **excluded** | AP + trauma | test PI's single-score expectation |
| R2 | censored | **trauma only** | test simpler framing (C1) |
| R3 | **excluded** | **trauma only** | combined PI-preferred spec |

Each run regenerates: exclusion cascade, Table 1, M1–M4 forest, KM curves,
year trend, disposition/insurance/severe-pain sensitivities. Compare HRs and
event counts across R0–R3 in a single side-by-side table before choosing.

## To execute (once you pick)
Tell me which rows of the matrix to run. I'll write `run_refinement.py` in this
folder that imports the existing analysis modules with the exclusion toggles and
redirected output paths — no edits to the committed pipeline until you approve
the winning spec.
