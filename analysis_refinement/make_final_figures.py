#!/usr/bin/env python3
"""Figures for the refined (S6-primary) analysis.

  fig_final_flow.png      cohort flow, raw extract -> primary analytic cohort
  fig_final_forest.png    primary M4 forest (social + clinical terms)
  fig_final_absolute.png  (A) CIF of reassessment by insurance
                          (B) Cox-standardized P(reassessed) at 60/120 min
  fig_final_cox_vs_fg.png Cox HR vs Fine-Gray sHR, key terms

Run: ./.venv/bin/python analysis_refinement/make_final_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "final"
FIGS = HERE / "figures"

INS_COLORS = {"private": "#1f77b4", "Medicaid": "#d62728",
              "Medicare": "#2ca02c", "undocumented": "#7f7f7f"}

SOCIAL_ORDER = [
    "Asian vs 'White'", "Black vs 'White'", "Hispanic vs 'White'",
    "Other vs 'White'", "Unknown vs 'White'",
    "Medicaid vs 'private'", "Medicare vs 'private'", "undocumented vs 'private'",
    "non-English vs 'English'", "undocumented vs 'English'",
]


def _save(fig, name: str) -> None:
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote figures/{name}.png")


N_MIMIC_ED = 425_087  # all ED stays in MIMIC-IV-ED v2.2 (PhysioNet), 2011-2019


def fig_flow() -> None:
    from analysis_refinement.scenario_runs import load_inputs

    stays, ev, _ = load_inputs()
    s = stays[stays["diagnosis_type"].isin(["acute_pancreatitis", "trauma"])]
    n_dx = len(s)

    # step 2 -> 3: at least one numeric pain score
    num = ev[ev["pain_numeric"].notna()].sort_values(["stay_id", "pain_charttime"])
    first = num.groupby("stay_id", as_index=False).first().rename(
        columns={"pain_charttime": "initial_pain_time"})
    second = num.groupby("stay_id").nth(1).reset_index(drop=True)[
        ["stay_id", "pain_charttime"]].rename(
        columns={"pain_charttime": "numeric_reassessment_time"})
    df = s.merge(first[["stay_id", "initial_pain_time"]], on="stay_id", how="inner")
    df = df.merge(second, on="stay_id", how="left")
    n_pain = len(df)

    # step 3 -> 4: split the final exclusion into its two reasons, mirroring
    # the S6 event definition (text entries can be the first reassessment)
    txt = ev[ev["text_group"].notna()][["stay_id", "pain_charttime"]]
    txt = txt.merge(first[["stay_id", "initial_pain_time"]], on="stay_id", how="inner")
    txt = txt[txt["pain_charttime"] > txt["initial_pain_time"]]
    first_txt = (txt.sort_values("pain_charttime").groupby("stay_id", as_index=False)
                 .first().rename(columns={"pain_charttime": "text_reassessment_time"}))
    df = df.merge(first_txt[["stay_id", "text_reassessment_time"]], on="stay_id", how="left")
    df["first_reassessment_time"] = df[
        ["numeric_reassessment_time", "text_reassessment_time"]].min(axis=1)
    df["time_end"] = df["first_reassessment_time"].where(
        df["first_reassessment_time"].notna(), df["outtime"])
    dur = (df["time_end"] - df["initial_pain_time"]).dt.total_seconds() / 60
    esi = pd.to_numeric(df["triage_acuity"], errors="coerce")
    n_nonpos = int((dur <= 0).sum())
    n_esi = int((esi.isna() & (dur > 0)).sum())

    full = pd.read_csv(OUT / "primary_cohort.csv", usecols=["stay_id"])
    cc = pd.read_csv(OUT / "primary_cohort_cc.csv",
                     usecols=["stay_id", "reassessment_event"])
    n_cc = len(cc)
    n_covar = len(full) - n_cc  # missing first vitals or age

    steps = [
        (f"MIMIC-IV-ED: all ED stays, 2011–2019\nn = {N_MIMIC_ED:,}",
         f"no acute pancreatitis or\ntrauma ED diagnosis: {N_MIMIC_ED - n_dx:,}"),
        (f"Acute pancreatitis or trauma ED diagnosis\nn = {n_dx:,}",
         f"no numeric pain score\ndocumented: {n_dx - n_pain:,}"),
        (f"≥1 numeric pain score (0–10) during the stay\nn = {n_pain:,}",
         f"first score charted at/after\nED departure: {n_nonpos:,}\n"
         f"missing triage acuity: {n_esi:,}\n"
         f"missing first vital signs or age: {n_covar:,}"),
        (f"Triage acuity documented,\ncomplete covariate data\nn = {n_cc:,}", None),
        (f"PRIMARY ANALYTIC COHORT\nn = {n_cc:,} "
         f"({int(cc['reassessment_event'].sum()):,} reassessed)", None),
    ]

    fig, ax = plt.subplots(figsize=(7.4, 7.8))
    ax.axis("off")
    y = 0.97
    box_h, gap = 0.135, 0.055
    for i, (label, side) in enumerate(steps):
        face = "#eef4fb" if i < len(steps) - 1 else "#dbe9d8"
        ax.add_patch(plt.Rectangle((0.03, y - box_h), 0.72, box_h,
                                   facecolor=face, edgecolor="#333", lw=1.1))
        ax.text(0.39, y - box_h / 2, label, ha="center", va="center", fontsize=8.6)
        if side:
            ax.annotate("", xy=(0.9, y - box_h / 2 - 0.001), xytext=(0.76, y - box_h / 2 - 0.001),
                        arrowprops=dict(arrowstyle="->", color="#777"))
            ax.text(0.91, y - box_h / 2, f"Excluded:\n{side}", ha="left", va="center",
                    fontsize=8.2, color="#555")
        if i < len(steps) - 1:
            ax.annotate("", xy=(0.39, y - box_h - gap + 0.008), xytext=(0.39, y - box_h - 0.004),
                        arrowprops=dict(arrowstyle="->", color="#333"))
        y -= box_h + gap
    ax.set_xlim(0, 1.35)
    ax.set_ylim(0, 1)
    _save(fig, "fig_final_flow")


def fig_forest() -> None:
    t = pd.read_csv(OUT / "primary_m1_m4_terms.csv")
    m4 = t[t["model"] == "M4"].set_index("comparison")

    groups = [
        ("Race / ethnicity (ref White)",
         ["Asian vs 'White'", "Black vs 'White'", "Hispanic vs 'White'",
          "Other vs 'White'", "Unknown vs 'White'"]),
        ("Insurance (ref private)",
         ["Medicaid vs 'private'", "Medicare vs 'private'", "undocumented vs 'private'"]),
        ("Language (ref English)",
         ["non-English vs 'English'", "undocumented vs 'English'"]),
        ("Age (ref 40–64)", ["18–39 vs '40-64'", "65+ vs '40-64'"]),
        ("Sex", ["M vs 'F'"]),
        ("Clinical", ["initial_pain_score", "triage_acuity"]),
    ]

    labels, hrs, los, his, header_rows = [], [], [], [], []
    for gname, terms in groups:
        header_rows.append(len(labels))
        labels.append(gname)
        hrs.append(np.nan); los.append(np.nan); his.append(np.nan)
        for term in terms:
            row = None
            if term in m4.index:
                row = m4.loc[term]
            else:
                hit = m4[m4.index.astype(str).str.replace("–", "-") ==
                         term.replace("–", "-")]
                sub = t[(t["model"] == "M4") & (t["term"] == term)]
                if len(hit):
                    row = hit.iloc[0]
                elif len(sub):
                    row = sub.iloc[0]
            if row is None:
                continue
            nice = {"initial_pain_score": "Initial pain score (per point)",
                    "triage_acuity": "Triage acuity (per ESI level)"}.get(
                        term, term.replace("'", ""))
            labels.append("   " + nice)
            hrs.append(float(row["hazard_ratio"]))
            los.append(float(row["ci_low"]))
            his.append(float(row["ci_high"]))

    ys = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(7.6, 0.34 * len(labels) + 1.4))
    for y, hr, lo, hi in zip(ys, hrs, los, his):
        if np.isnan(hr):
            continue
        sig = lo > 1 or hi < 1
        color = "#b2182b" if (sig and hr < 1) else ("#2166ac" if sig else "#666")
        ax.plot([lo, hi], [y, y], color=color, lw=1.6)
        ax.plot(hr, y, "o", color=color, ms=5.5)
        ax.text(1.62, y, f"{hr:.2f} ({lo:.2f}–{hi:.2f})",
                va="center", fontsize=8.2, color="#333")
    for i, lab in enumerate(labels):
        w = "bold" if i in header_rows else "normal"
        ax.text(-0.02, ys[i], lab, ha="right", va="center", fontsize=8.6,
                weight=w, transform=ax.get_yaxis_transform())
    ax.axvline(1.0, color="#999", lw=0.9, ls="--")
    ax.set_xlim(0.55, 1.6)
    ax.set_xscale("log")
    ax.set_xticks([0.6, 0.8, 1.0, 1.2, 1.4])
    ax.set_xticklabels(["0.6", "0.8", "1.0", "1.2", "1.4"], fontsize=8.5)
    ax.set_yticks([])
    ax.set_ylim(-0.8, len(labels) - 0.2)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("Adjusted HR for first pain reassessment (M4; log scale)\n"
                  "HR < 1 = slower reassessment", fontsize=9)
    ax.set_title("Primary model, inclusive cohort (n = 42,076; 31,313 events)",
                 fontsize=10)
    _save(fig, "fig_final_forest")


SECTIONS = [
    ("ED context / workflow", [
        ("ed_census_at_initial_pain_hour", "ED census at initial pain (per patient)"),
        ("ed_arrivals_past_1hr", "ED arrivals past 1 h (per arrival)"),
        ("arrival_weekend", "Weekend arrival"),
        ("night vs 'day'", "Night vs day arrival"),
        ("evening vs 'day'", "Evening vs day arrival"),
        ("other vs 'walk_in'", "Other vs walk-in arrival"),
        ("ambulance vs 'walk_in'", "Ambulance vs walk-in arrival"),
    ]),
    ("Clinical severity", [
        ("triage_acuity", "Triage acuity (per ESI level)"),
        ("heartrate_0_z", "First heart rate (per SD)"),
        ("resprate_0_z", "First respiratory rate (per SD)"),
        ("sbp_0_z", "First systolic BP (per SD)"),
    ]),
    ("Diagnosis / injury (ref acute pancreatitis)", [
        ("fall vs 'acute_pancreatitis'", "Fall"),
        ("fracture_dislocation vs 'acute_pancreatitis'", "Fracture / dislocation"),
        ("other_trauma vs 'acute_pancreatitis'", "Other trauma"),
    ]),
    ("Insurance (ref private)", [
        ("Medicaid vs 'private'", "Medicaid"),
        ("Medicare vs 'private'", "Medicare"),
        ("undocumented vs 'private'", "Undocumented"),
    ]),
    ("Demographics", [
        ("Asian vs 'White'", "Asian vs White"),
        ("Black vs 'White'", "Black vs White"),
        ("Hispanic vs 'White'", "Hispanic vs White"),
        ("Other vs 'White'", "Other vs White"),
        ("Unknown vs 'White'", "Unknown vs White"),
        ("18-39 vs '40-64'", "Age 18–39 vs 40–64"),
        ("65+ vs '40-64'", "Age 65+ vs 40–64"),
        ("M vs 'F'", "Male vs female"),
        ("non-English vs 'English'", "Non-English vs English"),
        ("undocumented vs 'English'", "Undocumented language vs English"),
    ]),
    ("Clinical presentation", [
        ("initial_pain_score", "Initial pain score (per point)"),
    ]),
]


def fig_forest_sectional() -> None:
    """Comprehensive M4 forest organized by model domain (mirrors the committed
    pipeline's sectional forest). Era terms adjusted for but not shown."""
    t = pd.read_csv(OUT / "primary_m1_m4_terms.csv")
    m4 = t[t["model"] == "M4"].copy()
    m4["key"] = m4["comparison"].fillna(m4["term"])
    lookup = {str(k).replace("–", "-"): r for k, r in
              zip(m4["key"], m4.to_dict("records"))}
    for r in m4.to_dict("records"):
        lookup[str(r["term"])] = r

    labels, hrs, los, his, headers = [], [], [], [], []
    for section, terms in SECTIONS:
        headers.append(len(labels))
        labels.append(section)
        hrs.append(np.nan); los.append(np.nan); his.append(np.nan)
        for key, nice in terms:
            r = lookup.get(key.replace("–", "-"))
            if r is None:
                continue
            labels.append("   " + nice)
            hrs.append(float(r["hazard_ratio"]))
            los.append(float(r["ci_low"]))
            his.append(float(r["ci_high"]))
        labels.append(""); hrs.append(np.nan); los.append(np.nan); his.append(np.nan)

    ys = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(8.4, 0.3 * len(labels) + 1.2))
    for y, hr, lo, hi in zip(ys, hrs, los, his):
        if np.isnan(hr):
            continue
        sig = lo > 1 or hi < 1
        color = "#b2182b" if (sig and hr < 1) else ("#2166ac" if sig else "#666")
        ax.plot([lo, hi], [y, y], color=color, lw=1.6)
        ax.plot(hr, y, "o", color=color, ms=5)
        ax.text(1.47, y, f"{hr:.2f} ({lo:.2f}–{hi:.2f})",
                va="center", fontsize=8.1, color="#333")
    for i, lab in enumerate(labels):
        if not lab:
            continue
        w = "bold" if i in headers else "normal"
        ax.text(-0.02, ys[i], lab, ha="right", va="center", fontsize=8.5,
                weight=w, transform=ax.get_yaxis_transform())
    ax.axvline(1.0, color="#999", lw=0.9, ls="--")
    ax.set_xscale("log")
    ax.set_xlim(0.62, 1.45)
    ax.set_xticks([0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3])
    ax.set_xticklabels(["0.7", "0.8", "0.9", "1.0", "1.1", "1.2", "1.3"], fontsize=8.5)
    ax.set_yticks([])
    ax.set_ylim(-0.6, len(labels) - 0.4)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("Adjusted HR for first pain reassessment (log scale)\n"
                  "HR < 1 = slower reassessment · calendar era adjusted, not shown",
                  fontsize=9)
    ax.set_title("Primary model (M4), inclusive cohort — n = 42,076; 31,313 events",
                 fontsize=10)
    _save(fig, "fig_final_forest_sectional")


