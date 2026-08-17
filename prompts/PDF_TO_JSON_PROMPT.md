# SoA Table Extraction: PDF → JSON (single-pass, non-interactive)

> Prompt version 3.7.1 | Schema: soa-table-extraction v1.0
> Supersedes the two-conversation PDF→Excel (v2.8) + Excel→JSON (v2.4) flow for non-interactive runs. Use the v2.x flow when a human-editable Excel checkpoint is wanted; use this when you want to attach the PDF and get extraction JSON in one pass.

Extract the SoA table(s) from the attached protocol directly to `soa-table-extraction` JSON — one file per table. Run start to finish without stopping for confirmation. Surface every judgement call in the **uncertainty report** at the end instead of asking mid-run.

**Attached / in project knowledge:** this prompt, the SoA PDF (optionally the full-protocol markdown), `soa-table-extraction.schema.json`, `soa_table_type_definitions.md`. Read the schema and the taxonomy and follow them exactly. Read the XLSX skill only if you also need to emit Excel — not required here.

---

## 1. Core principle — transcribe, do not infer

- Transcribe each cell literally as it appears: `X`, `✓`, `•`, arrows, text, numbers. An empty cell stays empty.
- Do NOT infer a cell's content from neighbouring cells, the row's pattern, or clinical logic. A stronger model is a stronger pattern-completer — actively resist "completing" a sparse grid. A missing mark is data.
- Visual formatting (grey shading, bold, indentation, borders) is a hierarchy or annotation signal — never a reason to alter cell content.
- If both PDF and protocol markdown are attached: use the **PDF for structure** (column boundaries, merged cells, hierarchy, cell marks) and the **markdown for text** (activity spelling, footnote wording, header labels). Prefer markdown for text, PDF for structure. Do not use pdfplumber. Flag any PDF/markdown disagreement in the report. The **PDF is authoritative for the row set** — markdown can silently omit whole rows and is often absent entirely for image-based PDFs, so confirm every body row (not just the footnotes) against the PDF; never trust markdown to be complete.

### 1a. Image-based / scanned tables (no text layer)

**Test for the vector layer separately from the text layer.** A page can carry a perfectly good text
layer and still be a picture of a table: the grid is one full-page raster image and the text sits on
top of it invisibly. `pdftotext` returns plenty, so the page looks like a §1b text-layer table, but
`page.rects` / `page.lines` / `page.curves` are EMPTY — there are no rule lines to read, and any
instruction here or in §6 that says "confirm it from the rule-line geometry" cannot be followed from
the vector layer. On NCT04677179, 20 of 30 SoA pages are like this and only one page has a vector
table. When the vector layer is empty, recover the rules from the **raster** instead (§1d) rather than
falling back to proximity — falling back is what produced that protocol's fragmented-then-over-merged
annotations across two extraction passes.

First test whether the SoA pages have a text layer (`pdftotext` returns little or nothing → scanned image; a lone small image such as a logo does not make a text-layer table "image-based"). If image-based, render each page and read the grid visually. For dense grids, reconstruct marks mechanically: detect the rule-line geometry (column and row boundaries) to define each cell rectangle, then flag a cell as marked by **counting near-black pixels** (intensity < ~90) inside it against an absolute **count threshold** — use a count, NOT a dark-pixel *fraction*, since tall row bands dilute the fraction and hide real marks. **Validate the detector cell-for-cell against direct visual reads** on several representative full-width rows (at least one dense and one sparse) before trusting it. State the image-based method in the report and recommend a spot-check of the resolved grid. Mixed documents occur — the grid may be scanned while the footnote pages carry a real text layer: pull footnote wording from the text layer, read the grid from the image.

### 1b. Text-layer tables — mechanical mark verification (bbox)

For a table WITH a text layer, do not eyeball the grid — re-derive the mark matrix mechanically and diff it against your visual read. This bbox mark-check is the verification surface that REPLACES the old PDF→Excel human checkpoint: on NCT03637764 it caught 4 merged-span errors the Excel-verified extraction had missed. The point is to keep a mechanical mark-check, not to skip verification.

