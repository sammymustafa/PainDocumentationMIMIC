#!/usr/bin/env python3
"""Render Table 1 as a clean publication-style PNG/PDF.

Run: ./.venv/bin/python analysis_refinement/make_table1_png.py
Out: figures/table1.png / table1.pdf
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "final"
FIGS = HERE / "figures"

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["STIXGeneral", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"


def main() -> None:
    t1 = pd.read_csv(OUT / "table1.csv").fillna("")
    rows = t1[t1["characteristic"] != "N"]  # N goes in the title

    ROW_H = 1.0
    SECTION_PAD = 0.45
    items: list[tuple[str, str, str]] = []  # (kind, label, value)
    last_section = None
    for _, r in rows.iterrows():
        if r["section"] and r["section"] != last_section:
            items.append(("section", r["section"], ""))
            last_section = r["section"]
        label = r["characteristic"]
        kind = "indent" if label.startswith("  ") else "row"
        items.append((kind, label.strip(), r["value"]))

    heights = [ROW_H + (SECTION_PAD if k == "section" else 0) for k, _, _ in items]
    total_h = sum(heights)

    fig_h = 0.23 * total_h + 1.35
    fig, ax = plt.subplots(figsize=(7.0, fig_h))
    ax.axis("off")

    x_label, x_value = 0.045, 0.955
    top, bottom = 0.935, 0.045
    span = top - bottom - 0.035  # header band

    ax.text(0.5, 0.985, "Table 1: Characteristics of the analytic cohort ($N$ = 42,076)",
            ha="center", va="top", fontsize=12.6)

    y_header = top
    ax.text(x_label, y_header - 0.010, "Characteristic", ha="left", va="top", fontsize=10.6)
    ax.text(x_value, y_header - 0.010, "Value", ha="right", va="top", fontsize=10.6)

    rule = dict(color="#222", lw=1.0, clip_on=False)
    ax.plot([0.02, 0.98], [top + 0.012, top + 0.012], **rule)
    ax.plot([0.02, 0.98], [top - 0.026, top - 0.026], **rule)

    y = top - 0.038
    unit = span / total_h
    for (kind, label, value), h in zip(items, heights):
        y -= h * unit
        y_text = y + 0.35 * ROW_H * unit
        if kind == "section":
            ax.plot([0.02, 0.98], [y + h * unit - SECTION_PAD * unit * 0.45,
                                   y + h * unit - SECTION_PAD * unit * 0.45],
                    color="#222", lw=0.7, clip_on=False)
            ax.text(x_label, y_text, label, ha="left", va="center",
                    fontsize=10.4, style="italic")
        else:
            xl = x_label + (0.028 if kind == "indent" else 0.0)
            ax.text(xl, y_text, label, ha="left", va="center", fontsize=10.2)
            ax.text(x_value, y_text, value, ha="right", va="center", fontsize=10.2)

    ax.plot([0.02, 0.98], [y - 0.006, y - 0.006], **rule)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    FIGS.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"table1.{ext}", dpi=300, bbox_inches="tight",
                    facecolor="white")
    plt.close(fig)
    print(f"wrote {FIGS/'table1.png'}")


if __name__ == "__main__":
    main()
