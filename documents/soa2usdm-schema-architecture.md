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
    USDM Instantiation (a documented manual step — see below)
```

---

## Layer 1: Extraction

**Schema:** `soa-table-extraction` v1.1

**Implementation:** A single non-interactive Claude pass (PDF→JSON, `PDF_TO_JSON_PROMPT.md`). The model transcribes the table, re-derives the mark matrix mechanically from the PDF (bbox column-binning on text-layer grids, rule-line detection on rasters), and ends with an uncertainty report whose open judgement calls are also carried as data (`review_items`) and decided on the review page. The two-conversation PDF→Excel→JSON path with a human-verified Excel checkpoint remains available when a human-editable intermediate is wanted.

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

**Schema:** `soa-table-corrections` v1.1

**Implementation:** Programmatic (ApplyCorrectionsStep)

Human review findings are recorded as a `*_corrections.json` sidecar and applied deterministically to produce `*_extraction.verified.json`. The raw extraction is never overwritten — the original model output is preserved and every change is auditable. Tables without a sidecar pass through untouched.

**Key Principle:** The human is an adjudicator, not an editor — judgment enters through an auditable sidecar, never by rewriting model output.

**Output:** `{NCTID}_Table_{NN}_extraction.verified.json` (only where corrections exist)

---

## Layer 2: Resolution

**Schema:** `soa-table-resolved` v1.2

**Implementation:** Programmatic (ResolveStep, no Claude API). Reads the verified extraction where a corrections sidecar exists, the raw extraction otherwise.

**Adds:**
- Stable identifiers (`prop-001`, `act-015`, `col-007`, `annot-002`)
- Derived parent-child relationships from indentation/hierarchy levels
- Explicit schedule columns with composite labels
- Bidirectional annotation cross-references
- Document references: the numbered section, appendix, attachment, table or figure an annotation text points at ('See Section 8.2.2'), stated as `document_references` (kind + number as printed). The pointer only; the target is not looked up in the protocol text
- Validation (structure, hierarchy, annotations); a table-wide note (marker on no element, only `schedule_property` locations) is table scope, not an orphan

**Key Principle:** Everything derivable is now derived; every element is addressable.

**Output:** `{NCTID}_Table_{NN}_resolved.json`

---

## Layer 3: Study Schedule Logic

**Schema:** `soa-tables-consolidated` v1.5

**Implementation:** Programmatic (ConsolidateStep, no Claude API)

**Structural consolidation (implemented):**
- Table type classification (main_soa, continuation, domain, subsidiary, track, reference) drives consolidation strategy — see `soa_table_type_definitions.md`
- Unified activities with cross-table matching (exact, fuzzy, cross-parent). Only the lowest-numbered `main_soa` table is the base; a further `main_soa` table is matched against it. A fuzzy match below the auto threshold is not merged on any table pair: the activity stays separate and carries the near match as a hint (`near_matches`)
- Human decisions on cross-table matches through a per-protocol sidecar, `consolidated/{NCTID}_consolidation_corrections.json` (schema `soa-consolidation-corrections` v1.0), read before matching — the Layer 3 analogue of Layer 1.5. Ops: `keep`, `split`, `merge`, and `refines` (a table or row details a row of another table without being merged). Entries name source rows (table number + activity id, activity name as a check); a stale entry stops consolidation. The consolidated view lists the matches to review and drafts the entries; it writes nothing
- Timeline segments (main, domain, track, subsidiary) with aligned columns
- Schedule matrix mapping (xact_id, xcol_id) → cell values
- Annotation deduplication with source occurrence tracking; table-wide notes carry `annotation_scope: "table"`
- Validation of cross-references and structural integrity

**Semantic interpretation (not yet implemented):**
- Timeline patterns (main, subsidiary, unscheduled)
- Footnote logic interpretation
- USDM mapping

**Key Principle:** This is no longer about tables—it's about what the protocol was expressing.

**Output:** `{NCTID}_consolidated.json`

---

## USDM Instantiation

Not a fourth layer: the USDM side the repo is named after. It turns one consolidated SoA into
a USDM v4 document. `soa2usdm.usdmgen` lifts the consolidated table into timelines,
instances, timings, activities and encounters and merges them into the study structure USDM
requires; `soa2usdm.usdm_manifest` supplies the objects the SoA does not state, each flagged
not stated. The only protocol reading is a short hand-written manifest
(`schemas/usdm-manifest.schema.json`), and its load-bearing part is the epoch axis — an
interpretation of the extraction, resolved and logged here, never marked in the Layer 1–3
schemas.

It is a documented manual step, not a pipeline step: a USDM document exists only for a
protocol someone chose to build. `tools/usdm_gate.py` checks each build against the pinned
usdm-rdf release and the NCI EVS codelists USDM borrows. The semantic items listed under
Layer 3 remain future work. Procedure, decisions and limits:
[`usdm-instantiation.md`](usdm-instantiation.md).

**Output:** `{NCTID}_usdm.json` and `{NCTID}_usdm_decisions.json`, with the manifest

---

## What Each Layer Excludes

| Layer | Explicitly Excluded |
|-------|---------------------|
| **Extraction** | Generated IDs, derived relationships, cross-table integration |
| **Resolution** | Multi-table integration, timeline structures |
| **Consolidation** | USDM-specific semantics (StudyEpoch, Encounter, Activity mappings) — these belong to USDM Instantiation |

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

Two mechanical checks bracket the extraction, one inside the pass and one after the pipeline; the review page puts both in front of the reviewer:

- **Mark-check (inside the extraction pass):** re-derives the mark matrix from PDF geometry — bbox column-binning where a text layer exists, rule-line detection on rasters — and diffs it cell-for-cell against the model's visual read. Disagreements go to the uncertainty report.
- **Row audit (after the pipeline):** `RowAuditStep` (`soa2usdm-row-audit`) compares every extracted activity row against the rows the SoA pages actually print, and writes `row_audit.json` per collection.
- **Review page (per protocol):** `ReviewPageStep` renders the source pages and draws the extraction on them — row bands, a cell-by-cell mark check, annotation markers where printed (activity, mark, header row, header cell), `review_items` as the reviewer's worklist with the corrections that decided them, consolidation's cross-table folds — so every schema-level fact can be checked against the printed page. The page writes nothing; a decision drafts a corrections-sidecar entry, keeping the sidecar the only write path.

Neither check trusts the model's read of the grid; both re-derive from the source PDF.

---

## File Structure

```
{NCTID}/SoA2USDM/
├── extracted/
│   ├── *_Table_{NN}_extraction.json          # Raw model output — immutable
│   ├── *_Table_{NN}_corrections.json         # Human corrections sidecar (where needed)
│   ├── *_Table_{NN}_extraction.verified.json # Sidecar applied (where one exists)
│   ├── *_Table_{NN}_extraction_viewer.html   # JSON viewer
│   ├── {NCTID}[_<name>]_uncertainty_report.* # One or more extraction reports (.md, .html)
│   └── {NCTID}_review.html                   # Review page
├── resolved/
│   ├── *_Table_{NN}_resolved.json   # One per table
│   └── *_Table_{NN}_resolved_viewer.html   # JSON viewer
├── consolidated/
│   ├── {NCTID}_consolidated.json    # Single file per protocol
│   └── {NCTID}_consolidated.html    # Consolidated visualization
└── usdm/                            # Only where a USDM document was built
    ├── {NCTID}_usdm_manifest.yaml   # Hand-written
    ├── {NCTID}_usdm.json            # USDM v4 document
    └── {NCTID}_usdm_decisions.json  # What was decided, derived or left out
