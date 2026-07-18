# Insurance-related differences in the timing of pain reassessment in the emergency department: a retrospective cohort study using MIMIC-IV-ED

*Draft for PI review — refined (inclusive-cohort) analysis, July 2026.*
*Word count ≈ 3,200 (abstract through discussion, excluding tables, references, and captions).*

---

## Abstract

**Background.** Timely reassessment after a documented pain score is a basic element of emergency department (ED) pain care, yet it is rarely measured. Whether reassessment timing differs by insurance, race and ethnicity, or language is not well described.

**Methods.** We conducted a retrospective cohort study of adult ED stays with an acute pancreatitis or trauma diagnosis in MIMIC-IV-ED, a public database from a single US academic center (2011–2019, date-shifted). The outcome was time from the first documented numeric pain score to the first subsequent pain assessment. We deliberately built an inclusive cohort: no stays were excluded for race or ethnicity category, undocumented insurance, a pain score of zero, or having only one pain score (such stays were censored at ED departure). Cause-specific Cox models were adjusted for pain score, diagnosis, demographics, triage acuity, vital signs, arrival mode, shift, crowding, and calendar era. We ran six sensitivity cohorts spanning the earlier, more restrictive specification, a Fine–Gray competing-risk model, E-values, and cohort-standardized absolute probabilities.

**Results.** Of 42,405 eligible stays, 31,403 (74.1%) had a reassessment before ED departure (median 159 minutes). Medicaid-insured patients were reassessed more slowly than privately insured patients (adjusted HR 0.87, 95% CI 0.84–0.91), a difference that persisted in every sensitivity cohort (HR 0.83–0.87), in the Fine–Gray model (sHR 0.86), and corresponded to a standardized absolute difference of 3.3 percentage points in the probability of reassessment within two hours (27.1% vs 30.4%). Black–White and Hispanic–White differences were close to null. An apparent Asian–White difference in the restrictive cohort (HR 0.87) reversed under inclusive handling of zero scores and was judged specification-dependent.

**Conclusions.** In this single-center cohort, Medicaid insurance was associated with modestly but consistently slower pain reassessment. The association was not explained by acuity, arrival characteristics, crowding, or departure as a competing risk, though unmeasured confounding of moderate strength (E-value 1.55) could account for it.

---

## Introduction

Pain is the most common reason for ED visits in the United States, and repeated assessment is the mechanism by which analgesia is titrated, deterioration is noticed, and a patient's report of pain enters the medical record at all. Regulatory attention has focused mainly on the initial assessment; The Joint Commission's standards, introduced in 2001 and revised since, require that pain be assessed and then reassessed, but leave the interval unspecified [1]. In practice, reassessment is the step most likely to be skipped, and skipped unevenly.

A large literature documents differences in ED analgesia by race and ethnicity, including lower rates of opioid prescribing for Black patients [2–4] and false beliefs among clinicians about biological differences in pain perception [5]. Far less is known about the documentation process that precedes treatment decisions. If pain reassessment happens later for some groups, their pain trajectories are less visible in the record, treatment adjustments come later, and quality metrics based on documented scores understate their burden. Documentation timing is also, unlike prescribing, a process measure that hospitals fully control.

We used MIMIC-IV-ED [6,7] to ask whether the time from a first documented pain score to the next pain assessment differs by insurance, race and ethnicity, and language among ED patients with two painful index conditions, acute pancreatitis and trauma. A preliminary version of this analysis excluded patients with undocumented insurance, small race and ethnicity categories, and pain scores of zero. Those exclusions removed almost two thirds of otherwise eligible stays, and their consequences motivated the design reported here: an inclusive primary cohort in which selection decisions are minimized, with the earlier restrictive specification retained as one of six sensitivity analyses. Because who gets excluded is itself patterned by the exposures of interest, cohort construction can manufacture or hide associations [8]; we treat that as a finding to report rather than a nuisance to bury in a flow diagram.

## Methods

### Data source and design

MIMIC-IV-ED contains deidentified records of 425,087 ED stays at Beth Israel Deaconess Medical Center between 2011 and 2019, with dates shifted for deidentification [6,7]. We linked ED stays to hospital records in MIMIC-IV v3.1 for insurance, language, and comorbidity information. The study is a retrospective cohort analysis reported in line with STROBE guidance [9]. Use of the database is covered by its data use agreement; no additional IRB review was required.

