"""Export key HRs across sequential M1–M4 models."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR
from analysis.term_utils import pick_term_row

KEY_TERM_SPECS: list[tuple[str, dict]] = [
    ("Black vs White", {"term_contains": "race_ethnicity", "level": "Black"}),
    ("Hispanic vs White", {"term_contains": "race_ethnicity", "level": "Hispanic"}),
    ("Asian vs White", {"term_contains": "race_ethnicity", "level": "Asian"}),
    ("Medicaid vs private", {"term_contains": "insurance_group", "level": "Medicaid"}),
    ("Medicare vs private", {"term_contains": "insurance_group", "level": "Medicare"}),
    ("ESI (per unit)", {"exact_term": "triage_acuity"}),
    ("Initial pain (per unit)", {"exact_term": "initial_pain_score"}),
    ("Comorbidity count (M3+)", {"exact_term": "comorbidity_count"}),
    ("Night vs day shift", {"term_contains": "arrival_shift", "level": "night"}),
    ("Weekend vs weekday", {"exact_term": "arrival_weekend"}),
    ("Ambulance vs walk-in", {"term_contains": "arrival_mode", "level": "ambulance"}),
]

MODEL_ORDER = ["M1", "M2", "M3", "M4"]


def build_model_sequence_key_hrs(sequential: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor_label, kwargs in KEY_TERM_SPECS:
        for model in MODEL_ORDER:
            r = pick_term_row(sequential, model, **kwargs)
            if r is None:
                rows.append(
                    {
                        "factor": factor_label,
                        "model": model,
                        "term": "",
                        "comparison": "",
                        "hazard_ratio": np.nan,
                        "ci_low": np.nan,
                        "ci_high": np.nan,
                        "pvalue": np.nan,
                        "in_model": False,
                    }
                )
                continue
            rows.append(
                {
                    "factor": factor_label,
                    "model": model,
                    "term": r["term"],
                    "comparison": r.get("comparison", ""),
                    "hazard_ratio": r["hazard_ratio"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                    "pvalue": r["pvalue"],
                    "in_model": True,
                }
            )
    return pd.DataFrame(rows)


def export_model_sequence_table(sequential: pd.DataFrame) -> pd.DataFrame:
    table = build_model_sequence_key_hrs(sequential)
    out_dir = ANALYSIS_OUT
    man_tables = MANUSCRIPT_DIR / "tables"
    man_tables.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_dir / "model_sequence_key_hrs.csv", index=False)
    table.to_csv(man_tables / "table_model_sequence_key_hrs.csv", index=False)
    return table
