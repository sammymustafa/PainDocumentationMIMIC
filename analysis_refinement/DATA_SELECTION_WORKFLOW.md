# Data selection workflow — exactly what was done

This documents the **current** cohort-selection cascade for the pain-reassessment
analysis (time from first documented pain to first reassessment). It is a
read-only description — no existing code was changed. Numbers below come from
`analysis_refinement/outputs/exclusion_cascade.{csv,json}` (regenerate with
`./.venv/bin/python analysis_refinement/exclusion_audit.py`).

Canonical counts the manuscript reports live in
`data/processed/analysis/flow_counts.json` (produced by
`analysis/prep_cohort.py::compute_flow_counts`). The audit reproduces the same
logic and lands within ~2% (17,535 vs the pipeline's 17,204); the small gap is
the second-score merge + the exact `time_end` duration definition, noted per
step below.

## Where selection happens (3 files)

| Stage | File | What it does |
|-------|------|--------------|
| SQL extract | `sql/pain_phenotypes.sql` | Pulls **only AP-or-trauma ED stays** that have ≥1 non-null pain row |
| Stay filter | `src/cohort_filters.py::filter_stay_cohort` | Diagnosis + small-race exclusions |
| Survival build | `analysis/prep_survival.py::build_survival_cohort` | Positive-pain requirement, race restriction, valid timing |
| Analytic filter | `analysis/prep_cohort.py::prep_analytic_cohort` | Non-missing ESI, insurance restriction |

The SQL already restricts the universe: `cohort_stays` (line 79) keeps a stay
only if `acute_pancreatitis_flag = 1 OR trauma_any_flag = 1`, and the final
`WHERE pe.pain_raw IS NOT NULL` (line 559) means a stay must have at least one
pain **row** (any value, numeric or text) to appear in the extract at all. So
patients who never had *any* pain documented are gone before Python even runs —
they are invisible to the attrition table. That is worth stating explicitly in
the manuscript.

## The exclusion cascade (starting from the 47,783-stay extract)

| # | Criterion | Dropped | Remaining | Source |
|---|-----------|--------:|----------:|--------|
| 0 | AP-or-trauma ED stays with a pain row (SQL extract) | — | 47,783 | `pain_phenotypes.sql` |
| 1 | Diagnosis must be **AP or trauma** (drops mixed `both_ap_and_trauma`) | 10 | 47,773 | `cohort_filters.py:53` |
| 2 | Drop **small race groups** (AI/AN, NH/PI, Two-or-More) | 202 | 47,571 | `cohort_filters.py:52` |
| 3 | Race must be **White / Black / Asian / Hispanic** (drops Unknown/Other) | 4,048 | 43,523 | `prep_survival.py:98` |
| 4 | Must have **≥1 pain score > 0** (pain=0 rows are discarded) | 13,109 | 30,414 | `prep_survival.py:61,97` |
| 5 | **Valid survival time** (initial pain before outtime, duration > 0) | 488 | 29,926 | `prep_survival.py:107` |
| 6 | **Non-missing ESI** (triage acuity numeric) | 237 | 29,689 | `prep_cohort.py:41` |
| 7 | **Insurance in {private, Medicaid, Medicare}** (drops `undocumented`) | 12,154 | 17,535 | `prep_cohort.py:52` |

**Final analytic cohort ≈ 17,204** (canonical) / 17,535 (audit approximation).

## The two exclusions that dominate — "who are they?"

These two steps remove **~25,000 of ~47,000** stays and are the ones the PI
wants characterized.

### Step 4 — no documented pain score > 0 (13,109 dropped)
- Composition: trauma 12,687 / AP 422; race White 9,159, Black 2,301, Hispanic 875, Asian 774.
- These are stays where **every** pain entry was 0, missing, or non-numeric
  ("unable to assess", "refused", text). Because `pain_numeric > 0` is required
  for the *initial* pain event, a patient whose only documented pain was 0 is
  excluded — and a reassessment that returned to 0 is dropped as an event too
  (see subtlety below).

### Step 7 — insurance not documented (12,154 dropped)
- Composition: **all 12,154 have `insurance_group = 'undocumented'`**; trauma 12,058 / AP 96; race White 7,731, Black 2,373, Hispanic 1,095, Asian 955.
- `undocumented` = insurance was NULL on the linked hospital admission
  (`pain_phenotypes.sql:138`). In the raw extract, **19,061 of 47,783 stays
  (40%)** have undocumented insurance — largely ED-only visits that were never
  admitted, so no `admissions` row exists to carry an insurance value.
- This is the single largest and most consequential exclusion. It
  disproportionately removes ED-discharged (non-admitted) patients, which
  **changes cohort composition** exactly as the PI warns — the retained cohort
  is enriched for admitted patients.

## Two subtleties that matter for the PI's notes

1. **Single pain-score patients are NOT excluded — they are censored.**
   The reassessment event is the *second* positive pain score
   (`prep_survival.py:63,95`). A stay with only one positive score gets
   `first_reassessment_time = NaN` → `reassessment_event = 0` and is **censored
   at outtime**, not dropped. In the final cohort, **6,712 stays (38.3%)** have
   exactly one positive pain score.
   → The PI note says "those with only one pain score were excluded." That is
   **not** what the current code does. This is a real decision point: keep them
   as censored (current) vs. exclude them (PI's stated expectation). See
   `RERUN_PLAN.md` item A.

2. **Pain = 0 is treated as "no pain" and discarded.**
   `prep_survival.py:61` filters to `pain_numeric > 0` before finding the first
   and second scores. Consequence: a reassessment where pain dropped to 0 (pain
   resolved) is not counted as a reassessment. Worth deciding whether a
   documented 0 should count as a valid reassessment.

## Diagnosis composition of the raw extract (for the pancreatitis/trauma decision)

- trauma: 45,811 · acute_pancreatitis: 1,962 · both: 10 (dropped).
- AP is ~4% of the raw pool and shrinks further through the cascade (only ~96 AP
  stays are lost at the insurance step, but AP starts small). This supports the
  PI's suggestion that **AP subtype splits (alcohol vs gallstone) will have very
  wide CIs** — see `RERUN_PLAN.md` item C.
