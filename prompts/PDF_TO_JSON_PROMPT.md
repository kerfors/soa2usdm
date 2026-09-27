# SoA Table Extraction: PDF → JSON (single-pass, non-interactive)

> Prompt version 3.9.1 | Schema: soa-table-extraction v1.0
> Supersedes the two-conversation PDF→Excel (v2.8) + Excel→JSON (v2.4) flow for non-interactive runs. Use the v2.x flow when a human-editable Excel checkpoint is wanted; use this when you want to attach the PDF and get extraction JSON in one pass.

Extract the SoA table(s) from the attached protocol directly to `soa-table-extraction` JSON — one file per table. Run start to finish without stopping for confirmation. Surface every judgement call in the **uncertainty report** at the end instead of asking mid-run.

**Attached / in project knowledge:** this prompt, the SoA PDF (optionally the full-protocol markdown), `soa-table-extraction.schema.json`, `soa_table_type_definitions.md`. Read the schema and the taxonomy and follow them exactly. Read the XLSX skill only if you also need to emit Excel — not required here.

---

## 1. Core principle — transcribe, do not infer

- Transcribe each cell literally as it appears: `X`, `✓`, `•`, arrows, text, numbers. An empty cell stays empty (§5 **Empty cells** says how it is recorded).
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

- **reference test first:** are the rows activities performed on subjects? If NO → `reference` (e.g. sample-spec tables whose rows are "Sample 1, Sample 2…" and give only collection specifications — tube, volume, processing — with no timing; abbreviation lists). A sampling table whose rows carry timing is not `reference`: see the PK-sampling note below. **But check what the rows key to before typing it `reference`:** if each row names an activity, visit or timepoint that already appears in the SoA and the row's other cell explains it, that content is annotations under §6 — emit one annotation per distinct note, bound to the element it names — not a table.
- **subsidiary vs track:** finer timing for a subset of activities already in another table → `subsidiary`; a genuinely separate timeline with its own visits/duration/population → `track` (set `track_label`, see below; and the next bullet).
- **track vs main_soa — does every participant pass through it?** A `track` is a branch that only some participants take: a sub-population, a cohort or arm, a sub-study, responders vs non-responders, or a later phase that only some participants enter (e.g. post-study access, or visits after early termination printed as a schedule of their own). A schedule that every participant passes through in sequence — screening, then treatment, then follow-up — is `main_soa` even when the source prints it as separate tables with their own visit numbering; each such table is typed `main_soa`. Sequence alone never makes a table a `track`. A table printed for visits entered on a condition rather than in sequence — early termination, unscheduled visits, conditional follow-up — is a `track`, also when it also carries a visit that every participant attends.
- **`track_label` is a short identifier, not a description.** Use the shortest phrase that tells this track apart from the other tracks in the *same study* — aim for one to four words, e.g. "Prediabetes", "Cohort 1", "Continued Access", "Extension (nonresponders)", "Early Termination / Unscheduled / Post-Treatment". Take the words from the source's own population or phase wording; do not compose a sentence, and do not restate the table number, the study name, the visit range, or filler like "Schedule of Activities" / "Treatment Period" when the label already distinguishes the track without it. Where the source spells the term inconsistently, follow the table title or the population statement rather than a column header. Keep the source's capitalisation of those words; when the source prints them inside running text, capitalise the first letter only. These labels surface as `population_track` on every column of the table, so they are read far more often than they are written.
- **domain vs continuation:** same columns as the parent — rows continue across a page break → `continuation` (set `continuation_of`); different activity category on the shared timeline, **for the same participants** → `domain`.
- **domain vs track — ask who attends, not what the columns say.** Same columns is NOT sufficient for `domain`. If the two tables schedule **mutually exclusive populations** (responders vs non-responders, arm A vs arm B), each is a `track` even when their visit labels, weeks and study days are numerically identical — the sponsor reused a numbering scheme, that is all. Misclassifying a population split as `domain` is silent: `schedule_matrix` and the column count are unchanged, but every column in that table loses its `population_track` and the branch identity disappears.
- otherwise the primary anchor grid → `main_soa`.

