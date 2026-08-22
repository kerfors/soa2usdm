# Backlog — inventory, annotation and schema items

Items motivated by working with the usdm_data corpus: two to the activity inventory (`soa2usdm/activity_inventory.py` → `activities.html` / `activities.json`), two to the annotation layer, one to the extraction schema, one that turns the report's open decisions into data, and — since the review page exists — its follow-ups and a naming question. Items 1–4 are additive — no schema break; raw extraction stays immutable, fixes flow through the corrections sidecar as usual. Item 5 tightens a schema field that is currently unconstrained. Items 6–8 belong to the review surface; the rule that bounds them is stated under item 7.

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

## 5 — Constrain the range notation in `soa-table-extraction.schema.json`

**Motivation.** `/definitions/schedule_grid_value/properties/merged_cell_range` is `{"type": "string"}` and its description reads *"the range notation (e.g., 'B2:D2')"* — a spreadsheet A1 cell reference. Every one of the 699 range values in the corpus is instead a numeric column-position range (`'4:5'`, `'6:9'`, `'12:24'`), and every acceptance invariant is written that way. Because the type is a bare string, both notations validate and the disagreement is invisible.

It is not hypothetical. Two independent blind extractions of NCT02107703 Table 1 reproduced the mark matrix exactly — 117 marks, symmetric difference 0 once the column-anchor offset is applied — but emitted `'4:5'` in one run and `'D1:E1'` in the other. The decisive evidence for the cause: `activity_schedule.source_range` carries no A1 example in its description and came out numeric in *both* runs. Only the field with the misleading example flipped.

**Sketch.** Reword the description to name the numeric convention (*"the covered column-position range, e.g. '4:9'"*), add `"pattern": "^\\d+:\\d+$"` so a non-numeric range fails validation instead of passing silently, and give `source_range` the same treatment for symmetry even though nothing has drifted there yet.

**Acceptance.** All 699 existing range values in the corpus validate against the new pattern (699/699, no exceptions carved out); an A1-style value fails. Add a regression test alongside the existing schema tests.

**Size.** Small. Schema + one test. Deferred 2026-08-17 — deliberately not bundled with prompt v3.7.0, so the remaining 18 studies run against an unchanged schema.

## 6 — Surface the open decisions: a report header block (prompt §7), then `review_items` in the schema

**Motivation.** The uncertainty report is the review surface that replaced the PDF→Excel human checkpoint (guide v2.6). On NCT05051579 it runs 390 lines, and the calls a reviewer must actually decide are spread across §5 (seven subsections), §6 and §9 — the `n12` annotation-scope decision is documented under *Synthesised values*, not under the section literally titled "The judgement calls, stated plainly". A reviewer who goes straight to the section named for decisions still misses one. A review surface that has to be read end to end to find its own worklist is not a checkpoint.

**Sketch.** Two steps, independent, (a) first.
(a) *Prompt only, no schema change.* §7 gains a required opening block: a **Decisions needed** table — one row per open call giving where it is (page, row/marker), the call made, the alternative, and the section holding the detail — followed by a short **Recorded, not open** list of calls made under an explicit rule. The existing detail sections stay exactly as they are.
(b) *Schema + pipeline.* Add an optional `review_items` array to `soa-table-extraction`: `{id, severity, location {page, row_position?, column_position?, annotation_marker?}, call_made, alternative, report_section}`. Route it into the `review_queue` that `consolidate` already carries (fed today only by fuzzy activity matching), show an open-decision count per protocol in the collection index beside the Report link, and add a gate check that every `review_items` entry names a report section that exists and vice versa — the cross-check the prose-only version cannot have.

**Acceptance.** (a) A regenerated report opens with the block, and the four open calls on NCT05051579 — PK sub-labels, `n12` scope, the `n1` intro paragraph, `Fasting Visit` type — are visible without scrolling. (b) `review_items` validates across the corpus with *absent* legal, so no backfill is forced; the index shows the per-protocol count; the gate fails when block and data disagree.

**Size.** (a) Small — prompt wording only; no code, no re-extraction, no schema version bump. (b) Medium — schema, consolidate, index generator, one gate check, tests.

**Raised 2026-08-20** from the first `test`-collection extraction (NCT05051579 / Lilly J2A-MC-GZGI). Do (a) and judge the shape against a real report before spending (b). The NCT05051579 report was hand-patched with the block on 2026-08-20 as the trial; the prompt is unchanged.

**Status 2026-08-22: (a) and (b) shipped together**, once the review-page prototype showed the page wants the decisions as data from the start. Prompt v3.8.0 §7 requires the two opening blocks and the one-to-one `review_items`; the schema field is optional (absent = pre-v3.8.0, no backfill forced); resolve passes it through and consolidate aggregates it as `review_items` with `table_number` — kept **separate from `review_queue`**, which stays consolidation's own low-confidence matches. The collection index shows "n / total open" beside the Report link; `tools/gate.py` check 13 compares the block and the arrays. One deviation from the sketch above: **resolution is derived, not stored** — an item is decided exactly when a corrections-sidecar entry names it in the new `review_item` field (new op `confirm` records "examined, call kept" without changing data), so the raw extraction stays immutable and the sidecar remains the only write path. NCT05051579's four items were backfilled through its sidecar (`target: review_items, op: add`), the route any pre-v3.8.0 extraction can use.