- Run `pdftotext -bbox` on the SoA pages to get every token's x/y box. Do NOT use pdfplumber.
- **Fix column x-centres from the header** day/visit/week labels — one centre per data column. The header anchors the grid; body marks do not define columns.
- **Bin each mark token to the nearest column centre.** Match marks with `^[Xx][*a-zA-Z0-9]?$` — a footnoted mark tokenises as `X*` / `Xa`, and an `== 'X'` filter silently drops it.
- **Resolve merged spans from per-row rule-line geometry:** a missing internal vertical boundary between two adjacent column centres means the cell is merged across them — distribute the mark across every covered column (§5), never onto the one the glyph happens to sit under.
- **De-duplicate repeated rows before counting:** header and `schedule_property` rows (e.g. Fasting / Telephone-visit bands) reprint on every continuation page; count each activity and each mark once.
- Diff the bbox matrix against your visual read cell-for-cell and report any disagreement in the uncertainty report (§7).

### 1c. Glyph-spread text layers — reconstruct words before transcribing

Some PDFs position every glyph as its own token, so the text layer comes back letter-spaced ("S c r e e n i n g", "Haemo globin"). Reconstruct real words BEFORE anything reaches the JSON, and apply the reconstruction to **every** text field — activity labels, header labels, **and `annotation_text`**. Annotation text is the field that gets skipped: it is long, it is never eyeballed against the grid, and the letter-spacing survives into the delivered JSON as intra-word gaps and missing inter-word spaces.

- Detect it: single-character tokens dominate the stream, or the x-gap between glyphs inside a word is close to the gap between words.
- Rebuild words from the glyph stream, then restore capitalisation and acronym casing from how the protocol spells the term elsewhere — from the source, never from a guess. Cross-check against the full-protocol markdown when it is attached.
- Re-read the result as running prose before delivering. State in the report (§7) that the source was glyph-spread and which fields were reconstructed.

### 1d. Recovering rule lines from the raster

When a page has no vector rule lines (§1a), render it and read the rules off the pixels. This is line
detection, not OCR — the text still comes from the text layer, only the cell boundaries come from the
image. It works on vector pages too, so use the one method for the whole table rather than switching
per page.

- Render at 200 dpi (`pdftoppm -r 200`); treat a pixel as ink below ~50% grey.
- **Vertical rules** = image columns whose ink fraction is high over the table's height; consecutive
  rules bound one table column. The two rightmost bound a right-hand notes column.
- **Horizontal rules** = image rows whose ink fraction exceeds ~85% *within one column's* x-range,
  inset a few pixels from the vertical rules. Consecutive rules bound one cell; discard slivers.
- Convert pixel y to PDF points by dividing by dpi/72, then assign each text-layer character to the
  band its centre falls in.
- **Take the row boundaries from a column that holds text, never from a redacted one.** A black
  redaction bar fills its cell edge to edge, reads as a horizontal rule, and makes that row vanish
  from the band list — on NCT04677179 this nearly dropped a CCI row that carries three marks. Read the
  boundaries from the notes column or another text column and apply them across the row.
- Sanity-check the recovered bands against a rendered crop of the same page before trusting them.

### 1e. Method provenance — record HOW, exception-based

Every interpreted value has a default method; when you arrive at a value any other way, record the
method in the schema's provenance fields. Absent = default — most extractions record nothing here.
Record **method, not confidence**: a method names a re-derivable procedure that can be checked against
the PDF; a confidence number cannot.

- `annotation_text_source.method` — note text not read from a rule-line-bounded text-layer cell:
  `deglyph_reconstruction` (§1c), `raster_band_cells` (§1d), `proximity_bounded` (only when rules are
  genuinely unrecoverable — the validator flags these for page verification), `visual_transcription` (§1a).
- `marker_locations[].method` — a scope not established by a printed marker: `synthesized` (§6
  conventions), `text_match` (bound by word overlap), `proximity` (nearest row; validator-flagged).