### Cohort

We included ED stays with a diagnosis of acute pancreatitis or trauma (ICD-9/10 codes beginning S or T, or diagnosis titles containing trauma, injury, fracture, laceration, contusion, or burn). These conditions were chosen because pain is central to both, while differing in mechanism and typical acuity. Acute pancreatitis was analyzed as a single group; subtype analyses were considered and set aside because the cell sizes could not support them.

Eligible stays required at least one numeric pain score (0–10) recorded in the ED vital-sign record and a documented triage acuity (Emergency Severity Index, ESI [10]). Stays whose first pain score carried the same timestamp as ED departure, or a later one — a charting artifact that leaves no observable follow-up time — were also excluded. Nothing else was. Specifically: all race and ethnicity categories were retained, with groups too small to model (American Indian or Alaska Native, Native Hawaiian or Other Pacific Islander, Two or More Races) pooled as "Other" and unknown race kept as its own level; undocumented insurance and undocumented language were kept as explicit covariate levels rather than dropped; initial pain scores of zero counted as valid documentation; and stays with a single pain score were retained and censored at ED departure. Figure 1 shows the flow into the primary cohort of 42,405 stays. For comparison, the earlier restrictive specification would have kept 17,609.

### Outcome

The outcome was time in minutes from the first documented numeric pain score to the next documented pain assessment during the same stay. A subsequent numeric score always counted as a reassessment. Non-numeric entries in the pain field (11.7% of raw entries — "UTA," "sleeping," "critical," and similar) were classified with a keyword taxonomy into entries suggesting clinical complications (unable to assess, sedated, intubated, critical) and entries suggesting the patient was unavailable or declined (sleeping, refused); in the primary analysis a text entry after the initial score counted as a reassessment attempt, since documentation occurred, and a sensitivity cohort ignored text entries entirely. Duplicate rows with identical stay, timestamp, and value were removed; we verified that no stay had conflicting numeric values recorded at the same instant. Stays without any second assessment were censored at ED departure.

### Statistical analysis

Cohort characteristics are summarized with counts and proportions or means and standard deviations (Table 1). The primary model was a cause-specific Cox proportional hazards model fit by maximum partial likelihood (lifelines 0.30, Python 3.13). Covariates entered in four pre-specified blocks: initial pain score and diagnosis/injury group (M1: acute pancreatitis as reference against fall, fracture/dislocation, and other trauma); race and ethnicity, age group, sex, insurance, and language (M2); triage acuity and standardized first vital signs — heart rate, respiratory rate, systolic blood pressure (M3); and arrival mode, arrival shift, weekend arrival, two ED crowding measures, and calendar era (M4, primary). Key estimates are reported at each step of the sequence (Appendix Table A1) so the contribution of each domain is visible, and the full M4 is displayed by domain in Figure 3. Hazard ratios above 1 indicate faster reassessment. Complete-case estimation was used; the fully adjusted model retained 42,076 stays (99.2% of the cohort), with 329 excluded for a missing model covariate — 318 lacking at least one first vital sign and 11 lacking age. We tabulated missingness of every analytic variable by race and insurance rather than imputing, since missingness was below 2% for all model covariates (Appendix Table A2).

Five additional analyses addressed specific threats to interpretation.

First, cohort-selection sensitivity: six alternative cohorts re-ran the identical M4 specification, varying one selection rule at a time — the earlier restrictive specification (S0); inclusive race handling only (S1); inclusive insurance only (S2); zero scores valid (S3); text entries ignored versus counted (S4); and trauma only, without pancreatitis (S5).

Second, competing risks: patients who elope, leave without being seen, leave against medical advice, die, or are transferred cannot be reassessed, and treating those departures as ordinary censoring can distort hazard ratios when departure rates differ by group. We refit the model as a Fine–Gray subdistribution hazards model [11,12] with these structural departures (n = 522) as the competing event, using the finegray weighting implementation in R (survival 3.8.3, R 4.5.2).

Third, unmeasured confounding: we computed E-values [13] for the key adjusted hazard ratios — the minimum strength of association an unmeasured confounder would need with both exposure and outcome to fully explain the estimate.