## 7 — Review page follow-ups (branch `review-page`)

**Context.** The review page (`soa2usdm/review_page.py`, `{NCTID}_review.html`) draws the extraction on its rendered source pages and reads `review_items` as the reviewer's worklist. Its scope test is fixed: a feature belongs on the page only if it makes a schema-level fact reviewable against the source page. The page writes nothing; the corrections sidecar stays the only write path. Four things surfaced in the first real use (NCT05051579 D2/D4 confirmed through the page; NCT04677179 generated across four tiled tables) and are deferred on purpose:

**7a — The "take the alternative" draft is too thin for scope decisions.** For a note-scope call such as D2 (note 12: FSH only vs FSH+LH+Estradiol) the real correction is three entries: rebind `marker_locations`, and clear `annotation_markers` on every row that leaves the binding, because resolve requires the two to agree. The page's skeleton should say this in words next to the placeholders, and prefill the row list from the item's `location`. Small; prompt-free.

**7b — Consolidation has no write path.** `review_queue` (fuzzy matches) is shown on the page tagged "from consolidation", but a reviewer who rejects a merge has nowhere to record it. Add a per-protocol consolidation sidecar (accept / reject per unified-activity pair, with `reason`, `by`, `at`) read by `consolidate` before matching — the consolidation analogue of the Layer 1 sidecar. Deferred until the first real reject exists (the corpus has 3 `fuzzy_review` items: NCT04557384, NCT01847274, NCT02291289 — one of them is the natural first case).

**7c — Round trip without a server.** Today: page drafts the entry → paste into the sidecar → re-run Layers 1.5–3 + review page + index → commit → push → Pages. Proposed last step: the page prefills the GitHub web editor with the merged sidecar text (`/new/<branch>?filename=&value=` for a new file; clipboard + edit URL for an existing one), the reviewer commits or opens a PR, and a GitHub Action on the collections repo re-runs the deterministic layers and regenerates the site. Git remains the only application. Do after 7a/7b and only once the page has been used for real on a multi-table protocol.

**7d — `page_grid.merged_cells` is not yet safe to consume.** A dashed rule is missed in the data columns, so two rows are recorded as one vertically merged cell (NCT05051579 doc p.13, Concomitant medications / Substance use: 19 columns). The review page avoids it by reading marks from the band rectangle; anything that wants merged-mark distribution (prompt §5) or cell-bounded annotation scope (§6) needs a dashed-run detector or a text tiebreak (two rows of label text = two rows) first. Related artefact, pinned in `tests/test_review_page.py`: on NCT04677179 doc p.36 a redacted (CCI) row's two marks fall into the neighbouring header band.

## 8 — Naming: "uncertainty report" vs "extraction log"

**Motivation.** The collection index now has two columns, **Review** (the review page, with "n open of N") and **Log** (the extractor's own account of the run), because the two are different objects: one is where decisions are taken, the other is provenance. The rendered page is titled "Extraction log" and the link reads "extraction log" — but the file is still `{NCTID}_uncertainty_report.md/.html`, the prompt (§7) and the workflow guide still say "uncertainty report", and `tools/gate.py` globs on that name. Two names for one artefact.

**Sketch.** Decide the name once and apply it everywhere in one prompt version: file name, §7 heading, guide table, gate glob, index code. "Extraction log" describes what it is (a log of what the extractor did and where it was unsure); "uncertainty report" describes what it was for when it was the review surface. If renamed, existing files are renamed by a one-off script (markdown content untouched) and the index accepts both names for one release. Not now — the Layer 1 file name is part of the prompt contract, and a rename mid-branch would split the corpus.

**Size.** Small, but it touches the prompt version. Raised 2026-08-22.

---

2026-08-15, item 5 added 2026-08-17, items 7–8 added 2026-08-22. Evidence: `collections/usdm_data/protocols/activities.json`, the per-protocol `*_resolved.json` annotation arrays, the NCT04677179 protocol markdown, and the two NCT02107703 Phase 2 pilot extractions.

**Status 2026-08-22:** items 1, 2, 4, 5 and 6 shipped; item 3 open (substantive, and the natural groundwork for the semantic layer); items 7–8 raised, deferred on purpose. Smaller items closed the same day outside this list: `config.DEFAULT_COLLECTION` pinned to `usdm_data` (sort order had silently skipped the PDF-backed tests once a second collection existed), and the NCT05051579 `proximity`→`synthesized` relabel through its sidecar.

**Status 2026-08-15:** items 1, 2 and 4 shipped; item 3 open. Item 2: `is_redacted` derived at resolve (exception-based — present only when true), carried onto `unified_activities`, filterable in the inventory, per-protocol count in the collection index (6/60, plus NCT05176314 2/24 and NCT05324124 1/20 — genuine redactions, not false positives). Item 4: legend density rule retypes footnote→`legend` at resolve with the extracted type kept in `annotation_type_source` (the 3 NCT04677179 unified legends; 0 false positives over 752 corpus annotations); header-bound detector warns at consolidation — measured base rate 5 across 4 protocols, all reading as deliberate group-scope notes, hence warning not error. The NCT04677179 header-bound misbind suspected above no longer exists in current data (the T4 c11 note was re-bound to the restored Dosing row on 2026-08-15).
