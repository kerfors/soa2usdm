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

**Context.** The review page (`soa2usdm/review_page.py`, `{NCTID}_review.html`) draws the extraction on its rendered source pages and reads `review_items` as the reviewer's worklist. The page is a proof of concept — envisioning a potential user interface for a review user and showcasing the pipeline's traceability — not a committed product surface. Its scope test is fixed: a feature belongs on the page only if it makes a schema-level fact reviewable against the source page. The page writes nothing; the corrections sidecar stays the only write path. Four things surfaced in the first real use (NCT05051579 D2/D4 confirmed through the page; NCT04677179 generated across four tiled tables) and are deferred on purpose:

**7a — The "take the alternative" draft is too thin for scope decisions.** For a note-scope call such as D2 (note 12: FSH only vs FSH+LH+Estradiol) the real correction is three entries: rebind `marker_locations`, and clear `annotation_markers` on every row that leaves the binding, because resolve requires the two to agree. The page's skeleton should say this in words next to the placeholders, and prefill the row list from the item's `location`. Small; prompt-free.

**7b — Consolidation has no write path.** `review_queue` (fuzzy matches) is shown on the page tagged "from consolidation", but a reviewer who rejects a merge has nowhere to record it. Add a per-protocol consolidation sidecar (accept / reject per unified-activity pair, with `reason`, `by`, `at`) read by `consolidate` before matching — the consolidation analogue of the Layer 1 sidecar. Deferred until the first real reject exists (the corpus has 3 `fuzzy_review` items: NCT04557384, NCT01847274, NCT02291289 — one of them is the natural first case).

**7c — Round trip without a server.** Today: page drafts the entry → paste into the sidecar → re-run Layers 1.5–3 + review page + index → commit → push → Pages. Proposed last step: the page prefills the GitHub web editor with the merged sidecar text (`/new/<branch>?filename=&value=` for a new file; clipboard + edit URL for an existing one), the reviewer commits or opens a PR, and a GitHub Action on the collections repo re-runs the deterministic layers and regenerates the site. Git remains the only application. Do after 7a/7b and only once the page has been used for real on a multi-table protocol.

**7d — `page_grid.merged_cells` is not yet safe to consume.** A dashed rule is missed in the data columns, so two rows are recorded as one vertically merged cell (NCT05051579 doc p.13, Concomitant medications / Substance use: 19 columns). The review page avoids it by reading marks from the band rectangle; anything that wants merged-mark distribution (prompt §5) or cell-bounded annotation scope (§6) needs a dashed-run detector or a text tiebreak (two rows of label text = two rows) first. Related artefact, pinned in `tests/test_review_page.py`: on NCT04677179 doc p.36 a redacted (CCI) row's two marks fall into the neighbouring header band.

## 8 — Naming: "uncertainty report" vs "extraction log"