def fig_absolute() -> None:
    curves = pd.read_csv(OUT / "finegray_cif_curves.csv")
    std = pd.read_csv(OUT / "standardized_probs.csv")

    fig, (a, b) = plt.subplots(1, 2, figsize=(10.6, 4.3),
                               gridspec_kw={"width_ratios": [1.25, 1]})
    for grp, sub in curves.groupby("group"):
        sub = sub[sub["time"] <= 360]
        a.step(sub["time"], sub["est"] * 100, where="post",
               color=INS_COLORS.get(grp, "#333"), lw=1.7, label=grp)
    a.set_xlabel("Minutes since initial pain documentation", fontsize=9.5)
    a.set_ylabel("Reassessed (%), cumulative incidence", fontsize=9.5)
    a.set_xlim(0, 360); a.set_ylim(0, None)
    a.legend(frameon=False, fontsize=9, title="Insurance", title_fontsize=9)
    a.set_title("A. Observed cumulative incidence\n(ED departure as competing event)",
                fontsize=9.8, loc="left")
    a.grid(alpha=0.25)

    order = ["private", "Medicare", "undocumented", "Medicaid"]
    width = 0.38
    x = np.arange(len(order))
    for i, t in enumerate((60, 120)):
        vals = [std[(std["insurance_set_to"] == g) & (std["t_min"] == t)]
                ["std_prob_reassessed"].iloc[0] * 100 for g in order]
        bars = b.bar(x + (i - 0.5) * width, vals, width,
                     color=["#c6dbef", "#6baed6"][i], edgecolor="#333", lw=0.6,
                     label=f"by {t} min")
        for xi, v in zip(x + (i - 0.5) * width, vals):
            b.text(xi, v + 0.5, f"{v:.1f}", ha="center", fontsize=8)
    b.set_xticks(x)
    b.set_xticklabels(order, fontsize=9)
    b.set_ylabel("Standardized P(reassessed) (%)", fontsize=9.5)
    b.legend(frameon=False, fontsize=9)
    b.set_title("B. Cox-standardized probability\n(cohort-standardized, M4 covariates)",
                fontsize=9.8, loc="left")
    b.grid(axis="y", alpha=0.25)
    for s in ("top", "right"):
        a.spines[s].set_visible(False); b.spines[s].set_visible(False)
    fig.tight_layout()
    _save(fig, "fig_final_absolute")


