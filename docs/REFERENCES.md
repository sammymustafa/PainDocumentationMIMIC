# References

Key methods and data sources for this analysis. Add full citations in the manuscript reference manager.

## Data

1. **Johnson AEW, Pollard TJ, Mark RG.** MIMIC-IV (Medical Information Mart for Intensive Care IV). PhysioNet, 2023. https://physionet.org/content/mimiciv/ — Emergency Department module (`mimiciv_ed`) for stay timing, triage, disposition, and demographics.

## Survival analysis

2. **Cox DR.** Regression models and life-tables. *Journal of the Royal Statistical Society: Series B*, 1972. — Cox proportional hazards model for time to first pain reassessment.

3. **Kaplan EL, Meier P.** Nonparametric estimation from incomplete observations. *Journal of the American Statistical Association*, 1958. — Kaplan–Meier curves for unadjusted reassessment timing.

## Equity and documentation in the ED

4. **Hausmann LRM, et al.** Racial and ethnic disparities in pain care. *The Clinical Journal of Pain*, 2011. — Framework for interpreting race/ethnicity and insurance in pain documentation studies.

5. **Todd KH, et al.** Ethnicity and analgesic practice. *Annals of Emergency Medicine*, 2000. — Classic ED pain treatment disparities literature.

## Triage and workflow

6. **Gilboy N, et al.** Emergency Severity Index (ESI): A Triage Tool for Emergency Department Care, Version 4. AHRQ, 2011. — ESI acuity interpretation.

## Study-specific notes

- De-identified MIMIC calendar years (e.g., 2110–2211) are **not** calendar dates; 5-year `year_era` bins are policy-era proxies for temporal trend sensitivity only.
- **Undocumented insurance** (missing payer in EHR) and **uninsured** (self-pay) are included as insurance categories in Cox models (reference: private).
- **Language** is reported descriptively in Table 1 only; it is not adjusted in Cox models due to high missing/undocumented documentation.
