"""Record the review-page walkthrough as a Playwright screencast (1920x960, .webm).

Usage:  python record.py [SITE_ROOT] [OUT_DIR]
  SITE_ROOT  root URL that serves cards.html and soa2usdm-collections/ (default
             http://127.0.0.1:8765/ — a local mirror, see README.md)
  OUT_DIR    where the .webm + marks.json land (default ./rec, wiped first)

The init script injects a visible cursor, a spotlight helper and a 14 px marker
square whose colour encodes the scene index (rgb(255, i*25, 0)); compose.py
reads that marker to time the captions, so captions never drift from the video.
"""
import json, shutil, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/").rstrip("/") + "/"
BASE = ROOT + "soa2usdm-collections/collections/usdm_data/protocols/"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "rec")
shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True)

INIT = r"""
(() => {
  function ready(fn){ if(document.readyState!=='loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  ready(() => {
    const st = document.createElement('style');
    st.textContent = `
      #__cap{position:fixed;left:0;right:0;bottom:0;z-index:99999;display:flex;justify-content:center;pointer-events:none;
             opacity:0;transition:opacity .35s ease;padding:0 0 36px}
      #__cap div{max-width:1640px;background:rgba(16,24,40,.90);color:#fff;font:500 28px/1.35 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
             padding:18px 34px;border-radius:12px;text-align:center;box-shadow:0 8px 30px rgba(0,0,0,.35)}
      #__cap div b{color:#ffd166;font-weight:600}
      #__cur{position:fixed;z-index:100000;width:26px;height:26px;pointer-events:none;transform:translate(-4px,-3px);
             transition:transform .08s}
      #__cur.down{transform:translate(-4px,-3px) scale(.8)}
      .__spot{outline:4px solid #ffd166 !important;outline-offset:4px;box-shadow:0 0 0 8px rgba(255,209,102,.25) !important;
              transition:outline-color .3s, box-shadow .3s}
      .__dim{transition:opacity .4s}
    `;
    document.head.appendChild(st);
    const mk = document.createElement('div'); mk.id='__mk0'; mk.style.cssText='position:fixed;left:0;top:0;width:14px;height:14px;z-index:100001;pointer-events:none;background:rgb(255,0,0)'; document.body.appendChild(mk);
    window.__setScene = (i) => { window.__scene=i; mk.style.background='rgb(255,'+(i*25)+',0)'; };
    const cur = document.createElement('div'); cur.id='__cur';
    cur.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M5 3l14 8.5-6.2 1.6L9.3 19z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    cur.style.left='-100px'; cur.style.top='-100px'; document.body.appendChild(cur);
    window.addEventListener('mousemove', e => { cur.style.left=e.clientX+'px'; cur.style.top=e.clientY+'px'; }, true);
    window.addEventListener('mousedown', () => cur.classList.add('down'), true);
    window.addEventListener('mouseup', () => cur.classList.remove('down'), true);
    window.__spot = (sel) => { document.querySelectorAll('.__spot').forEach(e=>e.classList.remove('__spot')); if(sel) document.querySelectorAll(sel).forEach(e=>e.classList.add('__spot')); };
  });
})();
"""