Note on the PK-sampling ambiguity: a table that breaks a single main-SoA activity (e.g. "PK sampling") into per-sample timing rows satisfies the `subsidiary` definition even though its rows read "Sample n". Classify by function (finer timing for an existing activity) and **transcribe it in printed orientation**: the rows stay the printed sample rows, the timing values (cycle, day, time) stay data cells in their own columns, and the columns that mark which analysis a sample serves stay mark columns. Do not transpose it into timepoint columns — that turns data values into column identities, which is interpretation; reshaping belongs to a downstream step. Name each row from the row-label heading and its printed number (e.g. 'Sample 3'), keeping the printed cell text in `cell_text`, and state in `table_metadata.notes` that the table is row-oriented. This is a rule, not an open call: list it under Recorded, not open (§7).

For any `table_type` that is not obvious from the discriminators alone, record the reasoning in `table_metadata.notes` as well as the report — the classification is an interpretation, and `notes` is where its provenance lives in the data.

## 3. Schedule properties (header rows)

Each header row → one `schedule_property`.

- **property_type** from the actual values: Screening/Treatment/Follow-up → `epoch`; V1/Baseline/EOS → `visit`; Day −7/Day 1 → `study_day`; Week 0/Week 4 → `week`; 0h/2h post-dose → `timepoint`; Cycle 1/Cycle 2 → `cycle`; ±3 days → `window`; unclear → `other`.
- **Header bands — typing.** Type a band by its dominant content: the values that span several columns decide; where no value spans several columns, all its values do. A printed row label wins over the values — a row labelled with a cycle term stays `cycle` even where some of its cells name something else. Single-column visit labels inside an epoch or period band (a randomisation visit, end of treatment, early discontinuation, end of study) stay values of that band; they do not make it a `visit` row. A blank span in a band stays blank (`""`, §5 **Empty cells**): do not copy into it the value of the band above or below. Where the bands' print order does not match the usual hierarchy (visit-type labels printed above periods), keep the print order for `hierarchical_level`, type each band by these rules, and say in `property_comment` what the band mixes.
- **Header cells over several rows.** A header cell that spans two or more header rows is recorded once, on the row whose `property_type` matches its content — the upper row when more than one matches; the cells it covers on the other rows stay empty (`""`). Where its printed lines match different rows (a phase name above a day range), split it by printed line, each line on its own row. Do not repeat the value on the covered rows and do not add a header row for it. A qualifier printed inside one header cell stays in that cell's value.
- **hierarchical_level** counted from the top (topmost row = 1, downward). Assign a level to every header row that helps distinguish one column from another — if removing the row would make two columns indistinguishable, it needs a level. Use `null` only for purely presentational qualifier rows that do not participate in telling columns apart. A row whose values follow from another header row — a duration that restates the day range, a fasting flag — does not tell columns apart: `null`.
- **property_comment** is REQUIRED — state what the row contains and the reasoning for its `property_type`.
- If the label cell is empty but the row clearly carries schedule data spanning columns, synthesise `property_name` and set `property_name_source.synthesized: true`. **A synthesised name is the fixed name of the row's `property_type`:** `Epoch`, `Period`, `Cycle`, `Visit`, `Study Day`, `Week`, `Timepoint`, `Window`, `Modality`, `Condition`; for `other`, a short noun phrase in sentence case that says what the values are. Where two synthesised rows in one table share a type, number them from the top (`Period 1`, `Period 2`). The same applies when the label cell prints the heading of the activity column (e.g. 'Procedure') rather than a name for the row: that text labels the activity column, so keep it in `property_name_source.cell_value` and synthesise the name. Document synthesised names in the report.
- When `property_type` or `hierarchical_level` come from layout geometry or working assumption rather than printed header labels, set `structure_method` (`inferred_from_layout` / `assumed`) — see §1e.
- A population / eligibility qualifier band (e.g. "Patients who have PD …" spanning only some columns) → `property_type: condition`; give it `hierarchical_level: null` when it does not by itself distinguish one column from another.

## 4. Activities (table body)

Each activity row → one `activity`.

