# SoA Table Extraction: PDF → JSON (single-pass, non-interactive)

> Prompt version 3.1.0 | Schema: soa-table-extraction v1.0
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

First test whether the SoA pages have a text layer (`pdftotext` returns little or nothing → scanned image; a lone small image such as a logo does not make a text-layer table "image-based"). If image-based, render each page and read the grid visually. For dense grids, reconstruct marks by detecting the rule-line geometry (column and row boundaries) and testing each cell for a mark (dark-pixel count), then **validate the detector against direct visual reads on several representative full-width rows** (at least one dense and one sparse) before trusting it. State the image-based method in the report and recommend a spot-check of the resolved grid. Mixed documents occur — the grid may be scanned while the footnote pages carry a real text layer: pull footnote wording from the text layer, read the grid from the image.

## 2. Tables — classify before extracting

Assign `table_type` to every table per `soa_table_type_definitions.md`. Apply the discriminators explicitly:

- **reference test first:** are the rows activities performed on subjects? If NO → `reference` (e.g. sample-spec tables whose rows are "Sample 1, Sample 2…", abbreviation lists).
- **subsidiary vs track:** finer timing for a subset of activities already in another table → `subsidiary`; a genuinely separate timeline with its own visits/duration/population → `track` (set `track_label` to the concise identifier, e.g. "Continued Access", "Responders", "Prediabetes").
- **domain vs continuation:** same columns as the parent — rows continue across a page break → `continuation` (set `continuation_of`); different activity category on the shared timeline → `domain`.
- otherwise the primary anchor grid → `main_soa`.

Note on the PK-sampling ambiguity: a table that breaks a single main-SoA activity (e.g. "PK sampling") into per-sample timing rows satisfies the `subsidiary` definition even though its rows read "Sample n". Classify by function (finer timing for an existing activity), and record the call in the report.

## 3. Schedule properties (header rows)

Each header row → one `schedule_property`.

- **property_type** from the actual values: Screening/Treatment/Follow-up → `epoch`; V1/Baseline/EOS → `visit`; Day −7/Day 1 → `study_day`; Week 0/Week 4 → `week`; 0h/2h post-dose → `timepoint`; Cycle 1/Cycle 2 → `cycle`; ±3 days → `window`; unclear → `other`.
- **hierarchical_level** counted from the top (topmost row = 1, downward). Assign a level to every header row that helps distinguish one column from another — if removing the row would make two columns indistinguishable, it needs a level. Use `null` only for purely presentational qualifier rows that do not participate in telling columns apart.
- **property_comment** is REQUIRED — state what the row contains and the reasoning for its `property_type`.
- If the label cell is empty but the row clearly carries schedule data spanning columns, synthesise `property_name` and set `property_name_source.synthesized: true`. Synthesised names are fine; document them in the report.
- A population / eligibility qualifier band (e.g. "Patients who have PD …" spanning only some columns) → `property_type: condition`; give it `hierarchical_level: null` when it does not by itself distinguish one column from another.

## 4. Activities (table body)

Each activity row → one `activity`.

- **indentation_level** from visual indentation / shading / bold: section header = 0, child = 1, grandchild = 2, …
- `activity_name` is CLEAN (no leading whitespace, no annotation markers); `activity_name_source.cell_text` is RAW (preserve whitespace and markers).
- Do NOT create activity rows for non-activities: repeated column-label bands (e.g. a "Procedure" header repeated on each page), or instruction-overflow rows that only carry footnote text. These are not procedures performed on subjects.
- Organizational / section-header rows (indentation_level 0 that group child activities) carry NO scheduling marks. Exception: a *flat* table where every row is a level-0 activity that itself carries marks — there are no grouping headers to keep mark-free.

## 5. Grid values and merged cells

- Column 1 is row labels — EXCLUDE it from `schedule_grid` and `activity_schedule`. Data columns start at position 2.
- Clean markers out of `cell_value` into `annotation_markers` (`Xᵃ` → `cell_value: "X"`, `annotation_markers: "a"`).
- A legend-defined in-grid scheduling mark stays as a `cell_value`, not an annotation — e.g. keep `P` in the grid where the legend defines `P = predose`. It is a scheduling indicator like `X`.
- **Merged marks — distribute, never centre.** A single mark sitting in a cell visually merged across N columns applies to ALL N columns. Emit one `activity_schedule` entry per covered column with the same `cell_value`, and set `source_range` to the span (e.g. `"4:15"`). Do NOT collapse a merged mark onto the one visually-centred column — that fabricates a single-visit schedule and destroys the real span. The same applies to merged text cells such as "See instructions" / "See Section x.y": one entry per covered column, `source_range` set. For merged header cells, record `is_merged_cell` / `merged_cell_range` on each covered position.
- **Arrows spanning columns.** A horizontal arrow (`↔`, `→`) drawn across N columns denotes a continuous activity over that span — distribute like a merged mark: one `activity_schedule` entry per covered column, `cell_value` the arrow glyph, `source_range` the span. Confirm arrow extents visually — arrows are vector graphics and are invisible to text-coordinate parsers.
- **Vertically-merged marks.** A single mark centred across two or more *activity rows* applies to every covered row. The schema has no vertical merge, so emit the mark on each covered activity's cell.
- **Qualified marks.** A mark carrying a parenthetical label ("X (Cycle 5 only)", "X (Day 3-5)"): if the label names a span of the table's own columns, distribute across those columns with `source_range`; if it is a condition not expressible as columns, keep the qualifier literally in `cell_value`.
- **Glyph case.** Transcribe `x` vs `X` (and `✓`, `•`) literally. Only normalise an obvious scan-rendering inconsistency, and flag it in the report when you do.