def run():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width":1920,"height":960}, device_scale_factor=1,
                            record_video_dir=str(OUT), record_video_size={"width":1920,"height":960})
        ctx.add_init_script(INIT)
        pg = ctx.new_page()
        marks = []          # (t, label) scene boundaries for verification
        t0 = time.time()
        def mark(label): marks.append((round(time.time()-t0,2), label))
        caps = []
        def cap(html=None):
            i = len(caps); caps.append(html or "")
            pg.evaluate("i=>window.__setScene(i)", i)
        def spot(sel=None):
            pg.evaluate("()=>window.__spot(null)")
            if sel: pg.locator(sel).evaluate_all("els=>els.forEach(e=>e.classList.add('__spot'))")
        def wait(ms): pg.wait_for_timeout(ms)
        def scroll_in(container, sel):
            pg.evaluate("""([c,s])=>{const w=document.querySelector(c), e=document.querySelector(s);
              const top = e.getBoundingClientRect().top - w.getBoundingClientRect().top + w.scrollTop - w.clientHeight/2 + e.offsetHeight/2;
              w.scrollTo({top:Math.max(0,top), behavior:'smooth'}); window.scrollTo(0,0);}""", [container, sel])
        def glide(sel, ms=700, dx=0, dy=0):
            bb = pg.locator(sel).first.bounding_box()
            x, y = bb["x"]+bb["width"]/2+dx, bb["y"]+bb["height"]/2+dy
            pg.mouse.move(x, y, steps=max(8, int(ms/25)))
            return x, y
        def click(sel, ms=700, dx=0, dy=0):
            x, y = glide(sel, ms, dx, dy); wait(150); pg.mouse.down(); wait(90); pg.mouse.up(); wait(120)

        # ---- 0 title card
        mark("title")
        pg.goto(ROOT+"cards.html", wait_until="load"); cap(""); wait(5000)

        # ---- 1 index
        mark("index")
        pg.goto(BASE+"index.html", wait_until="networkidle")
        pg.mouse.move(960, 600)
        wait(400)
        cap("Every protocol in the collection has a <b>review page</b> — human review is a step in the pipeline, not an afterthought.")
        spot("th:has-text('Review')"); pg.locator("a.link-review").evaluate_all("els=>els.forEach(e=>e.classList.add('__spot'))")
        wait(2200)
        glide("tr:has(td:has-text('NCT04184622')) a.link-review", 1200)
        wait(2400)
        click("tr:has(td:has-text('NCT04184622')) a.link-review", 300)
        pg.wait_for_load_state("networkidle")

        # ---- 2 tiles
        mark("tiles")
        pg.mouse.move(960, 760); wait(300)
        cap("The summary tiles are <b>independent checks re-derived from the PDF</b> — not the extractor's own report of itself.")
        spot("#tiles")
        wait(1200)
        glide("#tiles .tile:nth-child(2)", 900); wait(1500)
        glide("#tiles .tile:nth-child(4)", 900); wait(2000)
        spot(None)

        # ---- 3 panes
        mark("panes")
        cap("Left: the <b>source protocol page</b> with detected row bands overlaid.  Right: the <b>extracted table</b>. Nothing on the right exists without a place on the left.")
        spot("#pagewrap"); glide("#pagewrap", 800); wait(2600)
        spot("#tablewrap"); glide("#tablewrap", 800); wait(2600)
        spot(None)

        # ---- 4 click OGTT row
        mark("row")
        cap("Click an extracted row: the page jumps to <b>document page 20</b> and the printed row lights up. Row and marks are traceable to the cell they came from.")
        scroll_in("#tablewrap", "#soa tr[data-row='32']")
        wait(900)
        bb = pg.locator("#soa tr[data-row='32'] td.name").bounding_box()
        pg.mouse.move(bb["x"]+30, bb["y"]+14, steps=36); wait(150); pg.mouse.down(); wait(90); pg.mouse.up(); wait(120)
        wait(1800)
        glide("#pagetabs button.on", 800); wait(900)
        # sweep along the highlighted band on the page
        bb = pg.evaluate("""()=>{const b=document.querySelector('#overlay .sel, #overlay rect.sel, #overlay [class*=sel]'); if(!b) return null; const r=b.getBoundingClientRect(); return [r.x,r.y,r.width,r.height];}""")
        if bb:
            x, y, w, h = bb
            pg.mouse.move(x+20, y+h/2, steps=12); wait(300)
            pg.mouse.move(x+w-20, y+h/2, steps=40)
        wait(2600)

        # ---- 5 footnote
        mark("note")
        cap("Footnotes are <b>bound to the rows they govern</b>. The note is the page's own text, shown next to the row it changes.")
        click("#soa tr[data-row='32'] sup.mk[data-m='n21']", 900)
        wait(600)
        scroll_in("#side .body", ".notecard.on")
        wait(900)
        glide(".notecard.on", 700)
        spot(".notecard.on")
        wait(4200)
        spot(None)

        # ---- 6 checks
        mark("checks")
        cap("Precision, checked independently: every <b>×</b> in the page's text layer is binned into band and column and compared with the extraction.")
        click("#sidetabs button[data-t='check']", 800)
        wait(800)
        pg.evaluate("""()=>{const h=[...document.querySelectorAll('#tab-check h3')].find(x=>x.textContent.startsWith('Mark check')); h.id='__mk';}""")
        scroll_in("#side .body", "#__mk"); wait(900)
        glide("#__mk", 900)
        spot("#__mk")
        wait(4500)
        spot(None)

        # ---- 7 across tables
        mark("across")
        cap("The same activity across tables is matched with <b>both printed names</b> shown — the reviewer sees why, and can jump to either source.")
        click("#sidetabs button[data-t='across']", 800)
        wait(700)
        scroll_in("#side .body", ".foldcard[data-x='xact-027']")
        wait(900)
        spot(".foldcard[data-x='xact-027']")
        glide(".foldcard[data-x='xact-027']", 900)
        wait(2200)
        click(".foldcard[data-x='xact-027'] .src[data-t='2']", 700)
        wait(3400)
        spot(None)

        # ---- 8 decisions / draft
        mark("decisions")
        cap("Where the extractor's call could go the other way, the <b>reviewer decides here</b>. The page drafts the correction sidecar — nothing is saved from the browser; the decision is committed as data and the page regenerated.")
        click("#tabletabs button.tbl", 800)   # back to Table 1
        wait(500)
        click("#sidetabs button[data-t='dec']", 800)
        wait(800)
        glide("#draft", 900)
        spot("#draft")
        wait(6200)
        spot(None)

        # ---- 9 end card
        mark("end")
        pg.goto(ROOT+"cards.html#end", wait_until="load")
        cap("")
        pg.evaluate("()=>{document.getElementById('title').style.display='none';document.getElementById('end').style.display='flex';}")
        wait(5500)
        mark("stop")

        vid = pg.video
        pg.close(); ctx.close(); b.close()
        path = vid.path()
        json.dump({"marks":marks,"caps":caps}, open(OUT/"marks.json","w"), indent=1)
        print("video", path, "marks", marks)

run()
