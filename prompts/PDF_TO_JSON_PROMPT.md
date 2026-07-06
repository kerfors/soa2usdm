# SoA Table Extraction: PDF → JSON (single-pass, non-interactive)

> Prompt version 3.0.2 | Schema: soa-table-extraction v1.0
> Supersedes the two-conversation PDF→Excel (v2.8) + Excel→JSON (v2.4) flow for non-interactive runs. Use the v2.x flow when a human-editable Excel checkpoint is wanted; use this when you want to attach the PDF and get extraction JSON in one pass.

Extract the SoA table(s) from the attached protocol directly to `soa-table-extraction` JSON — one file per table. Run start to finish without stopping for confirmation. Surface every judgement call in the **uncertainty report** at the end instead of asking mid-run.

**Attached / in project knowledge:** this prompt, the SoA PDF (optionally the full-protocol markdown), `soa-table-extraction.schema.json`, `soa_table_type_definitions.md`. Read the schema and the taxonomy and follow them exactly. Read the XLSX skill only if you also need to emit Excel — not required here.

---

## 1. Core principle — transcribe, do not infer

- Transcribe each cell literally as it appears: `X`, `✓`, `•`, arrows, text, numbers. An empty cell stays empty.
- Do NOT infer a cell's content from neighbouring cells, the row's pattern, or clinical logic. A stronger model is a stronger pattern-completer — actively resist "completing" a sparse grid. A missing mark is data.
- Visual formatting (grey shading, bold, indentation, borders) is a hierarchy or annotation signal — never a reason to alter cell content.
- If both PDF and protocol markdown are attached: use the **PDF for structure** (column boundaries, merged cells, hierarchy, cell marks) and the **markdown for text** (activity spelling, footnote wording, header labels). Prefer markdown for text, PDF for structure. Do not use pdfplumber. Flag any PDF/markdown disagreement in the report.

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

## 4. Activities (table body)

Each activity row → one `activity`.

- **indentation_level** from visual indentation / shading / bold: section header = 0, child = 1, grandchild = 2, …
- `activity_name` is CLEAN (no leading whitespace, no annotation markers); `activity_name_source.cell_text` is RAW (preserve whitespace and markers).
- Do NOT create activity rows for non-activities: repeated column-label bands (e.g. a "Procedure" header repeated on each page), or instruction-overflow rows that only carry footnote text. These are not procedures performed on subjects.

## 5. Grid values and merged cells

- Column 1 is row labels — EXCLUDE it from `schedule_grid` and `activity_schedule`. Data columns start at position 2.
- Clean markers out of `cell_value` into `annotation_markers` (`Xᵃ` → `cell_value: "X"`, `annotation_markers: "a"`).
- A legend-defined in-grid scheduling mark stays as a `cell_value`, not an annotation — e.g. keep `P` in the grid where the legend defines `P = predose`. It is a scheduling indicator like `X`.
- **Merged marks — distribute, never centre.** A single mark sitting in a cell visually merged across N columns applies to ALL N columns. Emit one `activity_schedule` entry per covered column with the same `cell_value`, and set `source_range` to the span (e.g. `"4:15"`). Do NOT collapse a merged mark onto the one visually-centred column — that fabricates a single-visit schedule and destroys the real span. The same applies to merged text cells such as "See instructions" / "See Section x.y": one entry per covered column, `source_range` set. For merged header cells, record `is_merged_cell` / `merged_cell_range` on each covered position.

## 6. Annotations

Each footnote / legend / abbreviation → one `annotation`.

- **annotation_type:** explanatory logic or conditions → `footnote`; pure cross-references ("See Section x.y", "Refer to …") → `source_note`; symbol definitions (X = required) → `legend`; term expansions (BP = blood pressure) → `abbreviation`. Capture abbreviation and legend lists — the schema provides for them.
- **Deduplicate by text.** Emit one `annotation` per distinct note or reference, carrying a `marker_locations` entry for each occurrence. Do NOT emit a separate annotation for every row that cites the same note — a section reference cited by five rows is one annotation with five locations.
- **marker_locations** — scan the ENTIRE table for every place the marker appears: `schedule_property`, `activity_name`, or `schedule_cell` (include `column_position` for cells). Every annotation MUST have at least one location; an annotation with empty `marker_locations` is an orphan, invisible downstream. If a marker appears only on an activity label, it still needs an `activity_name` entry with that `row_position`.
- **Header-cell footnotes (per-timepoint).** A marker on a specific header/timepoint cell — "V2ᵃ", "ETVᵇ", "V997ᶜ" — encodes as `annotation_markers` on **that column's `schedule_grid` cell** (the exact column it sits on), with the marker cleaned out of `cell_value`. Do NOT put it on the `schedule_property` row's `annotation_markers` — that scopes it to the whole row, and the footnote loses which visit/encounter it governs. This is what lets the footnote resolve to its specific column rather than collapsing to the property or the table. (A note that genuinely applies to the *whole* header row — e.g. a fasting instruction across all visits — does belong on the `schedule_property`, per the previous bullet.)
- **Notes / Instructions / Comments column.** A right-hand notes column is NOT a schedule column and is NOT an activity. Each non-empty note becomes a `footnote` annotation. If the source gives the note no marker, synthesise one and link it via `marker_locations` to the row it sits beside (`activity_name` or `schedule_property`). A note attached to a header row (e.g. a fasting instruction spanning the visit row) links to that `schedule_property`. Record synthesised markers in the report.

## 7. Uncertainty report (this replaces the interactive gates)

After writing the JSON, output a short report — plain text, not JSON — for human post-hoc review against the per-table resolved HTML. Cover:

- **Per table:** `table_type` (and why, when not obvious), column count, activity count.
- **Merged-mark decisions:** which activity rows had a mark or text distributed across a span, and the spans.
- **Synthesised:** any synthesised `property_name` values and any synthesised annotation markers.
- **Low-confidence calls:** ambiguous `property_type`, subtle hierarchy, subsidiary-vs-reference-vs-track classifications, PDF/markdown text disagreements.
- **Orphan risk:** any annotation whose `marker_locations` you could not confidently place.

Only STOP mid-run if genuinely blocked (illegible PDF, missing pages). Otherwise proceed and flag — the report is the review surface, not a gate.

## 8. Output

One JSON file per table: `{NCTID}_Table_{NN}_extraction.json`. Before delivering, verify:

- `schema_name` = `soa-table-extraction`, `schema_version` = `1.0`, `extraction_status` = `ready_for_resolution`
- every `property_comment` is meaningful; every `cell_value` is clean (markers extracted)
- every annotation has ≥ 1 `marker_locations` entry (no orphans)
- merged marks distributed across their span with `source_range` set
- `track_label` set for `track` tables only