- `activity_name_source.method` (`glyph_reconstruction` / `visual_transcription`) and
  `activity_name_source.indentation_method` (`font_signal` / `visual_estimate` / `assumed_flat`).
- `activity_schedule` / `schedule_grid` cell `method` — `raster_pixel_detection` (§1a) / `visual_read`.
- `schedule_property.structure_method` — `inferred_from_layout` / `assumed`, when
  `property_type`/`hierarchical_level` do not come from printed header labels.

**`unresolved` is an allowed answer.** When a marker's target cannot be determined, keep the location
with `row_position` where the marker is printed — position is evidence — and set
`location_type: "unresolved"`. Never invent a scope, a target, or a location to satisfy the schema:
an honest `unresolved` is data; a guessed target is a defect that surfaces weeks later. If you catch
yourself about to guess, record the method or mark it unresolved instead.

## 2. Tables — classify before extracting

Assign `table_type` to every table per `soa_table_type_definitions.md`. Apply the discriminators explicitly:

- **reference test first:** are the rows activities performed on subjects? If NO → `reference` (e.g. sample-spec tables whose rows are "Sample 1, Sample 2…", abbreviation lists).
- **subsidiary vs track:** finer timing for a subset of activities already in another table → `subsidiary`; a genuinely separate timeline with its own visits/duration/population → `track` (set `track_label`, see below).
- **`track_label` is a short identifier, not a description.** Use the shortest phrase that tells this track apart from the other tracks in the *same study* — aim for one to four words, e.g. "Prediabetes", "Cohort 1", "Continued Access", "Extension (nonresponders)", "Early Termination / Unscheduled / Post-Treatment". Take the words from the source's own population or phase wording; do not compose a sentence, and do not restate the table number, the study name, the visit range, or filler like "Schedule of Activities" / "Treatment Period" when the label already distinguishes the track without it. Where the source spells the term inconsistently, follow the table title or the population statement rather than a column header. These labels surface as `population_track` on every column of the table, so they are read far more often than they are written.
- **domain vs continuation:** same columns as the parent — rows continue across a page break → `continuation` (set `continuation_of`); different activity category on the shared timeline, **for the same participants** → `domain`.
- **domain vs track — ask who attends, not what the columns say.** Same columns is NOT sufficient for `domain`. If the two tables schedule **mutually exclusive populations** (responders vs non-responders, arm A vs arm B), each is a `track` even when their visit labels, weeks and study days are numerically identical — the sponsor reused a numbering scheme, that is all. Misclassifying a population split as `domain` is silent: `schedule_matrix` and the column count are unchanged, but every column in that table loses its `population_track` and the branch identity disappears.
- otherwise the primary anchor grid → `main_soa`.

Note on the PK-sampling ambiguity: a table that breaks a single main-SoA activity (e.g. "PK sampling") into per-sample timing rows satisfies the `subsidiary` definition even though its rows read "Sample n". Classify by function (finer timing for an existing activity), and record the call in the report.

For any `table_type` that is not obvious from the discriminators alone, record the reasoning in `table_metadata.notes` as well as the report — the classification is an interpretation, and `notes` is where its provenance lives in the data.

## 3. Schedule properties (header rows)

Each header row → one `schedule_property`.

- **property_type** from the actual values: Screening/Treatment/Follow-up → `epoch`; V1/Baseline/EOS → `visit`; Day −7/Day 1 → `study_day`; Week 0/Week 4 → `week`; 0h/2h post-dose → `timepoint`; Cycle 1/Cycle 2 → `cycle`; ±3 days → `window`; unclear → `other`.
- **hierarchical_level** counted from the top (topmost row = 1, downward). Assign a level to every header row that helps distinguish one column from another — if removing the row would make two columns indistinguishable, it needs a level. Use `null` only for purely presentational qualifier rows that do not participate in telling columns apart.
- **property_comment** is REQUIRED — state what the row contains and the reasoning for its `property_type`.
- If the label cell is empty but the row clearly carries schedule data spanning columns, synthesise `property_name` and set `property_name_source.synthesized: true`. Synthesised names are fine; document them in the report.
- When `property_type` or `hierarchical_level` come from layout geometry or working assumption rather than printed header labels, set `structure_method` (`inferred_from_layout` / `assumed`) — see §1e.
- A population / eligibility qualifier band (e.g. "Patients who have PD …" spanning only some columns) → `property_type: condition`; give it `hierarchical_level: null` when it does not by itself distinguish one column from another.