**Motivation.** The collection index now has two columns, **Review** (the review page, with "n open of N") and **Log** (the extractor's own account of the run), because the two are different objects: one is where decisions are taken, the other is provenance. The rendered page is titled "Extraction log" and the link reads "extraction log" — but the file is still `{NCTID}_uncertainty_report.md/.html`, the prompt (§7) and the workflow guide still say "uncertainty report", and `tools/gate.py` globs on that name. Two names for one artefact.

**Sketch.** Decide the name once and apply it everywhere in one prompt version: file name, §7 heading, guide table, gate glob, index code. "Extraction log" describes what it is (a log of what the extractor did and where it was unsure); "uncertainty report" describes what it was for when it was the review surface. If renamed, existing files are renamed by a one-off script (markdown content untouched) and the index accepts both names for one release. Not now — the Layer 1 file name is part of the prompt contract, and a rename mid-branch would split the corpus.

**Size.** Small, but it touches the prompt version. Raised 2026-08-22.

## 9 — Correct `table_metadata` through the corrections sidecar

**Motivation.** The corrections schema's `target` enum covers `schedule_properties`, `schedule_grid`, `activities`, `activity_schedule`, `annotations` and `review_items` — not `table_metadata`. A reviewed decision on a table's type or track label therefore has no write path that keeps the raw extraction immutable. It came up in the sweep-1 pilot (track labels set by hand in staging) and again in the sweep-2 pilot: NCT04677179 Table 4 was extracted as `main_soa` (its judgement call D11), and the review decision (2026-09-27) is to keep the accepted `track` / 'Early Termination / Unscheduled / Post-Treatment'.

**Sketch.** Add `table_metadata` to the `target` enum with op `set` only (no `add` / `remove` — there is exactly one), apply it in ApplyCorrections before Resolve, and allow a `review_item` reference so the D11 decision is recorded as resolved on the review page.

**Acceptance.** A sidecar entry setting `table_type` and `track_label` on NCT04677179 Table 4 reproduces the accepted typing; resolve and consolidate see `track`; the review page shows D11 decided.

**Size.** Small. Schema enum + ApplyCorrections + one test. Needed before NCT04677179 can be promoted from sweep 2.

## 10 — Consolidate a study with more than one `main_soa` table

**Motivation.** `consolidate_tables` processes every `main_soa` table as a base (`is_base=True`), and base tables never match each other. With two `main_soa` tables in one study the activities split into two parallel sets. In the sweep-2 pilot, NCT04677179 with Table 4 typed `main_soa` consolidated to 102 unified activities instead of 64: Table 1 stood alone, and Tables 2 and 3 attached to Table 4. Activity names and parents were identical to the accepted extraction; only the table type differed. Item 9 fixes this study, but any study whose source really has two main schedules hits the same split.

**Sketch.** Keep the first `main_soa` table (lowest table number) as the base and match every further `main_soa` table against it like a non-base table; or make the base a single pass over all main tables that allows matching between them.

**Acceptance.** NCT04677179 consolidates to 64 unified activities with Table 4 typed either way; the other 21 usdm_data protocols consolidate unchanged.

**Size.** Small to medium — one function, but it changes consolidation output, so the whole collection is rebuilt and compared.

## 11 — Prompt: pin the conventions that flip between runs

**Motivation.** Sweep 2 reproduced content (marks, rows, annotations, merged ranges, anchoring) but not three conventions, which changed between runs of the same prompt (NCT02107703 run 1 vs run 2) and between sweeps. Each shows up as a delta that is not a change in the schedule, and each has to be explained by hand in review.
(a) *Empty grid cells.* Emitted as entries or omitted: NCT04004988 280 `activity_schedule` entries for 90 marks; NCT01797120 `schedule_grid` +3, NCT05051579 +22.
(b) *Marker numbering.* Synthesized markers are renumbered when an earlier one drops out: NCT05051579 n2→n1 … n14→n13 once the intro paragraph was not emitted; NCT03637764 n2–n8 → pr1–pr6 + n2 (this is what makes the parked Layer 4 labels stale).
(c) *Synthesized names.* Property and marker names chosen by the extractor drift: 'Study Phase'→'Phase', 'Screening/Lead-In Period'→'Screening/Lead-in sub-period', marker prefixes n→cm, tn→nt; `track_label` case.

**Sketch.** One prompt revision with a rule per convention: (a) emit or omit empty cells, one way; (b) number synthesized markers in reading order and never renumber — a dropped note leaves a gap; (c) a short naming rule for synthesized property names and a fixed prefix list for synthesized markers. The gate's `marks` metric already counts non-empty cells only (`133cd9e`), so (a) no longer shows as a false delta there.

**Acceptance.** A re-run of NCT02107703 under the new prompt reproduces run 1's conventions, not only its content.

**Size.** Small in text, but a prompt version bump: the blind `_instructions/` must be re-redacted before any extraction session (sweep-2 `redaction/`).

**Status 2026-09-27: text done in prompt 3.9.0** (with item 15, branch `prompt-3.9.0-2026-09-27`). Rules: §5 **Empty cells** (complete `schedule_grid` with `""`; `activity_schedule` non-empty only — 44 of 47 published tables already have the complete grid, 46 of 47 omit empty body cells); §6 **Synthesised markers** (prefixes `pr` / `n` / `g`, numbered per table in reading order, a dropped note leaves a gap); §3 synthesised property names = the fixed name of the `property_type`, and a label cell that heads the activity column is not the row's name; §2 `track_label` keeps the source's capitalisation; §4 **Whitespace in `activity_name`** (line breaks join with one space, none next to `/` or after a line-final `-`); §7 floor — a call a stated rule decides is Recorded, not open. Acceptance amended: the NCT02107703 re-run is checked against these rules, not against run 1 — they pick run 1 for the grid and `track_label`, run 2 for the synthesised row-1 name, the T2 markers and the whitespace. Acceptance test: next session (item 15). Published extractions are not backfilled (item 21h).

## 12 — `dryrun.py` rehearses studies of other collections

**Motivation.** Like `promote_dryrun.py` before `133cd9e`, `dryrun.py` takes every study folder in STAGING. With usdm_data and misc_studies staged together it copies extractions into protocol folders that do not exist in the chosen collection.

**Sketch.** The same filter as `promote_dryrun.py`: keep only studies with a protocol folder in `SOA2USDM_COLLECTION`, print the skipped ones.

**Size.** Small.

## 13 — Silent `except Exception: pass` in the page generators

**Motivation.** `220c6fd` made the index fail loudly on a missing dependency. Three blocks still hide an unreadable file rather than a missing package: the consolidated-JSON read in `index_generator.discover_protocol_outputs` (tables, activities, compression, redaction count go missing from the index row), and the resolved-file scans for the nav table list in `visualize.py` and `visualize_resolved.py` (a table drops out of the per-table navigation). None has fired in the corpus as far as known; the point is that nothing would say so if it did.

**Sketch.** Let the exception propagate, or log it as a step error. No fallback.

**Size.** Small.

## 14 — Legend rule retypes a footnote that quotes an abbreviation line

**Motivation.** The legend density rule (item 4) retyped NCT03283098 Table 3 `annot-001` (marker a) footnote→legend. The note is a footnote: it records that footnote a is not printed for Table 1c, quotes the abbreviation line that is printed ('HD = hemodialysis; ET = early termination; SDA = Study drug administration.'), and gives Table 1b's footnote a as a probable equivalent (sweep-2 judgement call D6, accepted). The quoted abbreviation line is what matches the pattern. `tests/test_pipeline_regression.py::test_legend_retypes_exactly_the_known_fragments` fails on it since the sweep-2 promotion (251 passed, 1 failed on `0a3deb8`).

**Sketch.** Tighten the rule so a legend-shaped span inside a longer explanatory text does not retype the whole note (e.g. require the legend pattern to cover most of the text), then re-measure the false-positive rate over the corpus. Do not add the case to `EXPECTED_LEGEND_RETYPES` — that would record a false positive as expected.

**Acceptance.** The test passes with `EXPECTED_LEGEND_RETYPES` unchanged; the four NCT04677179 fragments are still retyped.

**Size.** Small.

## 15 — Prompt: state the review rules the extractions already follow

**Motivation.** The 2026-09-27 review decided 111 of the 112 open sweep-2 review items; 106 were confirms. Most confirms apply one of a few rules the extractions follow already but the prompt does not state, so the same call is flagged again in every study. Rules as decided (each is quoted in the confirm reasons of the collections sidecars):
(a) *Spanned values* (group K). A merged cell's value is distributed over the columns its rule lines cover; a glyph drawn across ruled cells over the columns it crosses; a value in one ruled cell stays in that column, with its qualifier ('X (Day 3-5)'). Exceptions taken where the source itself shows the literal reading is wrong: NCT02107703 T1 dosing text limited to the treatment columns; NCT03637764 'See … Flow Chart' spans are cross-references (source_note), not timing.
(b) *Annotation binding* (group M). A note that names specific visits or columns is bound to those cells; a note on a group row governs the group; a note with no specific target stays table-wide. Applied as alternatives to NCT04557384 D5, NCT04677179 T4 D13 (sentence split into its own note), NCT05051579 D5.
(c) *Header bands* (group D-a). Typed by dominant content; a printed row label wins; single-column visit labels (Randomisation, EOT, ED, End of trial, Study Completion) stay values of an epoch/period band. Open: bands that mix visit types and phases over two rows (NCT04573309 rows 1–2) have no clean typing.
(d) *Header cells over several header rows* (group F). Recorded once, on the row whose type matches the content, split by printed line where lines match different rows; covered cells empty; no value repeated, no row added.
(e) *Hierarchy* (group H). From printed signals (indent, bold, shading, full-width bands); a group stays open across a page break until the next header; no implicit group; a label cell spanning sub-rows is a parent with children.
(f) *Table type* (group B). `track` is a branch some participants take (sub-study, extension, continued access, cohort, responders); a sequential schedule every participant passes through stays `main_soa` even when printed as separate tables (NCT03402841, NCT04320615 — their duplicate unified activities are item 10). The taxonomy's `track` definition ("different population or study phase") and its decision tree do not make this distinction yet.
(g) *Abbreviations* (group N). §6 is applied unevenly: CDISC_Pilot emits ET/RT on the header cells that consist of those terms; NCT05324124 and NCT04004988 do not emit 'ED = early discontinuation' although 'ED' is a header cell. Decide once and apply corpus-wide.
(h) *Row-oriented sampling tables* (group B). NCT04557384 T3 (rows = samples; cycle/day/time as data columns; PK/IG as mark columns) is kept `subsidiary` in printed orientation. The USDM-correct shape is transposed (samples as timepoint columns, PK/IG as activities), and the taxonomy's `reference` example names exactly this kind of table. Needs one rule.

**Sketch.** One prompt/taxonomy revision stating (a)–(h), done together with item 11 (one version bump; re-redact the blind `_instructions/`). Then the extraction flags only calls that fall outside a stated rule.

**Acceptance.** A re-extraction of two reviewed studies (e.g. NCT04557384, NCT04677179) raises no review item that one of (a)–(h) decides.

**Size.** Small to medium in text; a prompt version bump.

**Status 2026-09-27: text done in prompt 3.9.0 / taxonomy v7** (branch `prompt-3.9.0-2026-09-27`). (a) §5 **Spanned values** with the two exceptions (a cross-reference over the whole schedule → `source_note`, no cells; text that names its own columns → those columns only), arrows, and **Qualified marks** reworded (a qualifier stays in its ruled cell — the old "distribute if the label names columns" contradicted group K). (b) §6 **Binding by what a note names** (notes without a printed marker; split sentence; group row; table-wide `g` note anchored to the top header row, marker on no element). (c) §3 **Header bands — typing**; the open case decided as the D-a rule applied literally (option C1): NCT04573309 row 1 stays `epoch`, a blank span stays blank, the mix goes in `property_comment` — no published change. (d) §3 **Header cells over several rows**. (e) §4 **Hierarchy — printed signals only**. (f) §2 **track vs main_soa** + taxonomy v7 (main_soa, track definition, summary row, decision-tree node "does every participant pass through it?"). (g) Option G2: **abbreviations are not annotations** — CDISC_Pilot T1 ab1/ab2 to be removed by sidecar (item 21a); a glossary is item 21f. (h) Option H3: printed orientation, `subsidiary`, rows named 'Sample n'; taxonomy `reference` example narrowed to specification-only tables; the transpose is item 21g. Left out by decision: the page-top continuation rule (group M1, item 17) and the subtitle-in-notes rule (single case). Redaction re-run on a VM-local blind folder: 21 of 21 spans match once, 0 identifiers; no new spans. **Acceptance test (next session, plan in the SoA2USDM Project handoff):** blind re-extraction of NCT04557384, NCT04677179, CDISC_Pilot, NCT02107703, compared with the published `.verified.json` and discarded.

## 16 — Taxonomy: no property type for a visit attribute

**Motivation.** 'Fasting visit' rows (X at the fasting visits) were typed `other` by the extraction in NCT04184622 and NCT04677179 and `modality` in NCT05051579. The review aligned all to `modality` through sidecars (group E) so one attribute has one type, but `modality` means how a visit is conducted, not a requirement on it.

**Sketch.** Add a property type for visit attributes/requirements (or state that `modality` covers them), then retire the six alignment corrections.

**Size.** Small.

## 17 — Page-break defects the extraction does not detect

**Motivation.** (a) A label cell split by a page break with its marks on one page only: NCT04573309 T1 'PD: …' prints mark-free at the top of p.15 under the PK row of p.14; Table 2 prints PK and PD in one cell with shared marks. Kept mark-free with a labelled reviewer note (n1); no marks were invented. NCT04557384 T1 shows the same split, which the extraction did catch (review items D1/D2). (b) Reprinted headers that disagree: NCT03693430 V33 window ±3 on pp.9–10, ±5 on pp.11–12; recorded as ±3 with a labelled reviewer note (n1).

**Sketch.** (a) A check that flags a mark-free row at a page top whose label continues the last row of the previous page. (b) A gate check that compares reprinted header values across pages and reports disagreements.

**Size.** Small to medium.

## 18 — Activity inventory: cell-level notes

**Motivation.** `activities.json`/`.html` list only activity-level annotations. A note bound to a cell drops out of the inventory although it is in resolved and consolidated (`cell_references`): NCT05051579 n10 (Participant Survey × ET) since the review rebound it, and NCT04677179 T4 c15 (Vital signs × V997), split out by the review.

**Sketch.** List cell-level notes under the activity, with the column they bind to.

**Size.** Small.

## 19 — NCT03637764: extract the two flow charts

**Motivation.** Review item NCT03637764 T1 D1 is left open by decision (alternative, deferred). The 'Pharmacokinetics and Immunogenicity Flow Chart' (pp.22–23) and the 'Exploratory Biomarker Flow Chart' (p.24) carry the sample timing of the PK, ADA and biomarker rows of Table 1; since the group-K decision those rows carry only source_notes pr7/pr8 and no schedule data. A sidecar cannot add a table.

**Sketch.** A targeted extraction session (blind setup as in sweep 2) producing Tables 2 and 3, typed `subsidiary`; promote; then close D1 with a correction naming it.

**Size.** Small (one study, two tables) plus the promotion steps.

## 20 — Adding tables to an accepted study

**Motivation.** Item 19 added two flow charts (NCT03637764 Tables 02 and 03) to a study whose Table 01 was already accepted and reviewed. Four gaps:
(a) *Consolidation cannot link a subsidiary table to the main-SoA row it refines.* Matching is by activity name only (exact, then fuzzy). Table 01's 'PK', 'ADA' and 'Tumor Biopsy, Archival Tumor Tissue Collection, Biomarker Blood Draw' match nothing in Tables 02/03 ('Pharmacokinetics', 'Immunogenicity (ADA)', 'Peripheral Blood', …), and Table 02's IMP infusion rows do not match Table 01's 'Isatuximab Administration' / 'Atezolizumab Administration'. All 25 new activities consolidate as `new` (29 → 54 unified). The relation exists only as text: Table 01 source notes pr7/pr8 and `table_metadata.notes`.
(b) *One report per protocol.* The index and the nav bar link only `{NCT}_uncertainty_report.md`; the second session's `NCT03637764_flowcharts_uncertainty_report.md` is published but not linked.
(c) *Gate on a partial re-extraction.* With only the new tables staged, the default baseline reports Table 01 as MISSING (FAIL). The run used a baseline copy without the study (`SOA2USDM_BASELINE`).
(d) *`page_map.py --write` has no study filter.* It writes PAGEMAP.md for every decided study; the one needed was copied out of a temporary folder.
(e) *Row audit on the new tables.* It reads a single label column. On p.24 (three label columns, grey-filled cells) it finds 4 of 10 row bands, reports almost every extracted row as not on page, and reports 'Archival Pre-Treatment Tumor Tissue Collection …' as on page but not extracted. On p.22 it reads footnote lines a/b below the grid as two rows. usdm_data on-page-not-extracted 9 → 12; all three are false positives, checked on the page images.
(f) *Stale nav on unchanged pages.* The index step re-renders an extraction viewer or report page only when its source file is newer, so the Table 01 viewer and the report page kept a nav without Tables 02/03. Forced here by touching the two source files (modification time only, content unchanged).

**Sketch.** (a) An explicit link from a subsidiary table (or its rows) to the main-SoA activity it refines — derived from a resolved cross-reference source_note ('See … Flow Chart') or declared in `table_metadata` — used by consolidate as a refinement relation, not a name match. Related to item 3. (b) Link every `*_uncertainty_report.md` of a protocol. (c) A table filter or an expected-present list in gate. (d) `--study` on page_map.py. (e) Take the label-column count from the extraction's first data column; stop row detection at the footnote block. (f) Re-render the nav whenever the protocol's set of sibling pages changes.

**Size.** (a) medium (schema + consolidate); (b)–(d), (f) small; (e) small to medium.

## 21 — Follow-ups from prompt 3.9.0 (items 11 + 15)

**Motivation.** What the revision leaves outside the prompt text. None blocks the acceptance test.
(a) *CDISC_Pilot T1 abbreviations.* Rule 15g (G2) removes abbreviation annotations; the published T1 still carries ab1 ET / ab2 RT on the header property. Sidecar: remove both and clear the property's `annotation_markers`, naming review item D3 (alternative taken).
(b) *Table-wide notes anchored two ways.* NCT04557384 T3 g1–g4 and NCT03421379 T1 n1 carry the marker on header row 1's `annotation_markers` (row scope); NCT04004988 g1/g2 follow the table-scope convention that §6 now states. Align by sidecar, or leave.
(c) *Gate check 14 on a mixed-version corpus.* Check 14 compares `prompt_version` with the repo prompt, so gating any published table (3.8.1) now FAILs 14 — 47 of 47 in a calibration run on copies. Only matters for calibration; options: an accepted-versions list or an env override.
(d) *Gate check 13 reads one report.* `check_review` takes `reports[0]`; NCT03637764 has two since item 19, the flow-chart report sorts first, and 13 FAILs with data-only D1–D6. Same gap as item 20b.
(e) *Header-bound test since item 19.* `test_header_bound_annotations_match_base_rate[usdm_data/NCT03637764]` fails (3 notes bound to the T02 group rows 'Pharmacokinetics' / 'Immunogenicity (ADA)'), also on the 3.8.1 texts. The bindings follow rule 15b (a note on a group row governs the group); check them against p.22, then add the study to `EXPECTED_HEADER_BOUND`. Together with item 14 these are the 2 failing tests (250 passed).
(f) *Study-level glossary.* With abbreviations no longer annotations, the abbreviation block could be harvested once per study (term → expansion, page) and joined to header values such as ED / ET / UNS — deterministic, no LLM.
(g) *Transpose row-oriented sampling tables after resolve.* NCT04557384 T3 is extracted in printed orientation (rule 15h, H3). A deterministic reshape (sample rows → timepoint columns, mark columns → activities) would give the USDM shape and let its PK / IG rows link to Table 1's PK / IG by name (item 20a).
(h) *Published conventions not backfilled.* The 3.9.0 conventions differ from the published 3.8.1 extractions only in form: synthesised property names and marker prefixes, 3 activity names with a line break next to `/` (NCT02107703 T1, NCT03637764 T1, NCT05324124 T1), 3 tables without the complete grid (NCT03637764 T02/T03, NCT05259917), NCT04004988's 190 empty body cells. Left as is by decision; the gate counts non-empty marks.

**Size.** (a), (b), (e) small, sidecar or test; (c), (d) small, gate; (f) small to medium; (g) medium.

**Status 2026-09-27 (23:43–):** (a) done — CDISC_Pilot T1 corr-004..007 remove ab1/ab2 and clear the ET / RT header cells (the markers sat on the two VISIT grid cells, not on the property row). corr-003 (confirm) stays as history; D3 is decided either way (item 24a). (b)–(h) open.

## 22 — Prompt 3.9.0 acceptance test: rule gaps and conventions

**Motivation.** The blind acceptance run of prompt 3.9.0 (NCT04557384, NCT04677179, CDISC_Pilot, NCT02107703; 10 tables; results in `claude/prompt-3.9.0-ACCEPTANCE-RESULTS.md`, SoA2USDM Project) reversed three published calls and still raised five items that a stated rule decides. Each cause is in the rule text, not in the tools. Discarded, not promoted.
(a) *Several items in one ruled label cell.* CDISC_Pilot T1 'Study drug record / Medications dispensed / Medications returned': one ruled cell, three printed lines, one X per column. Published: three activities with the same marks (Phase 2 decision 2, D1 confirmed). The run made one activity (−2 rows, −22 marks). §5 **Vertically-merged marks** presumes separate rows; §4 **Whitespace** ("join the cell's printed lines") reads as one activity. Candidate: printed lines in one ruled label cell that name distinct items are one activity each, and the cell's marks go on each.
(b) *Prose above the table frame.* NCT04557384 T3 'General Instructions' (published g1–g4, Phase 1 decision 6) were left out as section text (review item D9); in the same run the T1 'Note:' above the frame was emitted (n1). §6 says how to bind a table-wide note, not whether text printed between the table title and the frame belongs to the table. Gate check 12 FAILs on T3 (bindings 4 → 0). Candidate: text printed inside the SoA section between the table title and the frame, or directly below the frame, belongs to the table.
(c) *Follow-up table with mixed columns.* NCT04677179 T4 (ETV, V997, V801, V802) came back `main_soa` (D7); published `track` by sidecar (D11). §2 names "visits after early termination printed as a schedule of their own" as track and a phase every participant passes as main_soa; T4 has both kinds of column. Needs a decision, then one sentence in §2 and the taxonomy.
(d) *Floor applied unevenly.* Raised although the run cites the deciding rule under Recorded: NCT02107703 D2 (§2 track vs main_soa), NCT04677179 D5/D6 (§6 Deduplicate by text, per-tile note variants). Raised where a rule and its exception compete: NCT02107703 D3 (T2 Fulvestrant text over Day 1 and Day 15 of extension cycles; §5 Spanned values vs *Text that names its own columns*). Candidate §7 sentence: a call whose rule is cited under Recorded is closed, do not also list it as open; and one worked case for the exception.
(e) *hierarchical_level of a row that tells no columns apart.* NCT02107703 T1/T2 'Approximate Duration (days)' got level 4 and 'Relative day within a cycle' level 5 (published null / 4, D3 confirmed, group D-b); not listed as a decision. §3 test was read as "carries per-column data". Candidate: add the Duration / Fasting case as the example of `null`.
(f) *Word broken without a hyphen.* NCT04557384 T1 'Inclusion/Exc|lusion criteria', 'Post-|Treatme|nt': §4 **Whitespace** literally gives 'Inclusion/Exc lusion criteria'. The run joined without a space (= published) and raised it (D4). Candidate: a word broken by a narrow column with no hyphen joins with no space.
(g) *Row numbering origin.* NCT04557384 T1/T2: published row 1 = the title band printed inside the frame (first header row 2); the run starts at the first header row. Every row_position shifts by 1; content identical. No rule; decide whether an in-frame title band counts as row 1.
(h) *Symbol inside legend / footnote text.* CDISC_Pilot T1 texts now read 'X = Performed at this visit.', 'Xa = …', 'Xb = …', 'P = …' (published without the symbol). Candidate §6: `annotation_text` excludes the printed marker or symbol and its '='.
(i) *Binding by what a note names, against published T4.* NCT04677179 T4: the V802 title note bound to the V802, V801 and ETV cells (published V802 only, D12 confirmed); ETV-restricted notes (Weeks-row interval note, lipid fasting, endoscopy, colon biopsy) bound to the ETV cells instead of the row; the colon biopsy note split in three. This follows §6 as written. Either narrow the rule (a visit named as context is not a condition on it) or align published T4 by sidecar.
(j) *New open calls outside every rule* (allowed; candidates): header cell over several rows where no covered row matches its content (NCT04557384 D1, '(Day Relative to C1D1)'); instruction notes that list visits (NCT04557384 D8); a redaction box over two ruled rows (NCT04677179 D1); a note naming a visit where the row has no mark (D2); 'at or after V2' as time anchor (D3); line breaks inside `annotation_text` (D8 — §4 Whitespace covers names, header values and `track_label` only). Data equal to published in every case.
(k) *Report claim vs data.* NCT02107703 T1 footnote a: the report says '(± 14 days)' was restored from the render; the data keeps the text-layer '( 14 days)'. CDISC_Pilot: the report quotes the three-line label joined with ' / ' — not verbatim (gate quotes CHECK ×2). Nothing compares report claims with the data.

**Size.** (a)–(j) prompt / taxonomy text: one revision after Kerstin's calls on (a), (b), (c), (g), (i); re-run `tools/redaction/apply_redactions.py`; repeat this acceptance run. (k) small, low value.

**Decisions (Kerstin, 2026-09-27 23:07).** (a) one activity per printed item, marks on each, flat — as published. (b) text between title and frame, or directly below it, belongs to the table — as published. (c) `track` — as published (D11). (g) row 1 = first header row; an in-frame title band is not a row — the corpus majority (45 of 47 tables); NCT04557384 T1/T2 (title band = row 1) stay as published, their sidecars match their own numbering. (i) bind a visit only where the note states a condition on it; a visit named as a reference point is not bound — published D12 stands; the ETV condition notes of NCT04677179 T4 (Weeks-row interval, lipid fasting, endoscopy, colon biopsy) move to the named cells by sidecar. (d), (e), (f), (h) one sentence each. Text: prompt 3.9.1 / taxonomy v8. Open: the T4 sidecar (with 21a); the repeat acceptance run.

**Status 2026-09-27 (23:43–):** (i) sidecar done — NCT04677179 T4 corr-007..021: c1 (Weeks-row interval note) → the V801 and V802 cells of the Weeks row, ETV not bound (reference point); c7 (lipid fasting) and c12 (endoscopy) → the ETV mark; c13 (colon biopsy) split per §6 into c13 (first sentence) and c17 (last sentence) on the ETV mark and c16 (the two middle sentences) on the row. D12 unchanged. Open: the repeat acceptance run.

## 23 — Review page: header rows and the page overlay (follow-ups from the header-row fix)

**Motivation.** The header-row fix (2026-09-27, branch `review-header-rows-2026-09-27`) draws every `schedule_properties` row once in the table pane, with its name, type badge and grid values, as the click target for `selectProp`. Found while reading and testing it; not fixed in that scope.

(a) *Header band ↔ property row on the page image.* The overlay selects and highlights a header band by `b.i+1` (`review_page.py` `showPage` / band `onclick`), i.e. it assumes band index + 1 = `row_position`. `_column_map` already knows the real mapping (`header_bands` {band index: property row}) but it is not put in the model. Measured over the 24 published review pages (175 table-pages, 249 header bands found): 83 bands satisfy the assumption, 166 do not — NCT04677179 T1–T4 (150), NCT01847274 T1–T3 (9), NCT03817853 T1 (3), NCT04320615 T1–T2 (3), NCT05259917 T1 (1). There, clicking a header row in the table highlights the wrong band or none, and clicking a header band selects the wrong property. On the first page of CDISC_Pilot, NCT04557384 and NCT02107703 no header band is found at all (label cell ≠ `property_name`), so selecting a header row highlights nothing on the image. Fix: carry `header_bands` per page into the model and use it both ways.
(b) *Notes tab.* A note bound to a header row is listed as 'header row N*'; the property name would read better (one line, l.750).
(c) *`visit_hdr` / `week_hdr`.* After the fix the page no longer uses them; they only feed `data_cols` (visit row ∪ week row ∪ mark columns). A column present only in another header row would be dropped from the table — none in the 45 published tables (checked: every grid column is in `data_cols`). Candidate: `data_cols` = all grid columns ∪ mark columns, then remove the two fields.
(d) *Sticky header block.* `thead` is sticky as a whole (any number of header rows). With `border-collapse` a 1-px strip of the scrolled body shows between header rows. Cosmetic.
(e) *Spanned header values, stored two ways.* NCT04557384 T1 repeats the epoch value in every column it spans ('Screening', 'Screening', …); NCT04320615 T1 stores 'Baseline' in the first column only and `""` in columns 4–6. The page draws the grid as stored, so the two look different. Not investigated against prompt §3 **Header cells over several rows** / §5 **Spanned values**; check which is the rule and whether published tables differ.

**Size.** (a) small–medium (model + JS, test on NCT04677179). (b)–(d) small. (e) a measurement first.

**Status 2026-09-27 (23:34–):** (a) and (b) done (branch `review-header-bands-2026-09-27`): each page band carries `prop` from `_column_map` (set on all 249 header bands, null elsewhere); the overlay selects and highlights by it in both directions; the Notes tab names the property. Checked on NCT04677179 T1 p.17 (header row 'Weeks from randomization' ↔ its band). Where no header band is recognised on the current page, nothing is highlighted. (c)–(e) open.

## 24 — Follow-ups from the 22i / 21a sidecar session

**Motivation.** Found while writing and rebuilding the NCT04677179 T4 and CDISC_Pilot T1 sidecars (2026-09-27, 23:43–). None fixed in that scope.
(a) *`review_status` reports the first correction naming an item.* `corrections.review_status` uses `setdefault`, so an item decided twice (a confirm, later an alternative) keeps pointing at the first correction. CDISC_Pilot D3: corr-003 (confirm) and corr-004/005 (removal, superseding it) — `review_status` returns corr-003 for D3. Candidate: take the last correction naming the item.
(b) *Fragment check on source-faithful repetition.* `find_adjacent_text_overlaps` (consolidate warning at 3 pairs; `test_annotations_not_fragmented`) counts NCT04677179 c12 ⊃ c13 since the c13 split: the Endoscopy and Colon biopsy comment cells both print 'Recommended at ETV based on judgment of the investigator and after discussion with the sponsor's medical monitor.' (p.45). NCT04677179 now has 3 pairs (019/020, 042/043, 051/052), so the test FAILs and consolidate warns 'likely one note cell fragmented'. Third failing test with items 14 and 21e. Candidate: a per-study list of known source-faithful pairs (as `EXPECTED_HEADER_BOUND`), or skip pairs whose notes are bound to different activities.
(c) *Activity inventory lists row-level notes only.* `activities.json` shows a note under an activity only when it is bound to the activity name. Notes bound to a mark (NCT04677179 T4 c7, c12, c13, c15, c17) or to a header cell are not listed under the activity, so moving a note from row to cell removes it from the inventory. Candidate: list cell-bound notes under their activity, with the column.
(d) *Review page, cell-level bindings.* The Notes tab names a cell binding as 'schedule_cell row R col C' (activity or property rows are named since 23b); the table pane draws note markers only on activity names — no marker on marks, header cells or header-row names (e.g. T4 c1 on the V801 / V802 Weeks cells, c15 on Vital signs × V997, t1 on V802, c2 on Fasting visit). Candidate: name the row and column label in the Notes tab; draw the markers in the table pane.

**Size.** (a) small (code). (b) small (test / consolidate). (c) small to medium. (d) small (review_page.py).

## 25 — Prompt 3.9.1 acceptance test: remaining gaps

**Motivation.** The repeat blind acceptance run (prompt 3.9.1 / taxonomy v8, same 4 studies / 10 tables; results in `claude/prompt-3.9.1-ACCEPTANCE-RESULTS.md`, SoA2USDM Project) fixed 22a, b, c, e and h: non-empty marks identical in 10 of 10 tables, 26 of 28 rule-mapped published calls closed. Not passed. Discarded, not promoted.
(a) *Published table-wide notes break §6.* NCT04557384 T3 (g1–g4 on 'Column heading') and NCT04677179 T1–T3 (t1–t4 on 'Visit number') carry the marker on the property row's `annotation_markers`; §6 (since 3.9.0) says a table-wide `g` note is on no element. The run follows §6, so gate check 12 FAILs on NCT04557384 T3 (4 → 0) and CHECKs on NCT04677179 T1–T3. Candidate: clear the property-row markers by sidecar (`marker_locations` unchanged) after measuring the rest of the corpus.
(b) *V802 note (NCT04677179 T4, published D12).* 'V802 is only for … All other participants will have their final visit at V801 or ETV.' The run bound V802, V801 and ETV (raised D6): §6 "states a condition on it (who attends …)" reads on the second sentence. Candidate: a sentence about participants outside the note's condition is not a condition on the visits it names.
(c) *Split rule with two sentences naming the same cell.* NCT04677179 T4 colon biopsy note (first and last sentence name ETV, middle two the row) kept whole on the ETV mark, not flagged; published c13 / c16 / c17 (22i). §6 says "one sentence". Candidate: every sentence naming the single cell is split off.
(d) *'/' join not applied.* NCT02107703 T1 'Study Entry /Enrollment' and 'Lab/ Diagnostic Tests' (published 'Lab/Diagnostic Tests'), both contrary to §4 **Whitespace**, not flagged; 3.9.0 had the first one right. Candidate: a worked example in §4; a gate check comparing `activity_name` with the §4 join of `cell_text`.
(e) *Floor.* Still raised although a rule decides: NCT02107703 D2 (T2 `track`, §2; also in 3.9.0) and NCT04557384 D3 (ECOG PS level 0 — §4 "a row that carries its own marks is an activity, not a group header" excludes the alternative).
(f) *Header-cell note `location_type`.* The run records notes on header cells as `schedule_property` with `column_position`; published uses `schedule_cell`. `annotation_markers` on the `schedule_grid` cells are identical, so resolve binds the same. The schema says to omit `column_position` for `schedule_property`. Candidate: one sentence in §6.
(g) *Window level.* NCT04677179 T1–T4 'Visit interval tolerance (days)': run null (§3, does not tell columns apart), published 4. Decide; align published or the rule.
(h) *Legend symbols with a superscript.* CDISC_Pilot 'Xa' / 'Xb' cells: run binds only 'a' / 'b', published 'X,a' / 'X,b' (5 cells). No rule.
(i) *Characters.* NCT02107703 T1 footnote a: U+F0B1 (Symbol-font private-use glyph from the text layer) while the report says '±' was restored (22k again). NCT04677179 'anti‑HBc' with U+2011 from the text layer (published '-'). Candidate: §1c sentence mapping PUA symbol glyphs and U+2011; a check for code points U+E000–U+F8FF in extraction text.
(j) *New open calls outside every rule* (allowed; candidates): row numbering in horizontally tiled tables (NCT04677179 D4); row numbers of lines split from one label cell (CDISC_Pilot D1); category parent row numbering (NCT02107703 D1); one table-wide note per paragraph or per block (NCT04557384 D7). 22j calls that came back: 4 of 6.
(k) *Gate quote check.* A report quoting a taxonomy sentence without its markdown backticks counts as unverified (NCT04677179, 'A page break inside ONE printed table is not a continuation'). Candidate: strip markdown from the instruction text before matching.

**Size.** (a) sidecars after a corpus measurement; (b)–(i) one sentence each in prompt / taxonomy, after Kerstin's calls on (a), (b), (f), (g), (h), (i); re-run `tools/redaction/apply_redactions.py`; repeat the acceptance run. (k) small (gate.py).

**Decisions (Kerstin, 2026-09-28 13:16), all as recommended.** Corpus measured first (published `.verified.json`, read-only): 30 notes are recorded on a header row only; 3 follow §6 (NCT03817853 gn1, NCT04004988 g1/g2), about 12 table-wide notes carry the marker on the property row, the rest are genuinely row-bound (printed marker on a header label, or a note about that row).
(a) Keep §6 — a table-wide note binds no element (with the marker on the property row, resolve gives it `property_ids` and consolidate scopes it to that header row, e.g. 'Visit number'; with no element marker it stays table-level). Align published by sidecar, markers cleared from the property row, `marker_locations` unchanged: NCT03421379 T1 n1; NCT04320615 T1, T2 tn1; NCT04557384 T3 g1–g4; NCT04677179 T1 t2, t3, T2 t1–t4, T3 t1, t2, t4. NCT04573309 T2 n1 ('Windows for PK/PD time points …') checked on the page first.
(b) D12 stands. §6 clause: a sentence about the participants the note's condition leaves out is not a condition on the visits it names.
(c) §6 split rule: every sentence that names the single cell becomes its own note bound to that cell; consecutive such sentences stay one note; the rest stays on the row (reproduces c13 / c16 / c17 and c12).
(f) §6 sentence: a note on a header cell is `schedule_cell` with its column. No sidecars (binding goes through `annotation_markers`; published has 153 `schedule_cell`, 23 `schedule_property` + column).
(g) §3 sentence: a window / tolerance row is a qualifier, `hierarchical_level` null. Published: 5 null, 8 with a level → sidecars on NCT04677179 T1–T4, NCT04184622 T1–T2, NCT03548987 T1, NCT05051579 T1 (misc_studies); check whether rows below need their level closed up.
(h) A legend symbol printed with a superscript ('Xa', 'Xb') is one symbol; bind only its own legend entry. §6 sentence; CDISC_Pilot T1 sidecar removes 'X' from the 5 cells and from the X legend's `marker_locations`.
(i) §1c sentence: map symbol-font private-use glyphs (U+F0B1 → '±') and U+2011 → '-'. gate.py: FAIL on any U+E000–U+F8FF in extraction text.
(d), (e), (k) need no call: §4 '/' join example, floor, gate quote check as candidates above.
Order: collections sidecars (a, g, h) · prompt 3.9.2 text (b, c, d, e, f, g, h, i) · gate.py (i, k) · `apply_redactions.py` · repeat acceptance run.

**Status 2026-09-28 (13:19–):** prompt 3.9.2 text (b)–(i) and gate.py (i: check 1c, FAIL on U+E000–U+F8FF; k: markdown stripped before the quote match) done, branch `prompt-3.9.2-2026-09-28`. Taxonomy unchanged (v8). Checks: `apply_redactions.py` 21 spans once, 0 identifiers; Tier-B scan of the added text against the four acceptance studies' published names (one example replaced); gate on the 47 published tables identical before / after; on the 3.9.1 acceptance output check 1c fires on NCT02107703 T1 (U+F0B1) and the quote false positive is gone; pytest 249 passed, 3 failed (14, 21e, 24b). Open: collections sidecars (a, g, h); repeat acceptance run.

**Status 2026-09-28 (sidecar session, 13:30–):** collections sidecars (a), (g), (h) done, branch `sidecars-item25-2026-09-28`. (a) Corpus measured again (published `.verified.json`): 27 notes on a property row only, 3 already on no element. Cleared from the property row, `marker_locations` unchanged, in 9 tables: the listed notes, NCT04573309 T2 n1 (checked on p.17: time-point windows, ECG at 4 hours, order of events — table-wide; printed footnote a stays on the row) and NCT01847274 T2 n1 (p.73, in-frame 'Note:' row across the table, no printed marker; found by the measurement, added by decision). (g) Window rows `hierarchical_level` null in 8 tables; in each the window row was the lowest levelled row, so no other level changed. (h) CDISC_Pilot T1: 'X' removed from the 5 Xa / Xb cells; X legend `marker_locations` 157 → 152. Checks: rebuild 0 errors; 115 files changed in content, 25 timestamp-only (not written); 41 sidecars schema-valid, each re-applied = its `.verified.json`; open review items 0; pytest 249 passed, 3 failed (14, 21e, 24b), no pinned count changed. Gate check 12 binding metric on the updated published tables = the 3.9.1 §6-conform run (NCT04557384 T3 0; NCT04677179 T1–T3 30 / 15 / 15; CDISC_Pilot T1 4).
(l) *'Orphan' warnings on table-wide notes.* Resolve reports a note that is table-wide by §6 (marker on no element) as "no referenced elements — orphan" and sets `resolution_status` to `resolved_with_warnings` — now 9 more tables (the 25a tables), besides NCT03817853 and NCT04004988. Consolidate keeps the note at table level; only the wording and status are wrong. Candidate: resolve / consolidate treat a synthesised `schedule_property` location with no element marker as table scope, not orphan.
(m) *Gate check 12 baseline comes from the raw extraction.* Check 12 derives its binding baseline from `SOA2USDM_CALIB/*_extraction.json`; sidecars never change the raw file. With CALIB = published raw (as in the 3.9.1 kickoff) the corrected tables still FAIL (NCT04557384 T3 4 → 0) and CHECK (NCT04677179 T1–T3). With CALIB = the published `.verified.json` copies renamed to `*_extraction.json`, 0 findings on the 10 acceptance tables. For the repeat acceptance run use CALIB = verified. Candidate: gate prefers `.verified.json` when present.
(n) *Borderline: table-wide or row-bound (Kerstin, 2026-09-28).* The §6 test "names no specific element" decides notes that partly speak about one header row: NCT04573309 T2 n1 (its first sentence is about the time-point windows), NCT04320615 T2 tn1 (assessment window), NCT04677179 T1–T3 t-notes (the population a schedule applies to; cross-references to Table 4 for ETV / V997 — arguably about the visit columns). The source prints no marker; position and wording are the only signals, and they do not settle it. The published record now follows one reading consistently; binding to the header row the first sentence names is also defensible. Watch in the repeat acceptance run and on the first unreviewed protocols: if extractions split on such notes, §6 needs a sharper test (where the note is printed, or a sentence-level split as for cells).

---

2026-08-15, item 5 added 2026-08-17, items 7–8 added 2026-08-22, items 9–10 and 11–14 added 2026-09-27, items 15–19 added 2026-09-27 (review session), item 20 added 2026-09-27 (item-19 session), item 21 added 2026-09-27 (prompt 3.9.0 session), item 22 added 2026-09-27 (3.9.0 acceptance session), item 23 added 2026-09-27 (review-page header-row session), item 24 added 2026-09-27 (22i / 21a sidecar session), item 25 added 2026-09-28 (3.9.1 acceptance session; (l)–(n) from the item-25 sidecar session). Evidence: `collections/usdm_data/protocols/activities.json`, the per-protocol `*_resolved.json` annotation arrays, the NCT04677179 protocol markdown, and the two NCT02107703 Phase 2 pilot extractions.

**Status 2026-09-28 (item-25 sidecar session, 13:30–):** collections sidecars for item 25 (a), (g), (h) on 15 tables in 10 studies; findings 25 (l)–(n).

**Status 2026-09-28 (3.9.1 acceptance session, 00:11–08:10):** prompt 3.9.1 / taxonomy v8 acceptance test run blind on the same 4 studies / 10 tables, output discarded. Not passed: gate 1 FAIL (from published table-wide notes, 25a), 3 rule-decided items raised, 3 rule-decided calls applied contrary. Item 22 (a), (b), (c), (e), (h) hold. Item 25 added.

**Status 2026-09-27 (22i / 21a sidecar session, 23:43–):** NCT04677179 T4 ETV condition notes moved to the cells they name, c13 split (item 22i); CDISC_Pilot T1 ab1/ab2 removed (item 21a). Collections sidecars only; follow-ups in item 24.

**Status 2026-09-27 (review-page header-row session, 23:17–):** review page header rows fixed (`soa2usdm/review_page.py`; each `schedule_properties` row drawn once with its name, type and values, and the click target for the property; the placeholder rows are gone); follow-ups in item 23.

**Status 2026-09-27 (3.9.0 acceptance session, 21:45–23:05):** prompt 3.9.0 / taxonomy v7 acceptance test run blind on 4 studies / 10 tables, output discarded. Not passed: gate 1 FAIL, three published calls reversed, 8 of 28 rule-mapped review items not closed by their rule. Item 22 added.

**Status 2026-09-27 (item-19 session, 20:30–21:10):** item 19 done. NCT03637764 'Pharmacokinetics and Immunogenicity Flow Chart' (pp.22–23) and 'Exploratory Biomarker Flow Chart' (p.24) extracted in a blind session (Opus 5.5, prompt 3.8.1) as subsidiary Tables 02 and 03; gate 0 FAIL; review items D7–D13 confirmed; D1 closed by Table 01 corr-013 (alternative taken). All 13 NCT03637764 review items decided. Collections branch `item19-2026-09-27`. Item 20 added from what the addition showed.

**Status 2026-09-27 (review session, 19:25–20:25):** items 15–19 added from the review of the 112 open sweep-2 review items: 111 decided (106 confirms, 5 alternatives), NCT03637764 T1 D1 left open (item 19). Decisions recorded in the collections sidecars, branch `review-2026-09-27` (15 commits, 3a64b9e..1baeedd).

**Status 2026-09-27 (evening):** items 11–14 added from the sweep-2 backlog. Shipped the same day outside this list: sweep-2 tool fixes (`133cd9e` — row audit `--collection` in both rehearsal scripts; `promote_dryrun.py` per-collection studies, review page and nav re-render; gate check 9 repointed at `source_range` consistency; gate `marks` counts non-empty cells; quotes from the prompt or taxonomy skipped, not unverified) and `220c6fd` (index generator fails loudly without openpyxl or markdown; `index` extra). The sweep-2 builds had published degraded pages for want of those two packages — repaired in collections `12375b6`. Evidence for 11–14: sweep-2 `PHASE1-RESULTS.md`, `PHASE2-RESULTS.md`, `MISC-RESULTS.md` (kept in the SoA2USDM Project).

**Status 2026-09-27:** item 9 shipped (`46dd147`): `table_metadata` is a corrections target (op `set`, no `match`, `table_number` protected). With a sidecar setting NCT04677179 Table 4 back to `track`, the study consolidates to 64 unified activities (102 without). Item 10 open.

**Status 2026-08-22:** items 1, 2, 4, 5 and 6 shipped; item 3 open (substantive, and the natural groundwork for the semantic layer); items 7–8 raised, deferred on purpose. Smaller items closed the same day outside this list: `config.DEFAULT_COLLECTION` pinned to `usdm_data` (sort order had silently skipped the PDF-backed tests once a second collection existed), and the NCT05051579 `proximity`→`synthesized` relabel through its sidecar.

**Status 2026-08-15:** items 1, 2 and 4 shipped; item 3 open. Item 2: `is_redacted` derived at resolve (exception-based — present only when true), carried onto `unified_activities`, filterable in the inventory, per-protocol count in the collection index (6/60, plus NCT05176314 2/24 and NCT05324124 1/20 — genuine redactions, not false positives). Item 4: legend density rule retypes footnote→`legend` at resolve with the extracted type kept in `annotation_type_source` (the 3 NCT04677179 unified legends; 0 false positives over 752 corpus annotations); header-bound detector warns at consolidation — measured base rate 5 across 4 protocols, all reading as deliberate group-scope notes, hence warning not error. The NCT04677179 header-bound misbind suspected above no longer exists in current data (the T4 c11 note was re-bound to the restored Dosing row on 2026-08-15).
