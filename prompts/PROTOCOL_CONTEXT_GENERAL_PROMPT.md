# Protocol context extraction — general profile

Prompt version: 1.2.0 · Schema: `soa2usdm-protocol-context-general` 1.1 · Profile: general (trials that are not cell or gene therapy)

You extract six kinds of information from ONE clinical trial protocol, beyond its Schedule of Activities (SoA).
The categories are chosen for trials in general; the cell and gene therapy profile is `prompts/PROTOCOL_CONTEXT_CGT_PROMPT.md`.
Four categories have the same shape as in that profile (cross_references, abbreviations, panels, lab_and_purpose); two are
this profile's own (instruments, measurements).
This is transcription, not interpretation.

## Inputs

Prepared by `tools/protocol_context_inputs.py` from the protocol PDF and the collection's consolidated SoA:

- `{NCTID}_pages.txt` (protocol folder, local only) — the protocol's text, page by page. `===== PAGE n =====` gives the page number of the posted PDF.
  Use these page numbers, never printed footers. A page without a text layer reads `[no text layer on this page]`.
- `SoA2USDM/context/{NCTID}_soa_inputs.json` — from the consolidated SoA (Layer 3):
  - `soa_activities` — the SoA row names (section headers excluded);
  - `soa_cross_references` — SoA notes that point to a section, appendix, table or figure, with the target as printed;
  - `soa_notes` — every SoA note (footnote) with the activities it is bound to.
- The protocol PDF, for checking a page visually when the text layer is unclear (rules 8 and 10).

## Hard rules

1. Every item carries `evidence`: a list of `{page, quote}`. Each `quote` is copied character for character from that page's text in
   `{NCTID}_pages.txt` (line breaks and runs of spaces may be collapsed to one space; nothing else). Keep quotes short — the sentence or
   table row that states the fact, not whole paragraphs.
