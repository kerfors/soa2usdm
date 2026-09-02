# SoA2USDM review page — showcase video storyboard

Captions only, no voice. 1920×1080, ~70 s. Recorded against the published collection
(kerfors.github.io/soa2usdm-collections, usdm_data, NCT04184622 review page, generated 2026-09-02).
Every number shown on screen is what the page itself shows; captions add no figures of their own.
Actual length after recording: 84 s (Playwright's screencast runs slower than the script clock).
The MP4 is a GitHub Release asset, not in git — see README.md in this folder.

| # | Screen | Caption | ~s |
|---|--------|---------|----|
| 0 | Title card | SoA2USDM — reviewing an SoA extraction against its source. Proof of concept: what a human-in-the-loop review interface could look like. | 5 |
| 1 | usdm_data index, Review column | Every protocol in the collection has a review page. Human review is a step in the pipeline, not an afterthought. | 7 |
| 2 | Review page, summary tiles | Summary tiles are independent checks re-derived from the PDF — not the extractor's own report. | 8 |
| 3 | Source page pane + table pane | Left: the source protocol page with detected row bands overlaid. Right: the extracted table. Nothing on the right exists without a place on the left. | 7 |
| 4 | Click OGTT row → page jumps to document p.20, printed row highlighted | Click an extracted row: the page jumps to document page 20 and the printed row lights up. Row and marks are traceable to the cell they came from. | 10 |
| 5 | Notes tab, footnote n21 | Footnotes are bound to the rows they govern. The note is the page's own text, shown next to the row it changes. | 8 |
| 6 | Checks tab | Precision, checked independently: every × in the page's text layer is binned into band and column and compared with the extraction. | 8 |
| 7 | Across tables tab, OGTT match T1 row 32 ↔ T2 row 23 | The same activity across tables is matched with both printed names shown — the reviewer sees why, and can jump to either source. | 8 |
| 8 | Decisions tab, draft pane | Where the extractor's call could go the other way, the reviewer decides here. The page drafts the correction sidecar; nothing is saved from the browser — the decision is committed as data and the page is regenerated. | 9 |
| 9 | End card | Traceability · Precision · Human in the loop. github.com/kerfors/soa2usdm | 5 |
