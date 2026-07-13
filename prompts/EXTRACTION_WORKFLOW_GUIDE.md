# SoA2USDM — Extraction Workflow Guide

**Version:** 2.4

How to use the extraction prompts and the processing pipeline. Each prompt is a standalone file — attach it to a new Claude conversation alongside your data files. Layer 1 (extraction) can be run two ways: the **non-interactive single-pass path** (v3.0, below) or the **two-conversation PDF→Excel→JSON path** (Conversations 1–2).

For architecture rationale, see [`documents/soa2usdm-schema-architecture.md`](../documents/soa2usdm-schema-architecture.md).
For table type definitions, see [`documents/soa_table_type_definitions.md`](../documents/soa_table_type_definitions.md).

---

## Preparation

- **Split screen:** Claude on left, PDF/Excel on right
- **One table per conversation** for complex protocols (many columns, merged cells)
- **Pre-extract SoA pages** using `00_download_extract.ipynb` — downloads protocol PDFs, extracts SoA pages, converts full protocol to markdown
- **Rendering note:** when a table spans ≥10 pages, `pdftoppm` zero-pads the rendered page names (`p-01.png`, not `p-1.png`); it also prints harmless `Bad annotation destination` warnings. Neither affects extraction.

---

## Non-interactive path (v3.0): PDF → JSON in one pass

The default for most runs. Use `PDF_TO_JSON_PROMPT.md` (v3.0) in place of Conversations 1 and 2 — no Excel checkpoint, no staged confirmations.

**Attach:** `PDF_TO_JSON_PROMPT.md` + SoA PDF (+ optionally protocol markdown) + `soa-table-extraction.schema.json` + `soa_table_type_definitions.md`

**Say:** "Please read and follow the attached prompt to extract the SoA tables from this protocol to JSON."

The model runs start to finish and returns one extraction JSON per table plus an **uncertainty report** (table types and why, merged-mark spans, synthesised names/markers, low-confidence calls, orphan-risk annotations). Review that report against the per-table resolved HTML instead of confirming at mid-run gates. The **mechanical mark-check** — bbox column-binning for text-layer grids, a rule-line/near-black-pixel detector for image-only grids — is the verification surface that replaces the old Excel checkpoint: it re-derives the mark matrix from the PDF and flags merged single-marks on grid-heavy tables, the one error class post-hoc review must still catch.

**Prefer the two-conversation flow below when:** you want a human-editable Excel artifact, or a very large/complex table where reviewing an intermediate is worth the extra time.

**Save as:** `{NCTID}_Table_{NN}_extraction.json` in the `extracted/` folder.

---

## Conversation 1: PDF → Excel (Layer 1a)

**Attach:** `PDF_TO_EXCEL_PROMPT.md` + SoA PDF (+ optionally protocol markdown)

**Say:** "Please carefully read and follow the attached prompt to extract the SoA tables from this protocol."

**Interact at checkpoints:**
- **Stage 1:** Confirm table count, column count, table types, track labels
- **Stage 2:** Confirm row labels and hierarchy
- **Stage 3:** Download the Excel file

**After download — verify in Excel:**
- Column count matches PDF
- Header rows match PDF structure
- Merged cells correct (fix manually if needed)
- Activity hierarchy correct (indentation levels)
- Cell values spot-checked against PDF
- All footnotes captured in Annotations sheet
- Table type and track label correct

**Save as:** `{NCTID}_SoA_Table_{NN}_verified.xlsx`

**Time:** 25–45 min per table (15–25 Claude + 10–20 verification)

---

## Conversation 2: Excel → JSON (Layer 1b)

**Attach:** `EXCEL_TO_JSON_PROMPT.md` + verified Excel

**Say:** "Please carefully read and follow the attached prompt to convert this verified Excel to extraction JSON."

**After download — verify:**
- JSON parses, `schema_name` is `soa-table-extraction`, `schema_version` is `1.0`
- `extraction_status` is `ready_for_resolution`
- All `property_comment` fields meaningful
- `hierarchical_level` values sensible (1→2→3)
- All `cell_value` fields clean (markers in `annotation_markers`)
- All annotations have `marker_locations`
- `track_label` present for track tables