2. Every field value is wording the protocol states. If the protocol does not state it, the value is `null`. Never fill a field from general
   knowledge (for example, do not supply an instrument's version, recall period, scoring range, a measurement's position or method, a
   specimen or an abbreviation's meaning that the document does not print).
3. Do not classify into CDISC domains, test codes or terminology. Only record what the document says.
4. If a category is not covered by the protocol, return an empty list and say so in `notes`.
5. Where the document says two different things (e.g. an amendment change, or serum in one section and urine in another), record both with
   their evidence and say so in `notes`.
6. SoA notes are protocol text too. When a note states a specimen, method, lab, position, unit or what an assessment includes, use it —
   quote it from the page it is printed on.
7. Ignore running headers, footers and watermark fragments in the text layer; never quote them as content.
8. A page that reads `[no text layer on this page]` may be read from the PDF page image. Mark every evidence entry or abbreviation taken
   from it with `"read_from": "page image"`; these are the only entries the quote checker cannot verify.
9. `soa_activities` values in `instruments`, `measurements` and `lab_and_purpose` are exact names from `soa_activities`. Name only the
   SoA activities the text links the item to (by name, by an SoA note bound to the activity, or by a section the SoA note points to).
10. A table whose text layer runs its columns together (typically the lab-tests table, with one column per panel) is read from the PDF
    page image before analytes are assigned to panels. Quotes still come from the text layer. Say in `notes` which pages were checked
    this way; if the image cannot be read, say which assignments rest on the text layer alone.
11. When the PDF holds the protocol together with amendments or several protocol versions, extract from the protocol version the SoA
    comes from (the pages of the SoA notes show which). Record what a later amendment in the PDF changes for an SoA activity or a
    category as an additional entry with its own evidence, and say so in `notes`.
12. A text layer can be letter-spaced (`a d verse e ve nt`). Write abbreviation terms and definitions as printed on the page, with normal
    word spacing (`adverse event`); the checker compares abbreviations without whitespace. Evidence quotes stay as in the text layer.
    A letter-spaced page has a text layer, so rule 8 does not apply to it.

## Output — one JSON file `SoA2USDM/context/{NCTID}_protocol_context.json`

```json
{
  "schema_name": "soa2usdm-protocol-context-general",
  "schema_version": "1.1",
  "nct_id": "NCT number as printed, or null when the document prints none",
  "document": "protocol identifier and version/amendment as printed on the title page",
  "pages_covered": "first-last",
  "page_numbers": "PDF page numbers of the protocol as posted on ClinicalTrials.gov",
  "provenance": {"prompt_version": "1.2.0", "model": "", "extracted_at": "", "pdf_sha256": "", "pages_file_sha256": ""},
  "cross_references": [ {"soa_note": "the SoA note text", "target_as_printed": "", "target_found": true, "target_heading": null,
                         "target_page": 0, "what_it_says": "a short verbatim quote from the target", "evidence": []} ],
  "abbreviations": [ {"term": "", "definition": "", "page": 0, "read_from": "text layer | page image (optional; default text layer)"} ],
  "panels": [ {"panel_name": "as printed (e.g. Hematology, Chemistry, Lipids, Urinalysis)", "analytes": ["as printed"], "specimen": null,
               "lab": null, "evidence": []} ],
  "lab_and_purpose": [ {"soa_activity": "exact name from soa_activities", "lab": "central | local | both | as stated", "purpose": null,
                        "specimen": null, "method": null, "evidence": []} ],
  "instruments": [ {"name": "as printed", "kind": "instrument | criteria", "abbreviation": null, "version": null, "type": null, "respondent_or_rater": null,
                    "recall_period": null, "mode": null, "scoring_or_range": null, "purpose": null,
                    "soa_activities": ["exact names from soa_activities"], "evidence": []} ],
  "measurements": [ {"name": "the measurement group as printed (e.g. Vital signs, Body measurements, 12-lead ECG)",
                     "components": ["as printed"], "position_or_condition": null, "method": null, "units": null,
                     "soa_activities": ["exact names from soa_activities"], "evidence": []} ],
  "notes": "free text: what was not found, conflicts, pages that could not be read"
}
```

Leave `provenance.model` and `provenance.extracted_at` for the caller to stamp if you cannot state them.

## Category guidance

- **cross_references** — one entry per target in `soa_cross_references`: a note that points to two targets gives two entries. Find the
  target in the pages; give its heading and page and a short quote of what it says about the SoA row. If the target cannot be found,
  `target_found: false`.
- **abbreviations** — the complete abbreviation list as printed (one entry per line of that list). Also abbreviations defined only under SoA
  tables, in SoA notes or in the lab-tests table, with their page.
- **panels** — lab panel composition (hematology, chemistry, lipids, coagulation, urinalysis, serology, hormones …): the analytes listed,
  the specimen and lab where stated. Pregnancy tests, drug screens and similar single tests listed in the lab-tests table also go here,
  under the heading the table gives them.
- **lab_and_purpose** — for SoA activities where the protocol (body or SoA notes) states central vs local lab, purpose, specimen or method.
  Only activities the text actually speaks to.
- **instruments** — every questionnaire, rating scale, diary, performance status, interview or other instrument the protocol names for an
  SoA activity (e.g. C-SSRS, PGI-C, a numeric rating scale for pain, ECOG performance status): name and abbreviation as printed, version,
  type as stated (questionnaire, scale, diary …), who completes or rates it, recall period, mode (paper, electronic, interview), scoring
  or range where printed, purpose, and the SoA activities it applies to. `kind`: `instrument` for these; `criteria` for grading,
  staging, classification, prognostic or response criteria the investigator applies (e.g. CTCAE, RECIST, Ann Arbor, NYHA) when the
  protocol names them for an SoA activity.
- **measurements** — what a measurement or examination group includes, as printed: vital signs, body measurements, ECG, physical
  examination and similar: the components listed (e.g. systolic and diastolic blood pressure, pulse, temperature, height, weight), the
  position or condition (supine, after 5 minutes rest, fasting), method, units, and the SoA activities it applies to. Measurements and
  examinations only: not demographics, medical or family history, or other collected data.

## Finish

Write the file, check that it is valid JSON and validates against `schemas/soa2usdm-protocol-context-general.schema.json`, then run
`tools/check_protocol_context.py`. Every quote must be found on its cited page. Report counts per category, failing quotes (should be none),
and anything notable — in particular tokens in SoA activity names that the abbreviation list does not define.
