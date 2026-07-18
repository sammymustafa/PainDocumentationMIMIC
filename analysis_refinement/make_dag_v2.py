#!/usr/bin/env python3
"""DAG v2 — decomposed causal structure for ED pain reassessment.

Improvements over fig01 per PI feedback:
  * every block broken into individual nodes (no lumped 'patient/social')
  * mediators (analgesia, disposition) drawn explicitly as downstream, dashed
  * NEW: selection nodes (squares) showing where cohort entry conditions on
    documentation — insurance documented (via admission) and pain documented —
    the mechanism the exclusion audit exposed
  * edge classes: confounding (grey), disparity paths of interest (red dashed),
    mediation (blue), selection (black double-line square nodes)

Output: analysis_refinement/figures/dag_v2.(png|pdf)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

FIGS = Path(__file__).resolve().parent / "figures"
FIGS.mkdir(exist_ok=True)

# ---- palette ----
C_SOCIAL = "#c0392b"
C_CLIN = "#7f8c8d"
C_TRIAGE = "#b7950b"
C_OPS = "#5b2c6f"
C_OUT = "#1e8449"
C_MED = "#2471a3"
C_SEL = "#17202a"

FILL = {
    "social": "#fdedec", "clin": "#f2f3f4", "triage": "#fef9e7",
    "ops": "#f4ecf7", "out": "#e9f7ef", "med": "#eaf2f8", "sel": "#fdfefe",
}
EDGE = {
    "social": C_SOCIAL, "clin": C_CLIN, "triage": C_TRIAGE,
    "ops": C_OPS, "out": C_OUT, "med": C_MED, "sel": C_SEL,
}

# ---- nodes: name -> (x, y, kind, label) ----
N = {
    # social identity (exposures of interest)
    "race":      (0.06, 0.86, "social", "Race /\nethnicity"),
    "insurance": (0.06, 0.68, "social", "Insurance"),
    "language":  (0.06, 0.50, "social", "Language"),
    "age_sex":   (0.06, 0.32, "social", "Age, sex"),
    # clinical presentation
    "dx":        (0.26, 0.92, "clin", "Diagnosis\n(AP / trauma)"),
    "pain0":     (0.26, 0.74, "clin", "Initial pain\nscore"),
    "vitals":    (0.26, 0.56, "clin", "Vital signs"),
    "comorbid":  (0.26, 0.38, "clin", "Comorbidity"),
    # triage
    "esi":       (0.45, 0.74, "triage", "ESI triage\nacuity"),
    # ED operations
    "mode":      (0.45, 0.92, "ops", "Arrival mode"),
    "shift":     (0.63, 0.92, "ops", "Shift /\nweekend"),
    "crowd":     (0.63, 0.74, "ops", "ED crowding\n(census, arrivals)"),
    "era":       (0.63, 0.56, "ops", "Calendar era"),
    # outcome
    "out":       (0.88, 0.66, "out", "Time to first\npain reassessment"),
    # mediators (downstream, NOT in primary model)
    "rx":        (0.55, 0.28, "med", "Analgesia\n(mediator)"),
    "dispo":     (0.74, 0.28, "med", "Disposition\nadmit vs home\n(mediator/collider)"),
    # selection (square)
    "sel_ins":   (0.30, 0.10, "sel", "S1: insurance documented\n(requires admission record)"),
    "sel_pain":  (0.62, 0.10, "sel", "S2: pain documented\n(cohort entry)"),
}

ARROWS = [
    # social -> clinical/triage/outcome (disparity paths of interest dashed red)
    ("race", "esi", "int"), ("race", "out", "int"),
    ("insurance", "out", "int"), ("insurance", "dispo", "int"),
    ("language", "esi", "int"), ("language", "out", "int"),
    ("age_sex", "pain0", "conf"), ("age_sex", "comorbid", "conf"), ("age_sex", "out", "conf"),
    # clinical structure
    ("dx", "pain0", "conf"), ("dx", "esi", "conf"), ("dx", "out", "conf"),
    ("pain0", "esi", "conf"), ("pain0", "rx", "med"), ("pain0", "out", "conf"),
    ("vitals", "esi", "conf"), ("comorbid", "vitals", "conf"), ("comorbid", "esi", "conf"),
    # triage -> downstream
    ("esi", "out", "conf"), ("esi", "dispo", "med"), ("esi", "rx", "med"),
    # operations
    ("mode", "esi", "conf"), ("mode", "out", "conf"),
    ("shift", "out", "conf"), ("crowd", "out", "conf"), ("crowd", "rx", "med"),
    ("era", "out", "conf"),
    # mediators -> outcome (dashed blue; analyzed separately, not in M4)
    ("rx", "out", "med"), ("dispo", "out", "med"),
    # selection machinery
    ("dispo", "sel_ins", "sel"), ("insurance", "sel_ins", "sel"),
    ("crowd", "sel_pain", "sel"), ("esi", "sel_pain", "sel"),
]

STYLE = {
    "conf": dict(color="#616a6b", ls="-", lw=1.3, alpha=0.75),
    "int":  dict(color=C_SOCIAL, ls=(0, (5, 3)), lw=1.8, alpha=0.9),
    "med":  dict(color=C_MED, ls=(0, (2, 2)), lw=1.5, alpha=0.9),
    "sel":  dict(color=C_SEL, ls=(0, (1, 1)), lw=1.3, alpha=0.8),
}

W, H = 0.115, 0.085


def draw():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    boxes = {}
    for k, (x, y, kind, label) in N.items():
        w = W * (1.55 if kind == "sel" else 1.25 if k == "out" else 1.0)
        h = H * (0.9 if kind == "sel" else 1.15 if k == "out" else 1.0)
        if kind == "sel":
            patch = Rectangle((x - w / 2, y - h / 2), w, h, fill=True,
                              facecolor=FILL[kind], edgecolor=EDGE[kind], lw=1.6, zorder=3)
            ax.add_patch(Rectangle((x - w / 2 - 0.005, y - h / 2 - 0.008),
                                   w + 0.01, h + 0.016, fill=False,
                                   edgecolor=EDGE[kind], lw=0.8, zorder=3))
        else:
            patch = FancyBboxPatch(
                (x - w / 2, y - h / 2), w, h,
                boxstyle="round,pad=0.008,rounding_size=0.015",
                facecolor=FILL[kind], edgecolor=EDGE[kind], lw=1.8, zorder=3)
        ax.add_patch(patch)
        fs = 9 if kind == "sel" else 10.5 if k != "out" else 12
        weight = "bold" if k == "out" else "normal"
        ax.text(x, y, label, ha="center", va="center", fontsize=fs,
                weight=weight, color="#1b2631", zorder=4)
        boxes[k] = (x, y, w, h)

    for a, b, cls in ARROWS:
        xa, ya, wa, ha = boxes[a]
        xb, yb, wb, hb = boxes[b]
        dx, dy = xb - xa, yb - ya
        # attach at box edges along the line
        import math
        ang = math.atan2(dy, dx)
        sx = xa + math.cos(ang) * (wa / 2 + 0.006)
        sy = ya + math.sin(ang) * (ha / 2 + 0.010)
        ex = xb - math.cos(ang) * (wb / 2 + 0.006)
        ey = yb - math.sin(ang) * (hb / 2 + 0.010)
        arr = FancyArrowPatch((sx, sy), (ex, ey),
                              arrowstyle="-|>", mutation_scale=13,
                              connectionstyle="arc3,rad=0.08",
                              zorder=2, **STYLE[cls])
        ax.add_patch(arr)

    ax.set_title("ED pain reassessment — decomposed causal structure (v2)",
                 fontsize=15, weight="bold", pad=14)

    # legend
    ly = 0.015
    items = [
        ("Disparity paths of interest", STYLE["int"]),
        ("Confounding / clinical structure (adjusted, M1–M4)", STYLE["conf"]),
        ("Mediation — analyzed separately, NOT in M4", STYLE["med"]),
        ("Selection into cohort/covariates (squares)", STYLE["sel"]),
    ]
    x0 = 0.01
    for label, st in items:
        ax.plot([x0, x0 + 0.03], [ly, ly], **{k: v for k, v in st.items()})
        ax.text(x0 + 0.037, ly, label, fontsize=8.5, va="center")
        x0 += 0.26
    ax.text(0.01, -0.03,
            "S1: insurance observed only when an admission record exists — conditioning on complete insurance selects toward admitted patients.\n"
            "S2: cohort entry requires a documented pain score; documentation itself depends on acuity and crowding.",
            fontsize=8.5, color="#424949", va="top")

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"dag_v2.{ext}", dpi=300, bbox_inches="tight")
    print(f"Wrote {FIGS/'dag_v2.png'} and .pdf")


if __name__ == "__main__":
    draw()