def fig_cox_vs_fg() -> None:
    cox = pd.read_csv(OUT / "primary_m1_m4_terms.csv")
    cox = cox[cox["model"] == "M4"]
    fg = pd.read_csv(OUT / "finegray_shr.csv")

    fg_map = {
        "race_ethnicityAsian": "Asian vs 'White'",
        "race_ethnicityBlack": "Black vs 'White'",
        "race_ethnicityHispanic": "Hispanic vs 'White'",
        "race_ethnicityUnknown": "Unknown vs 'White'",
        "insurance_groupMedicaid": "Medicaid vs 'private'",
        "insurance_groupMedicare": "Medicare vs 'private'",
        "insurance_groupundocumented": "undocumented vs 'private'",
        "language_groupnon-English": "non-English vs 'English'",
        "language_groupundocumented": "undocumented vs 'English'",
    }
    fg = fg[fg["term"].isin(fg_map)].copy()
    fg["comparison"] = fg["term"].map(fg_map)

    rows = []
    for comp in fg["comparison"]:
        c = cox[cox["comparison"] == comp]
        f = fg[fg["comparison"] == comp]
        if len(c) and len(f):
            rows.append((comp, c.iloc[0], f.iloc[0]))

    ys = np.arange(len(rows))[::-1]
    fig, ax = plt.subplots(figsize=(6.8, 0.42 * len(rows) + 1.3))
    for y, (comp, c, f) in zip(ys, rows):
        ax.plot([c["ci_low"], c["ci_high"]], [y + 0.13] * 2, color="#2166ac", lw=1.5)
        ax.plot(c["hazard_ratio"], y + 0.13, "o", color="#2166ac", ms=5)
        ax.plot([f["ci_low"], f["ci_high"]], [y - 0.13] * 2, color="#b2182b", lw=1.5)
        ax.plot(f["sHR"], y - 0.13, "s", color="#b2182b", ms=5)
        ax.text(-0.02, y, comp.replace("'", ""), ha="right", va="center",
                fontsize=8.6, transform=ax.get_yaxis_transform())
    ax.axvline(1.0, color="#999", lw=0.9, ls="--")
    ax.set_yticks([])
    ax.set_xlabel("HR / sHR (log scale)", fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks([0.8, 0.9, 1.0, 1.1, 1.2])
    ax.set_xticklabels(["0.8", "0.9", "1.0", "1.1", "1.2"], fontsize=8.5)
    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([], [], color="#2166ac", marker="o", ls="-", label="Cause-specific Cox (M4)"),
        Line2D([], [], color="#b2182b", marker="s", ls="-",
               label="Fine–Gray sHR (structural departures competing)"),
    ], frameon=False, fontsize=8.4, loc="upper left", bbox_to_anchor=(0.0, 1.10))
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title("Competing-risk robustness: Cox vs Fine–Gray", fontsize=10, pad=28)
    _save(fig, "fig_final_cox_vs_fg")


if __name__ == "__main__":
    fig_flow()
    fig_forest()
    fig_forest_sectional()
    fig_absolute()
    fig_cox_vs_fg()
