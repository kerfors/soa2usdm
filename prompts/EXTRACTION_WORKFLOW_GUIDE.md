# SoA2USDM — Extraction Workflow Guide

**Version:** 2.8

How to use the extraction prompts and the processing pipeline. Each prompt is a standalone file (each carries its own version header) — attach it to a new Claude conversation alongside your data files. Layer 1 (extraction) is one non-interactive single pass (below).

For architecture rationale, see [`documents/soa2usdm-schema-architecture.md`](../documents/soa2usdm-schema-architecture.md).
For table type definitions, see [`documents/soa_table_type_definitions.md`](../documents/soa_table_type_definitions.md).

---

## Preparation

- **Split screen:** Claude on left, PDF on right
- **One table per conversation** for complex protocols (many columns, merged cells)
- **Pre-extract SoA pages** using `00_download_extract.ipynb` — downloads protocol PDFs, extracts SoA pages, converts full protocol to markdown
- **Rendering note:** when a table spans ≥10 pages, `pdftoppm` zero-pads the rendered page names (`p-01.png`, not `p-1.png`); it also prints harmless `Bad annotation destination` warnings. Neither affects extraction.

---

## Extraction: PDF → JSON in one pass (Layer 1)

Use `PDF_TO_JSON_PROMPT.md`. There are no staged confirmations.

**Attach:** `PDF_TO_JSON_PROMPT.md` + SoA PDF (+ optionally protocol markdown) + `soa-table-extraction.schema.json` + `soa_table_type_definitions.md`

**Say:** "Please read and follow the attached prompt to extract the SoA tables from this protocol to JSON."

The model runs start to finish and returns one extraction JSON per table plus an **uncertainty report** (calls a stated rule decides under *Recorded, not open*; open judgement calls in a *Decisions needed* block, also carried as `review_items` in the JSON), with exception-based method provenance recorded in the JSON for any value derived by a non-default method (prompt §1e). Decide the open calls on the review page (`{NCTID}_review.html`) through the corrections sidecar instead of confirming at mid-run gates. The **mechanical mark-check** — bbox column-binning for text-layer grids, a rule-line/near-black-pixel detector for image-only grids — is the verification surface that replaces the old Excel checkpoint: it re-derives the mark matrix from the PDF and flags merged single-marks on grid-heavy tables, the one error class post-hoc review must still catch. For a wide table split into side-by-side column-block tiles (e.g. V10–V19 and a V20–V29 "(continued)" spread), run the mark-check across *all* tiles and take the per-row union — a recurring row usually appears in every tile, so checking only one tile silently drops the others' visits (see `PDF_TO_JSON_PROMPT.md` §5).

**Save as:** `{NCTID}_Table_{NN}_extraction.json` in the `extracted/` folder.

**Common issues:**

| Problem | Fix |
|---------|-----|
| Empty `property_comment` | Ask Claude to explain the classification |
| Markers in `cell_value` | Ask Claude to re-extract to `annotation_markers` |
| Missing `marker_locations` | Ask Claude to scan the table for that marker |
| Wrong level values | Verify against PDF header structure |
| Missing `track_label` | Ask Claude to identify the population from the table title |
| Unsure of the table type | `soa_table_type_definitions.md`: same columns, other activity category → domain; finer timing for some activities → subsidiary; a branch only some participants take → track; a schedule every participant passes through → main_soa |

---

## Pipeline: Layers 2–3 (Python)

Once extraction JSON files are in `{NCTID}/SoA2USDM/extracted/`, run `01_batch.ipynb`. Set `COLLECTION` in the config cell and execute.

The batch notebook runs six steps in sequence:

| Step | Class | Layer | What it does |
|------|-------|-------|-------------|
| 1 | `ApplyCorrectionsStep` | 1.5 | Applies `*_corrections.json` sidecars → `*_extraction.verified.json`; raw never overwritten |
| 2 | `ResolveStep` | 2 | Adds IDs, validates hierarchy, derives relationships — per table |
| 3 | `ConsolidateStep` | 3 | Cross-table integration, activity matching, annotation dedup |
| 4 | `VisualizeStep` | — | Consolidated HTML: the unified SoA, with its notes marked where they apply |
| 5 | `ReviewPageStep` | — | `{NCTID}_review.html`: the extraction against its rendered source pages — rows, marks, notes, review items and cross-table folds drawn where they refer to; drafts sidecar entries, writes nothing |

After all protocols: `IndexGeneratorStep` builds the collection index and renders the reports (refreshing each page's navigation), `CollectionsIndexStep` the root index, `ActivityInventoryStep` the activity inventory.

**Errors are collected, not raised** — partial success matters when one table out of four has issues. Check the batch output for error summaries.

### Headless (no notebook)

The same steps run as a plain script — useful for re-running one protocol without opening the notebook. From the repo root:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import ResolveStep
from soa2usdm.consolidate import ConsolidateStep
from soa2usdm.visualize import VisualizeStep
from soa2usdm.review_page import ReviewPageStep
from soa2usdm.index_generator import IndexGeneratorStep
from soa2usdm.collections_index import CollectionsIndexStep
from soa2usdm.activity_inventory import ActivityInventoryStep
from soa2usdm.errors import Errors
from soa2usdm.analytics import Analytics

COLLECTION = 'usdm_data'
pid = 'NCT00000000'

errors, analytics = Errors(), Analytics()
data = {'source': {'protocol_id': pid, 'collection': COLLECTION}}
for step_cls in (ApplyCorrectionsStep, ResolveStep,
                 ConsolidateStep, VisualizeStep, ReviewPageStep):
    data[step_cls.step_name] = step_cls(errors, analytics).execute(data)

# Rebuild the collection index, root index and activity inventory after any protocol change
IndexGeneratorStep(Errors(), Analytics()).execute({'source': {'collection': COLLECTION}})
CollectionsIndexStep(Errors(), Analytics()).execute({})
ActivityInventoryStep(Errors(), Analytics()).execute({'source': {'collection': COLLECTION}})

print(errors.has_errors(), errors.summary())
```

`ApplyCorrectionsStep` runs first — it applies any `*_corrections.json` sidecar over the raw extraction before resolution (raw is never overwritten).

---

## Row audit (independent check)

After the pipeline, `soa2usdm-row-audit --collection <name>` compares every extracted activity row against the rows its SoA pages actually print and writes `row_audit.json` to the collection root. Needs poppler (`pdftoppm`, `pdftotext`, `pdfinfo`) and the `bands` extra: `pip install -e '.[bands]'`.

---

## File Structure Per Protocol

```
{NCTID}/SoA2USDM/
├── extracted/
│   ├── {NCTID}_Table_{NN}_extraction.json            # raw, immutable
│   ├── {NCTID}_Table_{NN}_corrections.json           # sidecar (where needed) → .verified.json
│   ├── {NCTID}[_<name>]_uncertainty_report.md/.html  # one or more
│   └── {NCTID}_review.html
├── resolved/
│   ├── {NCTID}_Table_{NN}_resolved.json
│   └── {NCTID}_Table_{NN}_resolved_viewer.html
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