## 4. Activities (table body)

Each activity row → one `activity`.

- **source_page** — record the document page each row was read from, in the same numbering as
  `table_metadata.page_start`/`page_end`. **Then check coverage before delivering: every page in the
  declared range must contribute rows.** A page that contributes none has almost certainly been
  skipped — on NCT04677179 the whole first body page of Table 4 was missed, taking 14 activities and
  26 marks with it, and nothing downstream noticed for weeks because the table still looked internally
  consistent. If a page in the range genuinely has no activity rows (a footnote or abbreviation page),
  say so in the report. **Horizontally tiled tables (§5) are the one structural exception:** a row that
  prints in two tiles is ONE activity and carries the `source_page` of the tile it was first read from,
  so the pages carrying only the other tile contribute no rows while still supplying half the marks.
  That is expected, not a skipped page — state it in the report and name which marks each such page
  supplied, so a declared exception is never confused with a silent one.
- **indentation_level** from visual indentation / shading / bold: section header = 0, child = 1, grandchild = 2, … When the level does not come from text-layer whitespace, set `activity_name_source.indentation_method` (`font_signal` / `visual_estimate` / `assumed_flat` for flat tables) — see §1e.
- `activity_name` is CLEAN (no leading whitespace, no annotation markers); `activity_name_source.cell_text` is RAW (preserve whitespace and markers).
- Do NOT create activity rows for non-activities: repeated column-label bands (e.g. a "Procedure" header repeated on each page), or instruction-overflow rows that only carry footnote text. These are not procedures performed on subjects.
- Organizational / section-header rows (indentation_level 0 that group child activities) carry NO scheduling marks. Exception: a *flat* table where every row is a level-0 activity that itself carries marks — there are no grouping headers to keep mark-free.

## 5. Grid values and merged cells

