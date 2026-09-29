"""Capture hi-res stills of the page states used by the video (2x device scale).

Every state is a real page state reached by clicking the real UI; no page content is edited.
Writes stills/<name>.png (3840x2160) and stills/rects.json (CSS-px boxes of the elements the
camera and the cursor aim at).

Usage:  python capture.py [SITE_ROOT]
  SITE_ROOT  URL serving a soa2usdm-collections checkout (default http://127.0.0.1:8765/)
"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/").rstrip("/") + "/"
ROOT = SITE + "collections/usdm_data/protocols/"
REVIEW = ROOT + "NCT04184622/SoA2USDM/extracted/NCT04184622_review.html"
OUT = Path("stills"); OUT.mkdir(exist_ok=True)
rects = {}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    def box(sel):
        bb = pg.locator(sel).first.bounding_box()
        assert bb, sel
        return [round(bb["x"], 1), round(bb["y"], 1), round(bb["width"], 1), round(bb["height"], 1)]

    def snap(name, sels):
        pg.mouse.move(1919, 1079)
        pg.wait_for_timeout(1400)          # let smooth scrolls and image loads finish
        pg.screenshot(path=str(OUT / f"{name}.png"))
        rects[name] = {k: box(v) for k, v in sels.items()}

    # --- index
    pg.goto(ROOT + "index.html", wait_until="networkidle")
    snap("index", {"review_col": "th:has-text('Review')",
                   "row184": "tr:has(td:has-text('NCT04184622'))",
                   "table": "table"})
    # review-column cells, for the spotlight
    rects["index"]["review_cells"] = pg.evaluate("""()=>{
        const th=[...document.querySelectorAll('th')].find(t=>t.textContent.trim()==='Review');
        const i=[...th.parentNode.children].indexOf(th);
        const cells=[...document.querySelectorAll('tbody tr')].map(r=>r.children[i]).filter(c=>c && c.textContent.includes('decided'));
        const a=cells[0].getBoundingClientRect(), z=cells[cells.length-1].getBoundingClientRect();
        return [a.x, th.getBoundingClientRect().y, a.width, z.bottom-th.getBoundingClientRect().y, cells.length];}""")

    # --- review page, initial state (Table 1, p.18)
    pg.goto(REVIEW, wait_until="networkidle")
    snap("start", {"tiles": "#tiles", "tile_rows": "#tiles .tile:nth-child(2)",
                   "tile_marks": "#tiles .tile:nth-child(4)", "tile_dec": "#tiles .tile:nth-child(5)",
                   "pagewrap": "#pagewrap", "pageimg": "#pageimg", "right": "#right",
                   "tablewrap": "#tablewrap", "side": "#side", "header": "body > *:first-child"})

    # --- table scrolled to row 32 (OGTT), before the click
    pg.evaluate("""()=>{const w=document.getElementById('tablewrap'), tr=document.querySelector('#soa tr[data-row="32"]');
                    w.scrollTo({top:Math.max(0,tr.offsetTop-w.clientHeight/2)});}""")
    snap("pre_row", {"row32": "#soa tr[data-row='32'] td.name", "tablewrap": "#tablewrap", "pagewrap": "#pagewrap"})

    # --- click row 32: page jumps to doc p.20, printed row highlighted
    pg.locator("#soa tr[data-row='32'] td.name").click(position={"x": 40, "y": 10})
    snap("row", {"row32": "#soa tr[data-row='32'] td.name", "band": "#overlay rect.sel",
                 "pagetab": "#pagetabs button.on", "pagewrap": "#pagewrap", "tablewrap": "#tablewrap"})

    # --- click header row 'Week of Treatment' (property row 2): its printed band on p.20
    pg.locator("#soa tr.hdr[data-prop='2'] th.name").click()
    snap("hdr", {"hdr2": "#soa tr.hdr[data-prop='2'] th.name", "band": "#overlay rect.header.sel",
                 "pagewrap": "#pagewrap", "tablewrap": "#tablewrap"})

    # --- click footnote marker n21 on row 32: Notes tab, note card, bound row
    pg.locator("#soa tr[data-row='32'] sup.mk[data-m='n21']").first.click()
    pg.evaluate("()=>{document.querySelector('.notecard.on').scrollIntoView({block:'center'}); window.scrollTo(0,0);}")
    snap("note", {"sup": "#soa tr[data-row='32'] sup.mk[data-m='n21']", "card": ".notecard.on",
                  "band": "#overlay rect.note", "row32": "#soa tr[data-row='32'] td.name",
                  "side": "#side", "pagewrap": "#pagewrap"})

    # --- Decisions tab (overview), then D2 selected
    pg.locator("#sidetabs button[data-t='dec']").click()
    pg.evaluate("()=>document.querySelector('#side .body, #tab-dec').scrollTo && document.getElementById('tab-dec').scrollIntoView({block:'nearest'})")
    snap("dec", {"tab": "#sidetabs button[data-t='dec']", "d2": ".dec[data-id='D2']", "side": "#side",
                 "sidetabs": "#sidetabs"})
    pg.locator(".dec[data-id='D2'] .c").first.click()
    snap("dec_d2", {"d2": ".dec[data-id='D2']", "pill": ".dec[data-id='D2'] .pill.done",
                    "band": "#overlay rect.note", "row25": "#soa tr[data-row='25'] td.name",
                    "pagetab": "#pagetabs button.on", "pagewrap": "#pagewrap", "side": "#side"})

    # --- Table 1 extraction JSON viewer, and the consolidated SoA page (no clicks, top of page)
    for name, url in (("json", ROOT + "NCT04184622/SoA2USDM/extracted/NCT04184622_Table_01_extraction_viewer.html"),
                      ("consol", ROOT + "NCT04184622/SoA2USDM/consolidated/NCT04184622_consolidated.html")):
        pg.goto(url, wait_until="networkidle")
        snap(name, {})

    json.dump(rects, open(OUT / "rects.json", "w"), indent=1)
    print("page errors:", errs)
    b.close()
