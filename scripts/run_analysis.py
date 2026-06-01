#!/usr/bin/env python3
"""Single entry point: manuscript-ready ED pain reassessment analysis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis._paths import ANALYSIS_OUT, MANUSCRIPT_DIR  # noqa: E402
from analysis.figure_audit import save_figure_audit  # noqa: E402
from analysis.appendix_figures import run_appendix_analyses  # noqa: E402
from analysis.disposition_analysis import run_disposition_analysis  # noqa: E402
from analysis.extended_figures import run_extended_figures  # noqa: E402
from analysis.figures_manuscript import run_all_figures  # noqa: E402
from analysis.fit_primary import run_primary_cox  # noqa: E402
from analysis.iptw_sensitivity import run_iptw_sensitivity  # noqa: E402
from analysis.pain10_esi12_subgroup import run_pain10_esi12_subgroup  # noqa: E402
from analysis.post_analgesic import run_post_analgesic  # noqa: E402
from analysis.prep_cohort import compute_flow_counts, prep_analytic_cohort, save_flow_counts  # noqa: E402
from analysis.prep_survival import load_or_build_survival  # noqa: E402
from analysis.table1 import export_table1  # noqa: E402
from analysis.within_acuity import run_within_acuity  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rebuild-survival", action="store_true", help="Rebuild survival_cohort.csv from raw")
    p.add_argument("--skip-figures", action="store_true", help="Skip matplotlib figures")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    print("ED pain reassessment analysis pipeline")
    print("=" * 50)

    print("\n[1] Survival cohort...")
    survival = load_or_build_survival(rebuild=args.rebuild_survival)
    cohort = prep_analytic_cohort(survival)
    print(f"  Analytic cohort N={len(cohort):,}, events={int(cohort['reassessment_event'].sum()):,}")

    print("\n[2] Flow counts...")
    counts = compute_flow_counts(survival=survival)
    save_flow_counts(counts)

    print("\n[3] Table 1...")
    table1 = export_table1(cohort)

    print("\n[4] Primary Cox M1–M4 + disposition sensitivity...")
    cox = run_primary_cox(cohort)

    print("\n[5] Within-acuity models (fig11)...")
    run_within_acuity(cohort)

    print("\n[6] Disposition pathway sensitivity (fig09)...")
    run_disposition_analysis(cohort, m4=cox["m4"], m5=cox["m4_disposition"])

    print("\n[7] Pain=10 & ESI 1–2 subgroup (fig14)...")
    run_pain10_esi12_subgroup(cohort)

    print("\n[8] Post-analgesic pathway (fig13)...")
    run_post_analgesic(survival)

    if not args.skip_figures:
        print("\n[Audit] Figure vs model specification...")
        save_figure_audit(ANALYSIS_OUT / "figure_audit.csv")

        print("\n[Figures] Core deck fig01–06, fig13...")
        run_all_figures(cohort, table1=table1, m4=cox["m4"], flow_counts=counts)

        print("\n[Figures] Extended fig07–fig12...")
        run_extended_figures(cohort, cox)

        print("\n[Figures] IPTW sensitivity (fig15)...")
        run_iptw_sensitivity(cohort, m4=cox["m4"])

        print("\n[Appendix] Within-acuity appendix, vitals, interactions...")
        run_appendix_analyses(cohort, cox)

    print("\n" + "=" * 50)
    print(f"Outputs: {MANUSCRIPT_DIR}/fig01–fig15")
    print("Docs: docs/FIGURE_MANIFEST.md")


if __name__ == "__main__":
    main()