Fourth, absolute scale: because hazard ratios are hard to act on, we report (a) the observed Aalen–Johansen cumulative incidence of reassessment by 60, 120, and 180 minutes by insurance group, treating ED departure as a competing event, and (b) Cox-model-standardized probabilities of reassessment by 60 and 120 minutes under each insurance assignment, averaging predicted risks over the whole cohort (G-computation on the M4 fit).

Fifth, documentation content: we tabulated the non-numeric pain entries and the disposition profile of single-score stays, to characterize who is never reassessed and why.

A directed acyclic graph (Figure 2) encodes the assumed structure: social position (insurance, race, language) influences reassessment through triage assignment, arrival pathway, and unit workload, but may also act directly through clinician attention; disposition and analgesia are downstream of reassessment and were excluded from the primary model.

## Results

### Cohort

Table 1 describes the primary cohort: 42,405 stays (40,659 trauma, 1,746 acute pancreatitis; within trauma, 39.7% falls, 4.7% fracture or dislocation, 51.4% other injury). Mean age was 49.6 years (SD 21.3) and 50.9% of patients were female. The cohort was 63.4% White (n = 26,872), 17.7% Black (7,518), 6.7% Hispanic (2,853), 4.9% Asian (2,065), 6.9% unknown race (2,926), and 0.4% pooled small categories (171). Mean initial pain score was 4.3 (SD 3.6), and 28.7% of stays had an initial score of zero — the stratum the previous specification discarded. Insurance was undocumented for 17,110 stays (40.3%), Medicare for 12,184 (28.7%), private for 7,130 (16.8%), and Medicaid for 5,981 (14.1%). Undocumented insurance was concentrated among patients discharged home without hospital admission, and its prevalence varied by race, from 37.2% of White patients to 61.5% of Asian patients (Appendix Table A2) — the clearest illustration of why dropping those stays reshapes the cohort.

A reassessment occurred before ED departure in 31,403 stays (74.1%), at a median of 159 minutes after the initial score. Of the 11,002 censored stays, only 537 (4.9%) ended in a structural departure (eloped, left without being seen, left against medical advice, died, or transferred); the rest were routine discharges or admissions in which no second score was charted. Among stays that ended in leaving without being seen, 94.7% had only the single triage-associated score, which is the expected signature of that disposition.

### Primary model

Figure 3 shows the fully adjusted model by covariate domain, and Appendix Table A1 traces the key estimates as each block entered the sequence. Medicaid-insured patients were reassessed more slowly than privately insured patients (HR 0.87, 95% CI 0.84–0.91). The estimate was 0.88 at first adjustment (M2) and did not move as severity (M3) or workflow (M4) entered — whatever produces it is not carried by acuity, vital signs, arrival timing, or crowding. Patients with undocumented insurance also showed a modest difference (HR 0.92, 95% CI 0.87–0.99), while Medicare did not (HR 0.99, 95% CI 0.95–1.03). Differences by race and ethnicity were close to null: Black–White HR 0.99 (0.96–1.02), Hispanic–White 0.99 (0.94–1.04), Asian–White 1.05 (0.99–1.11). The small crude Black–White difference in M2 (0.96) moved to the null once triage acuity and vitals entered. Non-English language was not associated with reassessment timing (HR 0.99, 95% CI 0.94–1.04), although stays with undocumented language — largely the same stays lacking hospital-linked insurance data — appeared faster (HR 1.18, 95% CI 1.11–1.26), a pattern we interpret as an artifact of the linkage process rather than a care difference.

The clinical and workflow domains behaved as expected, which is itself a useful check on the outcome definition. Every trauma subtype was reassessed more slowly than acute pancreatitis (fall HR 0.79, fracture/dislocation 0.77, other trauma 0.82), consistent with pancreatitis patients' higher admission rates and continuous nursing contact. Higher triage acuity predicted faster reassessment (HR 0.81 per ESI level toward less acute, 95% CI 0.79–0.82), with small independent contributions from heart rate (1.02 per SD) and respiratory rate (1.01 per SD) but not blood pressure. Night-shift arrivals were reassessed faster than day-shift (HR 1.12, 95% CI 1.08–1.16); recent arrival volume slowed reassessment slightly (0.99 per arrival in the prior hour), while standing census did not. Model discrimination was modest (concordance 0.586), as expected for a process outcome dominated by unit-level routine.

