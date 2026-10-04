# SoA2USDM — Extraction Workflow Guide

**Version:** 2.9

How to use the extraction prompt and the processing pipeline. The prompt is a standalone file with its own version header — attach it to a new Claude conversation alongside your data files. Layer 1 (extraction) is one non-interactive single pass (below).

For architecture rationale, see [`documents/soa2usdm-schema-architecture.md`](../documents/soa2usdm-schema-architecture.md).
For table type definitions, see [`documents/soa_table_type_definitions.md`](../documents/soa_table_type_definitions.md).

---

## Preparation

- **Pre-extract SoA pages** using `00_download_extract.ipynb` — downloads protocol PDFs, extracts SoA pages, converts full protocol to markdown
- **Render the SoA pages** with `python3 tools/page_map.py --collection <name> --render` — writes `{NCTID}_soa_pages/pNN.png`, each stamped with its document page number; the review page draws the extraction on these
- **Run the extraction in Claude Cowork** — the mechanical mark-check needs file access and code execution in the same session that reads the table
- **Rendering note:** when a table spans ≥10 pages, `pdftoppm` zero-pads the rendered page names (`p-01.png`, not `p-1.png`); it also prints harmless `Bad annotation destination` warnings. Neither affects extraction.

---

## Extraction: PDF → JSON in one pass (Layer 1)

Use `PDF_TO_JSON_PROMPT.md`. There are no staged confirmations.

**Attach:** `PDF_TO_JSON_PROMPT.md` + SoA PDF (+ optionally protocol markdown) + `soa-table-extraction.schema.json` + `soa_table_type_definitions.md`

**Say:** "Please read and follow the attached prompt to extract the SoA tables from this protocol to JSON."

The model runs start to finish and returns one extraction JSON per table plus an **uncertainty report** (calls a stated rule decides under *Recorded, not open*; open judgement calls in a *Decisions needed* block, also carried as `review_items` in the JSON), with exception-based method provenance recorded in the JSON for any value derived by a non-default method (prompt §1e). Decide the open calls on the review page (`{NCTID}_review.html`) through the corrections sidecar instead of confirming at mid-run gates. The **mechanical mark-check** — bbox column-binning for text-layer grids, a rule-line/near-black-pixel detector for image-only grids — is the verification surface that replaces the old Excel checkpoint: it re-derives the mark matrix from the PDF and flags merged single-marks on grid-heavy tables, the one error class post-hoc review must still catch. For a wide table split into side-by-side column-block tiles (e.g. V10–V19 and a V20–V29 "(continued)" spread), run the mark-check across *all* tiles and take the per-row union — a recurring row usually appears in every tile, so checking only one tile silently drops the others' visits (see `PDF_TO_JSON_PROMPT.md` §5).

**Save as:** `{NCTID}_Table_{NN}_extraction.json` in the `extracted/` folder.

**Fixing an extraction after the run.** The raw extraction JSON is not edited, and the model is not asked to patch it. A fix is an entry in the table's corrections sidecar (`{NCTID}_Table_{NN}_corrections.json`, schema `soa-table-corrections`), with `reason`, `by` and `at`; the pipeline applies it and writes `*_extraction.verified.json`. The review page drafts the entry for an open decision.

| Problem | Fix (sidecar op) |
|---------|-----|
| Open judgement call (`review_items`) | `confirm` to keep the call, or the correction that takes the alternative; both name the `review_item` |
| Markers left in `cell_value` | `set` on the entry: clean `cell_value`, markers in `annotation_markers` |
| Marker location missing on an annotation | `add_item` on `marker_locations` |
| Wrong `hierarchical_level`, empty `property_comment` | `set` on the `schedule_properties` entry, checked against the printed header |
| Missing `track_label`, wrong `table_type` | `set` on `table_metadata` (no `match`) |
| Row or mark missing, or extracted twice | `add` / `remove` on `activities` and `activity_schedule` |
| Unsure of the table type | `soa_table_type_definitions.md`: same columns, other activity category → domain; finer timing for some activities → subsidiary; a branch only some participants take → track; a schedule every participant passes through → main_soa |

---

## Pipeline: Layers 2–3 (Python)

Once extraction JSON files are in `{NCTID}/SoA2USDM/extracted/`, run `01_batch.ipynb`. Set `COLLECTION` in the config cell and execute.

