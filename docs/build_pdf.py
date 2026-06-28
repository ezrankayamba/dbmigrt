#!/usr/bin/env python3
"""Render docs/SDD.md to docs/SDD.pdf with embedded diagrams.

Usage:  python docs/build_pdf.py
Requires: markdown, weasyprint  (pip install markdown weasyprint)
"""
import os
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

HERE = os.path.dirname(os.path.abspath(__file__))

md_text = open(os.path.join(HERE, "SDD.md"), encoding="utf-8").read()
html_body = markdown.markdown(
    md_text, extensions=["tables", "fenced_code", "toc", "sane_lists"]
)

CSS_TEXT = """
@page {
    size: A4; margin: 2cm 2cm 2.2cm 2cm;
    @bottom-center { content: "dbmigrt — Software Design Document";
                     font-size: 8pt; color: #888; }
    @bottom-right  { content: "Page " counter(page) " / " counter(pages);
                     font-size: 8pt; color: #888; }
}
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 22pt; color: #0b3d5b; border-bottom: 3px solid #0b3d5b;
     padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 15pt; color: #0b3d5b; border-bottom: 1px solid #ccc;
     padding-bottom: 3px; margin-top: 22px; }
h3 { font-size: 12pt; color: #244; margin-top: 16px; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt;
       background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 5px;
      padding: 10px; overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.5pt; line-height: 1.35; }
table { border-collapse: collapse; width: 100%; margin: 12px 0;
        font-size: 9.5pt; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 5px 8px; text-align: left;
         vertical-align: top; }
th { background: #0b3d5b; color: #fff; }
tr:nth-child(even) td { background: #f7f9fb; }
img { max-width: 100%; display: block; margin: 14px auto;
      page-break-inside: avoid; }
hr { border: none; border-top: 1px solid #ddd; margin: 18px 0; }
a { color: #0a66c2; text-decoration: none; }
strong { color: #000; }
"""

HTML(string=html_body, base_url=HERE).write_pdf(
    os.path.join(HERE, "SDD.pdf"),
    stylesheets=[CSS(string=CSS_TEXT, font_config=FontConfiguration())],
)
print("PDF written:", os.path.join(HERE, "SDD.pdf"))