### Sensitivity to cohort construction

The Medicaid association was stable in every alternative cohort, with hazard ratios between 0.83 and 0.87 across the restrictive specification, each single-rule variation, the trauma-only cohort, and the fully inclusive cohort (Figure 6). Two estimates were not stable, and we flag them as specification-dependent rather than substantive findings. The Asian–White hazard ratio was 0.87 (0.77–0.99) in the restrictive cohort but 1.03–1.05 when zero pain scores counted as documentation, so its sign depends on a data-handling rule. The Medicare–private difference (0.89 in the restrictive cohort) attenuated to null (0.99) in the inclusive cohort, consistent with the undocumented-insurance exclusion having selectively retained admitted, older patients.

### Competing risks, confounding strength, and absolute scale

The Fine–Gray model moved almost nothing (Figure 5): Medicaid sHR 0.86 (95% CI 0.83–0.90) against the Cox 0.87, with race and language estimates similarly unchanged. Differential departure before reassessment does not explain the insurance association; structural departures were too rare (1.2% of the model population) to do so.

The E-value for the Medicaid estimate was 1.55 (1.43 for the confidence limit): an unmeasured confounder associated with both Medicaid coverage and slower reassessment by hazard ratios of about 1.6 each, beyond the measured covariates, could fully account for the association. Unmeasured severity or behavioral-health comorbidity of that magnitude is plausible in principle, which is why we describe the finding as an association rather than an effect of insurance status.

On the absolute scale (Figure 4), the observed cumulative incidence of reassessment by two hours was 25.6% for Medicaid, 28.5% for private, 30.2% for Medicare, and 22.7% for undocumented insurance; by three hours the Medicaid–private gap was 40.6% versus 44.3%. Standardizing over the cohort with the adjusted model, the probability of reassessment within two hours was 30.4% under private insurance versus 27.1% under Medicaid — a difference of 3.3 percentage points (1.5 points at one hour). These are modest differences applied to a very common event.

### What the excluded data would have hidden

Non-numeric pain entries totaled 15,564 (11.7% of raw entries) across 7,317 stays: complication-type entries (8,240 in 3,683 stays; "UTA," "unable," "critical," "intubated," "sedated"), unavailability-type entries (5,223 in 3,213 stays; "sleeping," "asleep," "refused"), and 2,101 unclassifiable (Appendix Table A3). Counting these as reassessment attempts (the primary rule) versus discarding them changed no conclusion, but the entries are informative in themselves: roughly one in ten pain "scores" is a note about why no score could be obtained, and analyses that silently drop them treat sedated and sleeping patients as if they were never approached.

## Discussion

Across nine years of ED visits for trauma and pancreatitis at one academic center, patients on Medicaid waited somewhat longer for pain reassessment than privately insured patients — about 13% slower on the hazard scale, or three fewer reassessments per hundred patients by the two-hour mark. The estimate barely moved across seven cohort definitions, an adjustment ladder from crude to fully adjusted, and a competing-risk formulation. By contrast, the Black–White and Hispanic–White differences in reassessment timing were near null in this dataset, and the one racial difference that appeared under the earlier restrictive cohort (Asian–White) turned out to be a product of how zero scores were handled.

Two aspects of the analysis seem worth emphasizing beyond the estimates. The first is the cost of conventional exclusions. Requiring documented hospital-linked insurance discarded 40% of eligible stays, selectively: home-discharged, younger, and disproportionately Asian and Hispanic patients. Our restrictive-cohort estimates would have supported an Asian–White disparity claim that the inclusive cohort does not. That selection into an EHR cohort is itself an outcome of the processes under study is an old point [8], but it is usually raised as a limitation rather than tested. Testing it changed our conclusions.

The second is the value of reporting a process measure on an absolute scale. A hazard ratio of 0.87 sounds small, and a 3.3-percentage-point difference at two hours is small for any individual patient. Its interest is structural: reassessment timing is set by nursing workload, charting norms, and unit routine, all of which are modifiable, and pain documentation feeds the record on which subsequent treatment and quality measurement depend [1,14]. A gap that survives adjustment for acuity, vitals, arrival mode, crowding, and era is a gap in the routine itself.

