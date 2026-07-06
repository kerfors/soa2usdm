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
│  • Conversational workflow (Claude)     │
│  • Human verification checkpoint        │
│  • One file per table                   │
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

**Implementation:** Two Claude conversations per table — PDF→Excel (Conversation 1) with human verification, then Excel→JSON (Conversation 2). The Excel intermediate allows domain experts to verify structure before any JSON is generated.

**Contains:**
- Physical structure (rows, columns, positions)
- Cell values cleaned of annotation markers
- Basic domain interpretation (property_type, indentation_level, hierarchical_level)
- Table classification (main_soa, continuation, domain, subsidiary, track, reference)
- Annotation markers with location tracking

**Key Principle:** Extract what you see + interpret what's obvious.

**Output:** `{NCTID}_Table_{NN}_extraction.json`

---

## Layer 2: Resolution

**Schema:** `soa-table-resolved` v1.0

**Implementation:** Programmatic (ResolveStep, no Claude API)

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

## File Structure

```
{NCTID}/SoA2USDM/
├── extracted/
│   ├── *_verified.xlsx              # Verified Excel(s) from Conversation 1
│   └── *_Table_{NN}_extraction.json # One per table
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
| **Extraction** | What does this table show? | Conversational | per-table |
| **Resolution** | What precisely is in it? | Programmatic | per-table |
| **Consolidation** | What was the protocol expressing? | Programmatic | per-protocol |

The architecture acknowledges that SoA tables are lossy compressions of study logic, and provides a systematic path to recover that logic while maintaining full traceability.

---

**Version:** 3.0  
**Date:** 2026-07-06  
**Schemas:** soa-table-extraction v1.0, soa-table-resolved v1.0, soa-tables-consolidated v1.1
