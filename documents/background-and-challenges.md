# SoA2USDM — Background & Key Challenges

## Background

This work builds on two foundations:

**PHUSE EU Connect 2025.** The [ML-08 paper](https://phuse.s3.eu-central-1.amazonaws.com/Archive/2025/Connect/EU/Hamburg/PAP_ML08.pdf) documented a year-long journey from automated multi-pass extraction to a two-step conversational workflow. The main result was the first version of the SoA2USDM schema separating structural extraction from semantic interpretation, and the case for human-in-loop collaboration over full automation.

**Eli Lilly protocol collection (Summer 2025).** Processing 16 Eli Lilly protocols through a combination of manual and programmatic extraction into USDM Excel loaded into Neo4j produced the key insight behind the SoA2USDM architecture: a single protocol's study design often cannot fit in one table. Sponsors split SoA data across multiple tables for different reasons — page breaks, domain grouping, population tracks, subsidiary timing detail. Correctly classifying *why* a table exists is the precondition for everything downstream. This led to the six-type table taxonomy (main_soa, continuation, domain, subsidiary, track, reference) and the cross-table consolidation architecture that v7.3 lacked. See [soa2usdm_elililly_protocols](https://data4knowledge.sharepoint.com/:f:/s/d4k9/IgBf4uqzDq4PRbJhr8dsdBEpAUFcxFyz84Gd1JRcVzURwCY?e=QqPSkp) (d4k SharePoint, Projects / Project 0023 - Lilly Study Build, includes a README with context).

## From Conversation to Evidence

The workflow has changed shape three times over roughly two years (2024–2026), tracking LLM capability.

**Automation, rejected.** The starting point was automated multi-pass extraction. Its output could not be verified, and the ML-08 paper documents the journey away from it.

**Conversation as verification (2025).** The paper's answer was the two-conversation workflow: PDF→Excel with staged confirmations (table count, column count, row labels), a human-verified Excel checkpoint, then Excel→JSON. The human was the verification surface.

**Evidence as verification (2026).** Better models made a single non-interactive PDF→JSON pass viable — but only because verification was engineered in rather than performed live. Each conversational element has a mechanical replacement: the staged confirmations became an end-of-run uncertainty report; the Excel checkpoint became a mechanical mark-check that re-derives the mark matrix from the PDF (bbox column-binning where there is a text layer, rule-line detection on rasters); an independent programmatic row audit compares extracted rows against what the pages print; and human fixes flow through an auditable corrections sidecar over an immutable raw extraction. Claude Cowork made this shape practical: file access and code execution inside the extraction session let the same session that reads the table re-derive its own read from the PDF geometry.

This is not a return to the automation the paper rejected — that automation failed because its output was unverifiable, while the current pass is automated *and* verifiable. The human did not leave the loop; the role moved from guiding the extraction to reviewing its evidence. The two-conversation path remains available when a human-editable Excel intermediate is wanted.

## Key Challenges

Four structural elements of SoA tables each presented distinct extraction challenges — and each shaped a specific part of the architecture.

**Activity hierarchy.** Protocol authors express parent-child relationships through visual cues: bold text, background shading, indentation. These are presentation conventions, not data structures. Getting the hierarchy right is critical because it determines how activities consolidate across tables — a misplaced parent breaks the entire downstream tree. The solution was to extract indentation as a separate signal (indentation_level), then derive explicit parent-child relationships programmatically in the resolution layer rather than asking the LLM to infer them.

**Schedule column structure.** SoA column headers are typically multi-row — epoch on top, visit below, study day below that, sometimes with merged cells spanning groups. Extracting these correctly and composing them into meaningful composite labels (e.g., "Treatment / Visit 3 / Day 15") requires understanding which header row levels matter and how they nest. The staged extraction approach — confirm column count first, then row labels — catches errors before they propagate into the grid.

**Merged cells in the data grid.** This remains the hardest problem for any LLM-based extraction. Merged cells are a spatial construct — they define membership by visual extent across a 2D space, not by text content. LLMs process tokens, not drawings. This is precisely why the architecture originally used Excel as a human verification checkpoint: the person could see and fix merge boundaries that the LLM got wrong, before any structured data was generated. The mechanical mark-check has since replaced that checkpoint — and outperformed it: on NCT03637764 it caught four merged-span errors that the Excel-verified extraction had missed. The conclusion drawn from that: neither the LLM's visual read nor a person eyeballing a dense grid is reliable on merged cells; re-deriving the spans from the PDF's rule-line geometry is.

**Annotation linking.** Protocol authors encode additional information at multiple structural levels (schedule properties, section headers, individual activities, specific cells) using different mechanisms (superscript markers, free-text comments, parenthetical references). A single footnote might apply to an entire row, a specific column, or a single cell — and the only way to know is to find where its marker appears. Systematic extraction is genuinely challenging because there is no standard for where sponsors choose to place their annotations. The schema addresses this with explicit marker_locations that record every occurrence. Working through the corpus exposed a deeper problem than completeness: a marker's printed position is *evidence* of what a note governs, not the scope itself, and almost every annotation defect found so far traces to treating the two as the same fact — see [`annotation-model-problem.md`](annotation-model-problem.md) for the full analysis. The current response is method provenance (the extraction records *how* each annotation text and binding was derived, exception-based) and structural detectors with negative controls that flag suspect patterns for correction through the sidecar.


