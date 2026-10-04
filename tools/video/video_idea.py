"""Video 1: the idea - one real SoA page (NCT04184622, document page 18) read as five constructs,
one row followed through the three schemas, one real correction entry.

All values shown are read from the collection files at run time.

Usage: python video_idea.py <protocol dir of NCT04184622> <capture dir from capture_views.py> <out.mp4>
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from video_lib import (ASPECT, BG, FPS, INK, MUTED, VIEW_H, W, WHITE, Stills, card, encode, font, frame, mono, shot, still, wrap)

PROTO, CAP, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
PID = "NCT04184622"
SCHEMA_URL = "kerfors.github.io/soa2usdm/schema-chain.html"
COLORS = {"properties": (31, 71, 136), "grid": (46, 117, 182), "activities": (0, 121, 107),
          "schedule": (90, 125, 26), "annotations": (106, 27, 154)}
HUMAN, HUMAN_BG = (199, 119, 0), (255, 246, 229)

page = Image.open(PROTO / f"{PID}_soa_pages" / "p01.png").convert("RGB")
SCALE = page.width / 792
bands = json.loads((CAP / "boxes.json").read_text())["boxes"]["bands_p18"]
X0, X1 = bands[0]["x"], bands[0]["x"] + bands[0]["w"]

# label column edge: the first vertical rule to the right of the table's left edge, inside a header band
gray = page.convert("L")
hb = bands[1]
strip = gray.crop((0, int((hb["y"] + 2) * SCALE), page.width, int((hb["y"] + hb["h"] - 2) * SCALE)))
dark = [sum(1 for v in strip.crop((x, 0, x + 1, strip.height)).getdata() if v < 110) / strip.height for x in range(page.width)]
rules = [x / SCALE for x, v in enumerate(dark) if v > 0.85]
XL = next(x for x in rules if x > X0 + 20)

WORDS = Path(tempfile.mkdtemp()) / "words.html"
subprocess.run(["pdftotext", "-bbox", "-f", "1", "-l", "1", str(PROTO / f"{PID}_soa.pdf"), str(WORDS)], check=True)
words = re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', WORDS.read_text())
Y0, Y1 = bands[0]["y"], bands[-1]["y"] + bands[-1]["h"]
stars = [(float(a) - 2, float(b) - 1, float(c) + 2, float(d) + 1) for a, b, c, d, text in words
         if text.endswith("*") and Y0 <= float(b) <= Y1]

header = [b for b in bands if "header" in b["cls"]]
section = [b for b in bands if "blank" in b["cls"]]
rows = [b for b in bands if "matched" in b["cls"]]
REGIONS = {
    "properties": [(X0, b["y"], XL, b["y"] + b["h"]) for b in header],
    "grid": [(XL, b["y"], X1, b["y"] + b["h"]) for b in header],
    "activities": [(X0, b["y"], XL, b["y"] + b["h"]) for b in rows] + [(X0, b["y"], X1, b["y"] + b["h"]) for b in section],
    "schedule": [(XL, b["y"], X1, b["y"] + b["h"]) for b in rows],
    "annotations": stars,
}


def lit(regions, color, strength=0.30):
    """The page veiled in white, with the given regions (PDF points) kept and tinted."""
    out = Image.blend(page, Image.new("RGB", page.size, WHITE), 0.62)
    tint = Image.blend(page, Image.new("RGB", page.size, color), strength)
    draw = ImageDraw.Draw(out)
    for x0, y0, x1, y1 in regions:
        box = tuple(round(v * SCALE) for v in (x0, y0, x1, y1))
        out.paste(tint.crop(box), box[:2])
        draw.rectangle(box, outline=color, width=2)
    return out


S = Stills(SCALE)
S.add("page", page)
for name, regions in REGIONS.items():
    S.add(name, lit(regions, COLORS[name]))

# the row followed through the schemas, read from the files
base = PROTO / "SoA2USDM"
extraction = json.loads((base / "extracted" / f"{PID}_Table_01_extraction.verified.json").read_text())
resolved = json.loads((base / "resolved" / f"{PID}_Table_01_resolved.json").read_text())
consolidated = json.loads((base / "consolidated" / f"{PID}_consolidated.json").read_text())
corrections = json.loads((base / "extracted" / f"{PID}_Table_01_corrections.json").read_text())
ROW_NAME = "Weight"
ex = next(a for a in extraction["activities"] if a["activity_name"] == ROW_NAME)
rs = next(a for a in resolved["activities"] if a["activity_name"] == ROW_NAME)
ua = next(a for a in consolidated["unified_activities"] if a["activity_name"] == ROW_NAME)
corr = next(c for c in corrections["corrections"] if c["id"] == "corr-003")
row_band = next(b for b in rows if b["title"].startswith(ROW_NAME))
S.add("row", lit([(X0, row_band["y"], X1, row_band["y"] + row_band["h"])], COLORS["activities"], 0.34))

CARDS = [
    ("EXTRACTION", "written by the model", COLORS["activities"],
     [f'row_position {ex["row_position"]}    source_page {ex["source_page"]}',
      f'activity_name "{ex["activity_name"]}"    cell_text "{ex["activity_name_source"]["cell_text"]}"']),
    ("RESOLUTION", "derived by program", COLORS["activities"],
     [f'activity_id {rs["activity_id"]}    parent {rs["parent_activity_id"]}',
      f'linked note {", ".join(rs["linked_annotation_ids"])}']),
    ("CONSOLIDATION", "derived by program", COLORS["activities"],
     [f'{ua["xact_id"]}  <-  ' + f'Table {ua["source_refs"][0]["table_num"]} {ua["source_refs"][0]["activity_id"]} (row {ua["source_refs"][0]["row_position"]})']
     + [f'          <-  Table {r["table_num"]} {r["activity_id"]} (row {r["row_position"]})' for r in ua["source_refs"][1:]]),
]
STRIP_H = 300


def panel(draw, top, height, title, sub, color, fill=WHITE):
    draw.rounded_rectangle((40, top, W - 40, top + height), radius=10, fill=fill, outline=(217, 222, 229), width=2)
    draw.rectangle((40, top, W - 40, top + 7), fill=color)
    draw.text((66, top + 26), title, font=font(25, "Bold"), fill=color)
    draw.text((66 + draw.textlength(title, font=font(25, "Bold")) + 16, top + 28), sub, font=font(23, "Regular"), fill=MUTED)


def trace_content(shown):
    strip_w = (X1 - X0) + 36
    crop = ((X0 + X1) / 2, row_band["y"] + row_band["h"] / 2, strip_w)
    img = Image.new("RGB", (W, VIEW_H), BG)
    img.paste(S.view("row", crop, size=(W, STRIP_H)), (0, 0))
    draw = ImageDraw.Draw(img)
    top = STRIP_H + 26
    for index, (title, sub, color, lines) in enumerate(CARDS[:shown]):
        panel(draw, top, 172, title, sub, color)
        y = top + 74
        for line in lines:
            draw.text((66, y), line, font=mono(25), fill=INK)
            y += 40
        top += 172 + 22
    return img


def correction_content():
    crop = ((X0 + X1) / 2, bands[0]["y"] + (((X1 - X0) + 36) * STRIP_H / W) / 2 - 8, (X1 - X0) + 36)
    img = Image.new("RGB", (W, VIEW_H), BG)
    img.paste(S.view("annotations", crop, size=(W, STRIP_H)), (0, 0))
    draw = ImageDraw.Draw(img)
    top = STRIP_H + 34
    panel(draw, top, 500, "TABLE CORRECTIONS SIDECAR", "written by a human", HUMAN, HUMAN_BG)
    draw.text((66, top + 80), f'id {corr["id"]}    op {corr["op"]}    review_item {corr["review_item"]}', font=mono(25), fill=INK)
    first = corr["reason"].split(". ")[0] + ". ..."
    y = top + 140
    for line in wrap(draw, first, font(26, "Regular"), W - 150):
        draw.text((66, y), line, font=font(26, "Regular"), fill=INK)
        y += 38
    draw.text((66, top + 430), f'by {corr["by"]}    at {corr["at"][:10]}', font=mono(25), fill=INK)
    return img


def fade_in(seconds, a, b, caption, hold):
    n = round(seconds * FPS)
    for i in range(n):
        yield frame(Image.blend(a, b, (i + 1) / n), caption)
    for _ in range(round(hold * FPS)):
        yield frame(b, caption)


def timeline():
    yield "cut", still(3.5, card("SoA2USDM", ["A Schedule of Activities,", "as data you can check"]))

    full = (396, 306 + 10, 792 + 30)
    table = ((X0 + X1) / 2, (Y0 + Y1) / 2 - 6, (X1 - X0) + 40)
    printed = "A Schedule of Activities, as printed in the protocol"
    yield "fade", shot(S, 2.2, "page", full, caption=printed)
    yield "cut", shot(S, 1.8, "page", full, table, caption=printed)

    names = [("properties", "1  Schedule properties: the header rows"),
             ("grid", "2  Schedule grid: the header cells"),
             ("activities", "3  Activities: the body rows"),
             ("schedule", "4  Activity schedule: the marks"),
             ("annotations", "5  Annotations: every * points to a note")]
    for key, caption in names:
        yield "fade", shot(S, 2.3, key, table, caption=caption)

    trace = "Transcribed once by a model, derived twice by program. Every element points back to the page."
    states = [trace_content(i) for i in range(4)]
    yield "fade", still(1.0, frame(states[0], trace))
    for i in range(3):
        yield "cut", fade_in(0.4, states[i], states[i + 1], trace, 2.6)

    yield "fade", still(7.0, frame(correction_content(), "A reviewer's decision is a sidecar entry: who, when, why"))

    yield "fade", still(4.5, card("SoA2USDM", ["The schemas, on one page"], [SCHEMA_URL]))


encode(timeline(), OUT)
