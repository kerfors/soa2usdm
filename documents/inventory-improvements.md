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

---

2026-08-15, item 5 added 2026-08-17, items 7–8 added 2026-08-22, items 9–10 and 11–14 added 2026-09-27, items 15–19 added 2026-09-27 (review session). Evidence: `collections/usdm_data/protocols/activities.json`, the per-protocol `*_resolved.json` annotation arrays, the NCT04677179 protocol markdown, and the two NCT02107703 Phase 2 pilot extractions.

**Status 2026-09-27 (review session, 19:25–20:25):** items 15–19 added from the review of the 112 open sweep-2 review items: 111 decided (106 confirms, 5 alternatives), NCT03637764 T1 D1 left open (item 19). Decisions recorded in the collections sidecars, branch `review-2026-09-27` (15 commits, 3a64b9e..1baeedd).

**Status 2026-09-27 (evening):** items 11–14 added from the sweep-2 backlog. Shipped the same day outside this list: sweep-2 tool fixes (`133cd9e` — row audit `--collection` in both rehearsal scripts; `promote_dryrun.py` per-collection studies, review page and nav re-render; gate check 9 repointed at `source_range` consistency; gate `marks` counts non-empty cells; quotes from the prompt or taxonomy skipped, not unverified) and `220c6fd` (index generator fails loudly without openpyxl or markdown; `index` extra). The sweep-2 builds had published degraded pages for want of those two packages — repaired in collections `12375b6`. Evidence for 11–14: sweep-2 `PHASE1-RESULTS.md`, `PHASE2-RESULTS.md`, `MISC-RESULTS.md` (kept in the SoA2USDM Project).

**Status 2026-09-27:** item 9 shipped (`46dd147`): `table_metadata` is a corrections target (op `set`, no `match`, `table_number` protected). With a sidecar setting NCT04677179 Table 4 back to `track`, the study consolidates to 64 unified activities (102 without). Item 10 open.

**Status 2026-08-22:** items 1, 2, 4, 5 and 6 shipped; item 3 open (substantive, and the natural groundwork for the semantic layer); items 7–8 raised, deferred on purpose. Smaller items closed the same day outside this list: `config.DEFAULT_COLLECTION` pinned to `usdm_data` (sort order had silently skipped the PDF-backed tests once a second collection existed), and the NCT05051579 `proximity`→`synthesized` relabel through its sidecar.

**Status 2026-08-15:** items 1, 2 and 4 shipped; item 3 open. Item 2: `is_redacted` derived at resolve (exception-based — present only when true), carried onto `unified_activities`, filterable in the inventory, per-protocol count in the collection index (6/60, plus NCT05176314 2/24 and NCT05324124 1/20 — genuine redactions, not false positives). Item 4: legend density rule retypes footnote→`legend` at resolve with the extracted type kept in `annotation_type_source` (the 3 NCT04677179 unified legends; 0 false positives over 752 corpus annotations); header-bound detector warns at consolidation — measured base rate 5 across 4 protocols, all reading as deliberate group-scope notes, hence warning not error. The NCT04677179 header-bound misbind suspected above no longer exists in current data (the T4 c11 note was re-bound to the restored Dosing row on 2026-08-15).