- **`row_position`** counts the table's rows from the top, starting at 1 with the first header row; a title band printed inside the frame is not a row (it goes to `table_title`). Rows left out (a reprinted header, a 'Procedure' band) keep their number: never renumber.

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
- **Hierarchy — printed signals only.** A level comes from a printed signal: indent, bold, shading, or a full-width section band. A single leading space in the text layer is not an indent. A group stays open across a page break until the next group header, also where no band is reprinted at the top of the new page. Do not invent a group: rows printed before the first group header stay at level 0, and a row joins a group only through a printed signal — its own indent or shading, or a full-width band above it that is still open. A label cell spanning several sub-rows is a mark-free parent with the sub-rows as its children; a leading category column whose cells span several rows works the same way, and with several label columns each column is one level. A row that carries its own marks is an activity, not a group header.
- **Several procedures in one label cell.** A ruled label cell whose printed lines each name a distinct procedure — each line starts a new name rather than continuing the previous one — is one activity per line, in print order, at the level the cell would have; the cell's marks go on each. Lines that continue one name (a broken word, a line ending in '/' or '-', a line starting in lower case) are joined under **Whitespace**.
- `activity_name` is CLEAN (no leading whitespace, no annotation markers); `activity_name_source.cell_text` is RAW (preserve whitespace and markers). **Whitespace in `activity_name`:** join the cell's printed lines with one space, except where a line ends in `/` or `-` or the next line starts with `/` — there, join with no space (the hyphen stays). A word that a narrow column breaks without a hyphen ('Electrocardio' + 'gram') joins with no space. Collapse runs of spaces to one. A space inside a printed line stays as printed (`A / B` stays `A / B`). Header cell values and `track_label` follow the same rule.
- Do NOT create activity rows for non-activities: repeated column-label bands (e.g. a "Procedure" header repeated on each page), or instruction-overflow rows that only carry footnote text. These are not procedures performed on subjects.
- Organizational / section-header rows (indentation_level 0 that group child activities) carry NO scheduling marks. Exception: a *flat* table where every row is a level-0 activity that itself carries marks — there are no grouping headers to keep mark-free.

## 5. Grid values and merged cells

- **Leading label columns are excluded, and `column_position` keeps the source's own column numbering.** Count the label columns on the left: the activity-name column, plus any further column that labels the row rather than schedules it — a Protocol Reference column, a Procedure Category column, or the narrow column carrying the header rows' own labels ("VISIT", "WEEK"). EXCLUDE every one of them from `schedule_grid` and `activity_schedule`, and do NOT renumber what is left: with `L` label columns the first data column is position `L+1`. One label column therefore starts at 2 (the usual case), two start at 3, three start at 4. Renumbering the data columns to 2 when `L` > 1 shifts every `column_position`, every `source_range` and every `merged_cell_range` in the table while nothing about the source has changed, and no count-based check can see the difference. State `L` and the first data position in the report.
- Clean markers out of `cell_value` into `annotation_markers` (`Xᵃ` → `cell_value: "X"`, `annotation_markers: "a"`).
- **Empty cells — one convention.** `schedule_grid` is complete: one entry for every header row that has a `schedule_property` × every data column, with `cell_value: ""` where the header cell is blank or is covered by a header cell recorded on another row (§3). The grid is the only record of a data column that carries no header text at all, so leaving out a blank header cell drops the column. `activity_schedule` holds non-empty cells only: an empty body cell has no entry.
- A legend-defined in-grid scheduling mark stays as a `cell_value`, not an annotation — e.g. keep `P` in the grid where the legend defines `P = predose`. It is a scheduling indicator like `X`.
- **Merged marks — distribute, never centre.** A single mark sitting in a cell visually merged across N columns applies to ALL N columns. Emit one `activity_schedule` entry per covered column with the same `cell_value`, and set `source_range` to the span (e.g. `"4:15"`). Do NOT collapse a merged mark onto the one visually-centred column — that fabricates a single-visit schedule and destroys the real span. Confirm every span from the rule-line geometry (§1b text-layer / §1a image), not from where the glyph sits. The same applies to merged text cells such as "See instructions" / "See Section x.y": one entry per covered column, `source_range` set — except the two cases under **Spanned values** below. For merged header cells, record `is_merged_cell` / `merged_cell_range` on each covered position (horizontal spans; a header cell spanning several header rows: §3 **Header cells over several rows**).
- **Spanned values — which columns a value covers.** The rule lines decide, not the glyph. A value in a merged cell covers every column its rule lines enclose; a glyph (mark, arrow, text) drawn across ruled cells covers each cell it reaches; a value printed in one ruled cell stays in that one column, with any qualifier kept in `cell_value` (**Qualified marks** below). Two exceptions, taken only where the source itself shows that the literal reading is wrong; list each one under Recorded, not open (§7):
  - *A cross-reference over the whole schedule.* A cell that spans every data column (possibly running on into a notes column) and whose whole text is a pointer ("See …", "Refer to …") says nothing about timing. Emit it as a `source_note` on the activity (§6) and emit no `activity_schedule` entries for it. A pointer whose cell covers only some of the columns keeps its span: the span is the timing.
  - *Text that names its own columns.* Where a merged cell is drawn wider than what its text names — it names cycles, visits or a period that not every covered column carries — distribute it over the columns it names only, and state in `table_metadata.notes` which further columns the drawn cell covers.
