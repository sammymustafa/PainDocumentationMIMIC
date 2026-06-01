# Manuscript (LaTeX)

Draft manuscript for the ED pain reassessment study. This folder is **self-contained for Overleaf**: figures live in `figures/` next to `main.tex`.

## Upload to Overleaf

1. From the repo root, refresh statistics if the analysis changed:
   ```bash
   python scripts/export_manuscript_stats.py
   ```
2. Zip this folder (from inside `docs/manuscript`):
   ```bash
   cd docs/manuscript
   zip -r pain-reassessment-manuscript.zip . -x "*.aux" "*.log" "*.out" "*.fdb_latexmk" "*.fls"
   ```
3. In Overleaf: **New Project → Upload Project** → select the zip.
4. Set **main.tex** as the main document and compile.

## Build locally

```bash
cd docs/manuscript
python ../../scripts/export_manuscript_stats.py   # optional: sync HRs from pipeline CSVs
latexmk -pdf main.tex
```

Requirements: a LaTeX distribution (`latexmk` or `pdflatex`, `natbib`). On macOS: [MacTeX](https://tug.org/mactex/) or `brew install --cask mactex-no-gui`.

## Structure

| Path | Content |
|------|---------|
| `main.tex` | Document preamble and section includes |
| `manuscript_stats.tex` | Auto-generated `\newcommand`s (run export script) |
| `sections/` | Abstract, Introduction, Methods, Results, Discussion |
| `figures/` | PNGs referenced by Results (copied from pipeline output) |
| `references.bib` | Bibliography (placeholders to complete) |

Figures are loaded via `\graphicspath{{figures/}}` — no paths outside this folder.

## Updating numbers

After re-running `python scripts/run_analysis.py` at the repo root:

```bash
python scripts/export_manuscript_stats.py
# Re-copy figures if regenerated:
# cp ../../figures/manuscript/fig*.png figures/
latexmk -pdf main.tex
```

## Bundled figures

- `fig02_cohort_flow.png`
- `fig04_km_reassessment_overview.png`
- `fig05_reassessment_rates_60min.png`
- `fig06_m4_sectional_forest.png`
- `fig07_year_era_reassessment_trend.png`
- `fig08_sequential_attenuation_key_factors.png`
- `fig10_insurance_focused_analysis.png`
- `fig11_within_acuity_forests.png`
- `fig12_severe_pain_sensitivity.png`
- `fig13_post_analgesic_pathway.png`
