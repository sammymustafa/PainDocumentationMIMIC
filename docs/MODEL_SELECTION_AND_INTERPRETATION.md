# Model selection and interpretation

## Primary models M1–M4

The primary Cox sequence uses **baseline and early-encounter** information only:

1. **M1** — Clinical presentation at pain documentation  
2. **M2** — Patient/social factors (race, insurance, language, age, sex)  
3. **M3** — Severity and illness burden (ESI, vitals, comorbidity)  
4. **M4** — ED context and workflow (arrival, shift, weekend, crowding, year)

**M4** is the primary model for manuscript inference on race, insurance, and workflow.

## Downstream variables (not in M1–M4)

**Disposition** (admitted vs discharged home) and **analgesia** are downstream of initial pain documentation and affect reassessment opportunity. They are analyzed only in separate pathway/sensitivity models:

- Disposition: M4 + `disposition_pathway` (fig09)  
- Post-analgesic: new time zero at first analgesic (fig13)

Do not interpret disposition or analgesia as primary confounders in the M4 race/insurance estimates.

## Hazard ratios

- **HR > 1:** Faster time to first pain reassessment  
- **HR < 1:** Slower time to first pain reassessment  

## Vitals and figures

Vitals are included in **M3** for adjustment but are not displayed in the main M4 forest (fig06). See appendix vital-sign table.

## Sensitivity analyses

Within-acuity, severe pain, IPTW, and continuous-year analyses are **robustness/pathway** supplements, not replacements for M4.