- **Ranges are numeric column positions, always.** Both `source_range` and `merged_cell_range` take the form `"<first>:<last>"` in the same `column_position` numbering as the rest of the table — `"4:9"`, `"12:24"`. **Never spreadsheet A1 notation** (`"D1:E1"`). The schema's own description for `merged_cell_range` shows an A1-style example; it is wrong and this rule overrides it. The field is typed as a bare string, so an A1 value passes validation silently and splits the corpus into two notations that no count-based check can see.
- **Horizontally tiled wide tables — union rows across tiles.** When one logical table is split into side-by-side column-block tiles because it is too wide for the page (e.g. V10–V19 in one spread, V20–V29 in a "(continued)" spread), the tiles **share their body rows**: the same activity typically appears in *both* tiles, carrying marks in each. Merge by activity name and take the **union** of marks across tiles. Do NOT assume a recurring row prints in only one tile and keep only that tile's marks — that silently drops the other tile's visits. Confirm each row's presence in *every* tile against the PDF; a row genuinely absent from one tile is the exception (e.g. an explicit "Not applicable during V10–V19" note), not the rule. Decide per row.
- **Arrows spanning columns.** A horizontal arrow (`↔`, `→`) drawn across N columns denotes a continuous activity over that span — distribute like a merged mark: one `activity_schedule` entry per covered column, `cell_value` the arrow glyph, `source_range` the span. Confirm arrow extents visually — arrows are vector graphics and are invisible to text-coordinate parsers. An arrow inside a merged cell covers the cell's span even where the drawn arrow is shorter; an arrow drawn across ruled cells covers each cell its shaft or head reaches (**Spanned values**).
- **Vertically-merged marks.** A single mark centred across two or more *activity rows* applies to every covered row. The schema has no vertical merge, so emit the mark on each covered activity's cell.
- **Qualified marks.** A mark carrying a parenthetical label ("X (Cycle 5 only)", "X (Day 3-5)") stays in the ruled cell it is printed in, with the qualifier kept literally in `cell_value` — also when the label names other columns of the table. The label is a window or a condition on that one scheduled cell; distributing it would turn one mark into several visits. Only rule lines widen a value (**Spanned values**).
- **Glyph case.** Transcribe `x` vs `X` (and `✓`, `•`) literally. Only normalise an obvious scan-rendering inconsistency, and flag it in the report when you do.

## 6. Annotations

Each footnote / legend / cross-reference → one `annotation` (abbreviations are not annotations; see below).