```

The index generator discovers files by suffix pattern.

**Schema versions.** Each schema lists the versions it accepts in an `enum` on
`schema_version`. An additive change (a new optional field, enum value or op) is a
minor version: the new number is added to the list and files stamped with an older
one stay valid. A change that makes existing files invalid is a major version.
`resolve` and `consolidate` stamp the current version on every file they write;
`tools/gate.py` accepts the versions the extraction schema lists.

---

## Summary

| Layer | Question | Implementation | Scope |
|-------|----------|----------------|-------|
| **Extraction** | What does this table show? | Claude + mechanical verification | per-table |
| **Resolution** | What precisely is in it? | Programmatic | per-table |
| **Consolidation** | What was the protocol expressing? | Programmatic | per-protocol |

Between extraction and resolution, human adjudication enters through the corrections sidecar (Layer 1.5) without ever touching the raw extraction. After consolidation, USDM Instantiation turns a protocol's consolidated SoA into a USDM v4 document, as a documented manual step.

**Scope test for Layers 1–3: transcript, not interpretation.** A statement belongs in these layers when it can be checked against the printed SoA pages alone, with no judgement about what the author meant. A note's own words stated as data pass (`document_references`: 'Section 8.2.2' as kind + number as printed). What lies behind the words does not: looking the section up in the protocol body, recognising named documents or standards from a list, or deciding that two rows are the same activity. The last enters only as a human statement in a sidecar; the others belong to the semantic work after Layer 3, if anywhere.

The architecture acknowledges that SoA tables are lossy compressions of study logic, and provides a systematic path to recover that logic while maintaining full traceability.

---

**Version:** 4.6  
**Date:** 2026-10-04  
**Schemas:** soa-table-extraction v1.1, soa-table-corrections v1.1, soa-table-resolved v1.2, soa-tables-consolidated v1.5, soa-consolidation-corrections v1.0