Most disparity studies in ED pain care measure analgesia — whether and how quickly an opioid was given — and the largest report Black–White gaps in prescribing [2,4]. We measured an upstream documentation process and found an insurance gradient but little racial patterning. The two are not in tension: reassessment is largely nurse-driven and protocolized, while prescribing is discretionary, and discretion is where implicit bias has the most room to operate [5]. A racial difference in reassessment may also exist elsewhere and not at this hospital, or run through variables we adjusted for (arrival mode, triage acuity) that are themselves patterned by race. Distinguishing these needs multi-site data with charted reassessment times.

The findings should be read with the study's limits in view. This is one hospital; documentation culture varies widely, and MIMIC's date-shifting spreads the cohort over nine years of changing practice, adjusted for only coarsely. The insurance variable comes from hospital admission records, so "undocumented" mixes true self-pay patients with anyone not admitted; we kept the category visible rather than pretending to know what it contains. Charted reassessment is an imperfect proxy for attention — a nurse can ask about pain without charting it, and the reverse. The E-values make explicit that moderate unmeasured confounding could account for the Medicaid association; we lacked functional status, behavioral-health history, and income. And the pancreatitis stratum was small (4.1%), so these are effectively trauma estimates; generalization to medical pain presentations is untested.

Within those limits, the practical implication is narrow and concrete: EDs that audit pain-care equity should audit reassessment intervals by insurance, not only initial assessment and analgesia, and should do so on cohorts built to include the patients most likely to fall out of linked administrative data.

---

## Main table

**Table 1. Characteristics of the primary analytic cohort (N = 42,405).** (`outputs/final/table1.csv`)

| Characteristic | Value |
|---|---|
| **Demographics** | |
| Age (years), mean (SD) | 49.6 (21.3) |
| Female sex, n (%) | 21,565 (50.9) |
| White race/ethnicity, n (%) | 26,872 (63.4) |
| Black race/ethnicity, n (%) | 7,518 (17.7) |
| Hispanic race/ethnicity, n (%) | 2,853 (6.7) |
| Asian race/ethnicity, n (%) | 2,065 (4.9) |
| Unknown race/ethnicity, n (%) | 2,926 (6.9) |
| Other race/ethnicity, n (%) | 171 (0.4) |
| **Insurance and language** | |
| Medicare, n (%) | 12,184 (28.7) |
| Private, n (%) | 7,130 (16.8) |
| Medicaid, n (%) | 5,981 (14.1) |
| Undocumented insurance, n (%) | 17,110 (40.3) |
| Non-English preferred language, n (%) | 2,483 (5.9) |
| Undocumented language, n (%) | 15,676 (37.0) |
| **Clinical** | |
| ESI triage level, mean (SD) | 2.8 (0.8) |
| Initial pain score, mean (SD) | 4.3 (3.6) |
| Initial pain score = 0, n (%) | 12,161 (28.7) |
| Trauma diagnosis, n (%) | 40,659 (95.9) |
| — Fall, n (%) | 16,853 (39.7) |
| — Fracture/dislocation, n (%) | 2,001 (4.7) |
| — Other trauma, n (%) | 21,805 (51.4) |
| Acute pancreatitis, n (%) | 1,746 (4.1) |
| First heart rate, mean (SD) | 82.2 (16.8) |
| First respiratory rate, mean (SD) | 17.3 (8.9) |
| First systolic BP, mean (SD) | 135.6 (21.3) |
| **ED workflow** | |
| Ambulance arrival, n (%) | 18,529 (43.7) |
| Weekend arrival, n (%) | 12,048 (28.4) |
| Night shift arrival, n (%) | 7,508 (17.7) |
| Evening shift arrival, n (%) | 18,981 (44.8) |
| ED arrivals in prior hour, mean (SD) | 2.1 (1.3) |
| **Outcomes** | |
| Any reassessment before ED departure, n (%) | 31,403 (74.1) |
| Reassessed within 60 min, n (%) | 4,812 (11.3) |
| Reassessed within 120 min, n (%) | 11,201 (26.4) |
| Time to reassessment, median (IQR), min | 159 (92–250) |

