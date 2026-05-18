from __future__ import annotations

from pathlib import Path

import pandas as pd
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQL_PATH = REPO_ROOT / "sql" / "pain_phenotypes.sql"


def get_client(project_id: str) -> bigquery.Client:
    return bigquery.Client(project=project_id)


def load_sql(path: Path | None = None) -> str:
    sql_path = path or DEFAULT_SQL_PATH
    return sql_path.read_text()


def query_to_dataframe(
    client: bigquery.Client,
    sql: str,
    *,
    job_config: bigquery.QueryJobConfig | None = None,
) -> pd.DataFrame:
    job = client.query(sql, job_config=job_config)
    return job.to_dataframe()


def fetch_pain_cohort(
    project_id: str,
    sql_path: Path | None = None,
) -> pd.DataFrame:
    client = get_client(project_id)
    sql = load_sql(sql_path)
    return query_to_dataframe(client, sql)