- Column 1 is row labels — EXCLUDE it from `schedule_grid` and `activity_schedule`. Data columns start at position 2.
- Clean markers out of `cell_value` into `annotation_markers` (`Xᵃ` → `cell_value: "X"`, `annotation_markers: "a"`).
- A legend-defined in-grid scheduling mark stays as a `cell_value`, not an annotation — e.g. keep `P` in the grid where the legend defines `P = predose`. It is a scheduling indicator like `X`.
- **Merged marks — distribute, never centre.** A single mark sitting in a cell visually merged across N columns applies to ALL N columns. Emit one `activity_schedule` entry per covered column with the same `cell_value`, and set `source_range` to the span (e.g. `"4:15"`). Do NOT collapse a merged mark onto the one visually-centred column — that fabricates a single-visit schedule and destroys the real span. Confirm every span from the rule-line geometry (§1b text-layer / §1a image), not from where the glyph sits. The same applies to merged text cells such as "See instructions" / "See Section x.y": one entry per covered column, `source_range` set. For merged header cells, record `is_merged_cell` / `merged_cell_range` on each covered position.
- **Ranges are numeric column positions, always.** Both `source_range` and `merged_cell_range` take the form `"<first>:<last>"` in the same `column_position` numbering as the rest of the table — `"4:9"`, `"12:24"`. **Never spreadsheet A1 notation** (`"D1:E1"`). The schema's own description for `merged_cell_range` shows an A1-style example; it is wrong and this rule overrides it. The field is typed as a bare string, so an A1 value passes validation silently and splits the corpus into two notations that no count-based check can see.
- **Horizontally tiled wide tables — union rows across tiles.** When one logical table is split into side-by-side column-block tiles because it is too wide for the page (e.g. V10–V19 in one spread, V20–V29 in a "(continued)" spread), the tiles **share their body rows**: the same activity typically appears in *both* tiles, carrying marks in each. Merge by activity name and take the **union** of marks across tiles. Do NOT assume a recurring row prints in only one tile and keep only that tile's marks — that silently drops the other tile's visits. Confirm each row's presence in *every* tile against the PDF; a row genuinely absent from one tile is the exception (e.g. an explicit "Not applicable during V10–V19" note), not the rule. Decide per row.
- **Arrows spanning columns.** A horizontal arrow (`↔`, `→`) drawn across N columns denotes a continuous activity over that span — distribute like a merged mark: one `activity_schedule` entry per covered column, `cell_value` the arrow glyph, `source_range` the span. Confirm arrow extents visually — arrows are vector graphics and are invisible to text-coordinate parsers.
- **Vertically-merged marks.** A single mark centred across two or more *activity rows* applies to every covered row. The schema has no vertical merge, so emit the mark on each covered activity's cell.
- **Qualified marks.** A mark carrying a parenthetical label ("X (Cycle 5 only)", "X (Day 3-5)"): if the label names a span of the table's own columns, distribute across those columns with `source_range`; if it is a condition not expressible as columns, keep the qualifier literally in `cell_value`.
- **Glyph case.** Transcribe `x` vs `X` (and `✓`, `•`) literally. Only normalise an obvious scan-rendering inconsistency, and flag it in the report when you do.

## 6. Annotations

Each footnote / legend / abbreviation → one `annotation`.

