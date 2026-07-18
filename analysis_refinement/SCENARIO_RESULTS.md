# Scenario sensitivity results — cohort-selection refinements

Seven scenarios, one per contemplated change (nothing removed from the
committed pipeline; PI directive: include, don't exclude — compare, then decide).
Model: the existing M4 spec verbatim (`analysis/cox_models.py::formula_m4`).

Regenerate: `./.venv/bin/python analysis_refinement/scenario_runs.py`
then `make_comparison_forest.py`. Figure: `figures/scenario_comparison_forest.png`.

## Scenarios and cohort sizes

| Scenario | Change | N | Events (%) |
|---|---|--:|--:|
| S0 baseline | current spec | 17,609 | 10,894 (61.9%) |
| S1 all races | small groups pooled → 'Other'; 'Unknown' kept | 18,682 | 11,542 (61.8%) |
| S2 + undocumented insurance | 'undocumented' kept as level | 29,768 | 16,885 (56.7%) |
| S3 pain=0 valid | zeros count as documentation/events | 23,823 | 18,566 (77.9%) |
| S4 text = reassessed | text entry after initial score counts as event | 17,621 | 11,487 (65.2%) |
| S5 trauma only | AP dropped (framing probe; AP stays ONE group otherwise) | 16,322 | 9,989 (61.2%) |
| S6 all inclusive | S1+S2+S3+S4 | 42,405 | 31,403 (74.1%) |

S0 here is 17,609 vs the pipeline's 17,204 (~2%): this builder sources events
from the raw extract rather than the pre-filtered `pain_events.csv`; scenarios
are internally consistent with each other, which is what the comparison needs.

## Key M4 hazard ratios across scenarios (HR > 1 = faster reassessment)

| Term | S0 | S2 (+undoc ins) | S3 (pain=0) | S5 (trauma) | S6 (all) |
|---|---|---|---|---|---|
| Black vs White | 0.99 (0.94–1.04) | 0.97 (0.93–1.01) | 1.03 (0.99–1.07) | 1.00 (0.95–1.06) | 0.99 (0.96–1.02) |
| Hispanic vs White | 1.08 (0.99–1.17) | 1.04 (0.98–1.11) | 1.07 (1.00–1.14) | 1.09 (1.00–1.19) | 0.99 (0.94–1.04) |
| Asian vs White | **0.87 (0.77–0.99)** | 0.93 (0.86–1.01) | **1.03 (0.95–1.12)** | 0.88 (0.77–0.99) | **1.05 (0.99–1.11)** |
| Medicaid vs private | 0.83 (0.79–0.88) | 0.83 (0.79–0.88) | 0.83 (0.79–0.86) | 0.83 (0.78–0.88) | 0.87 (0.84–0.91) |
| Medicare vs private | 0.89 (0.84–0.94) | 0.91 (0.87–0.96) | 0.91 (0.87–0.95) | 0.88 (0.83–0.93) | **0.99 (0.95–1.03)** |
| undocumented vs private | — | 0.94 (0.86–1.02) | — | — | 0.92 (0.87–0.99) |
| non-English vs English | 0.95 (0.88–1.03) | 0.95 (0.88–1.02) | 0.92 (0.87–0.98) | 0.94 (0.87–1.02) | 0.99 (0.94–1.04) |

Full term-level table: `outputs/scenario_m4_terms.csv`; scenario stats:
`outputs/scenario_summary.csv`; per-scenario composition: `outputs/composition_*.json`.

## Reading

**Robust to every selection choice:**
- **Medicaid vs private: 0.83–0.87 in all seven scenarios.** The headline
  disparity finding survives every cohort-provenance decision. This is the
  strongest possible answer to the PI's "recipe for experience associations"
  concern.
- Black vs White: consistently null (0.97–1.03).

**Sensitive to selection choices (flagged for discussion):**
- **Asian vs White flips sign**: 0.87 (slower) under baseline → 1.03–1.05 (null/
  faster) when pain=0 documentation counts (S3, S6). The apparent Asian
  disparity partly rides on how zero scores are handled. Do not headline it.
- **Medicare vs private attenuates to null in S6** (0.89 → 0.99), consistent
  with the undocumented-insurance exclusion having enriched the baseline cohort
  for admitted (older, sicker) patients.
- Hispanic vs White: borderline ~1.08 → null in S6.

**Other findings along the way:**
- **No duplicate conflicts**: zero same-stay same-timestamp rows with
  conflicting numeric scores in the raw extract (`explore_raw_pain.py`) — the
  0-vs-number duplication concern is empirically resolved.
- **Text pain entries** (raw extract, before any filtering): 15,564 rows (11.7%)
  across 7,317 stays. Draft taxonomy: complications 6,666 (unable/UTA/critical/
  sedated/intubated), not_reassessed 5,273 (sleeping/asleep/refused), and 3,625
  unclassified — full value list in `outputs/text_pain_values.csv`; range values
  like "3-4" (≈400 rows) could be salvaged as midpoints.
- **Single-score stays** (kept + censored everywhere, per PI): disposition
  explains few of them — only 3.4% eloped/LWBS/AMA/expired/transfer; 94.7% of
  LWBS and 75.8% of eloped stays are single-score (sanity check passes), but
  the bulk of single-score stays are HOME (50.6% of HOME stays) — fast
  discharges. Full crosstab: `outputs/single_score_by_disposition.csv`.
  In every scenario, only ~3.5–5.3% of censored stays have a structural
  disposition reason.

## Recommendation (for discussion with PI)

1. Adopt **S6-style inclusion as the primary** (or S2 at minimum): the biggest
   current exclusion (undocumented insurance, 40% of extract) is a selection
   mechanism, not a data-quality issue. Keeping it as a level preserves
   representativeness and the Medicaid finding is unchanged.
2. Report S0 (current) as a sensitivity, not the primary — the reviewers'
   version of "provenance before modeling."
3. Treat pain=0 handling (S3) as a **pre-specified secondary definition** and
   soften any Asian-disparity language: it is definition-dependent.
4. Keep AP pooled as one group (done); trauma-only (S5) changes nothing
   materially, so there is no statistical need to drop AP.
5. Use censoring-reason (structural vs not) as a competing-risk robustness
   check (Fine-Gray with eloped/LWBS/AMA/expired/transfer as competing events).

## Next steps for a public health journal framing

**Strengthen the exposure story, not the model count.**
- Lead with the *documentation-as-process* framing: pain reassessment is a
  measurable process-of-care metric with an equity gradient. The Medicaid HR
  (0.83–0.87, invariant across all seven cohort definitions) is the paper; the
  scenario grid is the robustness appendix that pre-empts the "selection built
  your finding" review.
- Report the STROBE-style flow diagram from `outputs/exclusion_cascade.csv`
  with *who* was excluded at each step (composition JSONs), not just counts —
  this directly answers the PI's provenance concern and is what public health
  reviewers look for first.
- New observation worth featuring: in S2/S6, **undocumented language shows
  HR > 1 (1.11–1.18)** — likely an admission/documentation artifact, useful as
  a worked example of why the undocumented strata belong in the cohort rather
  than dropped.

**Analyses to add (in rough priority order):**
1. Fine-Gray competing risks (structural censoring: eloped/LWBS/AMA/expired/
   transfer) — machinery already exists (`docs/tab_S_finegray.csv`).
2. E-value for the Medicaid HR — cheap, standard for observational equity
   claims, quantifies how much unmeasured confounding would be needed.
3. Absolute-scale estimates: adjusted probability of reassessment by 60/120 min
   per insurance group (the `reassessed_by_*` flags exist). Public health
   journals want absolute differences, not only HRs.
4. Text-pain entries as a descriptive table (complications vs not-reassessed
   taxonomy from `outputs/text_pain_values.csv`) — frame as "what structured
   fields hide," a documentation-equity point in its own right.
5. Multiple imputation for ESI/vitals missingness instead of complete-case, or
   at minimum a missingness-pattern table by race/insurance.

**Things to stop doing:**
- Don't headline the Asian–White contrast (definition-dependent, flips with
  pain=0 handling). Report it as sensitive-to-specification.
- Don't subgroup pancreatitis (settled: one group; S5 shows trauma-only
  changes nothing).
- Avoid over-fitting the M1–M6 ladder in the main text; M4 + the scenario grid
  + one absolute-scale figure carries the argument.
