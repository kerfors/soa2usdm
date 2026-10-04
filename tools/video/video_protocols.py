"""Video 2: SoA2USDM on real protocols - a tour of the published HTML views.

Usage: python video_protocols.py <capture dir from capture_views.py> <out.mp4>
"""
import json
import sys
from pathlib import Path

from PIL import Image

from video_lib import ASPECT, Stills, card, encode, rect, rect_top, shot, still

SRC, OUT = Path(sys.argv[1]), sys.argv[2]
meta = json.loads((SRC / "boxes.json").read_text())
B = meta["boxes"]
S = Stills(meta["dpr"])
for png in SRC.glob("*.png"):
    S.add(png.stem, Image.open(png))

MAIN, PILOT, OTHER = "NCT04184622", "CDISC_Pilot", "NCT02291289"
COLLECTION_URL = "kerfors.github.io/soa2usdm-collections"
SCHEMA_URL = "kerfors.github.io/soa2usdm/schema-chain.html"


def centre(box):
    return (box[0] + box[2] / 2, box[1] + box[3] / 2)


def timeline():
    yield "cut", still(3.5, card("SoA2USDM", ["on real protocols"]))

    index = B["index"]
    wide = rect_top(16, 96, 1060)
    th = index["review_th"]
    close = (th[0] + th[2] / 2 - 120, 96 + (700 / ASPECT) / 2 + 60, 700)
    yield "fade", shot(S, 2.5, "index", wide, caption="22 protocols, one pipeline")
    yield "cut", shot(S, 3.5, "index", wide, close, caption="22 protocols, one pipeline")

    base = B["rv_base"]
    t0, t3, t4 = base["tile0"], base["tile3"], base["tile4"]
    left = rect_top(t0[0] - 8, t0[1] - 90, 720)
    right = rect_top(t4[0] + t4[2] + 8 - 720, t0[1] - 90, 720)
    tiles_caption = "93 activities, 725 marks, 45 annotations. Page and extraction agree on every mark."
    yield "fade", shot(S, 2.5, "rv_base", left, caption=tiles_caption)
    yield "cut", shot(S, 2.2, "rv_base", left, right, caption=tiles_caption)
    yield "cut", shot(S, 2.3, "rv_base", right, caption=tiles_caption)

    row = B["rv_row"]
    pane = rect(row["pagewrap"], margin=8, width=row["pagewrap"][2] + 30)
    pane = (pane[0], row["pagewrap"][1] - 50 + (pane[2] / ASPECT) / 2, pane[2])
    row_caption = "Every extracted row is found on its printed page"
    yield "fade", shot(S, 1.6, "rv_p20", pane, caption=row_caption)
    yield "cut", shot(S, 0.7, "rv_p20", pane, caption=row_caption, key_to="rv_row")
    yield "cut", shot(S, 2.6, "rv_row", pane, caption=row_caption, click=centre(row["band"]))
    tr = row["tr"]
    grid_w = 700
    grid = (tr[0] + grid_w / 2 - 14, min(tr[1] + tr[3] / 2, 1000 - (grid_w / ASPECT) / 2 + 30), grid_w)
    yield "cut", shot(S, 1.3, "rv_row", pane, grid, caption=row_caption)
    yield "cut", shot(S, 2.3, "rv_row", grid, caption=row_caption)

    note = B["rv_note"]
    side = rect(note["note"], width=700)
    note_caption = "A note is bound to what it applies to"
    yield "fade", shot(S, 3.2, "rv_note", side, caption=note_caption, click=(note["note"][0] + 60, note["note"][1] + 30))
    yield "cut", shot(S, 1.3, "rv_note", side, pane, caption=note_caption)
    yield "cut", shot(S, 2.5, "rv_note", pane, caption=note_caption)

    dec = B["rv_dec"]
    dec_crop = rect_top(dec["side"][0] - 12, dec["dec"][1] - 110, 690)
    yield "fade", shot(S, 6.0, "rv_dec", dec_crop, caption="Judgement calls are data. Decisions are sidecar entries.")

    other_caption = "Different layouts, same constructs"
    for pid in (PILOT, OTHER):
        box = B[f"rv_{pid}"]
        page = rect(box["pagewrap"], margin=8, width=box["pagewrap"][2] + 30)
        page = (page[0], box["pagewrap"][1] - 50 + (page[2] / ASPECT) / 2, page[2])
        table = B[f"rv_{pid}_grid"]["tablewrap"]
        cells = rect_top(table[0] - 10, table[1] - 16, 690)
        yield "fade", shot(S, 3.0, f"rv_{pid}", page, caption=other_caption)
        yield "fade", shot(S, 3.0, f"rv_{pid}_grid", cells, caption=other_caption)

    cons = B["cons"]
    g = cons["grid"]
    start = rect_top(g[0] - 14, g[1] - 46, 820)
    end = (start[0], start[1] + 260, start[2])
    cons_caption = "Two tables, one schedule: 93 rows become 55 activities"
    yield "fade", shot(S, 2.0, "cons", start, caption=cons_caption)
    yield "cut", shot(S, 5.0, "cons", start, end, caption=cons_caption)

    m = cons["matches"]["head"]
    left = rect_top(m[0] - 6, m[1] - 14, 820)
    right = (m[0] + m[2] + 6 - 410, left[1], 820)
    match_caption = "Whether two rows are the same activity is decided by a reviewer"
    yield "fade", shot(S, 3.0, "cons", left, caption=match_caption)
    yield "cut", shot(S, 2.0, "cons", left, right, caption=match_caption)
    yield "cut", shot(S, 2.5, "cons", right, caption=match_caption)

    acts = B["acts"]
    a = rect_top(acts["input"][0] - 16, acts["input"][1] - 70, 900)
    yield "fade", shot(S, 6.0, "acts", a, (a[0] - 30, a[1] + 20, 840), caption="889 activities across 22 protocols, searchable")

    yield "fade", still(5.0, card("SoA2USDM", ["Every page shown here is public"],
                                  [f"The protocols: {COLLECTION_URL}", f"The schemas: {SCHEMA_URL}"]))


encode(timeline(), OUT)
