#!/usr/bin/env python3
"""Render DRAFT_AJPH_v2.md as styled HTML for copy-paste into Google Docs.

Open the output in a browser, select all (Cmd+A), copy, paste into the Doc:
headings, bold/italic, superscripts, and both tables arrive formatted.

Run: ./.venv/bin/python analysis_refinement/make_draft_html.py
Out: outputs/final/draft_ajph_v2_gdoc.html
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE / "DRAFT_AJPH_v2.md"
OUT = HERE / "outputs" / "final" / "draft_ajph_v2_gdoc.html"

STYLE = """
body { font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.45;
       color: #111; max-width: 7.4in; margin: 36px auto; }
h1 { font-size: 15.5pt; line-height: 1.25; }
h2 { font-size: 13pt; margin-top: 22px; }
h3 { font-size: 11.5pt; margin-top: 16px; }
p  { margin: 9px 0; }
table { border-collapse: collapse; font-size: 9pt; margin: 10px 0; }
th, td { border: 0.5pt solid #888; padding: 2px 7px; text-align: left; }
th { background: #f1f1f1; }
ol li { margin: 5px 0; }
.editor-note { color: #777; font-style: italic; font-size: 9.5pt; }
"""


def main() -> None:
    text = SRC.read_text()
    # surface the HTML comment (reference housekeeping) as a visible note
    text = re.sub(
        r"<!--\s*(.*?)\s*-->",
        lambda m: f'<p class="editor-note">[Editor note: {m.group(1)}]</p>',
        text,
        flags=re.S,
    )
    body = markdown.markdown(text, extensions=["tables"])
    html = (f'<!doctype html>\n<meta charset="utf-8">\n<title>Pain Reassessment '
            f'Draft (Google Docs paste version)</title>\n<style>{STYLE}</style>\n'
            f"<body>\n{body}\n</body>")
    OUT.write_text(html)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
