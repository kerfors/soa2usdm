# SoA2USDM

> Conversational AI workflow and programmatic pipeline for extracting Schedule of Activities (SoA) tables from clinical trial protocols and transforming them into structured, fully traceable, USDM-ready data. A domain expert guides the LLM through extraction and verification; Python handles resolution, consolidation, and visualization.

This repository is the **product**: the Python package, JSON schemas, prompts, notebooks, and design documents. Protocol collections — the derived extraction outputs and their visualizations — live in a **separate data repository**, [`soa2usdm-collections`](https://github.com/kerfors/soa2usdm-collections), so that code and data version independently and a public code repo stays free of protocol PDFs.

The approach is described in the PHUSE paper *From Schedules of Activities (SoA) to USDM: Automating Protocol Extraction Using Large Language Models* (Forsberg & Ulander), available in the [PHUSE paper archive](https://phuse.global/).

## Architecture

Three processing layers:

| Step | Question | How | Scope |
|------|----------|-----|-------|
| **1. Extraction** | What does this table show? | Claude AI + human verification | per table |
| **2. Resolution** | What precisely is in it? | Programmatic (Python) | per table |
| **3. Consolidation** | What was the protocol expressing? | Programmatic (Python) | per protocol |

Layer 1 uses two Claude conversations per table (PDF→Excel→JSON, or a non-interactive PDF→JSON path) with human verification between steps. Layers 2–3 are pure Python, producing consolidated structured data and HTML visualizations.

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
│   └── index_generator.py           # Collection index page
│
├── notebooks/
│   ├── 00_download_extract.ipynb    # Download PDFs, extract SoA pages, scaffold folders
│   └── 01_batch.ipynb               # Batch processing across a collection
│
├── tests/
│   ├── test_pipeline_regression.py  # Golden-output regression over discovered protocols
│   └── fixtures/protocols/          # In-repo golden data (JSON only) — tests run standalone
│
└── pyproject.toml
```

## Running It

**Layer 1 — Extraction (Claude conversations):**
Attach the prompt file + your data to a new Claude conversation. See [`prompts/EXTRACTION_WORKFLOW_GUIDE.md`](prompts/EXTRACTION_WORKFLOW_GUIDE.md) for the full workflow.

**Layers 2–3 — Resolution, Consolidation & Visualization (Python):**
The `soa2usdm/` package implements all processing steps. Use `01_batch.ipynb` to run across a protocol collection — set `COLLECTION` in the config cell and execute.

## Key Design Decisions

**Errors collected, not raised.** Steps continue on errors — partial success matters when one table out of four has issues.

**Two conversations, not one.** Layer 1 splits across two Claude conversations with Excel verification in between. Catches errors before they propagate into JSON.

**One file per table, then integrate.** Each table gets its own extraction/resolution file. Consolidation handles cross-table logic.

**Raw + corrections, never overwrite.** A verified extraction is the raw extraction plus a corrections sidecar applied deterministically — the original model output is preserved and every change is auditable.

**Traceability throughout.** Every element traces from consolidated output back through resolved and extracted to PDF page and row position.

## Development Note

This work spans a period of rapid LLM advancement. Each model generation brought material improvements in vision understanding, table structure recognition, and semantic reasoning. All pipeline steps use the latest available Claude model.

## License

Code is licensed under the [MIT License](LICENSE). Documentation and schemas are shared under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

## Author

Kerstin Forsberg — information architect specializing in clinical data standards. Built iteratively with Claude (Anthropic).
