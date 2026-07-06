# SoA2USDM — Background & Key Challenges

## Background

This work builds on two foundations:

**PHUSE EU Connect 2025.** The [ML-08 paper](https://phuse.s3.eu-central-1.amazonaws.com/Archive/2025/Connect/EU/Hamburg/PAP_ML08.pdf) documented a year-long journey from automated multi-pass extraction to a two-step conversational workflow. The main result was the first version of the SoA2USDM schema separating structural extraction from semantic interpretation, and the case for human-in-loop collaboration over full automation.

**Eli Lilly protocol collection (Summer 2025).** Processing 16 Eli Lilly protocols through a combination of manual and programmatic extraction into USDM Excel loaded into Neo4j produced the key insight behind the SoA2USDM architecture: a single protocol's study design often cannot fit in one table. Sponsors split SoA data across multiple tables for different reasons — page breaks, domain grouping, population tracks, subsidiary timing detail. Correctly classifying *why* a table exists is the precondition for everything downstream. This led to the six-type table taxonomy (main_soa, continuation, domain, subsidiary, track, reference) and the cross-table consolidation architecture that v7.3 lacked. See [soa2usdm_elililly_protocols](https://data4knowledge.sharepoint.com/:f:/s/d4k9/IgBf4uqzDq4PRbJhr8dsdBEpAUFcxFyz84Gd1JRcVzURwCY?e=QqPSkp) (d4k SharePoint, Projects / Project 0023 - Lilly Study Build, includes a README with context).

## Key Challenges

Four structural elements of SoA tables each presented distinct extraction challenges — and each shaped a specific part of the architecture.

**Activity hierarchy.** Protocol authors express parent-child relationships through visual cues: bold text, background shading, indentation. These are presentation conventions, not data structures. Getting the hierarchy right is critical because it determines how activities consolidate across tables — a misplaced parent breaks the entire downstream tree. The solution was to extract indentation as a separate signal (indentation_level), then derive explicit parent-child relationships programmatically in the resolution layer rather than asking the LLM to infer them.

**Schedule column structure.** SoA column headers are typically multi-row — epoch on top, visit below, study day below that, sometimes with merged cells spanning groups. Extracting these correctly and composing them into meaningful composite labels (e.g., "Treatment / Visit 3 / Day 15") requires understanding which header row levels matter and how they nest. The staged extraction approach — confirm column count first, then row labels — catches errors before they propagate into the grid.

**Merged cells in the data grid.** This remains the hardest problem for any LLM-based extraction. Merged cells are a spatial construct — they define membership by visual extent across a 2D space, not by text content. LLMs process tokens, not drawings. This is precisely why the architecture uses Excel as a human verification checkpoint: the person can see and fix merge boundaries that the LLM gets wrong, before any structured data is generated.

**Annotation linking.** Protocol authors encode additional information at multiple structural levels (schedule properties, section headers, individual activities, specific cells) using different mechanisms (superscript markers, free-text comments, parenthetical references). A single footnote might apply to an entire row, a specific column, or a single cell — and the only way to know is to find where its marker appears. Systematic extraction is genuinely challenging because there is no standard for where sponsors choose to place their annotations. The schema addresses this with explicit marker_locations that record every occurrence, but populating them requires scanning the entire table — a step the LLM frequently needs prompting to complete.


