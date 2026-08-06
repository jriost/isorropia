"""Regenera PLAN.html y PLAN.pdf desde PLAN.md. Uso: python make_pdf.py"""
import subprocess
from pathlib import Path

import markdown

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CSS = """
body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; color: #1a1a1a; font-size: 13px; line-height: 1.55; }
h1 { font-size: 26px; border-bottom: 3px solid #6F4E37; padding-bottom: 8px; }
h2 { font-size: 18px; color: #6F4E37; margin-top: 28px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
h3 { font-size: 14px; margin-top: 18px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th, td { border: 1px solid #ccc; padding: 5px 8px; text-align: left; font-size: 12px; }
th { background: #f3ede8; }
code { background: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-size: 11px; }
pre { background: #f8f8f8; border: 1px solid #ddd; padding: 10px; border-radius: 6px; font-size: 11px; overflow-x: hidden; }
blockquote { border-left: 3px solid #6F4E37; margin-left: 0; padding-left: 12px; color: #555; }
li { margin: 2px 0; }
@media print { body { margin: 10mm; } h2 { page-break-after: avoid; } table, pre { page-break-inside: avoid; } }
"""

here = Path(__file__).parent
body = markdown.markdown((here / "PLAN.md").read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
html_path = here / "PLAN.html"
html_path.write_text(
    f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>',
    encoding="utf-8",
)
subprocess.run([
    EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer",
    f"--print-to-pdf={here / 'PLAN.pdf'}", html_path.as_uri(),
], check=True)
print("PLAN.pdf regenerado")
