# Heatmap options (time to first pain reassessment)

All heatmaps use **univariate Cox** models on the full AP + trauma cohort.  
Cell color = **signed −log₁₀(p)** (red → faster reassessment / HR>1; blue → slower / HR<1).

| File | What columns represent | When to use |
|------|------------------------|-------------|
| `fig_heatmap_by_pain_score.png` | Initial pain **1, 2, … 10** separately | Fine-grained “does bias differ at pain 7 vs 4?” (noisy, many columns) |
| `fig_heatmap_by_pain_severity.png` | **Mild (1–3), moderate (4–6), severe (7–10)** | Cleaner clinical groupings, more stable N per column |
| `fig_heatmap_overall_pooled.png` | **One column — entire cohort** | Simple “who is associated with faster/slower reassessment overall?” |
| `fig_heatmap_by_esi_acuity.png` | **ESI 1–2, ESI 3, ESI 4–5** | “Does equity differ by how sick they were at triage?” |
| `fig_heatmap_by_diagnosis.png` | **Trauma vs acute pancreatitis** | AP vs trauma pathways |
| `fig_heatmap_pain_interaction.png` | **Pain × factor interaction** (one column) | “Does initial pain level *change* the association?” (not stratified slices) |

Regenerate all: `python scripts/make_pain_score_heatmap.py`
