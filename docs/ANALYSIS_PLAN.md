# Analysis plan: ED pain reassessment (MIMIC-IV)

## Primary Cox sequence (early-encounter only)

| Model | Covariates |
|-------|------------|
| M1 | Initial pain, injury/diagnosis |
| M2 | Race, insurance, language, age, sex |
| M3 | ESI, vitals, comorbidity count (if available) |
| **M4** | Arrival mode, shift, weekend, ED crowding, year era |

**M4** is the primary adjusted model. Do not include disposition or analgesia in M1–M4.

## Pathway / sensitivity analyses (separate)

1. **Disposition:** M4 + admitted vs home (`m4_disposition_cox_hr.csv`, fig09)  
2. **Post-analgesic:** time zero = first analgesic; censor at outtime (fig13)  
3. **Severe pain:** subsets pain 7–10 and pain = 10 (fig12)  
4. **Pain=10 & ESI 1–2:** no pain score in model (fig14)  
5. **Within-acuity:** M4-style within ESI strata (fig11 + appendix)  
6. **IPTW:** Medicaid vs private; PS uses M1–M3 only (fig15)  
7. **Year:** M4 + continuous year (fig07)

## Presentation rules

- Vitals: in M3, not shown in fig06 (appendix `table_vital_sign_m4_hrs.csv`)  
- Other arrival mode: appendix only  
- Transfer/other disposition: excluded from main inference (`disposition_pathway` HOME vs ADMITTED only)

## Reproduce

```bash
python scripts/run_analysis.py
```
