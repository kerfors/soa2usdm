# SoA2USDM

> LLM extraction with mechanical verification, and a programmatic pipeline for transforming Schedule of Activities (SoA) tables from clinical trial protocols into structured, fully traceable, USDM-ready data. Claude extracts; mechanical checks re-derive the grid from the PDF; a domain expert reviews the evidence and adjudicates through auditable corrections; Python handles resolution, consolidation, and visualization.

**Start here:** [kerfors.github.io/soa2usdm](https://kerfors.github.io/soa2usdm/) — two short videos, the schemas on one page, and links into the published protocol collections.

This repository is the **product**: the Python package, JSON schemas, prompts, notebooks, and design documents. Protocol collections — the derived extraction outputs and their visualizations — live in a **separate data repository**, [`soa2usdm-collections`](https://github.com/kerfors/soa2usdm-collections), so that code and data version independently and a public code repo stays free of protocol PDFs.

The approach originated in the PHUSE EU Connect 2025 paper [*From Schedules of Activities (SoA) to USDM: Automating Protocol Extraction Using Large Language Models*](https://phuse.s3.eu-central-1.amazonaws.com/Archive/2025/Connect/EU/Hamburg/PAP_ML08.pdf) (Forsberg & Ulander). The workflow has evolved substantially since — see [A Two-Year Journey](#a-two-year-journey) below.

## Architecture

Three processing layers:

| Step | Question | How | Scope |
|------|----------|-----|-------|
| **1. Extraction** | What does this table show? | Claude + mechanical verification + human review | per table |
| **2. Resolution** | What precisely is in it? | Programmatic (Python) | per table |
| **3. Consolidation** | What was the protocol expressing? | Programmatic (Python) | per protocol |

Layer 1 runs as a single non-interactive Claude pass (PDF→JSON): the model extracts, re-derives the mark matrix mechanically from the PDF (bbox column-binning on text-layer grids, rule-line detection on scanned ones), and ends with an uncertainty report that surfaces every judgement call for human review. Human fixes flow through an auditable corrections sidecar — the raw extraction is never overwritten. Layers 2–3 are pure Python, producing consolidated structured data and HTML visualizations; an independent row audit compares extracted rows against what the source pages actually print. The cross-table matches made by consolidation are reviewed in the consolidated view and decided through a per-protocol consolidation sidecar, which consolidation reads before matching.

**USDM Instantiation** — the USDM side the repo is named after, not a fourth layer — turns one protocol's consolidated SoA and a short hand-written manifest into a USDM v4 document, checked by a gate against the pinned [usdm-rdf](https://github.com/kerfors/usdm-rdf) release and the NCI EVS codelists USDM borrows. It is a documented manual step, not a pipeline step: see [`documents/usdm-instantiation.md`](documents/usdm-instantiation.md).

**Towards CDISC (early work)** — two per-study sidecar steps after consolidation, a first cut towards linking SoA activities to CDISC terms. The *activity grain* tags each activity with how many tests it names (named test, panel, procedure, instrument, sample collection, other) and, for a named test, the kind of finding; *activity routing* gives each named test a target SDTMIG v3.4 domain, or the candidate domains and the question that stays open. Both use public [cdisc-for-ai](https://github.com/kerfors/cdisc-for-ai) material only and cite what each result rests on. The steps after them (test, target and the facets the protocol states) are not in this repository yet. See [`documents/activity-grain.md`](documents/activity-grain.md) and [`documents/activity-routing.md`](documents/activity-routing.md).

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
│   ├── soa-tables-consolidated.schema.json  # Layer 3
│   ├── soa-consolidation-corrections.schema.json  # Layer 3 corrections sidecar (match decisions)
│   ├── usdm-manifest.schema.json            # USDM Instantiation manifest
│   ├── soa2usdm-activity-inventory.schema.json  # Activity inventory (activities.json)
│   ├── soa2usdm-protocol-context-cgt.schema.json  # Protocol context beyond the SoA (CGT profile)
│   ├── soa2usdm-activity-grain.schema.json  # Activity grain per study
│   ├── soa2usdm-activity-grain-inputs.schema.json  # Inputs of the grain decisions prompt, per study
│   ├── soa2usdm-activity-grain-decisions.schema.json  # Activity grain decisions sidecar
│   ├── soa2usdm-activity-routing.schema.json  # Activity routing per study
│   └── soa2usdm-panel-context-members.schema.json  # Panel members from protocol context per study
│
├── prompts/
│   ├── EXTRACTION_WORKFLOW_GUIDE.md          # How to run extraction and the pipeline
│   ├── PDF_TO_JSON_PROMPT.md                 # Layer 1 extraction, single pass
│   ├── PROTOCOL_CONTEXT_CGT_PROMPT.md        # Protocol context beyond the SoA (cell and gene therapy)
│   └── ACTIVITY_GRAIN_DECISIONS_PROMPT.md    # Grain and kind for what the grain rules leave to decide
│
├── documents/
│   ├── soa2usdm-schema-architecture.md       # Three-layer design rationale
│   ├── usdm-instantiation.md                 # USDM Instantiation: procedure, design, decisions
│   ├── activity-grain.md                     # Activity grain: values, rules, decisions, status
│   ├── activity-routing.md                   # Activity routing: rows, status, rules, members-only material, status
│   ├── background-and-challenges.md          # Project history and key challenges
│   ├── soa_table_type_definitions.md         # Table classification (taxonomy)
│   ├── inventory-improvements.md             # Backlog: open and done items
│   ├── re-extraction-acceptance-checklist.md # Re-extraction criteria and promotion gate
│   ├── re-extraction-baseline*.json          # Machine baseline and mined claims (tools/)
│   └── *.md                                  # Design notes (annotation model, identifiers, timeline anchors, anchor survey)
│
├── docs/                             # Published on GitHub Pages: kerfors.github.io/soa2usdm
│   ├── index.html                   # Landing page: two videos, the infographic, links to collections and repos
│   ├── schema-chain.html            # Infographic of the schemas (generated by tools/build_explainer.py)
│   ├── consolidation.html           # Consolidation of tables (generated by tools/build_consolidation_explainer.py)
│   └── img/                         # Screenshots used by consolidation.html
│
├── soa2usdm/                         # Core Python package
│   ├── config.py                    # Paths, collection discovery
│   ├── base.py                      # PipelineStepBase
│   ├── errors.py                    # Error collection
│   ├── analytics.py                 # Metrics and timing
│   ├── corrections.py               # ApplyCorrectionsStep (raw + corrections)
│   ├── resolve.py                   # ResolveStep (Layer 2)
│   ├── references.py                # document_references: what an annotation text points at, as printed
│   ├── consolidate.py               # ConsolidateStep (Layer 3)
│   ├── consolidation_corrections.py # Consolidation sidecar: keep / split / merge / refines
│   ├── visualize.py                 # Consolidated HTML, with the 'Matches across tables' review section
│   ├── index_generator.py           # Collection index page; renders reports, refreshes nav
│   ├── collections_index.py         # Root index across collections
│   ├── activity_inventory.py        # Collection activity inventory (activities.json/.html)
│   ├── activity_grain.py            # Activity grain per study: rules, kind of finding, decisions
│   ├── activity_grain_inputs.py     # Inputs of the grain decisions prompt, per study (grain/*_grain_inputs.json)
│   ├── activity_grain_page.py       # Activity grain page per study (grain/*_activity_grain.html)
│   ├── activity_routing.py          # Activity routing per study: named test -> SDTMIG v3.4 domain, cited
│   ├── activity_routing_page.py     # Activity routing page per study (routing/*_activity_routing.html)
│   ├── panel_context_members.py     # Members of name-only panels from protocol context, per study
│   ├── protocol_context_page.py     # Protocol context page per study (context/*_protocol_context.html)
│   ├── nav.py                       # Shared navigation for all generated pages
│   ├── page_grid.py                 # Rule-line cell geometry (vector + raster)
│   ├── row_audit.py                 # RowAuditStep — extracted rows vs the pages
│   ├── review_page.py               # ReviewPageStep — the extraction on its source pages
│   ├── usdmgen.py                   # USDM Instantiation: consolidated SoA → USDM v4
│   ├── usdm_manifest.py             # USDM Instantiation: objects the SoA does not state
│   └── shellgen.py                  # Study shell generator, driven by the manifest
│
├── tools/                           # Re-extraction harness, the USDM gate, the infographic generator and the video scripts (tools/README.md)
│
├── ct/
│   └── usdm-borrowed-codelists.tsv  # NCI EVS codelists USDM borrows (built by tools/build_ct_extract.py)
│
├── notebooks/
│   ├── 00_download_extract.ipynb    # Download PDFs, extract SoA pages, scaffold folders
│   ├── 01_batch.ipynb               # Batch processing across a collection
│   └── 02_activity_grain.ipynb      # Activity grain across a collection: counts, samples, unsure, weak hits
│
├── tests/
│   ├── test_pipeline_regression.py  # Golden-output regression over discovered protocols
│   ├── test_page_geometry.py        # Cell geometry + row audit, incl. negative controls
│   ├── test_review_items.py         # review_items; decided via sidecar
│   ├── test_review_page.py          # Review page: model, tiled-table column map
│   ├── test_consolidation_corrections.py  # Consolidation sidecar: ops, stale entries, the matches view
│   ├── test_document_references.py  # document_references on annotations
│   ├── test_activity_grain.py       # Grain rules, kind of finding, decisions checks (negative controls), stale check
│   ├── test_activity_grain_inputs.py  # Grain inputs: items, stable rebuild, pointers, stale inputs stop the generator
│   ├── test_activity_routing.py     # Routing rules and status, public-only guard, published routing files
│   ├── test_panel_context_members.py  # Name rule, members from protocol context, published panel files
│   └── fixtures/                    # Golden protocols (JSON only), negative controls, pages — tests run standalone
│
└── pyproject.toml
```

## Running It

**Layer 1 — Extraction (Claude):**
Attach the prompt file + your data to a new Claude conversation. See [`prompts/EXTRACTION_WORKFLOW_GUIDE.md`](prompts/EXTRACTION_WORKFLOW_GUIDE.md) for the full workflow.

**Layers 2–3 — Resolution, Consolidation & Visualization (Python):**
The `soa2usdm/` package implements all processing steps. Use `01_batch.ipynb` to run across a protocol collection — set `COLLECTION` in the config cell and execute.

**Protocol context (Claude, then Python):**
Per protocol, beyond the SoA tables: `tools/protocol_context_inputs.py` prepares the inputs, a Claude session runs [`prompts/PROTOCOL_CONTEXT_CGT_PROMPT.md`](prompts/PROTOCOL_CONTEXT_CGT_PROMPT.md) (cell and gene therapy profile: product, immunogenicity, panels, assays, abbreviations and more, each value with its page and quote), and `tools/check_protocol_context.py` checks the result. Output: `SoA2USDM/context/{NCTID}_protocol_context.json`, shown on the collection index (column "Protocol context"). See [`tools/README.md`](tools/README.md).

**Activity grain (Python):**
`python -m soa2usdm.activity_grain --collection <name> [--protocol <NCTID>]` tags every activity of a study with its grain (named test, panel, procedure, instrument, sample collection, other, unsure) and, for a named test, the kind of finding. Each tag cites its rule and its public cdisc-for-ai lookup hits. A decisions file per study holds AI proposals and reviews for what the rules leave open; the AI proposals come from [`prompts/ACTIVITY_GRAIN_DECISIONS_PROMPT.md`](prompts/ACTIVITY_GRAIN_DECISIONS_PROMPT.md), run on inputs gathered by code (`python -m soa2usdm.activity_grain_inputs`). Output: `SoA2USDM/grain/`, with a page per study (shared navigation, linked from the collection index and the Activities page). Needs the `grain` extra and a cdisc-for-ai checkout next to this repo. See [`documents/activity-grain.md`](documents/activity-grain.md).

**Activity routing (Python):**
`python -m soa2usdm.activity_routing --collection <name> [--protocol <NCTID>]` gives each named test of the grain a target SDTMIG v3.4 domain (routed), or the candidate domains and the question that stays open (open, weak, not routed). Each result cites its rule, where it matched (label, parent label, footnote) and the public SDTMIG v3.4 statements it rests on; where no rule fires, the SDTM test code of the label (SDTM_Test_Identity) can route it. CDISC members-only material is not used. Output: `SoA2USDM/routing/`, with a page per study (shared navigation). Same requirements as the grain. Where a study has protocol context, `python -m soa2usdm.panel_context_members --collection <name>` runs first: it links the panels named only in the SoA to the protocol-context panels by name and records their members (`SoA2USDM/panels/`), which routing then routes as panel members. See [`documents/activity-routing.md`](documents/activity-routing.md).

**USDM Instantiation (manual step):**
Per protocol: write the manifest, run `python -m soa2usdm.usdmgen`, then `tools/usdm_gate.py` — the steps are in [`documents/usdm-instantiation.md`](documents/usdm-instantiation.md), *Running it*. Needs `pip install -e '.[shell,usdm-gate]'` and the usdm-rdf checkout next to this repo.

**Checking extractions against the source pages (Python):**
`soa2usdm-row-audit --collection <name>` compares every extracted activity row against the rows its SoA pages actually print, and writes `row_audit.json` to the collection root. Needs poppler (`pdftoppm`, `pdftotext`, `pdfinfo`) and the `bands` extra: `pip install -e '.[bands]'`.

**Reviewing an extraction (HTML):**
`ReviewPageStep` (run by `01_batch.ipynb`, or `soa2usdm-review-page <NCTID> --collection <name>`) writes `{NCTID}_review.html` in `extracted/`: the source pages (pre-rendered at ingest into `{NCTID}_soa_pages/` by `tools/page_map.py --render`, each stamped below the page bitmap with its document page number) with the extracted rows, marks, notes, decisions (`review_items`, open or decided with the corrections that decided them) and cross-table folds drawn where they refer to, linked both ways with the extracted table. It shows nothing that is not already in the pipeline's files and writes nothing — a decision only drafts an entry for the corrections sidecar. Same requirements as the row audit.

The review page is a proof of concept with two aims: to envision what a user interface for a review user could look like — worklist (`review_items`), evidence, and the sidecar write path in one place — and to showcase the traceability the pipeline already carries: every highlight is an existing extraction field drawn at the position on the source page it refers to. It also lays groundwork for the semantic/USDM layer: any claim about what an SoA table expresses should be checkable against a printed page in seconds, which is why the page images are pre-rendered and stamped at ingest.

**Reviewing cross-table matches (HTML):**
The consolidated view (`{NCTID}_consolidated.html`) has a section *Matches across tables*. It lists the rows consolidation merged on name similarity and the near matches it kept separate. A reviewer decides each one: `keep`, `split` or `merge`; `refines` states that a table or a row details a row of another table without being merged. The view drafts the entries for `consolidated/{NCTID}_consolidation_corrections.json` and writes nothing. Consolidation reads the sidecar before matching and stops on a stale entry. The collection index shows the state per protocol ('matches: n open of N'). The review page's *Across tables* tab shows the matched rows on their source pages; the decision is made in the consolidated view.

## Key Design Decisions

**Errors collected, not raised.** Steps continue on errors — partial success matters when one table out of four has issues.

**Verification before propagation.** No extraction reaches the pipeline unreviewed. The mechanism has changed four times — Excel checkpoint (2025), then mechanical mark-check plus uncertainty report, then an independent row audit on top, then a review page that draws the extraction on its source pages and turns the report's open decisions into data (`review_items`, decided through the corrections sidecar) — but the invariant has not: catch errors before they propagate into downstream JSON.

**Re-derive, don't eyeball.** The mark matrix is reconstructed mechanically from PDF geometry and diffed against the model's visual read — on dense grids this has caught merged-span errors that human Excel verification missed. Provenance fields record *how* each interpreted value was derived: a re-derivable method, not a confidence number.

**Claude as product, not API.** Layer 1 runs in Claude's product surface — first chat conversations, now Claude Cowork — not through an API integration. Cowork opened new possibilities: file access and code execution inside the extraction session are exactly what make mechanical self-verification possible, since the same session that reads the table re-derives the mark matrix from the PDF. While both the models and the workflow are changing this fast, an API solution would have frozen an earlier workflow shape into code and meant rebuilding harness plumbing the product provides — and improves — for free. An API path stays open once the workflow stabilizes.

**One file per table, then integrate.** Each table gets its own extraction/resolution file. Consolidation handles cross-table logic.

**Raw + corrections, never overwrite.** A verified extraction is the raw extraction plus a corrections sidecar applied deterministically — the original model output is preserved and every change is auditable. Layer 3 follows the same rule: decisions on cross-table matches are kept in a consolidation sidecar, not written into the consolidated output.

**Traceability throughout.** Every element traces from consolidated output back through resolved and extracted to PDF page and row position.

## A Two-Year Journey

This work spans roughly two years (2024–2026) of rapid LLM advancement, and the workflow changed shape with it. It began with automated multi-pass extraction, whose output could not be verified. The [2025 PHUSE paper](https://phuse.s3.eu-central-1.amazonaws.com/Archive/2025/Connect/EU/Hamburg/PAP_ML08.pdf) drew the consequence: a two-conversation workflow with a human-verified Excel checkpoint between PDF and JSON. Better models then made a third shape possible — a single non-interactive pass whose verification is engineered in rather than performed live: a mechanical mark-check re-derived from the PDF, an uncertainty report in place of interactive gates, a programmatic row audit, and an auditable corrections sidecar. Claude Cowork made this third shape practical — file access and code execution inside the extraction session itself. The human moved from guiding the extraction to reviewing its evidence.

Each model generation brought material improvements in vision understanding, table structure recognition, and semantic reasoning. All pipeline steps use the latest available Claude model. See [`documents/background-and-challenges.md`](documents/background-and-challenges.md) for the fuller history.

## License

Code is licensed under the [MIT License](LICENSE). Documentation and schemas are shared under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

## Author

Kerstin Forsberg — information architect specializing in clinical data standards. Built iteratively with Claude (Anthropic).
