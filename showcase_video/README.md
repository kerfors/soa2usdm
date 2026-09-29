# Showcase videos — the review page

Two captions-only videos (no voice) of the extraction review page, both on
NCT04184622, published as assets of one GitHub Release
(https://github.com/kerfors/soa2usdm/releases/tag/showcase-video-2026-09):

| video | made | format | scripts |
|-------|------|--------|---------|
| `SoA2USDM_review_showcase_v2.mp4` | 2026-09-29 | 79 s, 1080×1080 (LinkedIn, mobile) | [`v2/`](#v2--the-idea-end-to-end-2026-09-29) |
| `SoA2USDM_review_page_showcase.mp4` | 2026-09-02 | 84 s, 1920×1080 | this folder (below) |

## v1 — screen recording (2026-09-02)

A captions-only screen recording (no voice) of the extraction review page, made
2026-09-02 for sharing outside the repo. It is outreach material: a proof of
concept of what a human-in-the-loop review interface could look like, with the
two properties the whole SoA2USDM work rests on — traceability (every extracted
fact next to the protocol page it came from) and precision (independent checks
re-derived from the PDF).

The video itself is **not** in git. Binary media bloats the history for every
clone, so it is published as a GitHub Release asset instead:

https://github.com/kerfors/soa2usdm/releases/download/showcase-video-2026-09/SoA2USDM_review_page_showcase.mp4

What is here is what regenerates it:

| file | role |
|------|------|
| `storyboard.md` | the scenes and captions, one row each |
| `cards.html` | title and end card |
| `record.py` | Playwright walkthrough → `rec/*.webm` + `rec/marks.json` |
| `compose.py` | marker-timed captions + ffmpeg → 1920×1080 MP4 |

## Regenerating

The walkthrough is recorded against the published collection pages, served from
a local mirror so the recording does not depend on network timing:

```
mkdir -p site && cd site
B=https://kerfors.github.io/soa2usdm-collections
P=$B/collections/usdm_data/protocols
wget -x -nH $B/index.html $P/index.html $P/activities.html
for f in NCT04184622_soa_pages/p0{1..7}.png \
         SoA2USDM/extracted/NCT04184622_review.html; do
    wget -x -nH $P/NCT04184622/$f
done
cp ../cards.html .
python3 -m http.server 8765 &
cd ..
pip install playwright numpy pillow && playwright install chromium
python3 record.py http://127.0.0.1:8765/ rec
python3 compose.py rec SoA2USDM_review_page_showcase.mp4
```

Recording takes ~80 s, encoding ~1 min. The page-specific selectors in
`record.py` (`#soa tr[data-row=32]`, `sup.mk[data-m=n21]`, `.foldcard[data-x=xact-027]`)
are NCT04184622 Table 1 facts; a different protocol needs its own row, note and
fold ids, read off its review page.

## Why the marker square

Playwright's screencast does not run at wall-clock speed, so caption times taken
from the script would drift by several seconds by the end. `record.py` paints a
14 px square in the page corner whose colour encodes the scene number;
`compose.py` reads it back frame by frame and places each caption exactly where
its scene starts, then paints the square over with the header colour. Captions
sit in a separate 120 px bar under the page so nothing in the UI is covered.

## v2 — the idea end to end (2026-09-29)

https://github.com/kerfors/soa2usdm/releases/download/showcase-video-2026-09/SoA2USDM_review_showcase_v2.mp4

Square, for the LinkedIn feed on a phone. Not a screen recording: `v2/capture.py`
clicks through the real published pages and takes 2x stills of each state, and
`v2/render.py` animates them (camera moves, drawn cursor, cross-fades, captions),
so playback is smooth and every frame is readable at phone size. Captions only
state what the pages show; the one count in a caption (22 protocols, every call
decided) is read off the usdm_data index.

| # | shot | caption |
|---|------|---------|
| 0 | title card | — |
| 1 | printed SoA, document p.18 | A Schedule of Activities, as printed |
| 2 | Table 1 extraction JSON viewer | Extracted by AI as JSON, against a schema |
| 3 | review page, table pane | …rendered as a table for review |
| 4 | review page, whole; tiles 'Printed rows missed' and 'Mark check' | Source, extraction and checks — side by side · Independent checks re-read the PDF |
| 5 | click row 32 (OGTT) → printed row on p.20 | Click a row — the printed row lights up |
| 6 | click header row 'Week of Treatment' → its band on p.20 | Header rows trace back to the page too |
| 7 | click note n21 → Notes tab | Footnotes bound to exactly what they apply to |
| 8 | Decisions tab, D2 (decided · corr-004) → p.19 X* | The AI flags its own judgement calls · A human decides — kept as a correction · The raw extraction stays untouched |
| 9 | consolidated SoA page | After review: corrections applied, tables consolidated |
| 10 | usdm_data index, Review column | 22 protocols — every call decided · USDM-ready — not yet USDM |
| 11 | end card (repo URL, built with Claude) | — |

| file | role |
|------|------|
| `v2/capture.py` | Playwright → `stills/*.png` (3840×2160) + `stills/rects.json` |
| `v2/graphics.py` | title / end cards and caption plates → `gfx/` (Inter) |
| `v2/captions.json` | caption texts, one key per plate |
| `v2/render.py` | shot list and keyframes; frames piped to ffmpeg → MP4 |

Regenerating (stills were taken from soa2usdm-collections at 9dad214; a later
checkout gives the same video only while the pages look the same):

```
cd v2
git clone --depth 1 https://github.com/kerfors/soa2usdm-collections.git site
(cd site && python3 -m http.server 8765 --bind 127.0.0.1 &)
npm pack @fontsource/inter@5 && mkdir -p fonts && tar xzf fontsource-inter-*.tgz -C fonts
pip install playwright pillow && playwright install chromium
python3 capture.py && python3 graphics.py && python3 render.py
```

Capture takes ~30 s, rendering ~3 min (every frame is composed in Python).
`python3 render.py --at 12.5,40` writes single frames to `prev/` for checking.
Selectors and camera positions are NCT04184622 facts (row 32, header row 2,
note n21, decision D2); `v2/.gitignore` keeps stills, fonts, the site checkout and
the MP4 out of git.
