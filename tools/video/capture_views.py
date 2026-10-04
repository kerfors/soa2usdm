"""Capture stills and element boxes of the published views, for video 2 (and band geometry for video 1).

Usage: python capture_views.py <collection protocols dir> <outdir> <other protocol id> <other protocol id>
"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

B = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]); OUT.mkdir(exist_ok=True)
OTHER = sys.argv[3:]
DPR = 2
BOX = """(sel) => { const e = typeof sel === 'string' ? document.querySelector(sel) : sel; if (!e) return null;
  const r = e.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; }"""

async def main():
    boxes = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=DPR)
        async def shot(name, sels, full=False):
            await pg.wait_for_timeout(350)
            await pg.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
            boxes[name] = {k: await pg.evaluate(BOX, s) for k, s in sels.items()}

        await pg.goto((B / "index.html").as_uri())
        await shot("index", {"table": "table", "panel": ".panel, .card, table"})
        boxes["index"]["review_th"] = await pg.evaluate("""() => { const th = [...document.querySelectorAll('th')].find(t => /Extraction review/.test(t.textContent));
            const r = th.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }""")

        main_id = "NCT04184622"
        await pg.goto((B / f"{main_id}/SoA2USDM/extracted/{main_id}_review.html").as_uri())
        boxes["bands_p18"] = await pg.evaluate("""() => [...document.querySelectorAll('#overlay rect.band')].map(r => ({cls: r.getAttribute('class'),
            x: +r.getAttribute('x'), y: +r.getAttribute('y'), w: +r.getAttribute('width'), h: +r.getAttribute('height'), title: r.querySelector('title')?.textContent}))""")
        boxes["overlay_viewbox"] = await pg.evaluate("document.querySelector('#overlay').getAttribute('viewBox') + '|' + document.querySelector('#overlay').style.height")
        tiles = {"tiles": "#tiles", "pagewrap": "#pagewrap", "pagebox": "#pagebox", "side": "#side", "tablewrap": "#tablewrap"}
        for i in range(5):
            tiles[f"tile{i}"] = f"#tiles > *:nth-child({i + 1})"
        await shot("rv_base", tiles)
        await pg.click("#pagetabs button:has-text('p.20')")
        await shot("rv_p20", tiles)
        await pg.click('tr.act[data-row="32"] td.name')
        await shot("rv_row", {**tiles, "band": "#overlay .sel", "tr": 'tr.act[data-row="32"]'})
        await pg.click('#sidetabs button[data-t="notes"]')
        for c in await pg.query_selector_all("#tab-notes .notecard"):
            if (await c.text_content()).strip().startswith("n21"):
                await c.click(); break
        await shot("rv_note", {**tiles, "note": "#tab-notes .notecard.on", "band": "#overlay .sel, #overlay .note"})
        await pg.click('#sidetabs button[data-t="dec"]')
        await pg.evaluate("document.querySelectorAll('#right, #right *').forEach(e => { e.scrollTop = 0; })")
        await shot("rv_dec", {**tiles, "dec": "#tab-dec .dec", "tab": "#tab-dec"})

        for pid in OTHER:
            await pg.goto((B / f"{pid}/SoA2USDM/extracted/{pid}_review.html").as_uri())
            await shot(f"rv_{pid}", tiles)
            boxes[f"rv_{pid}"]["tiletext"] = await pg.evaluate("document.querySelector('#tiles').innerText")
            await pg.add_style_tag(content="#side{display:none} #tablewrap{height:590px!important;max-height:none!important}")
            await shot(f"rv_{pid}_grid", tiles)

        await pg.goto((B / f"{main_id}/SoA2USDM/consolidated/{main_id}_consolidated.html").as_uri())
        await pg.evaluate("""() => { const h = [...document.querySelectorAll('.comp-header')].find(e => /Matches across tables/.test(e.textContent));
            if (h.nextElementSibling.getBoundingClientRect().height === 0) h.click(); }""")
        await shot("cons", {"grid": "table"}, full=True)
        boxes["cons"]["matches"] = await pg.evaluate("""() => { const h = [...document.querySelectorAll('.comp-header')].find(e => /Matches across tables/.test(e.textContent));
            const a = h.getBoundingClientRect(), c = h.nextElementSibling.getBoundingClientRect();
            return {head: [a.left + scrollX, a.top + scrollY, a.width, a.height], body: [c.left + scrollX, c.top + scrollY, c.width, c.height],
                    html: h.parentElement.outerHTML.slice(0, 200), sib: h.nextElementSibling.className + '|' + getComputedStyle(h.nextElementSibling).display}; }""")
        boxes["cons"]["matches_text"] = await pg.evaluate("""() => [...document.querySelectorAll('.comp-header')].find(e => /Matches across tables/.test(e.textContent)).parentElement.innerText.slice(0, 900)""")

        await pg.goto((B / "activities.html").as_uri())
        await pg.fill('input[placeholder^="Search"]', "ECG")
        await shot("acts", {"input": 'input[placeholder^="Search"]', "table": "table"})
        boxes["acts"]["count"] = await pg.evaluate("document.body.innerText.slice(0, 400)")
        await b.close()
    (OUT / "boxes.json").write_text(json.dumps({"dpr": DPR, "boxes": boxes}, indent=1))

asyncio.run(main())
