# Pain Documentation MIMIC

MIMIC-IV ED cohort (acute pancreatitis and trauma) for **time to first pain reassessment** after initial pain documentation.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_pain_data.py          # optional: refresh from BigQuery
python scripts/run_analysis.py             # full manuscript pipeline
```

**Outputs:** `figures/manuscript/fig01`–`fig15`  
**Figure list:** `docs/FIGURE_MANIFEST.md`  
**Methods:** `docs/ANALYSIS_PLAN.md`  
**LaTeX manuscript (Overleaf-ready):** `docs/manuscript/` — zip that folder to upload; figures are in `docs/manuscript/figures/`

## Primary model sequence (M1–M4)

| Model | Content |
|-------|---------|
| M1 | Initial pain + injury |
| M2 | Race, insurance, language, age, sex |
| M3 | ESI + vitals (adjusted) + comorbidity if available |
| **M4** | Arrival mode, shift, weekend, crowding, year — **primary** |

**HR interpretation:** HR > 1 = faster reassessment; HR < 1 = slower reassessment.

Disposition and analgesia are **downstream** and **not** in the primary sequence. Vitals are in M3 but hidden from the main M4 forest (appendix table). Other arrival mode is appendix-only.

## Sensitivity / pathway analyses

- **Disposition:** M4 + admitted vs home (`fig09`) — transfer/other excluded from main inference  
- **Post-analgesic:** time zero = first analgesic (`fig13`)  
- **Severe pain:** pain 7–10 and pain = 10 (`fig12`)  
- **Pain=10 & ESI 1–2:** parsimonious subgroup (`fig14`)  
- **Within-acuity:** race/insurance main (`fig11`); appendix for other variables  
- **IPTW:** Medicaid vs private (`fig15`)  
- **Year:** continuous M4 + year (`fig07`)

## Main figures

| Fig | File |
|-----|------|
| 06 | `fig06_m4_sectional_forest.png` |
| 07 | `fig07_year_era_reassessment_trend.png` |
| 08 | `fig08_sequential_attenuation_key_factors.png` |
| 09 | `fig09_m4_disposition_sensitivity.png` |
| 10–14 | insurance, within-acuity, severe pain, post-analgesic, pain10/ESI1–2 |
| 15 | `fig15_iptw_sensitivity.png` |

```bash
python scripts/run_analysis.py
```