**Save as:** `{NCTID}_Table_{NN}_extraction.json` in the `extracted/` folder.

**Common issues:**

| Problem | Fix |
|---------|-----|
| Empty `property_comment` | Ask Claude to explain the classification |
| Markers in `cell_value` | Ask Claude to re-extract to `annotation_markers` |
| Missing `marker_locations` | Ask Claude to scan the table for that marker |
| Wrong level values | Verify against PDF header structure / Excel indentation |
| Missing `track_label` | Ask Claude to identify the population from the table title |
| Unsure domain vs main_soa | Same columns as another table → domain. Different → main_soa |

**Time:** 15–30 min per table

---

## Pipeline: Layers 2–3 (Python)

Once extraction JSON files are in `{NCTID}/SoA2USDM/extracted/`, run `01_batch.ipynb`. Set `COLLECTION` in the config cell and execute.

The batch notebook runs four steps in sequence:

| Step | Class | Layer | What it does |
|------|-------|-------|-------------|
| 1 | `ResolveStep` | 2 | Adds IDs, validates hierarchy, derives relationships — per table |
| 2 | `VisualizeResolvedStep` | — | Per-table HTML for debugging |
| 3 | `ConsolidateStep` | 3 | Cross-table integration, activity matching, annotation dedup |
| 4 | `VisualizeStep` | — | Consolidated HTML for review |

After all protocols: `IndexGeneratorStep` builds the collection index page.

**Errors are collected, not raised** — partial success matters when one table out of four has issues. Check the batch output for error summaries.

### Headless (no notebook)

The same steps run as a plain script — useful for re-running one protocol without opening the notebook. From the repo root:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import ResolveStep
from soa2usdm.visualize_resolved import VisualizeResolvedStep
from soa2usdm.consolidate import ConsolidateStep
from soa2usdm.visualize import VisualizeStep
from soa2usdm.index_generator import IndexGeneratorStep
from soa2usdm.errors import Errors
from soa2usdm.analytics import Analytics

COLLECTION = 'usdm_data'
pid = 'NCT00000000'

errors, analytics = Errors(), Analytics()
data = {'source': {'protocol_id': pid, 'collection': COLLECTION}}
for step_cls in (ApplyCorrectionsStep, ResolveStep, VisualizeResolvedStep,
                 ConsolidateStep, VisualizeStep):
    data[step_cls.step_name] = step_cls(errors, analytics).execute(data)

# Rebuild the collection index after any protocol change
IndexGeneratorStep(Errors(), Analytics()).execute({'source': {'collection': COLLECTION}})

print(errors.has_errors(), errors.summary())
```

`ApplyCorrectionsStep` runs first — it applies any `*_corrections.json` sidecar over the raw extraction before resolution (raw is never overwritten).

---

## File Structure Per Protocol

```
{NCTID}/SoA2USDM/
├── extracted/
│   └── {NCTID}_Table_{NN}_extraction.json
├── resolved/
│   ├── {NCTID}_Table_{NN}_resolved.json
│   └── {NCTID}_Table_{NN}_resolved.html
└── consolidated/
    ├── {NCTID}_consolidated.json
    └── {NCTID}_consolidated.html
```

---

## Publishing & commits

Code and data are **two repos that commit separately** — `soa2usdm` (package, schemas, prompts, notebooks) and `soa2usdm-collections` (the derived outputs).

In the **data repo**, `.gitignore` publishes only the sliced SoA PDFs (`{NCTID}_soa.pdf`) and everything under `SoA2USDM/**`. The full protocol PDF (`{NCTID}.pdf`) and the markdown dump (`{NCTID}.md`) stay local — never published.

Per protocol, stage `{NCTID}/SoA2USDM/`, `protocols/index.html`, and `studies_protocols.xlsx`, and **regenerate the index** (`IndexGeneratorStep`) before committing so the published page matches the outputs.

Commit-message style: name the protocol and what changed, e.g. `Re-run NCT… single-pass (supersede Excel-first)`.