- **annotation_type:** explanatory logic or conditions → `footnote`; pure cross-references ("See Section x.y", "Refer to …") → `source_note`; symbol definitions (X = required) → `legend`; term expansions (BP = blood pressure) → `abbreviation`. Capture a `legend`/`abbreviation` entry only when that term's marker actually appears in the table (e.g. a legend `X`/`P` used as an in-grid mark → `legend` with `marker_locations` on the cells that use it). Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker — every annotation needs ≥1 `marker_location` (§7), so an unreferenced list entry is an orphan and is dropped downstream. **An abbreviation's marker is the term printed as a marker in a grid cell, a header cell or an activity label — not the term merely occurring inside running text.** Word overlap is not a marker: do NOT bind an `abbreviation` by `method: "text_match"` to an activity whose name happens to contain the term, and do NOT attach one to a `schedule_property` with `method: "synthesized"` to give an otherwise-orphan list entry somewhere to live. Both are the standalone list this rule forbids, wearing a `marker_location`. If the only place a term appears is the abbreviation block itself, drop it — a 40-term abbreviation block should normally yield **zero** annotations, not forty. When a table genuinely does warrant several, name their synthesised markers consistently across every table of the same study (`ab1`, `ab2`, … in printed order), never the term itself. A `source_note` is a cross-reference to elsewhere in the protocol — a dedicated reference column, a standalone "See Section x.y" note, **and** a section/appendix/attachment reference printed inline in an activity's label (e.g. "Inclusion criteria (6.1)", "HbA1c (Appendix 2)", "Trial product compliance (7.1) (7.6)"). Strip inline references OUT of `activity_name` (keep them in `activity_name_source.cell_text`), emit each as a `source_note` deduplicated by text (one annotation per distinct reference), and add a synthesised marker (`pr1`, `pr2`, …) to every citing activity's `annotation_markers` so resolve links it — a synthesised marker that sits on no element resolves as table-scoped/unlinked. Split multiple references on one label into separate notes.
- **`annotation_markers` and `marker_locations` must agree — the first one is what actually binds.** For every location you record on an annotation, add that marker to the same row's `annotation_markers` (on the `schedule_property`, the `activity`, or the `schedule_cell`). Resolve links an annotation to its activity through the ROW's `annotation_markers` string; `marker_locations` is only consulted when that yields nothing. So a location recorded on one side and not the other is silently dropped, with nothing failing anywhere in the pipeline.
- **Deduplicate by text.** Emit one `annotation` per distinct note or reference, carrying a `marker_locations` entry for each occurrence. Do NOT emit a separate annotation for every row that cites the same note — a section reference cited by five rows is one annotation with five locations.
- **marker_locations** — scan the ENTIRE table for every place the marker appears: `schedule_property`, `activity_name`, or `schedule_cell` (include `column_position` for cells). Every annotation MUST have at least one location; an annotation with empty `marker_locations` is an orphan, invisible downstream. If a marker appears only on an activity label, it still needs an `activity_name` entry with that `row_position`.
- **Markers referenced but not defined (source defect).** If a marker appears on a cell/label but its footnote text is not printed anywhere in the extracted source (e.g. a continuation or variant table with its own numbering that omits some footnotes), transcribe the marker where it appears but do NOT fabricate text. Set `annotation_text` to state plainly that the definition is not printed in the source; if there is an obvious same-assessment equivalent elsewhere (e.g. the Main Study table), you may add it as a clearly-labelled *probable* cross-reference — never asserted as source content. Keeps the marker faithful and the annotation resolvable; flag it in the report.
- **Redacted / illegible content (source defect).** Where a redaction box or scan defect truncates a note or may hide rows, transcribe the visible portion, append "[remainder redacted in source]" to `annotation_text`, and never fabricate the hidden text. Cross-check the markdown if available. Flag any region that may conceal activity rows in the report.
- **Header-cell footnotes (per-timepoint).** A marker on a specific header/timepoint cell — "V2ᵃ", "ETVᵇ", "V997ᶜ" — encodes as `annotation_markers` on **that column's `schedule_grid` cell** (the exact column it sits on), with the marker cleaned out of `cell_value`. Do NOT put it on the `schedule_property` row's `annotation_markers` — that scopes it to the whole row, and the footnote loses which visit/encounter it governs. This is what lets the footnote resolve to its specific column rather than collapsing to the property or the table. (A note that genuinely applies to the *whole* header row — e.g. a fasting instruction across all visits — does belong on the `schedule_property`, per the previous bullet.)
- **Notes / Instructions / Comments column.** A right-hand notes column is NOT a schedule column and is NOT an activity. Each non-empty note becomes a `footnote` annotation. **Bound each note's TEXT by the cell's rule-line geometry, not by proximity** — read the column's horizontal rules to fix where one note cell ends and the next begins, then take that cell's full text as exactly one annotation. When the page has no vector rule lines, recover them from the raster (§1d); do NOT fall back to vertical-gap proximity, which fails in both directions — it splits one note across the rows its lines overlap AND merges adjacent notes whose gap happens to be small. In the rare case where rules are genuinely unrecoverable and proximity is all there is, record it: `annotation_text_source: {"method": "proximity_bounded"}` on each such note, so the validator flags them for page verification instead of the guess passing silently (§1e). This mirrors §5 for marks: confirm the span from the rule-line geometry, not from where the glyph sits. Proximity alone splits one note across whichever rows its lines happen to overlap — producing fragments duplicated on neighbouring rows — and merges two short notes that share a band. A note cell spanning several activity rows is ONE annotation with a `marker_location` per covered row, never one annotation per row. If the source gives the note no marker, synthesise one and link it via `marker_locations` to the row it sits beside (`activity_name` or `schedule_property`), with `method: "synthesized"` on the location; a binding established by word overlap rather than position gets `method: "text_match"`; a target you cannot determine gets `location_type: "unresolved"` rather than a guess (§1e). A note attached to a header row (e.g. a fasting instruction spanning the visit row) links to that `schedule_property`. Record synthesised markers in the report. A footnote marker printed on the Notes-column *header* itself (e.g. "Notesᶜ") has no modelled element to attach to — treat it as table-scope: give the annotation one `schedule_property` `marker_location` with `method: "synthesized"` for traceability and do NOT put the marker on any element's `annotation_markers`.

