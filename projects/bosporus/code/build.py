#!/usr/bin/env python
"""Render body.md -> index.html without Quarto.

body.md is a Quarto-flavoured markdown body: Pandoc fenced divs (`::: {.class}`),
raw-HTML blocks (```{=html}), heading attributes ({.class}) and `{{< include >}}`
shortcodes. Quarto renders it directly (`quarto render index.qmd`); this script
renders the same file with python-markdown so the site can be served on a box
with no Quarto installed. Keep both paths working — body.md is the single source.
"""
import argparse, pathlib, re, datetime, html
import markdown

S = pathlib.Path(__file__).resolve().parents[1]

ap = argparse.ArgumentParser()
ap.add_argument("--asset-prefix", default="",
                help="prefix for figures/ interactive/ crossing/ links, e.g. 'bosporus_files/'")
ap.add_argument("--out", default=str(S / "index.html"))
ap.add_argument("--inline-css", action="store_true", default=True)
A = ap.parse_args()

# ---- the DSLR section, generated so the page adapts to whatever is on disk ----
dslr = sorted(p for p in (S / "figures/dslr").glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
if dslr:
    tiles = "\n".join(
        f'<figure><a href="figures/dslr/{p.name}"><img loading="lazy" src="figures/dslr/{p.name}" '
        f'alt="DSLR photograph of the crossing"></a></figure>' for p in dslr)
    body = "::: {.gallery}\n```{=html}\n<div class=\"tiles\">\n" + tiles + "\n</div>\n```\n:::\n"
else:
    body = ("::: {.todo}\nDSLR photos: drop them into `figures/dslr/` and re-run `code/build.py`.\n:::\n\n"
            "![KHRIZOPRAZ off Salacak, 07:58 local (webcam)](figures/khrizopraz_salacak_best.jpg)\n\n"
            "![PIROP off Salacak, 09:27 local (webcam)](figures/pirop_salacak_best.jpg)\n")
(S / "dslr.md").write_text(body)

src = (S / "body.md").read_text()

# ---- resolve {{< include x.md >}} ----------------------------------------
def _inc(m):
    return (S / m.group(1)).read_text()
for _ in range(4):
    src, n = re.subn(r"\{\{<\s*include\s+([^\s>]+)\s*>\}\}", _inc, src)
    if not n:
        break

# ---- asset prefix (for a site that serves the assets from a sidecar dir) --
if A.asset_prefix:
    src = re.sub(r'(?<=[("])(figures/|interactive/|crossing/)', A.asset_prefix + r"\1", src)

# ---- protect ```{=html} blocks -------------------------------------------
raw = []
def _raw(m):
    raw.append(m.group(1))
    return f"\n\nRAWHTMLTOKEN{len(raw)-1}RAWHTMLTOKEN\n\n"
src = re.sub(r"```\{=html\}\n(.*?)\n```", _raw, src, flags=re.S)

# ---- Pandoc fenced divs -> <div class=...> (md_in_html keeps them parsed) --
out, stack = [], []
for line in src.split("\n"):
    m = re.match(r"^:::+\s*\{([^}]*)\}\s*$", line)
    if m:
        cls = " ".join(c[1:] for c in m.group(1).split() if c.startswith("."))
        out.append(f'<div class="{cls}" markdown="1">')
        stack.append(True)
        continue
    if re.match(r"^:::+\s*$", line) and stack:
        stack.pop()
        out.append("</div>")
        continue
    out.append(line)
src = "\n".join(out)

md = markdown.Markdown(extensions=["tables", "attr_list", "md_in_html", "toc", "sane_lists"],
                       extension_configs={"toc": {"permalink": False, "toc_depth": "2-2"}})
body_html = md.convert(src)
toc = md.toc

# ---- standalone image paragraphs -> <figure> with the alt text as caption ----
def _fig(m):
    tag, alt = m.group(0), m.group(1)
    return f"<figure>{tag[3:-4]}<figcaption>{alt}</figcaption></figure>"
body_html = re.sub(r'<p><img alt="([^"]*)"[^>]*></p>', _fig, body_html)

for i, r in enumerate(raw):
    body_html = body_html.replace(f"<p>RAWHTMLTOKEN{i}RAWHTMLTOKEN</p>", r).replace(
        f"RAWHTMLTOKEN{i}RAWHTMLTOKEN", r)

TITLE = "Frozen transponders in the Bosporus"
SUB = ""
built = datetime.datetime.now(datetime.timezone.utc).strftime("%d %B %Y")

page = (S / "code/template.html").read_text()
page = page.replace("{{CSS}}", (S / "code/site.css").read_text())
if "<li>" not in toc:   # no headings -> no contents column
    page = re.sub(r"<aside>.*?</aside>", "", page, flags=re.S).replace('<div class="shell">', '<div class="shell notoc">')
page = (page.replace("{{TITLE}}", html.escape(TITLE))
            .replace("{{SUB}}", html.escape(SUB))
            .replace("{{TOC}}", toc)
            .replace("{{BODY}}", body_html)
            .replace("{{BUILT}}", built))
out = pathlib.Path(A.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(page)
print("wrote", out, f"({len(page)/1024:.0f} KB), dslr photos: {len(dslr)}, prefix={A.asset_prefix!r}")
