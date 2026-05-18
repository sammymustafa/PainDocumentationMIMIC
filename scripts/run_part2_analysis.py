#!/usr/bin/env python3
"""PART 2: Within-acuity and post-analgesic pathway analyses."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.part2_analgesic import run_part2b  # noqa: E402
from analysis.part2_within_acuity import run_part2a  # noqa: E402
from analysis.prep_part2 import prep_part2a_cohort  # noqa: E402

PART2_DIR = REPO_ROOT / "figures" / "part2"


def main() -> None:
    print("PART 2 analysis")
    print("=" * 50)
    cohort = prep_part2a_cohort()
    print(f"PART 2A cohort: N={len(cohort):,}, events={int(cohort['reassessment_event'].sum()):,}")

    print("\n--- PART 2A: Within-acuity ---")
    res2a = run_part2a(cohort)

    print("\n--- PART 2B: Post-analgesic pathway ---")
    rx = run_part2b(cohort)

    print("\n" + "=" * 50)
    print("Files created in figures/part2/:")
    for p in sorted(PART2_DIR.glob("*")):
        print(f"  {p}")

    print("\n--- Key race HRs (grouped ESI, within-acuity) ---")
    g = res2a[res2a["model_label"] == "Grouped ESI Cox"]
    for _, r in g.iterrows():
        print(
            f"  {r['acuity_stratum']} | {r['comparison']}: HR={r['hazard_ratio']:.2f}, "
            f"p={r['p_value']:.3f}"
        )

    print("\n--- Post-analgesic Cox (race) ---")
    import pandas as pd

    cox = pd.read_csv(PART2_DIR / "post_analgesic_reassessment_cox_results.csv")
    race = cox[cox["variable"].astype(str).str.contains("race_ethnicity", na=False)]
    for _, r in race.iterrows():
        print(f"  {r['comparison']}: HR={r['HR']}, p={r['p-value']}")

    print(f"\nPost-analgesic cohort N={len(rx):,}, events={int(rx['post_analgesic_event'].sum()):,}")


if __name__ == "__main__":
    main()
