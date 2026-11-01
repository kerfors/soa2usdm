# Protocol context extraction — cell and gene therapy trials

Prompt version: 1.0.0 · Schema: `soa2usdm-protocol-context-cgt` 1.0 · Profile: cell and gene therapy (CGT)

You extract eight kinds of information from ONE clinical trial protocol, beyond its Schedule of Activities (SoA).
The categories are chosen for cell and gene therapy trials (AAV gene therapy, CAR-T, CAR-NK and similar).
This is transcription, not interpretation.

## Inputs

Prepared by `tools/protocol_context_inputs.py` from the protocol PDF and the collection's consolidated SoA:

- `{NCTID}_pages.txt` (protocol folder, local only) — the protocol's text, page by page. `===== PAGE n =====` gives the page number of the posted PDF.
  Use these page numbers, never printed footers. A page without a text layer reads `[no text layer on this page]`.
- `SoA2USDM/context/{NCTID}_soa_inputs.json` — from the consolidated SoA (Layer 3):
  - `soa_activities` — the SoA row names (section headers excluded);
  - `soa_cross_references` — SoA notes that point to a section, appendix, table or figure, with the target as printed;
  - `soa_notes` — every SoA note (footnote) with the activities it is bound to.
- The protocol PDF, for checking a page visually when the text layer is unclear.

## Hard rules

1. Every item carries `evidence`: a list of `{page, quote}`. Each `quote` is copied character for character from that page's text in
   `{NCTID}_pages.txt` (line breaks and runs of spaces may be collapsed to one space; nothing else). Keep quotes short — the sentence or
   table row that states the fact, not whole paragraphs.
2. Every field value is wording the protocol states. If the protocol does not state it, the value is `null`. Never fill a field from general
   knowledge (for example, do not supply a capsid serotype, a method, a specimen or an abbreviation's meaning that the document does not print).
3. Do not classify into CDISC domains, test codes or terminology. Only record what the document says.
4. If a category is not covered by the protocol, return an empty list and say so in `notes`.
5. Where the document says two different things (e.g. an amendment change, or serum in one section and plasma in another), record both with
   their evidence and say so in `notes`.
6. SoA notes are protocol text too. When a note states a specimen, method, lab or unit for an activity (e.g. "Whole blood samples will be
   collected …", "by a validated PCR-based assay"), use it — quote it from the page it is printed on.
7. Ignore running headers, footers and watermark fragments in the text layer; never quote them as content.
8. A page that reads `[no text layer on this page]` may be read from the PDF page image. Mark every evidence entry or abbreviation taken
   from it with `"read_from": "page image"`; these are the only entries the quote checker cannot verify.

## Output — one JSON file `SoA2USDM/context/{NCTID}_protocol_context.json`

```json
{
  "schema_name": "soa2usdm-protocol-context-cgt",
  "schema_version": "1.0",
  "nct_id": "...",
  "document": "protocol identifier and version/amendment as printed on the title page",
  "pages_covered": "first-last",
  "page_numbers": "PDF page numbers of the protocol as posted on ClinicalTrials.gov",
  "provenance": {"prompt_version": "1.0.0", "model": "", "extracted_at": "", "pdf_sha256": "", "pages_file_sha256": ""},
  "product": [ {"name": "", "other_names": [], "type": "", "vector_or_capsid": null, "transgene": null, "manufacturing_or_source": null,
                "evidence": [ {"page": 0, "quote": ""} ]} ],
  "immunogenicity": [ {"measure": "the antibody/assay as named", "target": null, "specimen": null, "method": null, "units": null,
                       "purpose": "as stated (e.g. eligibility, safety, response monitoring)", "timing": null, "lab": null, "evidence": []} ],
  "cross_references": [ {"soa_note": "the SoA note text", "target_as_printed": "", "target_found": true, "target_heading": null,
                         "target_page": 0, "what_it_says": "a short verbatim quote from the target", "evidence": []} ],
  "abbreviations": [ {"term": "", "definition": "", "page": 0, "read_from": "text layer | page image (optional; default text layer)"} ],
  "panels": [ {"panel_name": "as printed (e.g. Hematology, Chemistry, Coagulation)", "analytes": ["as printed"], "specimen": null,
               "lab": null, "evidence": []} ],
  "endpoint_assays": [ {"topic": "PK | cellular kinetics | persistence | shedding | biodistribution | expression/activity | other",
                        "what": "as named", "matrix": null, "method": null, "units": null, "endpoint_text": null, "evidence": []} ],
  "genetic_testing": [ {"what": "as named", "gene_variant_or_hla": null, "purpose": null, "method": null, "specimen": null, "evidence": []} ],
  "lab_and_purpose": [ {"soa_activity": "exact name from soa_activities", "lab": "central | local | both | as stated", "purpose": null,
                        "specimen": null, "method": null, "evidence": []} ],
  "notes": "free text: what was not found, conflicts, pages that could not be read"
}
```

Leave `provenance.model` and `provenance.extracted_at` for the caller to stamp if you cannot state them.

## Category guidance

- **product** — the study therapy and any other investigational or lymphodepleting product: name, type (AAV gene therapy, CAR-T, CAR-NK …),
  vector/capsid, transgene/construct, as printed (title page, synopsis, investigational product section).
- **immunogenicity** — every antibody or immune-response assay (anti-capsid total or neutralizing, anti-transgene product, inhibitors such as
  Bethesda, anti-product/ADA, anti-HLA/donor-specific, cellular immunogenicity …): target, specimen, method, units, purpose, timing, lab.
- **cross_references** — one entry per target in `soa_cross_references`: a note that points to two targets gives two entries. Find the
  target in the pages; give its heading and page and a short quote of what it says about the SoA row. If the target cannot be found,
  `target_found: false`.
- **abbreviations** — the complete abbreviation list as printed (one entry per line of that list). Also abbreviations defined only under SoA
  tables, in SoA notes or in the lab-tests table, with their page.
- **panels** — lab panel composition (hematology, chemistry, coagulation, urinalysis, serology, liver tests …): the analytes listed, the
  specimen and lab where stated.
- **endpoint_assays** — definitions of PK, cellular kinetics, persistence, vector shedding, biodistribution, factor activity/expression:
  matrix (blood, plasma, saliva, semen …), method (PCR, flow cytometry, one-stage assay …) and units, as stated.
- **genetic_testing** — genotyping, gene/variant tests, HLA/KIR typing, vector integration, replication-competent virus tests: what,
  gene/variant, purpose, method, specimen.
- **lab_and_purpose** — for SoA activities where the protocol (body or SoA notes) states central vs local lab, purpose, specimen or method.
  Only activities the text actually speaks to.

## Finish

Write the file, check that it is valid JSON and validates against `schemas/soa2usdm-protocol-context-cgt.schema.json`, then run
`tools/check_protocol_context.py`. Every quote must be found on its cited page. Report counts per category, failing quotes (should be none),
and anything notable — in particular tokens in SoA activity names that the abbreviation list does not define.
