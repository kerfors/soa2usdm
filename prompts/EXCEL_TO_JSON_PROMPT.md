# SoA Table Extraction: Excel to JSON

> Prompt version 2.4.0 | Schema: soa-table-extraction v1.0

Convert the attached verified Excel SoA table to soa-table-extraction JSON format.

The soa-table-extraction.schema.json is in project knowledge — read it and follow it exactly.

---

## EXTRACTION LOGIC

### Table Metadata

From the Annotations sheet, capture:
- table_number
- table_type (main_soa, continuation, domain, subsidiary, track, reference)
- table_title
- table_purpose
- page_start / page_end
- continuation_of (if applicable)
- track_label (for track tables only)
- notes

### Track Label (track tables only)

If table_type is "track", set track_label to the short population identifier:
- "Responders", "Non-responders", "Extension", "Prediabetes", "Cohort A", etc.
- Extract from table title or Annotations sheet — use the most concise identifier
- Omit for non-track tables

---

### Schedule Properties (Header Rows)

Each header row becomes a schedule_property entry.

**Interpretation required:**

property_type — Look at the actual values:
- "Screening", "Treatment", "Follow-up" → epoch
- "V1", "V2", "Baseline", "EOS" → visit
- "Day -7", "Day 1", "Day 28" → study_day
- "Week 0", "Week 4" → week
- "0h", "2h", "4h post-dose" → timepoint
- "Cycle 1", "Cycle 2" → cycle
- "±3 days" → window
- If unclear → other

hierarchical_level — Count from top:
- Topmost header row = 1
- Next row down = 2, etc.
- Assign a level to EVERY header row that helps identify what a column represents, regardless of property_type. If removing the row would make two columns indistinguishable, it needs a level.
- Only set null for rows that are purely presentational qualifiers and don't participate in distinguishing columns from each other.

property_comment — REQUIRED: Explain what data appears and your reasoning.

If column 1 is empty but row has data: synthesize property_name, set synthesized: true

---

### Activities

Each activity row becomes an activity entry.

**Interpretation required:**

indentation_level — From Excel text indentation:
- No leading spaces = 0 (section header)
- 2 spaces = 1 (child)
- 4 spaces = 2 (grandchild)

activity_name — CLEAN (no leading spaces, no annotation markers)
activity_name_source.cell_text — RAW (preserve spaces and markers)

---

### Cell Values

All cell_value fields must be CLEAN of annotation markers.
Extract markers to annotation_markers field.

Example: "Xᵃ" → cell_value: "X", annotation_markers: "a"

---

### Annotations

For each footnote/legend:

annotation_type:
- Explanatory logic/conditions → footnote
- Symbol definitions (X = required) → legend  
- Term expansions (BP = blood pressure) → abbreviation

marker_locations — Scan entire table for where each marker appears:
- schedule_property (header row)
- activity_name (activity label)
- schedule_cell (data cell — include column_position)

Every annotation MUST have at least one entry in marker_locations. An annotation with empty marker_locations becomes an orphan — invisible to downstream processing. If a marker appears only on an activity name (not on any specific cell), it still needs an activity_name entry with the row_position.

---

### Annotation Verification

Before generating the JSON, present an annotation linkage summary:

**For each annotation:** marker, type, and what it links to (property/activity/cells).

**Flag any annotation where:**
- marker_locations is empty (will become orphan)
- marker appears only in a comments/instructions column with no activity link

**ASK ME:** "Here is the annotation linkage summary. N annotations linked, M unlinked. Please confirm or direct fixes."

**WAIT for confirmation before generating JSON.**

---

### Grid Values

Column 1 is row labels — EXCLUDE from schedule_grid and activity_schedule.
Data columns start at column 2.

For merged cells: create entry for EACH physical cell position.

---

## OUTPUT

Generate ONE JSON file per table.

Filename: {NCTID}_Table_{NN}_extraction.json

Before delivering, verify:
- schema_name: "soa-table-extraction"
- schema_version: "1.0"  
- extraction_status: "ready_for_resolution"
- All property_comment fields meaningful
- All cell_value fields clean (markers extracted)
- All annotations have complete marker_locations
- No annotation has empty marker_locations
- track_label set for track tables (omitted for others)

---

## ASK IF UNCLEAR

If any interpretation is ambiguous, ask before proceeding:
- Unclear property_type classification
- Ambiguous hierarchy levels
- Unusual annotation patterns
- Unclear track_label for track tables
- Whether a table is domain vs separate main_soa
