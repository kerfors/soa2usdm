# SoA2USDM Schema Architecture

## From Table Presentation to Study Logic

### The Core Insight

The Schedule of Activities (SoA) table in a protocol document is not the study schedule—it's a **2D presentation** of multi-dimensional study logic, constrained by paper. Footnotes are the overflow mechanism for logic that doesn't fit the grid.

This architecture separates the journey from presentation to logic into three processing layers.

---

## The Pipeline

```
PDF Protocol Document
        │
        ▼
┌─────────────────────────────────────────┐
│      Layer 1: EXTRACTION                │
│      soa-table-extraction               │
│      "What does this table show?"       │
│                                         │
│  • Single-pass Claude run (PDF→JSON)    │
│  • Mechanical mark-check (from PDF)     │
│  • Uncertainty report → human review    │
│  • One file per table                   │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│      Layer 1.5: CORRECTIONS             │
│      soa-table-corrections              │
│      "What did the human adjudicate?"   │
│                                         │
│  • Sidecar applied deterministically    │
│  • Raw extraction never overwritten     │
│  • Only for tables with a sidecar       │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│      Layer 2: RESOLUTION                │
│      soa-table-resolved                 │
│      "What precisely is in this table?" │
│                                         │
│  • Programmatic (ResolveStep)           │
│  • IDs, relationships, validation       │
│  • One file per table                   │
└─────────────────────────────────────────┘
        │
        ├── Table 1 ──┐
        ├── Table 2 ──┼── Integration
        └── Table 3 ──┘
                │
                ▼
┌─────────────────────────────────────────┐
│      Layer 3: STUDY SCHEDULE LOGIC      │
│      soa-tables-consolidated            │
│      "What was the protocol expressing?"│
│                                         │
│  STRUCTURAL (implemented):              │
│  • Cross-table activity matching        │
│  • Timeline segment alignment           │
│  • Annotation consolidation             │
│                                         │
│  SEMANTIC (not yet implemented):        │
│  • Timeline pattern interpretation      │
│  • Footnote logic made explicit         │
│  • USDM mapping                         │
└─────────────────────────────────────────┘
        │
        ▼
    USDM Mapping (future)
```

---

## Layer 1: Extraction

**Schema:** `soa-table-extraction` v1.0

**Implementation:** A single non-interactive Claude pass (PDF→JSON, `PDF_TO_JSON_PROMPT.md`). The model transcribes the table, re-derives the mark matrix mechanically from the PDF (bbox column-binning on text-layer grids, rule-line detection on rasters), and ends with an uncertainty report that surfaces every judgement call for human review against the resolved HTML. The two-conversation PDF→Excel→JSON path with a human-verified Excel checkpoint remains available when a human-editable intermediate is wanted.

**Contains:**
- Physical structure (rows, columns, positions)
- Cell values cleaned of annotation markers
- Basic domain interpretation (property_type, indentation_level, hierarchical_level)
- Table classification (main_soa, continuation, domain, subsidiary, track, reference)
- Annotation markers with location tracking
- Method provenance, exception-based (*how* a value was derived when not by the default method — a re-derivable procedure, not a confidence number)

**Key Principle:** Extract what you see + interpret what's obvious.

**Output:** `{NCTID}_Table_{NN}_extraction.json`

---

## Layer 1.5: Corrections

**Schema:** `soa-table-corrections` v1.0

**Implementation:** Programmatic (ApplyCorrectionsStep)

Human review findings are recorded as a `*_corrections.json` sidecar and applied deterministically to produce `*_extraction.verified.json`. The raw extraction is never overwritten — the original model output is preserved and every change is auditable. Tables without a sidecar pass through untouched.

**Key Principle:** The human is an adjudicator, not an editor — judgment enters through an auditable sidecar, never by rewriting model output.

**Output:** `{NCTID}_Table_{NN}_extraction.verified.json` (only where corrections exist)

---

## Layer 2: Resolution

**Schema:** `soa-table-resolved` v1.0

**Implementation:** Programmatic (ResolveStep, no Claude API). Reads the verified extraction where a corrections sidecar exists, the raw extraction otherwise.

**Adds:**
- Stable identifiers (`prop-001`, `act-015`, `col-007`, `annot-002`)
- Derived parent-child relationships from indentation/hierarchy levels
- Explicit schedule columns with composite labels
- Bidirectional annotation cross-references
- Validation (structure, hierarchy, annotations)

**Key Principle:** Everything derivable is now derived; every element is addressable.