- **annotation_type:** explanatory logic or conditions → `footnote`; pure cross-references ("See Section x.y", "Refer to …") → `source_note`; symbol definitions (X = required) → `legend`. Capture a `legend` entry only when that symbol actually appears in the table (e.g. a legend `X`/`P` used as an in-grid mark → `legend` with `marker_locations` on the cells that use it). Do NOT emit a standalone legend *list* whose symbols carry no in-grid mark — every annotation needs ≥1 `marker_location` (§7), so an unreferenced list entry is an orphan and is dropped downstream. **Abbreviations are not annotations.** A term expansion (BP = blood pressure) describes a term, not a schedule element: do not emit it, wherever the term is printed — in running text, inside an activity label, or as a whole header or grid cell (an abbreviated visit label stays as printed in its `cell_value`). An abbreviation block therefore yields **zero** annotations. The schema keeps the `abbreviation` type for older extractions; do not use it. A `source_note` is a cross-reference to elsewhere in the protocol — a dedicated reference column, a standalone "See Section x.y" note, **and** a section/appendix/attachment reference printed inline in an activity's label (e.g. "Inclusion criteria (6.1)", "HbA1c (Appendix 2)", "Trial product compliance (7.1) (7.6)"). Strip inline references OUT of `activity_name` (keep them in `activity_name_source.cell_text`), emit each as a `source_note` deduplicated by text (one annotation per distinct reference), and add a synthesised marker (`pr1`, `pr2`, …) to every citing activity's `annotation_markers` so resolve links it — a synthesised marker that sits on no element resolves as table-scoped/unlinked. Split multiple references on one label into separate notes.
- **`annotation_markers` and `marker_locations` must agree — the first one is what actually binds.** For every location you record on an annotation, add that marker to the same row's `annotation_markers` (on the `schedule_property`, the `activity`, or the `schedule_cell`). Resolve links an annotation to its activity through the ROW's `annotation_markers` string; `marker_locations` is only consulted when that yields nothing. So a location recorded on one side and not the other is silently dropped, with nothing failing anywhere in the pipeline.
- **Deduplicate by text.** Emit one `annotation` per distinct note or reference, carrying a `marker_locations` entry for each occurrence. Do NOT emit a separate annotation for every row that cites the same note — a section reference cited by five rows is one annotation with five locations.
- **Marker out of the text.** `annotation_text` starts after the printed marker or symbol and its '=' ('X = Required.' → 'Required.'); the symbol is the `annotation_marker`.
- **marker_locations** — scan the ENTIRE table for every place the marker appears: `schedule_property`, `activity_name`, or `schedule_cell` (include `column_position` for cells). Every annotation MUST have at least one location; an annotation with empty `marker_locations` is an orphan, invisible downstream. If a marker appears only on an activity label, it still needs an `activity_name` entry with that `row_position`.
- **Markers referenced but not defined (source defect).** If a marker appears on a cell/label but its footnote text is not printed anywhere in the extracted source (e.g. a continuation or variant table with its own numbering that omits some footnotes), transcribe the marker where it appears but do NOT fabricate text. Set `annotation_text` to state plainly that the definition is not printed in the source; if there is an obvious same-assessment equivalent elsewhere (e.g. the Main Study table), you may add it as a clearly-labelled *probable* cross-reference — never asserted as source content. Keeps the marker faithful and the annotation resolvable; flag it in the report.
- **Redacted / illegible content (source defect).** Where a redaction box or scan defect truncates a note or may hide rows, transcribe the visible portion, append "[remainder redacted in source]" to `annotation_text`, and never fabricate the hidden text. Cross-check the markdown if available. Flag any region that may conceal activity rows in the report.
- **Header-cell footnotes (per-timepoint).** A marker on a specific header/timepoint cell — "V2ᵃ", "ETVᵇ", "V997ᶜ" — encodes as `annotation_markers` on **that column's `schedule_grid` cell** (the exact column it sits on), with the marker cleaned out of `cell_value`. Do NOT put it on the `schedule_property` row's `annotation_markers` — that scopes it to the whole row, and the footnote loses which visit/encounter it governs. This is what lets the footnote resolve to its specific column rather than collapsing to the property or the table. (A note that genuinely applies to the *whole* header row — e.g. a fasting instruction across all visits — does belong on the `schedule_property`, per the previous bullet.)
- **Notes / Instructions / Comments column.** A right-hand notes column is NOT a schedule column and is NOT an activity. Each non-empty note becomes a `footnote` annotation. **Bound each note's TEXT by the cell's rule-line geometry, not by proximity** — read the column's horizontal rules to fix where one note cell ends and the next begins, then take that cell's full text as exactly one annotation. When the page has no vector rule lines, recover them from the raster (§1d); do NOT fall back to vertical-gap proximity, which fails in both directions — it splits one note across the rows its lines overlap AND merges adjacent notes whose gap happens to be small. In the rare case where rules are genuinely unrecoverable and proximity is all there is, record it: `annotation_text_source: {"method": "proximity_bounded"}` on each such note, so the validator flags them for page verification instead of the guess passing silently (§1e). This mirrors §5 for marks: confirm the span from the rule-line geometry, not from where the glyph sits. Proximity alone splits one note across whichever rows its lines happen to overlap — producing fragments duplicated on neighbouring rows — and merges two short notes that share a band. A note cell spanning several activity rows is ONE annotation with a `marker_location` per covered row, never one annotation per row. If the source gives the note no marker, synthesise one and link it via `marker_locations` to the row it sits beside (`activity_name` or `schedule_property`) — unless its text names specific visits or columns, or no element at all (**Binding by what a note names**, next bullet) — with `method: "synthesized"` on the location; a binding established by word overlap rather than position gets `method: "text_match"`; a target you cannot determine gets `location_type: "unresolved"` rather than a guess (§1e). A note attached to a header row (e.g. a fasting instruction spanning the visit row) links to that `schedule_property`. Record synthesised markers in the report. A footnote marker printed on the Notes-column *header* itself (e.g. "Notesᶜ") has no modelled element to attach to — treat it as table-scope: give the annotation one `schedule_property` `marker_location` with `method: "synthesized"` for traceability and do NOT put the marker on any element's `annotation_markers`.
- **Text above or below the frame.** Text printed between the table's title and its frame, or directly below the frame before the next heading, belongs to the table: emit it as annotations, bound under **Binding by what a note names** — a note naming no element is table-wide (`g`). Abbreviation lines stay excluded (**Abbreviations are not annotations**).
- **Binding by what a note names.** For a note the source prints without a marker, bind it to what its text names, not to where it happens to be printed (a printed marker's positions are its binding, §1e):
  - A note that names specific visits or columns (by visit label, day, week or cycle) is bound to those cells: to the header cells when it is a condition on the visit, to the activity's cells when it is a condition on one scheduled mark. Where no printed marker establishes the binding, the location gets `method: "text_match"`. Bind to a visit only what states a condition on it (who attends, what is done or not done, when); a visit named as a reference point or comparison is not bound.
  - Where one sentence of a longer note names a single cell and the rest applies to the whole row, split that sentence into its own note bound to that cell. Both texts stay verbatim and together are the whole printed text.
  - A note printed on a mark-free group row governs the group: bind it to the group row, not to each child.
  - A note that names no specific element — a precedence rule among procedures, an instruction for the whole table — stays table-wide: give it a `g` marker and one `schedule_property` `marker_location` on the top header row with `method: "synthesized"`, and do NOT put the marker on any element's `annotation_markers` (the same table-scope convention as a marker on the Notes-column header).
- **Synthesised markers — prefix and numbering.** Use exactly these prefixes: `pr` for a cross-reference `source_note` (an inline label reference or a reference-column entry), `n` for a note the source prints without a marker (a notes / comments / instructions column cell, an unmarked note paragraph, a sentence in a header or title cell), `g` for a table-wide note with no specific target. Number per table, from 1, in reading order: header rows top to bottom and left to right, then body rows, then text below the table; a note cited in several places takes the number of its first occurrence. Number every candidate note before deciding whether to emit it: a note you then do not emit leaves its number unused — never renumber the others to close the gap. A synthesised marker never repeats a marker the source prints.

## 7. Uncertainty report (this replaces the interactive gates)

After writing the JSON, output a short report — plain text, not JSON — for human post-hoc review against the per-table resolved HTML.

**The report opens with two blocks, before anything else:**

1. **`## Decisions needed (N)`** — one table row per open judgement call: a call you made deliberately that a reviewer could reasonably overturn **and that no rule of this prompt or of the taxonomy decides**. A call that a stated rule decides is not open, whatever its severity: it goes in the next block. Columns: `#` (D1, D2, … — numbered once across ALL tables of the protocol, in report order), `where` (document page and the row(s) or marker), `call made`, `alternative`, `detail` (the report section holding the reasoning). Write `call made` and `alternative` so that a reviewer who has never seen the schema can choose between them. Nothing here is a suspected error — errors go in the sections below. N may be 0; the heading is still printed. A call whose rule you cite under Recorded, not open is closed: do not also list it here.
2. **`## Recorded, not open (N)`** — calls made under an explicit rule of this prompt or of the taxonomy, one line each naming the rule by its section and bold name (e.g. `§5 Empty cells`), so a reviewer knows they were considered rather than overlooked.

**Every row of the Decisions-needed block is ALSO emitted as data**: the `review_items` array of the extraction JSON of the table the call belongs to (one entry per row, same `id`, `severity` high when the call changes rows, marks or what a note governs / medium when it changes a type or a name / low for presentation, `location` with the document page and the row position(s) or marker, `call_made`, `alternative`, `report_section`). The block and the arrays must agree one-to-one — the gate checks it. A call that concerns more than one table goes in the first table's array. Do NOT record a resolution anywhere: the raw extraction is immutable, and an item becomes "decided" only when a later corrections-sidecar entry names its id.

Then cover:

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

One JSON file per table: `{NCTID}_Table_{NN}_extraction.json`.

Set `extraction_metadata` provenance as follows:

- `extractor` = `Claude, PDF_TO_JSON_PROMPT single-pass` — exactly this string
- `prompt_version` = the version in this prompt's header line, e.g. `3.9.1`
- do **not** set `model` — the orchestration step records it from the run setting

Before delivering, verify:

- `schema_name` = `soa-table-extraction`, `schema_version` = `1.0`, `extraction_status` = `ready_for_resolution`
- every `property_comment` is meaningful; every `cell_value` is clean (markers extracted)
- every annotation has ≥ 1 `marker_locations` entry (no orphans)
- any annotation whose text is contained in another's has been **re-verified against the page** — a containment pair is usually one note cell split across rows (§6), but it can also be source-faithful, where the source opens a longer note with the whole text of a shorter one on the row above. Check the page and say which it is in the report. Do NOT merge, truncate or drop either note to make the pair go away: on NCT04677179 T1 the serum-pregnancy and urine-pregnancy notes are a genuine pair, printed that way on doc pp.20 and 21
- each annotation's text is complete against its source cell: it starts at the cell's first word, ends at its last, and carries no letter-spacing or missing inter-word spaces (§1c)
- `by_type` is not degenerate across > 20 annotations — in particular NOT all `source_note`: a notes / comments column yields `footnote`s (§6). All-`footnote` IS normal.
- no `abbreviation` annotation at all — abbreviations are not annotations (§6)
- every annotation whose entire text is a bare pointer — one sentence starting "See …" / "Refer to …" with nothing explained, e.g. "See Section 8.2.2.", "See Appendix 8." — is typed `source_note`, not `footnote` (§6). A note that points *and* explains ("See Appendix 2 for details. Day 1 predose sample is for baseline only.") stays a `footnote`
- every page in each table's `page_start`..`page_end` contributed activity rows, or the report says why not (§4)
- every marker in an annotation's `marker_locations` also appears in that row's `annotation_markers` (§6)
- merged marks distributed across their span with `source_range` set
- `track_label` set for `track` tables only
- `method` provenance fields recorded wherever a non-default method was used (§1e) — and no guessed targets: an undeterminable scope is `location_type: "unresolved"`, never an invented one
- every row of the report's Decisions-needed block (§7) has exactly one `review_items` entry with the same id, and no `review_items` entry lacks a row; ids run D1, D2, … once across the whole protocol
- no Decisions-needed row names a call that a stated rule decides (§7) — such a call is listed under Recorded, not open
