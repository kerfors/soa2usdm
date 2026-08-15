# Backlog — inventory and annotation improvements

Four improvements motivated by working with the usdm_data corpus: two to the activity inventory (`soa2usdm/activity_inventory.py` → `activities.html` / `activities.json`), two to the annotation layer. All are additive — no schema break; raw extraction stays immutable, fixes flow through the corrections sidecar as usual.

## 1 — Carry linked footnote text into the activity inventory

**Motivation.** SoA footnotes carry the content that distinguishes otherwise identically-named activities: performer context ("Locally performed"), timing constraints ("Screening endoscopy must occur ≤14 days prior to randomization"), conditional execution ("Only for participants who are positive for anti-HBc at screening"), preconditions ("Fasting samples are preferred…"), co-timing ("Performed at time of endoscopy"). The inventory currently carries only `any_marks`; the footnote text is invisible to inventory search and browsing, although the row↔annotation join already exists in the resolved layer (`linked_annotation_ids` / `annotation_markers`).

**Sketch.** In `activity_inventory._collect`, for each occurrence pull the linked annotations from the already-loaded resolved JSON; attach to the consolidated row as `annotations: [{marker, table_number, text}]`, deduped by text. Render in `activities.html` as an expandable per-row detail and include annotation text in the search index.

**Acceptance.** Searching "sigmoidoscopy" in activities.html finds NCT04677179 "Colon biopsy sample collection" (the term occurs only in that row's footnote, not in any activity name). The activities.json row carries the footnote text verbatim. Counts unchanged.

**Size.** Small — one module + template; additive field.

## 2 — Redaction as a first-class flag

**Motivation.** Public protocol documents redact some SoA rows (activity name replaced by "CCI"). These rows are currently indistinguishable from real activity names except by string matching. NCT04677179 has 6 redacted rows of 60. A per-protocol redaction count is a useful data-quality signal for anyone selecting protocols from a collection, and redacted rows should be excludable from name-based analyses.

**Sketch.** Detector on activity names (`CCI`, `CCI (redacted)` and variants) setting `is_redacted: true` at the resolved layer; propagate to the inventory; surface a per-protocol redaction count in the collection index and an inventory filter.

**Acceptance.** NCT04677179 reports 6 redacted rows; negative control: no false positives across the other 21 protocols (no legitimate activity name matches the pattern).

**Size.** Small.

## 3 — Resolve "See Section X" footnote cross-references

**Motivation.** Footnotes frequently defer their content to the protocol body ("See Section 8.2.2") — the annotation records the pointer but not what it points to, so the actual constraint stays invisible to anyone working from the extraction outputs. The deferred content is often substantive: in NCT04677179 the body behind such references specifies who performs and interprets an assessment and how a multi-component score is calculated — details stated nowhere in the SoA itself. The full protocol markdown already sits next to the extraction outputs in the collection, so this is a join, not new source material.

**Sketch.** Post-resolve, pure-Python step (no LLM): detect `See Section N(.N…)` patterns in `annotation_text`, locate the section heading in the protocol markdown, attach the section's text (bounded — to the next same-level heading, with a length cap) as `referenced_section: {number, title, text}` on the annotation, with page provenance where recoverable.

**Acceptance.** The "See Section 8.2.2" annotations on NCT04677179 carry §8.2.2's text; a footnote citing a section the markdown does not contain flags `[UNRESOLVED]` rather than guessing. Raw extraction files untouched.

**Size.** Small–medium. Independent of items 1–2; composes with item 1 (resolved sections could surface in the inventory detail later).

## 4 — `legend` annotation type + binding-smell detectors

**Motivation.** Some SoA-table footnotes are abbreviation legends, not activity qualifiers, and the extractor currently binds them to activity rows like any other footnote — NCT04677179 has three, OCR-garbled ("Srs=columbia–suicide severity rating scale; Bs urface antigen; …"). Separately, two suspected marker misbinds exist in the same protocol (a footnote bound to an unrelated activity row; a footnote bound to a section-header row). Legends pollute any downstream use of footnote text (item 1); misbinds corrupt the row↔footnote join itself.

**Sketch.** Two detectors in the existing detector-set style, with negative controls: (i) legend pattern (`X=Y; Z=…` density) → `annotation_type: legend`; (ii) footnote bound to an `is_section_header` row → warning (measure the base rate across the corpus before treating it as an error). Fixes flow through the corrections sidecar; raw stays immutable.

**Acceptance.** The three NCT04677179 legend annotations are typed `legend`; the header-bound footnote is flagged; no false-positive legend typing across the 22-protocol corpus.

**Size.** Small. Feeds item 1 (harvest quality).

---

2026-08-15. Evidence: `collections/usdm_data/protocols/activities.json`, the per-protocol `*_resolved.json` annotation arrays, and the NCT04677179 protocol markdown.

**Status 2026-08-15:** items 1, 2 and 4 shipped; item 3 open. Item 2: `is_redacted` derived at resolve (exception-based — present only when true), carried onto `unified_activities`, filterable in the inventory, per-protocol count in the collection index (6/60, plus NCT05176314 2/24 and NCT05324124 1/20 — genuine redactions, not false positives). Item 4: legend density rule retypes footnote→`legend` at resolve with the extracted type kept in `annotation_type_source` (the 3 NCT04677179 unified legends; 0 false positives over 752 corpus annotations); header-bound detector warns at consolidation — measured base rate 5 across 4 protocols, all reading as deliberate group-scope notes, hence warning not error. The NCT04677179 header-bound misbind suspected above no longer exists in current data (the T4 c11 note was re-bound to the restored Dosing row on 2026-08-15).