## 6. Annotations

Each footnote / legend / abbreviation → one `annotation`.

- **annotation_type:** explanatory logic or conditions → `footnote`; pure cross-references ("See Section x.y", "Refer to …") → `source_note`; symbol definitions (X = required) → `legend`; term expansions (BP = blood pressure) → `abbreviation`. Capture a `legend`/`abbreviation` entry only when that term's marker actually appears in the table (e.g. a legend `X`/`P` used as an in-grid mark → `legend` with `marker_locations` on the cells that use it). Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker — every annotation needs ≥1 `marker_location` (§7), so an unreferenced list entry is an orphan and is dropped downstream. A `source_note` is a cross-reference to elsewhere in the protocol — a dedicated reference column, a standalone "See Section x.y" note, **and** a section/appendix/attachment reference printed inline in an activity's label (e.g. "Inclusion criteria (6.1)", "HbA1c (Appendix 2)", "Trial product compliance (7.1) (7.6)"). Strip inline references OUT of `activity_name` (keep them in `activity_name_source.cell_text`), emit each as a `source_note` deduplicated by text (one annotation per distinct reference), and add a synthesised marker (`pr1`, `pr2`, …) to every citing activity's `annotation_markers` so resolve links it — a synthesised marker that sits on no element resolves as table-scoped/unlinked. Split multiple references on one label into separate notes.
- **Deduplicate by text.** Emit one `annotation` per distinct note or reference, carrying a `marker_locations` entry for each occurrence. Do NOT emit a separate annotation for every row that cites the same note — a section reference cited by five rows is one annotation with five locations.
- **marker_locations** — scan the ENTIRE table for every place the marker appears: `schedule_property`, `activity_name`, or `schedule_cell` (include `column_position` for cells). Every annotation MUST have at least one location; an annotation with empty `marker_locations` is an orphan, invisible downstream. If a marker appears only on an activity label, it still needs an `activity_name` entry with that `row_position`.
- **Markers referenced but not defined (source defect).** If a marker appears on a cell/label but its footnote text is not printed anywhere in the extracted source (e.g. a continuation or variant table with its own numbering that omits some footnotes), transcribe the marker where it appears but do NOT fabricate text. Set `annotation_text` to state plainly that the definition is not printed in the source; if there is an obvious same-assessment equivalent elsewhere (e.g. the Main Study table), you may add it as a clearly-labelled *probable* cross-reference — never asserted as source content. Keeps the marker faithful and the annotation resolvable; flag it in the report.
- **Redacted / illegible content (source defect).** Where a redaction box or scan defect truncates a note or may hide rows, transcribe the visible portion, append "[remainder redacted in source]" to `annotation_text`, and never fabricate the hidden text. Cross-check the markdown if available. Flag any region that may conceal activity rows in the report.
- **Header-cell footnotes (per-timepoint).** A marker on a specific header/timepoint cell — "V2ᵃ", "ETVᵇ", "V997ᶜ" — encodes as `annotation_markers` on **that column's `schedule_grid` cell** (the exact column it sits on), with the marker cleaned out of `cell_value`. Do NOT put it on the `schedule_property` row's `annotation_markers` — that scopes it to the whole row, and the footnote loses which visit/encounter it governs. This is what lets the footnote resolve to its specific column rather than collapsing to the property or the table. (A note that genuinely applies to the *whole* header row — e.g. a fasting instruction across all visits — does belong on the `schedule_property`, per the previous bullet.)
- **Notes / Instructions / Comments column.** A right-hand notes column is NOT a schedule column and is NOT an activity. Each non-empty note becomes a `footnote` annotation. If the source gives the note no marker, synthesise one and link it via `marker_locations` to the row it sits beside (`activity_name` or `schedule_property`). A note attached to a header row (e.g. a fasting instruction spanning the visit row) links to that `schedule_property`. Record synthesised markers in the report. A footnote marker printed on the Notes-column *header* itself (e.g. "Notesᶜ") has no modelled element to attach to — treat it as table-scope: give the annotation one `schedule_property` `marker_location` for traceability and do NOT put the marker on any element's `annotation_markers`.

## 7. Uncertainty report (this replaces the interactive gates)

After writing the JSON, output a short report — plain text, not JSON — for human post-hoc review against the per-table resolved HTML. Cover:

- **Per table:** `table_type` (and why, when not obvious), column count, activity count.
- **Merged-mark decisions:** which activity rows had a mark or text distributed across a span, and the spans.
- **Synthesised:** any synthesised `property_name` values and any synthesised annotation markers.
- **Low-confidence calls:** ambiguous `property_type`, subtle hierarchy, subsidiary-vs-reference-vs-track classifications, PDF/markdown text disagreements.
- **Orphan risk:** any annotation whose `marker_locations` you could not confidently place, or any marker whose definition is not printed in the source (see §6).

Only STOP mid-run if genuinely blocked (illegible PDF, missing pages). Otherwise proceed and flag — the report is the review surface, not a gate.

## 8. Output

One JSON file per table: `{NCTID}_Table_{NN}_extraction.json`. Before delivering, verify:

- `schema_name` = `soa-table-extraction`, `schema_version` = `1.0`, `extraction_status` = `ready_for_resolution`
- every `property_comment` is meaningful; every `cell_value` is clean (markers extracted)
- every annotation has ≥ 1 `marker_locations` entry (no orphans)
- merged marks distributed across their span with `source_range` set
- `track_label` set for `track` tables only
