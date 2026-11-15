"""Build report/MotteBench.pdf from report/REPORT.md (Apart sprint template layout).
usage: python3 report/build_pdf.py   (needs: pip install markdown; weasyprint CLI)"""
import os, re, subprocess, markdown
D = os.path.dirname(os.path.abspath(__file__))
md = open(f"{D}/REPORT.md").read()
md = re.sub(r"^> DRAFT.*\n", "", md, flags=re.M)
body = markdown.markdown(md, extensions=["tables", "attr_list"])
# the first h1 is the title; the bold line after it is the author block
body = re.sub(r"<p><strong>(.*?)</strong> · (.*?)</p>", r'<p class="authors">\1<br><span>\2</span></p>', body, count=1)
css = """
@page { size: A4; margin: 22mm 20mm 20mm 20mm; @bottom-center { content: counter(page); font-size: 9pt; color: #666; } }
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; line-height: 1.42; color: #111; }
h1 { font-size: 17pt; line-height: 1.2; margin: 0 0 8pt; }
.authors { font-size: 10pt; color: #333; margin-bottom: 14pt; } .authors span { color: #666; }
h2 { font-size: 12.5pt; margin: 14pt 0 5pt; border-bottom: 1px solid #ddd; padding-bottom: 2pt; }
h3 { font-size: 10.5pt; margin: 10pt 0 4pt; }
p { margin: 0 0 6pt; text-align: justify; } li { margin-bottom: 3pt; }
table { border-collapse: collapse; width: 100%; font-size: 8.3pt; margin: 6pt 0 4pt; page-break-inside: avoid; }
th, td { border-bottom: 1px solid #ccc; padding: 2.5pt 4pt; text-align: left; vertical-align: top; } th { border-bottom: 1.5px solid #333; }
img { max-width: 82%; display: block; margin: 6pt auto 2pt; page-break-inside: avoid; }
p.caption, em.caption { font-size: 8.5pt; color: #444; }
code { font-size: 8.5pt; }
"""
html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
open(f"{D}/report.html", "w").write(html)
subprocess.run(["weasyprint", "-u", D + "/", f"{D}/report.html", f"{D}/MotteBench.pdf"], check=True)
print("wrote", f"{D}/MotteBench.pdf")