## Appendix

**Table A1. Key hazard ratios (95% CI) across the sequential models M1–M4.** M1: initial pain and diagnosis/injury. M2: + race/ethnicity, age, sex, insurance, language. M3: + triage acuity and first vital signs. M4 (primary): + arrival mode, shift, weekend, crowding, calendar era. HR > 1 = faster reassessment. (`outputs/final/model_sequence_key_terms.csv`)

| Term | M1 | M2 | M3 | M4 (primary) |
|---|---|---|---|---|
| Initial pain score (per point) | 0.99 (0.98–0.99) | 0.99 (0.99–0.99) | 0.99 (0.99–1.00) | 0.99 (0.99–1.00) |
| Fall vs acute pancreatitis | 0.82 (0.77–0.87) | 0.80 (0.76–0.85) | 0.79 (0.74–0.83) | 0.79 (0.75–0.84) |
| Fracture/dislocation vs AP | 0.86 (0.80–0.92) | 0.83 (0.77–0.89) | 0.77 (0.72–0.83) | 0.77 (0.72–0.83) |
| Other trauma vs AP | 0.84 (0.79–0.89) | 0.82 (0.77–0.86) | 0.81 (0.77–0.86) | 0.82 (0.77–0.87) |
| Black vs White | — | 0.96 (0.93–0.99) | 0.99 (0.96–1.02) | 0.99 (0.96–1.02) |
| Hispanic vs White | — | 0.97 (0.92–1.02) | 0.99 (0.94–1.04) | 0.99 (0.94–1.04) |
| Asian vs White | — | 1.01 (0.96–1.07) | 1.04 (0.99–1.10) | 1.05 (0.99–1.11) |
| Medicaid vs private | — | 0.88 (0.84–0.91) | 0.87 (0.84–0.91) | 0.87 (0.84–0.91) |
| Medicare vs private | — | 0.98 (0.94–1.02) | 0.98 (0.95–1.02) | 0.99 (0.95–1.03) |
| Undocumented vs private | — | 0.97 (0.91–1.03) | 0.95 (0.89–1.01) | 0.92 (0.87–0.99) |
| Non-English vs English | — | 0.96 (0.92–1.01) | 0.98 (0.93–1.03) | 0.99 (0.94–1.04) |
| Triage acuity (per ESI level) | — | — | 0.80 (0.78–0.81) | 0.81 (0.79–0.82) |
| Night vs day arrival | — | — | — | 1.12 (1.08–1.16) |

**Table A2. Missingness and documentation patterns by race and insurance.** Missing ESI ≤ 3.2% and missing first vitals ≤ 1.1% in every group; undocumented insurance 37.2% (White) to 61.5% (Asian) (`outputs/final/missingness_by_group.csv`).

**Table A3. Non-numeric pain entry taxonomy.** Entry counts, stay counts, and the 12 most frequent raw strings per class (`outputs/final/text_pain_taxonomy.csv`).

**Table A4. Sensitivity grid.** M4 hazard ratios for all key terms across S0–S6 (`outputs/scenario_m4_terms.csv`; summary in `outputs/scenario_summary.csv`). Cohort sizes 16,322–42,405; Medicaid HR range 0.83–0.87.

**Table A5. E-values for all key M4 estimates** (`outputs/final/evalues.csv`).

**Table A6. Full Fine–Gray coefficient table** (`outputs/final/finegray_shr.csv`).

**Figure A1. Scenario comparison forest** (`figures/scenario_comparison_forest.png`).

**Figure A2. Directed acyclic graph** (`figures/dag_v2.png`).

**Single-score stays.** 50.6% of home-discharged stays had exactly one pain score; 94.7% of left-without-being-seen and 75.8% of eloped stays were single-score (`outputs/single_score_by_disposition.csv`). These stays are retained and censored in all analyses.

---

## Figure legends

**Figure 1.** Cohort flow, from all 425,087 MIMIC-IV-ED stays through diagnosis selection (acute pancreatitis or trauma), pain-score documentation, and triage-acuity documentation. No exclusions for race category, insurance documentation, zero pain scores, or single-score stays; the previous restrictive specification is retained as sensitivity cohort S0. (`figures/fig_final_flow.png`)

