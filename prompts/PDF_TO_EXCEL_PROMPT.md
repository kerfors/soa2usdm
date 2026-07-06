# SoA Table Extraction: PDF to Excel

> Prompt version 2.8.0 | Schema: soa-table-extraction v1.0

Extract the SoA table(s) from the attached protocol to Excel.

Read the XLSX skill first: /mnt/skills/public/xlsx/SKILL.md

---

## CRITICAL EXTRACTION PRINCIPLE

**Transcribe each cell's content literally as it appears in the PDF.**

- If a cell contains X, ✓, •, text, numbers — transcribe exactly what you see
- If a cell is empty — leave it empty
- Do NOT apply clinical or domain logic to decide what "should" be in a cell
- Do NOT infer patterns from neighboring cells or rows
- Visual formatting (grey shading, colors, borders) is metadata to note in the Annotations sheet, not a signal to modify cell contents

---

## DUAL-SOURCE EXTRACTION

When both SoA PDF and protocol markdown are attached, use each for what it does best:

**PDF — use for:**
- Visual table layout (column boundaries, merged cells)
- Hierarchy detection (bold text, shading, indentation)
- Cell content markers (X, ✓, •, arrows)
- Table boundaries and page structure

**Markdown — use for:**
- Activity name spelling (avoids PDF rendering artifacts like run-together words)
- Footnote text accuracy
- Header label text
- Cross-referencing ambiguous PDF content

**When they disagree:** Flag in Annotations sheet. Prefer markdown for text, PDF for structure.

**Do NOT use pdfplumber.** The markdown already provides the text content that pdfplumber would extract, without its artifacts (split rows, missing spaces, broken headers).

---

## WORK IN STAGES - VERIFY BEFORE PROCEEDING

### STAGE 1: Structure Discovery

Examine the table(s) and report:

1. How many SoA tables in this document?
2. For each table:
   - Table title (as written)
   - Page numbers (start-end)
   - Purpose (Screening? Treatment? Follow-up? PK sampling?)
   - Is it a continuation of another table?
   - **Table type classification** (see below)
   - **Track label** (for track tables only)
3. Column count for each table
4. Header row structure (how many levels? what do they represent?)

**Table type classification:**

| Type | Column Structure | Row Content | Consolidation Action |
|------|------------------|-------------|---------------------|
| `main_soa` | Primary grid | Activities | Anchor table |
| `continuation` | SAME as parent | Activities continue | Append rows to parent |
| `domain` | SAME as main_soa | Different activity category | Merge activities into shared timeline |
| `subsidiary` | DIFFERENT (finer) | Activity subset, detailed timing | Link to parent activities |
| `track` | DIFFERENT | Different population/phase | Separate ScheduleTimeline |
| `reference` | N/A | Non-activities | Metadata/annotations only |

*subsidiary vs track:*
- `subsidiary` = **Finer timing** for a subset of procedures (e.g., hourly PK sampling)
- `track` = **Separate timeline** for a different population/phase (own visits, own duration)

*reference:* "Are the rows activities performed on subjects?" If NO → `reference`.

**For track tables:** Capture a short population/phase label (e.g., "Responders", "Extension", "Prediabetes") — this becomes the `track_label` in JSON.

**For continuation tables:** Specify `continuation_of` with the table number being continued.

**ASK ME:** "I found X table(s). Here's what I see: [summary with table_type for each, plus track_label for any track tables]. 
How many columns do you count? Please confirm before I proceed."

**WAIT for my confirmation.**

---

### STAGE 2: Row Label Extraction

Extract ALL row labels in order:

1. Header rows (phases, visits, days, timepoints, etc.)
2. Activity/procedure rows with hierarchy detected from:
   - Bold text or background colors (section headers)
   - Visual indentation (parent-child relationships)

Show hierarchy with TEXT INDENTATION in Excel:
- Section headers: NO leading spaces (level 0)
- Child activities: 2 spaces per level
- Grandchildren: 4 spaces, etc.

Preserve ALL annotation markers (ᵃ, ᵇ, ᶜ or ^a, ^b, ^c)

**ASK ME:** "Here are the row labels I found: [list with hierarchy]. 
Please confirm the hierarchy is correct."

**WAIT for my confirmation.**

---

### STAGE 3: Excel Generation

Generate Excel from the PDF visual layout and markdown text content.

**Follow any special instructions the user provided at conversation start.**

Create Excel file with TWO sheets per table:

**SHEET: Table_01** (Table_02, etc.)
- Header rows exactly as shown (preserve merged cells)
- Activity rows with hierarchy via text indentation
- All cell content transcribed literally from source
- All annotation markers preserved
- Empty cells stay empty

**SHEET: Table_01_Annotations**
Capture for each table:
- Table number
- **Table type** (from Stage 1 classification)
- **Track label** (for track tables only)
- Table title (exact)
- Page start / Page end  
- Table purpose
- Continuation of (if applicable)
- ALL footnotes with their markers (exact text)
- ALL abbreviations/legends
- Visual formatting notes (e.g., "Columns X-Y have grey shading")
- Any extraction uncertainties

---

## WHAT TO EXPECT

**You WILL get right:**
- Column count
- Row labels in correct order
- Hierarchy preserved via indentation
- Cell content transcribed literally
- Annotation markers preserved
- Table type classification

**You MAY struggle with:**
- Complex merged cell ranges (I'll fix manually)
- Header merge boundaries

**I WILL:**
- Verify column count at Stage 1
- Verify hierarchy at Stage 2
- Confirm table type classifications
- Confirm track labels for track tables
- Fix header merges manually after download
- Correct any errors before JSON conversion