## 7. Uncertainty report (this replaces the interactive gates)

After writing the JSON, output a short report — plain text, not JSON — for human post-hoc review against the per-table resolved HTML. Cover:

- **Per table:** `table_type` (and why, when not obvious), column count, activity count, and **activity rows per page across the declared page range** — call out any page in the range that contributed none (§4).
- **Merged-mark decisions:** which activity rows had a mark or text distributed across a span, and the spans.
- **Synthesised:** any synthesised `property_name` values and any synthesised annotation markers.
- **Mechanical mark-check:** the method used (bbox column-binning for text-layer §1b, rule-line/near-black-pixel detector for image §1a) and any cell where the mechanical matrix disagreed with the visual read.
- **Annotation text integrity:** whether the source text layer was glyph-spread and which fields you reconstructed (§1c); any pair of annotations whose text substantially overlaps — one contained in the other, or a long shared run at a note boundary — which usually means one note cell was split across rows, but can also be source-faithful where the source opens a longer note with the whole text of a shorter one on the row above; re-verify the pair against the page and report **which of the two it is**, not which one you assumed; and any note you could not bound confidently against its source cell.
- **Low-confidence calls:** ambiguous `property_type`, subtle hierarchy, subsidiary-vs-reference-vs-track classifications, PDF/markdown text disagreements.
- **Orphan risk:** any annotation whose `marker_locations` you could not confidently place, or any marker whose definition is not printed in the source (see §6).
- **Method provenance:** every non-default method recorded (§1e) and every `unresolved` marker location — one line each, so the report and the data agree about what was interpreted rather than read.

Only STOP mid-run if genuinely blocked (illegible PDF, missing pages). Otherwise proceed and flag — the report is the review surface, not a gate.

## 8. Output

One JSON file per table: `{NCTID}_Table_{NN}_extraction.json`. Before delivering, verify:

- `schema_name` = `soa-table-extraction`, `schema_version` = `1.0`, `extraction_status` = `ready_for_resolution`
- every `property_comment` is meaningful; every `cell_value` is clean (markers extracted)
- every annotation has ≥ 1 `marker_locations` entry (no orphans)
- any annotation whose text is contained in another's has been **re-verified against the page** — a containment pair is usually one note cell split across rows (§6), but it can also be source-faithful, where the source opens a longer note with the whole text of a shorter one on the row above. Check the page and say which it is in the report. Do NOT merge, truncate or drop either note to make the pair go away: on NCT04677179 T1 the serum-pregnancy and urine-pregnancy notes are a genuine pair, printed that way on doc pp.20 and 21
- each annotation's text is complete against its source cell: it starts at the cell's first word, ends at its last, and carries no letter-spacing or missing inter-word spaces (§1c)
- `by_type` is not degenerate across > 20 annotations — in particular NOT all `source_note`: a notes / comments column yields `footnote`s (§6). All-`footnote` IS normal.
- no `abbreviation` annotation is bound *only* by `method: "text_match"` or `method: "synthesized"` — that is the standalone abbreviation list §6 forbids, and it must be dropped rather than given a location
- every annotation whose entire text is a bare pointer — one sentence starting "See …" / "Refer to …" with nothing explained, e.g. "See Section 8.2.2.", "See Appendix 8." — is typed `source_note`, not `footnote` (§6). A note that points *and* explains ("See Appendix 2 for details. Day 1 predose sample is for baseline only.") stays a `footnote`
- every page in each table's `page_start`..`page_end` contributed activity rows, or the report says why not (§4)
- every marker in an annotation's `marker_locations` also appears in that row's `annotation_markers` (§6)
- merged marks distributed across their span with `source_range` set
- `track_label` set for `track` tables only
- `method` provenance fields recorded wherever a non-default method was used (§1e) — and no guessed targets: an undeterminable scope is `location_type: "unresolved"`, never an invented one
