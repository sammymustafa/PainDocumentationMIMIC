# Pain Documentation MIMIC

Pull ED pain assessment data from **MIMIC-IV** via PhysioNet BigQuery, matching the cohort and processing logic in the Colab notebook `5_18_pain_phenotypes.ipynb`.

## Cohort

- **Setting:** MIMIC-IV Emergency Department (`mimiciv_ed`)
- **Diagnoses:** acute pancreatitis or trauma (ICD S00–T88)
- **Outcome rows:** vital signs with non-null pain scores, joined to demographics and ED stay timing

SQL lives in [`sql/pain_phenotypes.sql`](sql/pain_phenotypes.sql).

## Prerequisites

1. **PhysioNet credentialed access** to MIMIC-IV and BigQuery export enabled on your Google account.
2. A GCP project with BigQuery billing (default in config: `mimic-pain-ap`).
3. Python 3.10+.

## Authentication (local, not Colab)

Colab used `google.colab.auth`. Locally, use Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project mimic-pain-ap
```

Or point to a service account (do not commit the JSON file):

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

Edit [`config/settings.yaml`](config/settings.yaml) if your billing project or output paths differ.

## Setup

```bash
cd PainDocumentationMIMIC
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Fetch from BigQuery and run the cleaning / feature pipeline:

```bash
python scripts/fetch_pain_data.py
```

Options:

```bash
# Save raw only (no processing)
python scripts/fetch_pain_data.py --raw-only

# Re-run processing on saved raw parquet
python scripts/fetch_pain_data.py --skip-fetch
```

Outputs (gitignored):

| File | Description |
|------|-------------|
| `data/raw/pain_raw.parquet` | BigQuery extract |
| `data/raw/pain_raw.csv` | Same raw data as CSV |
| `data/processed/pain_filtered.parquet` | Cleaned cohort with trajectory features |
| `data/processed/pain_filtered.csv` | Same processed data as CSV |

## Project layout

```
config/settings.yaml    # project ID, thresholds, output paths
sql/pain_phenotypes.sql # BigQuery SQL (same logic as Colab)
src/
  bigquery_io.py        # client + query → DataFrame
  pain_cleaning.py      # pain score parsing
  pain_processing.py    # cohort filters and derived columns
scripts/fetch_pain_data.py
```

## Reassessment analysis (models + figures)

Among stays with initial and first reassessment documented (`final_modeling_dataset.csv`):

```bash
python scripts/run_reassessment_analysis.py
```

**Sequential OLS models** (outcome: log minutes to reassessment):

| Model | Adjustment |
|-------|------------|
| M1 | Initial pain only |
| M2 | + demographics (race incl. Unknown, age, sex, insurance, language) |
| M3 | + clinical (ESI, diagnosis, trauma subtype, vitals) |
| M4 | + workflow (5 de-identified year eras, shift, weekend, ED census/arrivals) |
| M5 | + analgesic before reassessment |
| M6 | Sensitivity: + disposition & ED LOS |

**Outputs:**

- `figures/main/` — 7 main figures (DAG, ECDF by race, sequential models, multi-factor forest, factor panels, ESI stratification, analgesic × disposition)
- `figures/supplement/` — ECDF/adjusted plots for insurance, language, sex, age, diagnosis, shift, disposition, era trends, logistic windows, sensitivity
- `data/processed/analysis/sequential_ols_results.csv`

Year eras are ~20-year buckets over de-identified years 2110–2211 (not calendar years).

## Table 1 by race

From `data/processed/modeling/final_modeling_dataset.csv` (vertical layout: characteristics as rows, race strata as columns):

```bash
python scripts/make_demographic_table.py
```

Outputs: `figures/table1_by_race.csv`, `figures/table1_by_race.png`

Or in Python:

```python
from src.demographic_table import make_demographic_table

make_demographic_table()
```

## Use in Python

```python
from src.bigquery_io import fetch_pain_cohort
from src.pain_processing import process_pain_dataframe

pain = fetch_pain_cohort("mimic-pain-ap")
pain_filtered = process_pain_dataframe(pain)
```

## Notes

- MIMIC data must **not** be committed to GitHub. Parquet paths are in `.gitignore`.
- The query reads from `physionet-data.*` datasets; your GCP user must have PhysioNet BigQuery access linked to that project.
