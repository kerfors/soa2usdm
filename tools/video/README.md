# Videos

Two short captions-only videos (square, 1080 x 1080), linked from `docs/index.html` and published on YouTube.

| Video | Script | Shows |
|---|---|---|
| The idea | `video_idea.py` | One printed SoA page (NCT04184622, document page 18) read as five constructs, one row followed through the three schemas, one correction entry |
| On real protocols | `video_protocols.py` | A tour of the published views: collection index, review page, consolidated view, activity inventory |

Both are built from still images that are cropped, moved and cross-faded frame by frame; nothing is screen-recorded. Every value shown is read from the collection files or from the published pages.

## Regenerate

Needs a checkout of `soa2usdm-collections`, plus Playwright with Chromium, Pillow, ffmpeg and pdftotext.

```bash
P=<soa2usdm-collections>/collections/usdm_data/protocols
python capture_views.py $P cap CDISC_Pilot NCT02291289
python video_idea.py $P/NCT04184622 cap SoA2USDM_the_idea.mp4
python video_protocols.py cap SoA2USDM_on_real_protocols.mp4
```

The scripts name page elements and rows of NCT04184622 directly (the OGTT row, note n21, correction corr-003, the Weight row). If those change in the collection, the scripts stop with an error.

The MP4 files are not kept in the repository.
