"""Render title card, end card and caption plates as PNGs (Inter, via Playwright).

Needs the Inter webfont unpacked under fonts/ (see README.md); captions come from captions.json.
Writes gfx/title.png, gfx/end.png and gfx/cap_<key>.png.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

F = Path("fonts/package/files").resolve()
OUT = Path("gfx"); OUT.mkdir(exist_ok=True)

FONTS = "".join(
    f"@font-face{{font-family:Inter;font-weight:{w};src:url('file://{F}/inter-latin-{w}-normal.woff2') format('woff2')}}"
    for w in (400, 500, 600, 700, 800))

BASE = FONTS + """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1080px;font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased}
.card{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(1200px 900px at 15% 0%,#24497f 0%,#132a4d 45%,#0b1a31 100%)}
.grid{position:absolute;inset:0;opacity:.07;
      background-image:linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px);
      background-size:54px 54px}
.pad{position:absolute;left:96px;right:96px}
.eyebrow{font-weight:600;font-size:22px;letter-spacing:.18em;text-transform:uppercase;color:#f3c969}
h1{font-weight:800;font-size:112px;letter-spacing:-.035em;line-height:1}
.sub{font-weight:500;font-size:40px;line-height:1.28;color:#dbe5f3;letter-spacing:-.01em}
.rule{width:72px;height:6px;border-radius:3px;background:#f3c969}
.foot{font-weight:500;font-size:24px;color:#9fb3cf}
.foot b{color:#fff;font-weight:600}
.pill{display:inline-block;font-weight:600;font-size:24px;padding:10px 22px;border-radius:999px;
      border:1.5px solid rgba(255,255,255,.28);color:#fff;margin-right:12px}
.url{font-weight:600;font-size:38px;color:#fff;letter-spacing:-.01em}
.claude{display:flex;align-items:center;gap:14px;font-weight:500;font-size:26px;color:#dbe5f3}
.claude .dot{width:12px;height:12px;border-radius:50%;background:#d97757}
"""

TITLE = """<div class="card"><div class="grid"></div>
<div class="pad" style="top:340px"><div class="eyebrow">Proof of concept</div></div>
<div class="pad" style="top:392px"><h1>SoA2USDM</h1></div>
<div class="pad" style="top:540px"><div class="rule"></div></div>
<div class="pad" style="top:580px"><div class="sub">From a printed Schedule of Activities<br>to data you can check against the source</div></div>
<div class="pad" style="bottom:92px"><div class="foot"><b>Kerstin Forsberg</b></div></div>
</div>"""

END = """<div class="card"><div class="grid"></div>
<div class="pad" style="top:300px"><div class="eyebrow">SoA2USDM · proof of concept</div></div>
<div class="pad" style="top:356px">
  <span class="pill">Traceable</span><span class="pill">Checked</span><span class="pill">Human-decided</span></div>
<div class="pad" style="top:470px"><div class="rule"></div></div>
<div class="pad" style="top:512px"><div class="url">github.com/kerfors/soa2usdm</div></div>
<div class="pad" style="top:572px"><div class="sub" style="font-size:30px;color:#9fb3cf">Open code · public protocols · review pages on GitHub Pages</div></div>
<div class="pad" style="bottom:92px;display:flex;justify-content:space-between;align-items:center">
  <div class="foot"><b>Kerstin Forsberg</b></div>
  <div class="claude"><span class="dot"></span>Built with Claude</div></div>
</div>"""

CAP_CSS = FONTS + """
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:transparent;font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{width:1080px;display:flex;justify-content:center;padding:30px 0}
.cap{max-width:1010px;white-space:nowrap;background:rgba(11,22,42,.92);color:#fff;font-weight:600;font-size:36px;line-height:1.26;
     letter-spacing:-.012em;padding:20px 34px 22px;border-radius:18px;text-align:center;
     box-shadow:0 14px 40px rgba(0,0,0,.35),0 0 0 1px rgba(255,255,255,.06) inset}
.cap em{font-style:normal;color:#f3c969}
"""

CAPTIONS = json.load(open("captions.json"))

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1080})
    for name, body in (("title", TITLE), ("end", END)):
        (OUT / "tmp.html").write_text(f"<meta charset='utf-8'><style>{BASE}</style>{body}", encoding="utf-8")
        pg.goto((OUT / "tmp.html").resolve().as_uri()); pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT / f"{name}.png"))
    for key, text in CAPTIONS.items():
        pg.set_viewport_size({"width": 1080, "height": 400})
        (OUT / "tmp.html").write_text(f"<meta charset='utf-8'><style>{CAP_CSS}</style><div class='wrap'><div class='cap'>{text}</div></div>", encoding="utf-8")
        pg.goto((OUT / "tmp.html").resolve().as_uri()); pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(150)
        pg.locator(".wrap").screenshot(path=str(OUT / f"cap_{key}.png"), omit_background=True)
    b.close()
print("ok", len(CAPTIONS))
