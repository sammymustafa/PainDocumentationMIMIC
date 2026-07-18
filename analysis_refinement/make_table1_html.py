#!/usr/bin/env python3
"""Table 1 as a compact HTML table for copy-paste into Google Docs.

Run: ./.venv/bin/python analysis_refinement/make_table1_html.py
Out: outputs/final/table1_gdoc.html  (open in browser, select table, copy,
     paste into the Google Doc — arrives as a real table, one page at 9.5pt)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "final"

CELL = "padding:1px 8px; font-family:Arial, sans-serif; font-size:9.5pt; border:none;"
SECTION = CELL + " font-style:italic; font-weight:bold; border-top:0.75pt solid #444; padding-top:3px;"
HEADER = CELL + " font-weight:bold; border-top:1.25pt solid #000; border-bottom:0.75pt solid #000;"
LAST = " border-bottom:1.25pt solid #000;"


def main() -> None:
    t1 = pd.read_csv(OUT / "table1.csv").fillna("")
    rows = t1[t1["characteristic"] != "N"]

    body: list[str] = []
    last_section = None
    items = list(rows.iterrows())
    for k, (_, r) in enumerate(items):
        is_last = k == len(items) - 1
        if r["section"] and r["section"] != last_section:
            body.append(
                f'<tr><td colspan="2" style="{SECTION}">{r["section"]}</td></tr>')
            last_section = r["section"]
        label = r["characteristic"]
        pad = "padding-left:22px;" if label.startswith("  ") else ""
        style = CELL + pad + (LAST if is_last else "")
        vstyle = CELL + "text-align:right;" + (LAST if is_last else "")
        body.append(
            f'<tr><td style="{style}">{label.strip()}</td>'
            f'<td style="{vstyle}">{r["value"]}</td></tr>')

    html = f"""<!doctype html>
<meta charset="utf-8">
<title>Table 1</title>
<body style="margin:24px;">
<p style="font-family:Arial, sans-serif; font-size:10.5pt;"><b>Table 1.</b>
Characteristics of the analytic cohort (<i>N</i> = 42,076)</p>
<table cellspacing="0" cellpadding="0" style="border-collapse:collapse; width:460px;">
<tr><td style="{HEADER}">Characteristic</td>
<td style="{HEADER} text-align:right;">Value</td></tr>
{chr(10).join(body)}
</table>
<p style="font-family:Arial, sans-serif; font-size:8.5pt; color:#444;">
ESI, Emergency Severity Index (1 = most acute); BP, blood pressure;
IQR, interquartile range. Undocumented insurance/language: no linked hospital
admission record. Time to reassessment summarized among reassessed stays.</p>
</body>"""
    path = OUT / "table1_gdoc.html"
    path.write_text(html)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