**Output:** `{NCTID}_Table_{NN}_resolved.json`

---

## Layer 3: Study Schedule Logic

**Schema:** `soa-tables-consolidated` v1.1

**Implementation:** Programmatic (ConsolidateStep, no Claude API)

**Structural consolidation (implemented):**
- Table type classification (main_soa, continuation, domain, subsidiary, track, reference) drives consolidation strategy — see `soa_table_type_definitions.md`
- Unified activities with cross-table matching (exact, fuzzy, cross-parent)
- Timeline segments (main, domain, track, subsidiary) with aligned columns
- Schedule matrix mapping (xact_id, xcol_id) → cell values
- Annotation deduplication with source occurrence tracking
- Validation of cross-references and structural integrity

**Semantic interpretation (not yet implemented):**
- Timeline patterns (main, subsidiary, unscheduled)
- Footnote logic interpretation
- USDM mapping

**Key Principle:** This is no longer about tables—it's about what the protocol was expressing.

**Output:** `{NCTID}_consolidated.json`

---

## What Each Layer Excludes

| Layer | Explicitly Excluded |
|-------|---------------------|
| **Extraction** | Generated IDs, derived relationships, cross-table integration |
| **Resolution** | Multi-table integration, timeline structures |
| **Consolidation** | USDM-specific semantics (StudyEpoch, Encounter, Activity mappings) |

---

## Traceability

Every element traces back to source:

```
consolidated.unified_activities[].source_refs[]
  → table_num, activity_id
    → resolved.activities[]
      → extraction.activities[]
        → PDF page, row position
```

Cross-table IDs (`xact-NNN`, `xcol-NNN`, `xannot-NNN`) link to per-table IDs (`act-NNN`, `col-NNN`, `annot-NNN`).

---

## Independent Verification

Two mechanical checks bracket the extraction, one inside the pass and one after the pipeline:

- **Mark-check (inside the extraction pass):** re-derives the mark matrix from PDF geometry — bbox column-binning where a text layer exists, rule-line detection on rasters — and diffs it cell-for-cell against the model's visual read. Disagreements go to the uncertainty report.
- **Row audit (after the pipeline):** `RowAuditStep` (`soa2usdm-row-audit`) compares every extracted activity row against the rows the SoA pages actually print, and writes `row_audit.json` per collection.
- **Review page (per protocol):** `ReviewPageStep` renders the source pages and draws the extraction on them — row bands, a cell-by-cell mark check, annotation bindings, `review_items` as the reviewer's worklist, consolidation's cross-table folds — so every schema-level fact can be checked against the printed page. The page writes nothing; a decision drafts a corrections-sidecar entry, keeping the sidecar the only write path.

Neither check trusts the model's read of the grid; both re-derive from the source PDF.

---

## File Structure

```
{NCTID}/SoA2USDM/
├── extracted/
│   ├── *_Table_{NN}_extraction.json          # Raw model output — immutable
│   ├── *_Table_{NN}_corrections.json         # Human corrections sidecar (where needed)
│   ├── *_Table_{NN}_extraction.verified.json # Sidecar applied (where one exists)
│   └── *_verified.xlsx                       # Excel(s) — two-conversation path only
├── resolved/
│   ├── *_Table_{NN}_resolved.json   # One per table
│   └── *_Table_{NN}_resolved.html   # Per-table visualization
└── consolidated/
    ├── {NCTID}_consolidated.json    # Single file per protocol
    └── {NCTID}_consolidated.html    # Consolidated visualization
```

The index generator discovers files by suffix pattern, so naming variations
in the Excel files (e.g., table ranges, extra labels) are handled gracefully.

---

## Summary

| Layer | Question | Implementation | Scope |
|-------|----------|----------------|-------|
| **Extraction** | What does this table show? | Claude + mechanical verification | per-table |
| **Resolution** | What precisely is in it? | Programmatic | per-table |
| **Consolidation** | What was the protocol expressing? | Programmatic | per-protocol |

Between extraction and resolution, human adjudication enters through the corrections sidecar (Layer 1.5) without ever touching the raw extraction.

The architecture acknowledges that SoA tables are lossy compressions of study logic, and provides a systematic path to recover that logic while maintaining full traceability.

---

**Version:** 4.0  
**Date:** 2026-08-15  
**Schemas:** soa-table-extraction v1.0, soa-table-corrections v1.0, soa-table-resolved v1.0, soa-tables-consolidated v1.1
