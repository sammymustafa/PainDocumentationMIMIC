#!/usr/bin/env python3
"""Pull MIMIC-IV ED pain cohort from BigQuery and run cleaning pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.bigquery_io import fetch_pain_cohort  # noqa: E402
from src.config import load_settings  # noqa: E402
from src.pain_processing import process_pain_dataframe  # noqa: E402


def save_parquet_and_csv(df, parquet_path: Path, csv_path: Path, label: str) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    print(f"Saved {label} to {parquet_path} and {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to settings YAML (default: config/settings.yaml)",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip BigQuery; re-process existing raw parquet only",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Fetch from BigQuery and save raw data without processing",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings(args.config)

    bq_cfg = settings["bigquery"]
    proc_cfg = settings["processing"]
    out_cfg = settings["output"]

    raw_path = REPO_ROOT / out_cfg["raw_path"]
    processed_path = REPO_ROOT / out_cfg["processed_path"]
    raw_csv_path = REPO_ROOT / out_cfg["raw_csv_path"]
    processed_csv_path = REPO_ROOT / out_cfg["processed_csv_path"]

    if args.skip_fetch:
        import pandas as pd

        if not raw_path.exists():
            raise FileNotFoundError(
                f"--skip-fetch set but raw file not found: {raw_path}"
            )
        pain = pd.read_parquet(raw_path)
        print(f"Loaded raw data from {raw_path}: {pain.shape}")
    else:
        print(f"Querying BigQuery (project={bq_cfg['project_id']})...")
        pain = fetch_pain_cohort(bq_cfg["project_id"])
        print(f"Fetched {pain.shape[0]:,} rows x {pain.shape[1]} columns")
        save_parquet_and_csv(pain, raw_path, raw_csv_path, "raw data")

    if args.raw_only:
        return

    pain_filtered = process_pain_dataframe(
        pain,
        language_threshold=proc_cfg["language_threshold"],
        insurance_threshold=proc_cfg["insurance_threshold"],
        exclude_races=proc_cfg["exclude_races"],
        excluded_races=proc_cfg["excluded_races"],
    )
    print(f"Processed shape: {pain_filtered.shape}")
    save_parquet_and_csv(
        pain_filtered, processed_path, processed_csv_path, "processed data"
    )


if __name__ == "__main__":
    main()
