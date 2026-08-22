# SoA2USDM

> LLM extraction with mechanical verification, and a programmatic pipeline for transforming Schedule of Activities (SoA) tables from clinical trial protocols into structured, fully traceable, USDM-ready data. Claude extracts; mechanical checks re-derive the grid from the PDF; a domain expert reviews the evidence and adjudicates through auditable corrections; Python handles resolution, consolidation, and visualization.

This repository is the **product**: the Python package, JSON schemas, prompts, notebooks, and design documents. Protocol collections — the derived extraction outputs and their visualizations — live in a **separate data repository**, [`soa2usdm-collections`](https://github.com/kerfors/soa2usdm-collections), so that code and data version independently and a public code repo stays free of protocol PDFs.

The approach originated in the PHUSE EU Connect 2025 paper [*From Schedules of Activities (SoA) to USDM: Automating Protocol Extraction Using Large Language Models*](https://phuse.s3.eu-central-1.amazonaws.com/Archive/2025/Connect/EU/Hamburg/PAP_ML08.pdf) (Forsberg & Ulander). The workflow has evolved substantially since — see [A Two-Year Journey](#a-two-year-journey) below.

## Architecture

Three processing layers:

| Step | Question | How | Scope |
|------|----------|-----|-------|
| **1. Extraction** | What does this table show? | Claude + mechanical verification + human review | per table |
| **2. Resolution** | What precisely is in it? | Programmatic (Python) | per table |
| **3. Consolidation** | What was the protocol expressing? | Programmatic (Python) | per protocol |

Layer 1 runs as a single non-interactive Claude pass (PDF→JSON): the model extracts, re-derives the mark matrix mechanically from the PDF (bbox column-binning on text-layer grids, rule-line detection on scanned ones), and ends with an uncertainty report that surfaces every judgement call for human review. Human fixes flow through an auditable corrections sidecar — the raw extraction is never overwritten. A two-conversation PDF→Excel→JSON path with an Excel checkpoint remains available when a human-editable intermediate is wanted. Layers 2–3 are pure Python, producing consolidated structured data and HTML visualizations; an independent row audit compares extracted rows against what the source pages actually print.

The core processing logic lives in the `soa2usdm/` package; a batch notebook (`01_batch.ipynb`) provides the execution wrapper across protocol collections.

See [`documents/soa2usdm-schema-architecture.md`](documents/soa2usdm-schema-architecture.md) for the full design rationale and [`documents/background-and-challenges.md`](documents/background-and-challenges.md) for project history and the key extraction challenges that shaped this architecture.

## Repositories

| Repo | Contents |
|------|----------|
| **soa2usdm** (this repo) | Package, schemas, prompts, notebooks, documents, regression fixtures |
| [**soa2usdm-collections**](https://github.com/kerfors/soa2usdm-collections) | Protocol collections: derived extraction/resolution/consolidation outputs and HTML visualizations (GitHub Pages). No protocol PDFs. |

The two repos are designed to sit side by side:

```
parent/
├── soa2usdm/                 # this repo
└── soa2usdm-collections/     # data repo
```

The package discovers collections at `../soa2usdm-collections/collections/` by default. Override with the `SOA2USDM_COLLECTIONS` environment variable to point anywhere.

Cloning **soa2usdm** alone is fully functional: the regression suite runs against fixtures shipped in `tests/fixtures/`, so tests pass with no collections checkout present. To build your own collection, clone `soa2usdm-collections` (or start an empty one with the same layout) and work through protocols with the notebooks.

## Structure

```
soa2usdm/
├── schemas/
│   ├── soa-table-extraction.schema.json     # Layer 1
│   ├── soa-table-corrections.schema.json    # Layer 1 corrections sidecar
│   ├── soa-table-resolved.schema.json       # Layer 2
│   └── soa-tables-consolidated.schema.json  # Layer 3
│
├── prompts/
│   ├── EXTRACTION_WORKFLOW_GUIDE.md          # How to run all conversations
│   ├── PDF_TO_EXCEL_PROMPT.md                # Conversation 1
│   ├── EXCEL_TO_JSON_PROMPT.md               # Conversation 2
│   └── PDF_TO_JSON_PROMPT.md                 # Non-interactive single-pass path
│
├── documents/
│   ├── soa2usdm-schema-architecture.md       # Three-layer design rationale
│   ├── background-and-challenges.md          # Project history and key challenges
│   └── soa_table_type_definitions.md         # Table classification
│
├── soa2usdm/                         # Core Python package
│   ├── config.py                    # Paths, collection discovery
│   ├── base.py                      # PipelineStepBase
│   ├── errors.py                    # Error collection
│   ├── analytics.py                 # Metrics and timing
│   ├── corrections.py               # ApplyCorrectionsStep (raw + corrections)
│   ├── resolve.py                   # ResolveStep (Layer 2)
│   ├── consolidate.py               # ConsolidateStep (Layer 3)
│   ├── visualize.py                 # Consolidated HTML
│   ├── visualize_resolved.py        # Per-table HTML (debugging)
│   ├── index_generator.py           # Collection index page
│   ├── page_grid.py                 # Rule-line cell geometry (vector + raster)
│   ├── row_audit.py                 # RowAuditStep — extracted rows vs the pages
│   └── review_page.py               # ReviewPageStep — the extraction on its source pages
│
├── notebooks/
│   ├── 00_download_extract.ipynb    # Download PDFs, extract SoA pages, scaffold folders
│   └── 01_batch.ipynb               # Batch processing across a collection
│
├── tests/
│   ├── test_pipeline_regression.py  # Golden-output regression over discovered protocols
│   ├── test_page_geometry.py        # Cell geometry + row audit, incl. negative controls
│   └── fixtures/protocols/          # In-repo golden data (JSON only) — tests run standalone
│
└── pyproject.toml
```

## Running It

**Layer 1 — Extraction (Claude):**
Attach the prompt file + your data to a new Claude conversation. See [`prompts/EXTRACTION_WORKFLOW_GUIDE.md`](prompts/EXTRACTION_WORKFLOW_GUIDE.md) for the full workflow.

**Layers 2–3 — Resolution, Consolidation & Visualization (Python):**
The `soa2usdm/` package implements all processing steps. Use `01_batch.ipynb` to run across a protocol collection — set `COLLECTION` in the config cell and execute.

**Checking extractions against the source pages (Python):**
`soa2usdm-row-audit --collection <name>` compares every extracted activity row against the rows its SoA pages actually print, and writes `row_audit.json` to the collection root. Needs poppler (`pdftoppm`, `pdftotext`, `pdfinfo`) and the `bands` extra: `pip install -e '.[bands]'`.

**Reviewing an extraction (HTML):**
`ReviewPageStep` (run by `01_batch.ipynb`, or `soa2usdm-review-page <NCTID> --collection <name>`) writes `{NCTID}_review.html` (plus the rendered pages in `{NCTID}_review_pages/`) next to the extraction report: the rendered source pages with the extracted rows, marks, notes, open decisions (`review_items`) and cross-table folds drawn where they refer to, linked both ways with the extracted table. It shows nothing that is not already in the pipeline's files and writes nothing — a decision only drafts an entry for the corrections sidecar. Same requirements as the row audit.

## Key Design Decisions

**Errors collected, not raised.** Steps continue on errors — partial success matters when one table out of four has issues.

**Verification before propagation.** No extraction reaches the pipeline unreviewed. The mechanism has changed four times — Excel checkpoint (2025), then mechanical mark-check plus uncertainty report, then an independent row audit on top, then a review page that draws the extraction on its source pages and turns the report's open decisions into data (`review_items`, decided through the corrections sidecar) — but the invariant has not: catch errors before they propagate into downstream JSON.

**Re-derive, don't eyeball.** The mark matrix is reconstructed mechanically from PDF geometry and diffed against the model's visual read — on dense grids this has caught merged-span errors that human Excel verification missed. Provenance fields record *how* each interpreted value was derived: a re-derivable method, not a confidence number.

**Claude as product, not API.** Layer 1 runs in Claude's product surface — first chat conversations, now Claude Cowork — not through an API integration. Cowork opened new possibilities: file access and code execution inside the extraction session are exactly what make mechanical self-verification possible, since the same session that reads the table re-derives the mark matrix from the PDF. While both the models and the workflow are changing this fast, an API solution would have frozen an earlier workflow shape into code and meant rebuilding harness plumbing the product provides — and improves — for free. An API path stays open once the workflow stabilizes.

**One file per table, then integrate.** Each table gets its own extraction/resolution file. Consolidation handles cross-table logic.

**Raw + corrections, never overwrite.** A verified extraction is the raw extraction plus a corrections sidecar applied deterministically — the original model output is preserved and every change is auditable.

**Traceability throughout.** Every element traces from consolidated output back through resolved and extracted to PDF page and row position.

## A Two-Year Journey

This work spans roughly two years (2024–2026) of rapid LLM advancement, and the workflow changed shape with it. It began with automated multi-pass extraction, whose output could not be verified. The [2025 PHUSE paper](https://phuse.s3.eu-central-1.amazonaws.com/Archive/2025/Connect/EU/Hamburg/PAP_ML08.pdf) drew the consequence: a two-conversation workflow with a human-verified Excel checkpoint between PDF and JSON. Better models then made a third shape possible — a single non-interactive pass whose verification is engineered in rather than performed live: a mechanical mark-check re-derived from the PDF, an uncertainty report in place of interactive gates, a programmatic row audit, and an auditable corrections sidecar. Claude Cowork made this third shape practical — file access and code execution inside the extraction session itself. The human moved from guiding the extraction to reviewing its evidence.

Each model generation brought material improvements in vision understanding, table structure recognition, and semantic reasoning. All pipeline steps use the latest available Claude model. See [`documents/background-and-challenges.md`](documents/background-and-challenges.md) for the fuller history.

## License

Code is licensed under the [MIT License](LICENSE). Documentation and schemas are shared under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

## Author

Kerstin Forsberg — information architect specializing in clinical data standards. Built iteratively with Claude (Anthropic).