**Figure 2.** Assumed causal structure (DAG). Disposition and analgesia are downstream of reassessment and excluded from the primary model. (`figures/dag_v2.png`)

**Figure 3.** Adjusted hazard ratios for first pain reassessment by covariate domain (clinical presentation, demographics, insurance, diagnosis/injury, clinical severity, ED context/workflow), primary inclusive cohort (M4; n = 42,076, 31,313 events). Calendar era adjusted for, not shown. (`figures/fig_final_forest_sectional.png`; compact social-factors version in `figures/fig_final_forest.png`)

**Figure 4.** Absolute scale. (A) Aalen–Johansen cumulative incidence of reassessment by insurance, ED departure as competing event. (B) Cox-standardized probability of reassessment by 60 and 120 minutes under each insurance assignment. (`figures/fig_final_absolute.png`)

**Figure 5.** Cause-specific Cox versus Fine–Gray subdistribution hazard ratios, structural departures (eloped/LWBS/AMA/expired/transfer) as the competing event. (`figures/fig_final_cox_vs_fg.png`)

**Figure 6.** Key hazard ratios across the seven cohort-selection scenarios. (`figures/scenario_comparison_forest.png`)

---

## References

1. Baker DW. History of The Joint Commission's pain standards: lessons for today's prescription opioid epidemic. JAMA. 2017;317(11):1117–1118.
2. Pletcher MJ, Kertesz SG, Kohn MA, Gonzales R. Trends in opioid prescribing by race/ethnicity for patients seeking care in US emergency departments. JAMA. 2008;299(1):70–78.
3. Green CR, Anderson KO, Baker TA, et al. The unequal burden of pain: confronting racial and ethnic disparities in pain. Pain Med. 2003;4(3):277–294.
4. Anderson KO, Green CR, Payne R. Racial and ethnic disparities in pain: causes and consequences of unequal care. J Pain. 2009;10(12):1187–1204.
5. Hoffman KM, Trawalter S, Axt JR, Oliver MN. Racial bias in pain assessment and treatment recommendations, and false beliefs about biological differences between blacks and whites. Proc Natl Acad Sci U S A. 2016;113(16):4296–4301.
6. Johnson AEW, Bulgarelli L, Shen L, et al. MIMIC-IV, a freely accessible electronic health record dataset. Sci Data. 2023;10(1):1.
7. Johnson A, Bulgarelli L, Pollard T, Celi LA, Mark R, Horng S. MIMIC-IV-ED (version 2.2). PhysioNet; 2023.
8. Hernán MA, Hernández-Díaz S, Robins JM. A structural approach to selection bias. Epidemiology. 2004;15(5):615–625.
9. von Elm E, Altman DG, Egger M, et al. The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement: guidelines for reporting observational studies. Lancet. 2007;370(9596):1453–1457.
10. Gilboy N, Tanabe P, Travers D, Rosenau AM. Emergency Severity Index (ESI): A Triage Tool for Emergency Department Care, Version 4. Implementation Handbook. AHRQ; 2011.
11. Fine JP, Gray RJ. A proportional hazards model for the subdistribution of a competing risk. J Am Stat Assoc. 1999;94(446):496–509.
12. Austin PC, Lee DS, Fine JP. Introduction to the analysis of survival data in the presence of competing risks. Circulation. 2016;133(6):601–609.
13. VanderWeele TJ, Ding P. Sensitivity analysis in observational research: introducing the E-value. Ann Intern Med. 2017;167(4):268–274.
14. Todd KH, Ducharme J, Choiniere M, et al. Pain in the emergency department: results of the pain and emergency medicine initiative (PEMI) multicenter study. J Pain. 2007;8(6):460–466.
15. Herr K, Coyne PJ, McCaffery M, Manworren R, Merkel S. Pain assessment in the patient unable to self-report: position statement with clinical practice recommendations. Pain Manag Nurs. 2011;12(4):230–250.
16. Sterne JAC, White IR, Carlin JB, et al. Multiple imputation for missing data in epidemiological and clinical research: potential and pitfalls. BMJ. 2009;338:b2393.