The batch notebook runs five steps in sequence:

| Step | Class | Layer | What it does |
|------|-------|-------|-------------|
| 1 | `ApplyCorrectionsStep` | 1.5 | Applies `*_corrections.json` sidecars → `*_extraction.verified.json`; raw never overwritten |
| 2 | `ResolveStep` | 2 | Adds IDs, validates hierarchy, derives relationships — per table |
| 3 | `ConsolidateStep` | 3 | Cross-table integration, activity matching, annotation dedup; reads `{NCTID}_consolidation_corrections.json` where one exists |
| 4 | `VisualizeStep` | — | Consolidated HTML: the unified SoA, with its notes marked where they apply, and the *Matches across tables* section |
| 5 | `ReviewPageStep` | — | `{NCTID}_review.html`: the extraction against its rendered source pages — rows, marks, notes, review items and cross-table folds drawn where they refer to; drafts sidecar entries, writes nothing |

After all protocols: `IndexGeneratorStep` builds the collection index and renders the reports (refreshing each page's navigation), `CollectionsIndexStep` the root index, `ActivityInventoryStep` the activity inventory.

The collection index follows the workflow. Per table, against the source pages: Source, 1. Extraction, 2. Resolution, Extraction review, Log. Per protocol, across tables: 3. Consolidation (view, JSON, 'matches: n open of N'), Redacted.

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

## Consolidation review (cross-table matches)

Consolidation merges rows of different tables with the same name, and rows with a name similarity at or above the auto threshold. Below the threshold nothing is merged; the row stays separate and carries the near match as a hint (`near_matches`).

The section *Matches across tables* in `{NCTID}_consolidated.html` lists the merges made on similarity and the near matches kept separate, for review. Decide each match with `keep`, `split` or `merge`; use `refines` where a table or a row details a row of another table without being merged. The view drafts the entries and writes nothing. Save them as `consolidated/{NCTID}_consolidation_corrections.json` (schema `soa-consolidation-corrections`), fill in `reason` and `by`, and re-run the pipeline: `ConsolidateStep` reads the sidecar before matching, refuses draft placeholders, and stops on an entry that no longer fits the tables.

The review page's *Across tables* tab shows the matched rows on their source pages. The decision is made in the consolidated view.

---

## Row audit (independent check)

After the pipeline, `soa2usdm-row-audit --collection <name>` compares every extracted activity row against the rows its SoA pages actually print and writes `row_audit.json` to the collection root. Needs poppler (`pdftoppm`, `pdftotext`, `pdfinfo`) and the `bands` extra: `pip install -e '.[bands]'`.

---

## File Structure Per Protocol

```
{NCTID}/SoA2USDM/
├── extracted/
│   ├── {NCTID}_Table_{NN}_extraction.json            # raw, immutable
│   ├── {NCTID}_Table_{NN}_corrections.json           # sidecar (where needed)
│   ├── {NCTID}_Table_{NN}_extraction.verified.json   # sidecar applied (where one exists)
│   ├── {NCTID}_Table_{NN}_extraction_viewer.html     # JSON viewer
│   ├── {NCTID}[_<name>]_uncertainty_report.md/.html  # one or more
│   └── {NCTID}_review.html
├── resolved/
│   ├── {NCTID}_Table_{NN}_resolved.json
│   └── {NCTID}_Table_{NN}_resolved_viewer.html
└── consolidated/
    ├── {NCTID}_consolidated.json
    ├── {NCTID}_consolidation_corrections.json        # match decisions sidecar (where needed)
    └── {NCTID}_consolidated.html
```

---

## Publishing & commits

Code and data are **two repos that commit separately** — `soa2usdm` (package, schemas, prompts, notebooks) and `soa2usdm-collections` (the derived outputs).

In the **data repo**, `.gitignore` publishes only the sliced SoA PDFs (`{NCTID}_soa.pdf`) and everything under `SoA2USDM/**`. The full protocol PDF (`{NCTID}.pdf`) and the markdown dump (`{NCTID}.md`) stay local — never published.

Per protocol, stage `{NCTID}/SoA2USDM/`, `protocols/index.html`, and `studies_protocols.xlsx`, and **regenerate the index** (`IndexGeneratorStep`) before committing so the published page matches the outputs.

Commit-message style: name the protocol and what changed, e.g. `NCT…: consolidation review, 4 matches decided`.
