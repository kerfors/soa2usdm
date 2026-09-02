# Showcase video — the review page

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
