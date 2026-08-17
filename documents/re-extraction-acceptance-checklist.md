# Re-extraction Acceptance Checklist — usdm_data, prompt v3.6.0

Criteria the re-extracted corpus is judged against. Written **before** any re-extraction, so a
delta can be classified rather than rationalised. Every item is derived from work already done:
the 21 uncertainty reports, the 69 applied corrections, the row audit, and the QC decisions
recorded across earlier sessions.

**How to use it.** A fresh extraction is not accepted because it looks good. It is accepted when
every difference from the baseline below falls into one of three buckets:

| Bucket | Meaning | Action |
|---|---|---|
| **Expected delta** | A v3.6.0 rule mandates the new behaviour | Confirm the rule actually applies, then accept |
| **Regression** | Baseline established something the new output loses or contradicts | Do not promote; investigate |
| **New finding** | Neither the baseline nor v3.6.0 predicted it | Human review before promotion |

Anything that cannot be placed in a bucket blocks promotion of that table.

---

## 1. Scope

22 studies, 45 tables. NCT03523273 is excluded — its posted protocol contains no SoA table
(`excluded_reason` in the manifest). CDISC_Pilot has no uncertainty report; its criteria are
count-based only.

## 2. Machine baseline — authoritative counts

These are computed from the corpus, not asserted by any model. Where a mined claim below states a
count that disagrees with this table, **this table wins**.

| Study | T | type | pages | acts | marks | props | grid | ann | fn | sn | ab | lg |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CDISC_Pilot | 1 | main_soa | 53-53 | 28 | 71 | 2 | 16 | 6 | 2 | 0 | 2 | 2 |
| CDISC_Pilot | 2 | continuation | 54-54 | 28 | 68 | 2 | 14 | 6 | 1 | 0 | 4 | 1 |
| NCT01847274 | 1 | main_soa | 63-66 | 28 | 90 | 2 | 16 | 28 | 28 | 0 | 0 | 0 |
| NCT01847274 | 2 | track | 72-73 | 17 | 79 | 3 | 18 | 13 | 13 | 0 | 0 | 0 |
| NCT01847274 | 3 | track | 78-78 | 15 | 40 | 3 | 12 | 15 | 15 | 0 | 0 | 0 |
| NCT02107703 | 1 | main_soa | 73-77 | 38 | 108 | 5 | 38 | 17 | 16 | 1 | 0 | 0 |
| NCT02107703 | 2 | track | 78-78 | 4 | 6 | 5 | 14 | 3 | 3 | 0 | 0 | 0 |
| NCT02291289 | 1 | main_soa | 169-171 | 21 | 56 | 3 | 14 | 20 | 20 | 0 | 0 | 0 |
| NCT02291289 | 2 | track | 174-176 | 25 | 47 | 2 | 8 | 24 | 24 | 0 | 0 | 0 |
| NCT02291289 | 3 | track | 179-181 | 24 | 39 | 2 | 8 | 21 | 21 | 0 | 0 | 0 |
| NCT02291289 | 4 | track | 184-185 | 22 | 40 | 2 | 8 | 21 | 21 | 0 | 0 | 0 |
| NCT02291289 | 5 | track | 189-191 | 26 | 45 | 2 | 8 | 23 | 23 | 0 | 0 | 0 |
| NCT03283098 | 1 | main_soa | 32-33 | 14 | 94 | 1 | 20 | 9 | 9 | 0 | 0 | 0 |
| NCT03283098 | 2 | domain | 34-35 | 14 | 65 | 1 | 20 | 8 | 8 | 0 | 0 | 0 |
| NCT03283098 | 3 | domain | 36-36 | 7 | 23 | 1 | 20 | 1 | 1 | 0 | 0 | 0 |
| NCT03402841 | 1 | main_soa | 40-41 | 18 | 19 | 1 | 2 | 8 | 8 | 0 | 0 | 0 |
| NCT03402841 | 2 | main_soa | 42-44 | 15 | 45 | 3 | 17 | 11 | 11 | 0 | 0 | 0 |
| NCT03421379 | 1 | main_soa | 11-18 | 36 | 80 | 2 | 15 | 27 | 25 | 2 | 0 | 0 |
| NCT03548935 | 1 | main_soa | 8-13 | 78 | 428 | 4 | 100 | 37 | 7 | 30 | 0 | 0 |
| NCT03548987 | 1 | main_soa | 8-11 | 69 | 378 | 4 | 100 | 33 | 4 | 29 | 0 | 0 |
| NCT03637764 | 1 | main_soa | 18-21 | 29 | 159 | 3 | 30 | 11 | 4 | 7 | 0 | 0 |
| NCT03693430 | 1 | main_soa | 9-12 | 63 | 470 | 4 | 136 | 30 | 4 | 26 | 0 | 0 |
| NCT03817853 | 1 | main_soa | 100-102 | 27 | 89 | 4 | 31 | 29 | 28 | 0 | 1 | 0 |
| NCT04004988 | 1 | main_soa | 10-10 | 17 | 70 | 2 | 27 | 12 | 12 | 0 | 0 | 0 |
| NCT04004988 | 2 | continuation | 11-11 | 3 | 20 | 2 | 27 | 9 | 8 | 0 | 1 | 0 |
| NCT04184622 | 1 | main_soa | 18-21 | 54 | 414 | 5 | 93 | 27 | 27 | 0 | 0 | 0 |
| NCT04184622 | 2 | track | 22-24 | 39 | 311 | 5 | 74 | 18 | 18 | 0 | 0 | 0 |
| NCT04320615 | 1 | main_soa | 77-80 | 28 | 56 | 3 | 11 | 21 | 21 | 0 | 0 | 0 |
| NCT04320615 | 2 | main_soa | 81-83 | 17 | 220 | 2 | 53 | 12 | 12 | 0 | 0 | 0 |
| NCT04320615 | 3 | main_soa | 84-85 | 14 | 32 | 2 | 4 | 8 | 8 | 0 | 0 | 0 |
| NCT04557384 | 1 | main_soa | 16-22 | 25 | 234 | 5 | 70 | 26 | 1 | 25 | 0 | 0 |
| NCT04557384 | 2 | track | 23-23 | 3 | 3 | 2 | 4 | 4 | 1 | 3 | 0 | 0 |
| NCT04557384 | 3 | reference | 24-24 | 15 | 20 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| NCT04573309 | 1 | main_soa | 14-16 | 43 | 212 | 2 | 46 | 24 | 24 | 0 | 0 | 0 |
| NCT04573309 | 2 | subsidiary | 17-17 | 1 | 8 | 1 | 11 | 3 | 3 | 0 | 0 | 0 |
| NCT04677179 | 1 | main_soa | 17-23 | 59 | 158 | 5 | 35 | 31 | 31 | 0 | 0 | 0 |
| NCT04677179 | 2 | track | 24-32 | 36 | 180 | 5 | 82 | 14 | 14 | 0 | 0 | 0 |
| NCT04677179 | 3 | track | 33-42 | 36 | 211 | 5 | 82 | 14 | 14 | 0 | 0 | 0 |
| NCT04677179 | 4 | track | 43-46 | 34 | 54 | 5 | 8 | 15 | 15 | 0 | 0 | 0 |
| NCT04730349 | 1 | main_soa | 28-30 | 21 | 17 | 1 | 1 | 18 | 18 | 0 | 0 | 0 |
| NCT04730349 | 2 | main_soa | 31-38 | 27 | 84 | 2 | 12 | 23 | 21 | 2 | 0 | 0 |
| NCT04730349 | 3 | main_soa | 39-42 | 19 | 51 | 1 | 4 | 15 | 13 | 2 | 0 | 0 |
| NCT05176314 | 1 | main_soa | 10-11 | 24 | 122 | 2 | 42 | 8 | 7 | 0 | 1 | 0 |
| NCT05259917 | 1 | main_soa | 17-18 | 24 | 61 | 2 | 9 | 19 | 19 | 0 | 0 | 0 |
| NCT05324124 | 1 | main_soa | 9-12 | 20 | 77 | 3 | 41 | 9 | 7 | 1 | 1 | 0 |
| **TOTAL** | **45** | | | **1205** | **5154** | **124** | **1403** | **731** | **590** | **128** | **10** | **3** |

A drop in `marks` is the single most serious signal — marks are the data. A drop in `acts` means a
row was lost. Increases are not automatically good: v3.6.0 adds `source_note` splitting, so `sn`
rising while `fn` falls is expected in specific studies (§4), whereas `marks` rising needs a page.

## 3. Row-audit baseline

`soa2usdm-row-audit` compares extracted activity labels against what the pages actually print —
the one completeness check that cannot be built from the JSON alone. Baseline, re-run 2026-08-17
and matching the value recorded when the module shipped:

```
22/22 protocols, 45 tables, 33 on-page-not-extracted, 88 extracted-not-on-page
```

23 of the 33 are NCT04677179's four section-header conventions, omitted consistently including in
Table 1 — convention, not loss. **Acceptance: 33 must not rise.** Any new on-page-not-extracted
entry is a dropped row until proven otherwise.

Blind spots the audit cannot cover, so they need human eyes: no text layer at all on the table
pages (NCT02291289, NCT03693430, NCT04557384), rotated text (NCT03548935, NCT03548987), and
NCT04320615 T3 whose captions do not discriminate so it gets no pages assigned.

## 4. Corrections disposition — all 69, predicted before the sweep

Confirming a prediction is review. Inspecting an unexplained diff is archaeology. Each correction
is predicted **retired** (v3.6.0 produces it natively), **still needed** (must be re-authored), or
**contingent** (retires only if a specific invariant holds).

### 4.1 Family A — NCT02107703 Protocol Reference column · 54 corrections · predicted RETIRED

T1 has 49 (19 `annotations add` creating source_notes pr1–pr19, 30 `activities set` attaching
markers); T2 has 5 (2 add pr1–pr2, 3 set). All carry the same reason: the Protocol Reference
column was *omitted from the raw extraction* and captured afterwards as `source_note` annotations
deduplicated by text.

v3.6.0 §6 now mandates exactly this, down to the marker naming:

> A `source_note` is a cross-reference to elsewhere in the protocol — a dedicated reference column
> … emit each as a `source_note` deduplicated by text (one annotation per distinct reference), and
> add a synthesised marker (`pr1`, `pr2`, …) to every citing activity's `annotation_markers`

**This is the single biggest test of the sweep's premise.** If re-extracting NCT02107703 produces
pr1–pr19 natively with the same bindings, the prompt work is validated and 78% of all corrections
retire. If it does not, that is the most important finding of the pilot and the sweep's rationale
needs revisiting before the remaining studies run.

Check: T1 has ≥19 `source_note` annotations; each cites the same activity rows as the current
`*.verified.json`; no duplicate `source_note` texts.

### 4.2 Family B — NCT01847274 Table 03 undefined footnotes · 12 corrections · predicted STILL NEEDED

All 12 are `annotations set` recording **human research verdicts** reached by reading §7.4 of the
full protocol: 7 hypotheses confirmed against the Procedures-by-Visit narrative, 3 retained as
unconfirmed hypotheses, 1 unresolved (marker 4, no candidate), 1 flagged as a source-internal
contradiction (marker 10, RECIST cadence — Table 7 fn22 says every 6 cycles post-C14, §7.4.2 says
every 3).

No re-extraction can reproduce these: they required corroborating prose outside the SoA pages and
a clinical judgement. v3.6.0 §6 will correctly emit the markers with text stating the definition
is not printed — which is the *right* extraction output — but the adjudicated verdicts live only
in the corrections sidecar. **Re-author all 12.**

Good news on cost: these match on `annotation_marker`, not `row_position`, so they survive
re-extraction as long as the marker names stay 4–15. Re-authoring is mechanical.

### 4.3 Family C — NCT04677179 Table 04 Dosing row · 3 corrections · CONTINGENT

corr-001 adds the never-extracted `Dosing` row (found by the row audit on doc p.46), corr-002
removes footnote c11 from the wrong row, corr-003 re-binds c11 to the restored row.

Retires **only if** the fresh extraction includes `Dosing` natively with c11 bound to it. That is
an invariant to verify, never an assumption — this row has been missed once already.

### 4.4 The duplication trap — read this before re-running the pipeline

`corrections.apply_corrections` implements `op: add` as a bare append:

```python
if op == "add":
    arr.append(c["set"])
```

No match key, no dedup. So if a fresh extraction produces the pr1–pr19 source_notes natively **and
the old corrections file is still in place**, ApplyCorrections silently appends 21 duplicate
annotations to NCT02107703 and 1 duplicate activity row to NCT04677179 T4. Nothing errors.

**Rule: retire or empty each corrections sidecar before the rebuilt pipeline runs over a
re-extracted table.** Affected: the 21 `add` ops in Family A and corr-001 in Family C.

Match-key stability, for re-authoring cost:

| Match key | Count | Survives re-extraction? |
|---|---:|---|
| `annotation_marker` | 13 | Yes, if marker names are stable |
| `row_position` | 34 | **No** — positions shift |
| none (`op: add`) | 22 | N/A — appends blindly, see trap above |

## 5. Adjudicated findings — must NOT be re-litigated

Each of these was investigated and closed in an earlier session. A fresh extraction that
"corrects" one is producing a regression, not an improvement.

### 5.1 Documented non-defects

| Item | Study | Why it looks wrong | Why it is right |
|---|---|---|---|
| `xannot-023` | NCT04677179 | Identical PK note text on two rows reads as a cross-table binding conflict | The note genuinely prints twice — on *PK samples* and on the redacted *CCI* row below it, confirmed on doc p.22. A detector limitation, not a data defect. Still the only cross-table conflict in the corpus. |
| 4 section headers | NCT04677179 | Row audit reports them as on-page-not-extracted (23 of the 33) | *Patient-Reported Outcomes (Electronic)*, *Clinician-Administered Questionnaires (Paper)*, *Laboratory Tests and Sample Collections*, *Stool Samples* are omitted consistently including in T1 — a sponsor convention, not loss |
| `xannot-035` | NCT04677179 | Reported orphaned | T4 c1 is `schedule_property` scope and the consolidator deliberately does not expand property refs to columns. Benign. |
| ±3 vs ±5 window | NCT03693430 | V33 visit window inconsistent | **Confirmed source defect.** Both values legibly printed on the repeated header — ±3 on doc p9, ±5 on doc p11, body never restates. No tiebreaker, so first occurrence (±3) stands. Not an extraction error. |
| soa.pdf p.5 flow chart | NCT03637764 | Row audit keeps reporting the page | **Out of scope by decision.** Rows are sample types, cells carry sample IDs and dosing-relative windows ("SOI", "EOI +30 min"), not marks — study timing, which the three-layer model does not carry. |

### 5.2 Restorations that must survive

Rows and marks recovered by earlier investigation. A fresh extraction that drops any of these has
repeated a defect the corpus already paid to find.

| Restoration | Study | What must be present |
|---|---|---|
| Genetics sample row | NCT04677179 | Present in T2, T3 **and** T4, positioned after *Flow cytometry panel*. Carries **no marks** (sampled once at screening), so `schedule_matrix` is unaffected — its absence is invisible to every count-based check. |
| Table 4 doc p.43 | NCT04677179 | 14 rows (Concomitant medications, Adverse events, Review MMS, Tobacco use, Physical Evaluation, Weight, Vital signs, Symptom-directed PE, CCI, 12-lead ECG, Patient Diary (Electronic), Diary return, IBDQ, PGI-C) and their **26 ETV/V997/V801/V802 marks**. This whole page was never extracted originally. |
| Table 4 Dosing row | NCT04677179 | doc p.46, under *Randomization and Dosing*, carrying c11 |
| V10–V19 marks | NCT04677179 | T2/T3 recurring rows appear in **both** horizontal tiles; the extractor originally kept only V20–V29. +34 / +38 cells. v3.6.0 §5 guards this ("union rows across tiles") — verify it holds. |
| 12 annotation over-merges | NCT04677179 | Longest contiguous duplicated sentence run within one unified annotation must stay at **0** chars (was 145). Gate threshold 100; NCT02291289 at 75 and NCT04557384 at 52 are legitimate list content. |

### 5.3 Known-unrecoverable source content

Do not expect these to improve, and treat any new "resolution" of them as fabrication:

- **NCT04730349** — redaction boxes may hide rows; footnote `c` table-scope unconfirmed.
- **NCT05176314**, **NCT05324124** — fully redacted CCI activity rows.
- **NCT01847274** T3 — markers 4–15 have no printed definitions (see §4.2).
- **NCT04677179** — 4 corrupt abbreviation-key fragments (T1 c23, T2/T3 c13, T4 c12) from the
  multi-column footnote block; left as found by decision.
- **NCT04677179** T1 `c21_2` reads "Addition alc. Difficile testing" where doc p.23 reads
  "Additional *C. difficile* testing" — an italic run broke word segmentation. If v3.6.0 §1c
  glyph reconstruction fixes this, that is a genuine improvement; record it as one.

### 5.4 The binding gotcha that cost a silent revision

`resolve` attaches an annotation to an activity through the **row's `annotation_markers` string**,
not through `marker_locations`. Correcting `marker_locations` alone leaves the raw JSON looking
right while `referenced_xacts` still shows the old activity, and nothing fails anywhere. v3.6.0 §6
states the rule; a detector for the mismatch now ships in `resolve.py`. **Run it on every
re-extracted table** — this failure is invisible to inspection.

## 6. Page-number convention

Three different page numbers are in play and mixing them has already caused one confusing
exchange. State which is meant, every time:

- **PDF page** — index into the sliced `_soa.pdf`
- **doc page** — index into the full protocol PDF; what extractions and reports use
- **printed footer page** — what a human reads on the page. For NCT04677179 this runs **one lower**
  than the doc page. It is per-protocol and not derivable.

## 7. Per-study criteria

Mined from each study's uncertainty report by seven parallel agents, then mechanically verified:
**420 of 422 evidence quotes are verbatim** in the source report or extraction JSON. The two that
are not are marked ⚠️ — in both cases the underlying claim checks out but the quote was composed,
so treat the quote as a pointer, not as evidence.

Counts stated here are superseded by §2 wherever they disagree.

Legend: **INV** invariant to reproduce · **SRC** source defect to flag, never repair ·
**JDG** adjudicated judgement — a different call needs review · **Δ** expected v3.6.0 change.

### CDISC_Pilot

2 table(s): T1 main_soa pp53-53 (28a/71m/6n), T2 continuation pp54-54 (28a/68m/6n)

_No uncertainty report exists for this study; criteria are the §2 counts and the §3 row audit only._

### NCT01847274

3 table(s): T1 main_soa pp63-66 (28a/90m/28n), T2 track pp72-73 (17a/79m/13n), T3 track pp78-78 (15a/40m/15n)

- **INV** _all_ The study yields exactly three SoA tables (Table 7 main study, Table 8 food-effect sub-study, Table 9 extended visit cycle).
  - check: Exactly three files NCT01847274_Table_01/02/03_extraction.json exist; no Table_04.
- **INV** _1_ Table 01 is table_type main_soa, page_start 63 / page_end 66, with 28 activities, 90 activity_schedule cells and 28 annotations (markers 1-28).
  - check: Table_01: table_metadata.table_type == 'main_soa'; page_start==63, page_end==66; len(activities)==28; len(activity_schedule)==90; len(annotations)==28 and the annotation_marker set == {'1'..'28'}.
- **INV** _2_ Table 02 is table_type track with track_label 'Food Effect Sub-Study', pages 72-73, 17 activities, 79 cells, 13 annotations.
  - check: Table_02: table_type=='track'; track_label=='Food Effect Sub-Study'; page_start==72, page_end==73; len(activities)==17; len(activity_schedule)==79; len(annotations)==13.
- **INV** _3_ Table 03 is table_type track with track_label 'Extended Visit Cycle', single page 78, 15 activities, 40 cells.
  - check: Table_03: table_type=='track'; track_label=='Extended Visit Cycle'; page_start==page_end==78; len(activities)==15; len(activity_schedule)==40.
- **INV** _all_ The SoA page span for the study is document pages 63-78 (regenerated 7-page excerpt covering Table 7 pp63-66, Table 8 pp72-73, Table 9 p78).
  - check: min(page_start) across the three tables == 63 and max(page_end) == 78.
- **INV** _1_ Table 7's Bone marrow aspirate and biopsy row carries a single X merged across on-study columns 3-10, distributed with source_range '3:10' and marker 28.
  - check: Table_01: the activity whose activity_name is 'Bone marrow aspirate and biopsy' has activity_schedule entries at column_position 3..10, each with source_range '3:10' and annotation_markers containing '28'.
- **INV** _2_ Table 8's Bone marrow row is a single X merged across columns 3-9, source_range '3:9', marker 15.
  - check: Table_02: bone marrow activity has 7 activity_schedule entries at column_position 3..9, each source_range '3:9', annotation_markers '15'.
- **INV** _3_ Table 9's Bone marrow row is a single X merged across all data columns 2-6, source_range '2:6', marker 15.
  - check: Table_03: the 'Bone marrow aspirate and biopsy' row (row_position 15 in the existing extraction) has 5 activity_schedule entries at column_position 2..6, each source_range '2:6' and annotation_markers '15'.
- **INV** _1_ Table 7 header markers: 1 scopes the whole Cycle header row; 2 sits on the 'Subsequent Cycles' header cell (column 8); 3 sits on the Cycle 1 Day 1 header cell (column 3).
  - check: Table_01: schedule_properties row 1 annotation_markers contains '1'; schedule_grid cell (row 1, column 8, cell_value 'Subsequent Cycles') annotation_markers=='2'; schedule_grid cell (row 2, column 3) annotation_markers=='3'.
- **INV** _1_ Two elements in Table 7 carry split (two-footnote) markers: the Serum CA-125 activity name carries '13,14' and the PK Cycle-1 Day-1 cell carries '19,20'.
  - check: Table_01: the activity named 'Serum CA-125' has annotation_markers '13,14'; one PK activity_schedule cell has annotation_markers '19,20'; annotations 13, 14, 19, 20 each have a marker_location on those elements.
- **INV** _all_ The abbreviation blocks in each table footer are NOT emitted as annotations, because none of their terms carries an in-grid marker.
  - check: For all three tables: no annotation has annotation_type == 'abbreviation' (existing files are 100% 'footnote').
- **INV** _3_ Table 9's three 'Subsequent Cycles' columns are distinguished only by the Location header row (In Clinic / Site Staff Telephone / Local Clinic or In-Home), which is therefore a level-bearing header row.
  - check: Table_03: three schedule_properties exist (Cycle, Day, Location); the Location row has distinct cell_values across columns 2,3,4 while the Cycle row repeats 'Subsequent Cycles'.
- **INV** _3_ Markers 4-15 are retained on the Table 9 cells/activity names even though their footnote text is not printed.
  - check: Table_03: annotations exist with annotation_marker '4' through '15', each having >=1 marker_location, and the corresponding rows/cells carry those markers in annotation_markers.
- **SRC** _3_ Table 9 prints only footnotes 1-3, but its body references markers 4-15. Footnotes 4-15 are simply absent from the source page.
  - expected handling: Markers 4-15 must be transcribed where printed, and each annotation_text must state plainly that the definition is not printed in the source. A probable Table 7 cross-reference may be added only as a clearly-labelled hypothesis (prompt v3.6.0 §6 'Markers referenced but not defined'). A fresh extraction that silently supplies Table 7 footnote text as if printed in Table 9 is a fabrication.
- **SRC** _3_ Table 9 has its own footnote numbering: its printed 1-3 are the Location-column definitions and are unrelated to Table 7's footnotes 1-3.
  - expected handling: Table 9 annotations 1-3 must carry the Location-column definitions, NOT Table 7's footnote 1-3 text. Cross-table marker reuse must not be assumed.
- **SRC** _3_ Marker 4 (Vital signs cell in the local-clinic/in-home column) has no confident Table 7 equivalent; clinical review could not resolve it.
  - expected handling: Annotation 4 must remain honestly labelled as undefined with no asserted content and no invented Table 7 mapping. Its marker_location must stay on the Vital signs cell in the local-clinic/in-home column (row 2, column 4 in the existing extraction).
- **SRC** _3_ Marker 10 (RECIST) sits on a source-internal contradiction: Table 7 footnote 22 says post-Cycle-14 imaging every 6 cycles while Section 7.4.2 says every 3 cycles.
  - expected handling: Neither imaging cadence may be asserted as the definition. The annotation must remain flagged/unasserted; a fresh extraction that picks one cadence has resolved a source contradiction it cannot resolve.
- **SRC** _all_ The originally prepared _soa.pdf excerpt (doc pp 62-71) was the wrong slice: it contained Table 7 plus Section 7.2 narrative and omitted Tables 8 and 9 entirely.
  - expected handling: The re-extraction must run against the regenerated 7-page excerpt (Table 7 pp63-66, Table 8 pp72-73, Table 9 p78). If the new run produces only one table, the stale excerpt was used - that is an input defect, not an extraction finding.
- **JDG** _1_ Table 7 header row 1 was typed property_type 'cycle' rather than 'epoch'.
  - rationale: The row is labeled 'Cycle' but its values mix cycles with Screening / Discontinuation / Post-Treatment phases; 'epoch' was noted as defensible. A fresh extraction choosing 'epoch' is a defensible alternative, not automatically an improvement - route to human review.
- **JDG** _2_ Table 8's continuation page (doc p73) re-labels the header footnotes as 12 and 13 with text identical to 1 and 2; markers 12 and 13 are deliberately NOT emitted because the header is encoded once under markers 1 and 2.
  - rationale: Deduplication of a reprinted header on a continuation page. Page-73 body markers 14 and 15 ARE kept. A fresh extraction that emits 12 and 13 has duplicated the header footnotes.
- **JDG** _2_ Table 8 classified as track (separate Food-Effect sub-study population) with track_label 'Food Effect Sub-Study', not subsidiary or a second main_soa.
  - rationale: It is a genuinely separate population/timeline. Prompt v3.6.0 §2 requires the reasoning to be recorded in table_metadata.notes as well as the report.
- **JDG** _3_ Table 9 classified as track (extended-visit-cycle variant) with track_label 'Extended Visit Cycle'.
  - rationale: It is the extended-visit-cycle variant of the Main Study timeline, modelled as its own track rather than a continuation or subsidiary of Table 7.
- **JDG** _3_ Specific probable Table 7 mappings were assigned as labelled hypotheses for markers 5-15 (5~T7 fn10 SAEs, 6~fn12 CBC, 7~fn13 + 8~fn14 CA-125, 9~fn16 ECG, 10~fn22 RECIST, 11~fn24 PROs, 12~fn25, 13~fn26, 14~fn27, 15~fn28).
  - rationale: These are already-adjudicated hypotheses, seven of which (5, 9, 11, 12, 13, 14, 15) were subsequently confirmed against the Section 7.4 narrative by clinical review on 2026-08-15. A fresh extraction proposing different mappings needs human review against that review record.
- **JDG** _3_ Markers 6, 7, 8 remain 'hypothesis retained, unconfirmed' after clinical review; their hypothesised Table 7 content is not restated by Section 7.4.
  - rationale: Section 7.4 does not restate these on-treatment lab rules, and marker 7's Table 7 fn13 content is partly screening/Cycle-1-specific. These must stay labelled as unconfirmed hypotheses, not promoted to asserted definitions.
- **JDG** _2_ Table 8 modelled with a three-level header: Period -> Cycle -> Day, with the 'Cycle' group cell (cols 5-7) carrying marker 1.
  - rationale: The source stacks Period / Cycle / Day bands; all three were given hierarchical levels because each is needed to tell columns apart.
- **JDG** _all_ Marks were placed from pdftotext -bbox coordinates treated as authoritative, cross-checked against every rendered page.
  - rationale: These are text-layer tables; the bbox matrix is the mechanical verification surface (prompt v3.6.0 §1b). A fresh extraction should use the same method, and any cell where the mechanical matrix disagrees with the visual read must be reported.
- **Δ** No activity in any of the three tables carries a source_page value (all null in the v3.0.2-v3.1.0 output).
  - expect: Every activity should now carry source_page, and the report must state activity rows per page across the declared page range, calling out any page in the range that contributed none.
  - rule: §4 source_page and page-coverage check; §7 'activity rows per page across the declared page range'
- **Δ** No method provenance fields are present anywhere (annotation_text_source, marker_locations[].method, activity_name_source.method/indentation_method, cell method, structure_method are all absent).
  - expect: v3.6.0 records method exception-based. For these text-layer tables most values stay default (absent), but any non-default method must now be recorded and listed one line each in the report.
  - rule: §1e Method provenance; §7 'Method provenance: every non-default method recorded'
- **Δ** Table 7 header markers 2 and 3 are recorded with location_type 'schedule_property' plus a column_position (rows 1 and 2, columns 8 and 3).
  - expect: Per-column header footnotes should now be recorded as schedule_cell locations on that column's schedule_grid cell. The binding annotation_markers on the grid cells (row1/col8 -> '2', row2/col3 -> '3') must remain unchanged either way.
  - rule: §6 'Header-cell footnotes (per-timepoint)' - encode on that column's schedule_grid cell, not the schedule_property row
- **Δ** Table 8 and Table 9 are typed 'track'; the reasoning currently lives mainly in the uncertainty report.
  - expect: The track/main_soa reasoning must now also be recorded in table_metadata.notes for every non-obvious table_type. (Table 02/03 notes already carry partial reasoning; expect it to be explicit about the classification.)
  - rule: §2 'record the reasoning in `table_metadata.notes` as well as the report'
- **Δ** Table 9 markers 4 and 10 are recorded with concrete marker_locations and hedged annotation_text.
  - expect: v3.6.0 explicitly permits location_type 'unresolved' when a marker's target cannot be determined. Marker 4's target cell IS determined (Vital signs, local-clinic/in-home column), so it should stay a schedule_cell location; a switch to 'unresolved' would be a change in modelling, not a fix, and should be reviewed.
  - rule: §1e '`unresolved` is an allowed answer' / 'Never invent a scope, a target, or a location'
- **Δ** The report describes the abbreviation blocks as 'not captured' with a rationale.
  - expect: v3.6.0 now forbids emitting an unreferenced abbreviation/legend list by rule, so the same output is expected - but the omission is now rule-driven rather than a judgement call.
  - rule: §6 'Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker'

_Notes:_ Discrepancy worth carrying into acceptance: the report says Table 03 has '14 footnotes', but NCT01847274_Table_03_extraction.json contains 15 annotations with markers '1'..'15' (markers 1-3 printed + 4-15 undefined). I treated 15 annotations as the invariant and did NOT assert 14. The 2026-08-15 clinical-review resolution (corrections sidecar NCT01847274_Table_03_corrections.json) was applied to *_extraction.verified.json only; the raw *_extraction.json is unchanged, so the acceptance checks above target the raw file.

### NCT02107703

2 table(s): T1 main_soa pp73-77 (38a/108m/17n), T2 track pp78-78 (4a/6m/3n)

- **INV** _all_ The study yields exactly two SoA tables.
  - check: Exactly NCT02107703_Table_01_extraction.json and _Table_02_extraction.json exist.
- **INV** _1_ Table 01 is main_soa with 38 activity rows, 8 leaf data columns, 25 header-grid cells, 108 activity-by-column marks and 17 footnotes a-q.
  - check: Table_01: table_type=='main_soa'; len(activities)==38; distinct column_position count in activity_schedule ==8; len(activity_schedule)==108; len(annotations)==17 with annotation_marker set {'a'..'q'}.
- **INV** _1_ The 38 rows decompose as 7 category header rows + 3 category-level standalone activities + 28 procedures.
  - check: Table_01: 10 activities have activity_name_source.indentation_level==0 (7 mark-free category headers + Survival Information, Adverse Event Collection/CTCAE Grading, Concomitant Medications which carry marks); 28 have indentation_level==1.
- **INV** _2_ Table 02 is table_type track with track_label 'Extension period', 4 activity rows, 3 leaf columns, 3 footnotes a-c.
  - check: Table_02: table_type=='track'; track_label=='Extension period'; len(activities)==4; 3 distinct column positions; len(annotations)==3 markers a,b,c.
- **INV** _all_ The SoA excerpt is complete - no _soa.pdf regeneration is needed for this study.
  - check: The new report must not claim missing SoA pages; page coverage 73-77 (Table 1) and 78 (Table 2).
- **INV** _all_ Attachment cover page (Document p72) is excluded from page_start; the main grid is doc pp73-75 with footnote overflow on 76-77 and the extension schedule on p78.
  - check: Table_01: page_start==73, page_end==77. Table_02: page_start==page_end==78. No table declares page_start 72.
- **INV** _1_ The table is landscape but non-rotated; marks were reconstructed with the standard row-clustering bbox method and validated against 130-200 dpi renders.
  - check: New report states bbox column-binning (§1b) as the mark-check method, not image-based pixel detection.
- **INV** _1_ Table 1 has five header rows: Study Phase (epoch, synthesized name), Cycle, Visit, Approximate Duration (days), Relative day within a cycle.
  - check: Table_01: len(schedule_properties)==5 in that order; the Study Phase row has property_name_source.synthesized == true and property_type 'epoch'.
- **INV** _1_ Header merges: Baseline 4:5, Patients on Study Treatment 6:9, Postdiscontinuation Follow-Up 10:11, and Cycle '1' / Visit '1' merged 6:7.
  - check: Table_01 schedule_grid: is_merged_cell / merged_cell_range values '4:5', '6:9', '10:11' on the Study Phase row and '6:7' on the Cycle and Visit rows.
- **INV** _1_ 'Medical History' legitimately appears twice - once as a category header and once as a procedure - exactly as printed.
  - check: Table_01: two activities named 'Medical History' (one indentation_level 0, one indentation_level 1). A dedup to one row is a regression.
- **INV** _1_ Adverse Event Collection and Concomitant Medications each show a single X centred over Cycle 1 Day 1 + Day 15+/-3 (no internal divider) and are distributed across columns 6-7 with source_range '6:7'.
  - check: Table_01: rows 'Adverse Event Collection/CTCAE Grading' and 'Concomitant Medications (with analgesics)' each have activity_schedule entries at column_position 6 and 7 with source_range '6:7'.
- **INV** _1_ Weight, Vital Signs, ECOG, Central hematology and Central serum chemistry have two separate X's and are kept as distinct Cycle-1 Day-1 and Day-15 marks (no merge).
  - check: Table_01: those five rows have activity_schedule entries at columns 6 and 7 with source_range absent/null.
- **INV** _1_ Fulvestrant Therapy and LY2835219 Therapy merged treatment-text cells are distributed across columns 6-9 with source_range '6:9', carrying the verbatim treatment text as cell_value.
  - check: Table_01: 'Fulvestrant Therapy' has 4 entries cols 6-9 with cell_value 'Days 1 and 15 of Cycle 1, then Day 1 of Cycle 2 and beyond'; 'LY2835219 Therapy' has 4 entries cols 6-9 with cell_value 'Every 12 hours on Days 1 through 28 of every cycle'; all source_range '6:9'.
- **INV** _1_ Footnote a is a header-cell footnote bound to the Cycle row on columns 10-11 as schedule_cell locations.
  - check: Table_01: annotation 'a' has two marker_locations with location_type 'schedule_cell', row_position 2, column_position 10 and 11; both grid cells carry annotation_markers 'a'.
- **INV** _1_ Footnote p is a header-cell footnote bound to the Relative-day row on columns 8-9 as schedule_cell locations.
  - check: Table_01: annotation 'p' has marker_locations location_type 'schedule_cell', row_position 5, column_position 8 and 9; both grid cells carry annotation_markers 'p'.
- **INV** _1_ Footnote m is typed source_note (a pure cross-reference to Attachment 7), not footnote.
  - check: Table_01: annotation with marker 'm' has annotation_type=='source_note'.
- **INV** _1_ Footnote q (Informed Consent) is printed on both the activity name and the baseline X but is anchored to the activity name.
  - check: Table_01: annotation 'q' has an activity_name marker_location on the Informed Consent row (row_position 7 in the existing file).
- **INV** _2_ Table 2 has 3 leaf columns (extension cycle Day 1, Day 15, Extension Period Follow-Up / Visit 901), Adverse Events Collection marks at cols 4 and 6, and Fulvestrant/LY therapy merged-text cells across cols 4-5.
  - check: Table_02: schedule_grid column positions {4,5,6}; 'Adverse Events Collection/CTCAE Grading' has entries at columns 4 and 6 only; Fulvestrant and LY therapy rows have entries at columns 4-5 with source_range covering that span.
- **INV** _all_ There are no orphan annotations: all footnotes a-q (Table 1) and a-c (Table 2) are referenced and every activity/header marker resolves.
  - check: Every annotation has len(marker_locations)>=1, and every marker in an annotation's marker_locations also appears in that row's annotation_markers.
- **SRC** _1_ The detailed PK sampling timing for the C/D/E columns is not in this excerpt - it lives in Attachment 7, referenced only by footnote m.
  - expected handling: The PK timing must not be invented or reconstructed. Footnote m stays a source_note cross-reference to Attachment 7, and the report must flag that the detailed timing is outside the extracted source.
- **JDG** _2_ Table 2 typed track (track_label 'Extension period') rather than a second main_soa.
  - rationale: It is a genuinely separate timeline with its own cycle X-Y and visit 501-5XX/901 numbering. The report explicitly flags this as a judgment call that could alternatively be a second main_soa - a v3.6.0 run choosing main_soa needs human review, not automatic acceptance.
- **JDG** _1_ Baseline sub-columns A (<=28 days) and B (<=14 days) were assigned from bbox x-centres (A~283, B~310), with baseline-only marks following the footnote timing where stated (Informed Consent -> A/<=28; Inclusion-Exclusion, Medical History, Weight, lab tests -> B/<=14).
  - rationale: The two baseline sub-columns are visually close; the assignment rests on x-centre geometry plus footnote timing. A fresh extraction that flips any baseline mark between columns 4 and 5 is changing an adjudicated call.
- **JDG** _1_ Where the source repeats a footnote marker on every cell (Xc, Xb, Xi, Xj, Xd, Xe, Xf, Xk, Xl, Xm, Xn, Xo), the footnote is anchored once to the activity name rather than duplicated on every cell.
  - rationale: The footnote's meaning is per-activity, so per-cell duplication was collapsed. This was explicitly flagged as a low-confidence call. Prompt v3.6.0 §6 now says to scan the ENTIRE table for every place the marker appears, so a fresh run may legitimately add cell locations - see expected_v360_changes.
- **JDG** _1_ Category header rows were synthesized as their own activity rows to represent the source's two-column Procedure Category / Procedure hierarchy, with indent 0 for categories and indent 1 for procedures.
  - rationale: The source has separate Category and Procedure columns; encoding the category as a row is a modelling choice, and three category-level standalone activities (Survival Information, Adverse Event Collection/CTCAE Grading, Concomitant Medications) sit at indent 0 WITH marks because they span both columns.
- **JDG** _1_ Data column positions were anchored at 4-11 (not 2-9), because the source carries three leading label columns (Protocol Reference, Procedure Category, Procedure).
  - rationale: §5 says data columns start at position 2 after excluding the single label column; with three label columns the existing extraction kept source column indexing. A v3.6.0 run that renumbers to 2-9 shifts every column_position and every merged span string - a modelling change to review, not a defect.
- **Δ** The source's Protocol Reference column (per-activity section cross-references, e.g. 'Section 8.1', 'Section 10.3') was not captured in the original extraction and had to be added afterwards via corrections sidecars as pr1-pr19 (Table 1) and pr1-pr2 (Table 2), 54 corrections in total.
  - expect: v3.6.0 should capture the Protocol Reference column natively in the RAW extraction: ~19 source_note annotations in Table 1 and 2 in Table 2, deduplicated by text, each with synthesised pr-style markers added to every citing activity's annotation_markers. The corrections sidecar should become unnecessary. Table 1 annotation count should rise from 17 to roughly 36 (17 footnotes + ~19 source_notes).
  - rule: §6 'A `source_note` is a cross-reference to elsewhere in the protocol — a dedicated reference column ... emit each as a `source_note` deduplicated by text ... and add a synthesised marker (`pr1`, `pr2`, …) to every citing activity's `annotation_markers`'
- **Δ** Per-cell repeated footnote markers were collapsed to a single activity_name anchor and flagged as a low-confidence call.
  - expect: v3.6.0 requires scanning the entire table for every place a marker appears, including schedule_cell with column_position. Expect additional schedule_cell marker_locations on footnotes c, b, i, j, d, e, f, k, l, m, n, o. This is an expected expansion, not a duplication defect - but the activity_name location must survive.
  - rule: §6 'marker_locations — scan the ENTIRE table for every place the marker appears: `schedule_property`, `activity_name`, or `schedule_cell` (include `column_position` for cells)'
- **Δ** No activity carries source_page; pages 76-77 are footnote overflow inside the declared 73-77 range and contribute no activity rows.
  - expect: Every activity must now carry source_page, and the report must explicitly state that doc pages 76-77 are footnote pages contributing no activity rows.
  - rule: §4 'every page in the declared range must contribute rows ... If a page in the range genuinely has no activity rows (a footnote or abbreviation page), say so in the report'
- **Δ** No method provenance fields are present in either table.
  - expect: Non-default methods must now be recorded (e.g. method 'synthesized' on the pr-marker locations and on any synthesised property name), with one report line each.
  - rule: §1e Method provenance; §7 'Method provenance: every non-default method recorded'
- **Δ** Table 2's track classification reasoning lives in the report; table_metadata.notes only says 'Separate timeline from Table 1 (main schedule).'
  - expect: table_metadata.notes must now carry the full classification reasoning for the non-obvious track call.
  - rule: §2 'For any `table_type` that is not obvious from the discriminators alone, record the reasoning in `table_metadata.notes` as well as the report'
- **Δ** Table 1's by_type after the pr-note additions is 17 footnote + ~19 source_note.
  - expect: v3.6.0's delivery check requires by_type not be degenerate across >20 annotations, in particular not all source_note. The mixed 17/19 split satisfies this - a fresh run that produces all-source_note or drops the footnotes fails the check.
  - rule: §8 '`by_type` is not degenerate across > 20 annotations — in particular NOT all `source_note`'

_Notes:_ Report explicitly states 'SOURCE ISSUE — none' for this study, so source_defects is deliberately near-empty; the single entry (Attachment 7 PK timing outside the excerpt) is the only content the report identifies as referenced-but-absent. Note that the pr1-pr19 / pr1-pr2 source_notes live only in *_extraction.verified.json today; the raw *_extraction.json has 17 and 3 annotations respectively.

### NCT02291289

5 table(s): T1 main_soa pp169-171 (21a/56m/20n), T2 track pp174-176 (25a/47m/24n), T3 track pp179-181 (24a/39m/21n), T4 track pp184-185 (22a/40m/21n), T5 track pp189-191 (26a/45m/23n)

- **INV** _all_ The SoA is five appendices (11.1-11.5) extracted as exactly five tables.
  - check: Exactly five files NCT02291289_Table_01..05_extraction.json exist.
- **INV** _1_ Table 1 = Appendix 1 (Screening/Baseline + Induction, All Patients), table_type main_soa, doc pages 169-171, 6 data columns, 21 activities, 20 annotations a-t.
  - check: Table_01: table_type=='main_soa'; track_label absent; page_start==169, page_end==171; distinct schedule_grid column_position == [2,3,4,5,6,7] (6 columns); len(activities)==21; len(annotations)==20 with markers a-t.
- **INV** _2_ Table 2 = Appendix 2 Maintenance, track_label 'Cohort 1', pages 174-176, 4 columns, 25 activities, 24 annotations a-x.
  - check: Table_02: table_type=='track'; track_label=='Cohort 1'; page_start==174, page_end==176; 4 distinct data columns [2,3,4,5]; len(activities)==25; len(annotations)==24.
- **INV** _3_ Table 3 = Appendix 3 Maintenance, track_label 'Cohort 2', pages 179-181, 4 columns, 24 activities, 21 annotations a-u.
  - check: Table_03: track_label=='Cohort 2'; page_start==179, page_end==181; len(activities)==24; len(annotations)==21.
- **INV** _4_ Table 4 = Appendix 4 Maintenance, track_label 'Cohort 3', pages 184-185, 4 columns, 22 activities, 21 annotations a-u.
  - check: Table_04: track_label=='Cohort 3'; page_start==184, page_end==185; len(activities)==22; len(annotations)==21.
- **INV** _5_ Table 5 = Appendix 5 Maintenance, track_label 'Cohort 4', pages 189-191, 4 columns, 26 activities, 23 annotations a-w.
  - check: Table_05: track_label=='Cohort 4'; page_start==189, page_end==191; len(activities)==26; len(annotations)==23.
- **INV** _all_ Appendix 6 (FOLFOX Regimens) on doc page 194 is a dosing-regimen table, not a Schedule of Assessments, and is deliberately out of scope.
  - check: No table has page_start or page_end == 194; no activity references FOLFOX regimen dosing rows.
- **INV** _all_ All marks are transcribed as lowercase 'x' (Roche house style).
  - check: Across all five tables, activity_schedule cell_value marks are 'x' (or a text cell), never bare 'X'.
- **INV** _1_ Appendix 1 has three header rows: a level-null condition band over an epoch phase row and a timepoint timing row; Apps 2-5 have two header rows (epoch phase + timepoint timing).
  - check: Table_01: len(schedule_properties)==3, with one property_type=='condition' and hierarchical_level==null, one 'epoch' level 1, one 'timepoint' level 2. Tables 02-05: len(schedule_properties)==2 (epoch + timepoint).
- **INV** _1_ App1's 'Study medication administration' row shows 'x Administered every 2 weeks' spanning the two Induction columns and is distributed with source_range '4:5'.
  - check: Table_01: two activity_schedule entries at column_position 4 and 5 with cell_value 'x Administered every 2 weeks' and source_range '4:5'.
- **INV** _all_ Footnote c in every table binds three elements: the Post-Treatment Follow-Up header plus the 'Subsequent anti-cancer therapies (see [c])' and 'Patient survival (see [c])' activities.
  - check: In each of Tables 01-05: annotation 'c' has >=3 marker_locations - one on the Post-Treatment Follow-Up header element and one activity_name location each on the subsequent-anti-cancer-therapies and patient-survival rows.
- **INV** _1_ Footnote r in App1 is one annotation deduplicated over two activities (Whole blood and Plasma samples), not two annotations.
  - check: Table_01: exactly one annotation with marker 'r', carrying two activity_name marker_locations (rows 15 and 16 in the existing file).
- **INV** _all_ Certain activities are deliberately modelled with no annotation_markers because none is printed: Cohort-specific informed consent, Stool sample (all maintenance tables), and TSH/T3/T4 + Pulse oximetry (Cohorts 2 and 4).
  - check: In Tables 02-05: the Cohort-specific informed consent and Stool sample activities have annotation_markers null/absent; in Tables 03 and 05 the TSH/T3/T4 and Pulse oximetry rows likewise.
- **INV** _all_ Cohort-specific content is read faithfully per appendix and never copied between cohorts: Cohort 1 has Head & neck / Chest CT / Dermatology / Anal-pelvic exams; Cohort 2 has TSH/T3/T4, Pulse oximetry, Tuberculosis test, HIV/HBV/HCV serology; Cohort 3 has LVEF and HER2 (trastuzumab/pertuzumab); Cohort 4 adds Ophthalmology exam.
  - check: Table_02 has Head & neck / Chest CT / Dermatology / Anal-pelvic activities and Table_03 does not; Table_04 has LVEF and HER2 activities; Table_05 has Ophthalmology exam. Per-cohort cycle wording differs (e.g. Pulse oximetry Cohort 2 'Prior to Cycle 1 then every 2 cycles' vs Cohort 4 'Prior to Cycles 1, 3, 5, 7…').
- **INV** _5_ App5 footnote g spans a grid page and continues on the following text page; the two fragments were assembled into one annotation.
  - check: Table_05: exactly one annotation with marker 'g' whose text runs past the grid-page break; no second partial 'g' annotation and no containment pair with another annotation's text.
- **INV** _all_ Text cells are transcribed verbatim as cell_value, including 'As required', 'If clinically indicated', 'Mandatory at end of Induction Treatment Phase', 'According to local standard of care', 'Every cycle', 'At 6 months', 'Prior to Cycles 1, 4, 7…', 'Experimental arm only', 'No sample collection / Supplemental Biomarker Program CLOSED'.
  - check: Grep those literal strings in the activity_schedule cell_value fields across Tables 01-05; each must still appear.
- **INV** _all_ All five tables are schema-valid with no orphan annotations; every element marker resolves and every annotation is referenced.
  - check: Every annotation has len(marker_locations)>=1; every marker appearing in a marker_location also appears in that row's annotation_markers.
- **SRC** _all_ Every grid page of all five appendices is a scanned image with no text layer; marks and text cells could not be read from a text layer.
  - expected handling: The re-extraction must handle these as image-based (§1a): render each page, detect marks mechanically by near-black pixel COUNT inside rule-line-bounded cells, validate the detector cell-for-cell against direct visual reads on representative dense and sparse rows, state the image-based method in the report and recommend a spot-check. A fresh report claiming bbox/text-layer mark extraction for the grids is wrong about the source.
- **SRC** _all_ Mixed document: the grids are scanned but the dedicated footnote pages carry a real text layer, while the header/early footnotes printed on the grid images (App1 a-e, App2 a-j, App3 a-e, App5 a-g) have no text layer and had to be read visually.
  - expected handling: Footnote wording must come from the text layer where it exists; the on-grid footnotes must be flagged as visually transcribed (and under v3.6.0 carry annotation_text_source.method 'visual_transcription'). Silently claiming verbatim text-layer capture for App1 a-e / App2 a-j / App3 a-e / App5 a-g would misstate provenance.
- **SRC** _3_ Scan-rendering inconsistency: a few cells render as uppercase 'X' in an otherwise all-lowercase-'x' table (e.g. App3 HIV serology, TSH/Pulse-oximetry discontinuation cells).
  - expected handling: Per §5 'Glyph case', normalisation of an obvious scan-rendering inconsistency is allowed ONLY if flagged in the report. A fresh extraction must either keep 'X' literally or normalise AND flag; silently normalising without flagging loses the defect.
- **JDG** _all_ Appendix 1 classified main_soa (shared anchor); Appendices 2-5 classified track with track_label Cohort 1-4.
  - rationale: Appendices 2-5 are per-cohort Maintenance timelines. This was an explicit human decision ('per your decision'); a v3.6.0 run reclassifying any of them (e.g. as domain or continuation) needs human review rather than automatic acceptance.
- **JDG** _1_ App1's top band ('Patients who have PD … not eligible for any study cohort', cols 6-7) modelled as a level-null condition property rather than folded into the phase cells.
  - rationale: Explicitly listed as a low-confidence call. Prompt v3.6.0 §3 now codifies exactly this handling, so the same output is expected; folding it into the phase cells would now contradict the rule.
- **JDG** _all_ Multi-line grid text cells are joined into a single space-separated string; line breaks are not preserved.
  - rationale: Modelling choice for multi-line tumour-assessment and pregnancy-test schedule cells. A fresh extraction that preserves newlines changes cell_value equality for those cells.
- **JDG** _all_ Inline section/appendix references inside FOOTNOTE text (e.g. 'See Appendix 8', 'Section 4.4') were left in the footnote wording and not split out as separate source_note annotations.
  - rationale: v3.6.0 §6 mandates splitting inline section/appendix references out of ACTIVITY LABELS and out of a dedicated reference column - it does not require rewriting footnote wording. So the existing decision is expected to hold; a fresh run that strips references out of footnote text would change footnote wording and should be reviewed, not accepted as an improvement.
- **Δ** Marks and text cells were 'read visually from the rendered pages' with no mechanical detector described.
  - expect: v3.6.0 requires a mechanical mark detector for image-based grids: rule-line cell rectangles plus a near-black pixel COUNT threshold (not a fraction), validated cell-for-cell against visual reads on at least one dense and one sparse full-width row. The report must state the detector and list every cell where the mechanical matrix disagreed with the visual read. Expect a possibly different mark set on dense rows - each difference needs adjudication against the render, not automatic acceptance.
  - rule: §1a 'reconstruct marks mechanically ... counting near-black pixels (intensity < ~90) ... use a count, NOT a dark-pixel fraction ... Validate the detector cell-for-cell against direct visual reads'
- **Δ** No rule-line geometry is described; cell boundaries were established by visual reading of the scans.
  - expect: v3.6.0 requires recovering rule lines from the raster (200 dpi render, ink threshold ~50% grey, vertical rules by ink fraction over table height, horizontal rules by >85% ink within one column's x-range) and applying the one method across the whole table, rather than falling back to proximity.
  - rule: §1d 'Recovering rule lines from the raster'
- **Δ** No method provenance fields are recorded in any of the five extraction files.
  - expect: Expect activity_name_source.method 'visual_transcription' and activity_name_source.indentation_method on activities; annotation_text_source.method 'visual_transcription' on the on-grid footnotes (App1 a-e, App2 a-j, App3 a-e, App5 a-g) and default/absent on the text-layer footnote pages; activity_schedule cell method 'raster_pixel_detection' or 'visual_read'; and one report line per non-default method.
  - rule: §1e Method provenance; §7 'Method provenance: every non-default method recorded (§1e)'
- **Δ** No activity carries source_page across doc pages 169-171, 174-176, 179-181, 184-185, 189-191.
  - expect: Every activity must now carry source_page, and the report must state activity rows per page for each declared range and call out any page contributing none.
  - rule: §4 source_page and page-coverage check; §7 per-page row counts
- **Δ** Footnote c's header binding is recorded as location_type 'schedule_property' with column_position 7 (the Post-Treatment Follow-Up phase cell); the same pattern applies to footnotes a and b on the Induction and Discontinuation phase cells.
  - expect: Per-column header footnotes should now be recorded as schedule_cell locations on that column's schedule_grid cell. The binding annotation_markers already sit on the grid cells (App1 row2: col4 'a', col6 'b', col7 'c') and must remain unchanged.
  - rule: §6 'Header-cell footnotes (per-timepoint) ... Do NOT put it on the `schedule_property` row's `annotation_markers`'
- **Δ** Table classification reasoning for the main_soa/track split lives in the report; table_metadata.notes currently records only appendix number, scan status, column count and footnote page split.
  - expect: table_metadata.notes must now also record the main_soa-vs-track reasoning for each appendix, since the classification is not obvious from the discriminators alone.
  - rule: §2 'record the reasoning in `table_metadata.notes` as well as the report'
- **Δ** The report recommends a spot-check of the resolved grids but does not include a mechanical-vs-visual diff.
  - expect: The new report must include the §7 'Mechanical mark-check' section naming the rule-line/near-black-pixel detector and listing disagreements, in addition to the spot-check recommendation.
  - rule: §7 'Mechanical mark-check: the method used (bbox column-binning for text-layer §1b, rule-line/near-black-pixel detector for image §1a) and any cell where the mechanical matrix disagreed with the visual read'

_Notes:_ The report's 'cols' column counts data columns (6 for App1, 4 for Apps 2-5); in the JSON these are column_position 2-7 and 2-5 respectively. Column-position numbering here already starts at 2 per §5, unlike NCT02107703. Redaction/illegibility is NOT reported for this study, so no §6 redaction defect entry was created.

### NCT03283098

3 table(s): T1 main_soa pp32-33 (14a/94m/9n), T2 domain pp34-35 (14a/65m/8n), T3 domain pp36-36 (7a/23m/1n)

- **INV** _all_ The single protocol 'Table 1. Schedule of Assessments' (Section 7.1, document pages 32-36) is modelled as exactly THREE extraction files, not one and not five.
  - check: extracted/ contains exactly three files NCT03283098_Table_01/02/03_extraction.json and no Table_04.
- **INV** _Table_01_ Table 01 = 1a Non-laboratory Assessments: table_type main_soa, pages 32-33, 14 activities, 94 mark cells, 9 annotations.
  - check: Table_01: table_metadata.table_type=='main_soa', page_start==32, page_end==33, len(activities)==14, len(activity_schedule)==94, len(annotations)==9.
- **INV** _Table_02_ Table 02 = 1b Laboratory Assessments: table_type domain, pages 34-35, 14 body rows (1 section header + 13 lab activities), 65 cells, 8 annotations.
  - check: Table_02: table_type=='domain', page_start==34, page_end==35, len(activities)==14 with exactly one indentation_level 0 row ('Laboratory Assessments'), len(activity_schedule)==65, len(annotations)==8.
- **INV** _Table_03_ Table 03 = 1c Pharmacokinetic Assessments: table_type domain, page 36 only, 7 body rows (1 section header + 6 PK activities), 23 cells, 1 annotation.
  - check: Table_03: table_type=='domain', page_start==page_end==36, len(activities)==7 with one indentation_level 0 row ('Central Laboratory'), len(activity_schedule)==23, len(annotations)==1.
- **INV** _all_ All three tables share one 20-column timeline occupying data column positions 2-21, beginning Screening, -2, 1 (HD) and ending 55 (HD).
  - check: In each table schedule_grid has 20 entries for header row 1 at column_position 2..21; column 2 cell_value=='Screening', column 3=='-2', column 21=='55 (HD)'.
- **INV** _all_ Every grid cell value is the mark X; no timing-text cells anywhere in this protocol.
  - check: set(x['cell_value'] for x in activity_schedule) == {'X'} in all three files.
- **INV** _all_ No orphan annotations and no scheduling marks on section-header rows.
  - check: Every annotation has len(marker_locations)>=1; no activity with indentation_level 0 in Table_02/Table_03 appears as a row_position in activity_schedule.
- **INV** _Table_01_ Markers a and h both sit on the 29/ET header cell at grid column 18 (column-scoped), not on the schedule_property row as a whole.
  - check: Table_01 schedule_grid entry row_position 1 / column_position 18 has cell_value '29/ET (HD)' and annotation_markers containing both 'a' and 'h'; annotations 'a' and 'h' each have a marker_location with column_position 18.
- **INV** _Table_01_ Footnote b binds to three activity rows (Body Height, Body Weight, Physical exam) as one annotation; c,d,e,f,g,i each bind to exactly one activity.
  - check: Table_01 annotation 'b' has exactly 3 activity_name marker_locations (rows 6,7,8); annotations c,d,e,f,g,i each have exactly 1 activity_name location.
- **INV** _Table_02_ Footnote b in Table 1b is CELL-level on the Day -2 column (grid column 3) of five activities (Albumin, Phosphorus, Calcium, Pregnancy, iPTH), not activity-level.
  - check: Table_02 annotation 'b' has 5 marker_locations, all location_type schedule_cell with column_position 3, on the Albumin/Phosphorus/Calcium/Pregnancy/iPTH rows.
- **INV** _Table_02_ Footnote d in Table 1b binds to two activity names, Albumin and Calcium.
  - check: Table_02 annotation 'd' has exactly 2 activity_name marker_locations, on 'Albumin' and 'Calcium (cCa)'.
- **INV** _Table_03_ Table 1c has exactly one annotation, marker a, scoped to the 29/ET column (col 18).
  - check: Table_03 len(annotations)==1, annotation_marker=='a', its single marker_location has column_position 18.
- **INV** _Table_01_ Table 1a is a flat activity list: no section headers, all 14 rows at indentation_level 0 and all eligible to carry marks; by contrast 1b and 1c each have a level-0 section header that carries no marks.
  - check: Table_01: every activity has activity_name_source.indentation_level==0 and marks are present on level-0 rows; Table_02 row 1 'Laboratory Assessments' and Table_03 row 1 'Central Laboratory' are level 0 with zero activity_schedule entries.
- **INV** _all_ The abbreviation legend terms (ET, HD, cCa, SDA, Kt/V, URR) are deliberately NOT emitted as abbreviation annotations, because they carry no in-grid markers and would be orphans.
  - check: No annotation in any of the three files has annotation_type=='abbreviation'.
- **SRC** _Table_03_ Footnote marker 'a' is printed on the 29/ET header of Table 1c, but page 36 prints only the abbreviation legend - the text of footnote 'a' is not restated anywhere on that page. The v3.0.2 extraction filled the gap by copying the Day-29-withdrawal footnote text defined for 1a/1b on pages 33/35.
  - expected handling: Per prompt v3.6.0 section 6 'Markers referenced but not defined (source defect)': keep the marker where it is printed, and annotation_text must state plainly that the definition is not printed on page 36; any text borrowed from 1a/1b must be labelled a PROBABLE cross-reference, never asserted as source content. The report must flag it. A fresh extraction that presents the borrowed sentence as if it were printed in 1c is repeating the defect, not fixing it.
- **SRC** _Table_02_ The protocol markdown renders Table 1b with a duplicated Day-1 column ('1 (HD) | 1 (HD)') that does not exist in the PDF; the PDF bbox confirms a single Day-1 column and 20 day columns, identical to 1a.
  - expected handling: Per section 1 the PDF is authoritative for structure and the row/column set; the markdown doubling is a transposition artifact. Table 1b must have 20 data columns (positions 2-21), identical to 1a, and the PDF/markdown disagreement must be flagged in the new uncertainty report. A 21-column Table 1b is a regression.
- **JDG** _Table_03_ Table 1c was classified table_type 'domain' rather than 'subsidiary', on the ground that it shares 1a's exact 20 day columns (finer timing is within-visit via the Time qualifier, not finer day granularity).
  - rationale: Classified per the taxonomy's own Amgen 1a/1b/1c example; the report explicitly records that 'subsidiary' is arguable and flags it.
- **JDG** _all_ The 'Study Visit (Day)' caption row above the day-number row was collapsed into ONE study_day schedule_property at hierarchical_level 1, using the caption as the property name, rather than modelled as two header rows.
  - rationale: The caption row is non-distinguishing (removing it would not make any two columns indistinguishable), so it does not need its own level.
- **JDG** _Table_02_ The left-hand 'Time' qualifier column of Table 1b ('Pre HD', printed once at the top of the Laboratory block in the PDF text layer) was captured as a single synthesized annotation t1 on the 'Laboratory Assessments' section header, NOT folded per-row.
  - rationale: The PDF prints it once for the whole block (the markdown replicated it per row); only physical column 1 is treated as the label column so the day columns stay indexed 2-21, aligning with 1a.
- **JDG** _Table_03_ The left-hand 'Time' qualifier of Table 1c, which varies per row, was folded into activity_name ('PK (Pre HD)', 'PK (SDA + 10 min)', ...) while activity_name_source.cell_text was kept as the raw 'PK'.
  - rationale: The Time qualifier is the only thing distinguishing six otherwise-identical 'PK' rows; the asymmetry with 1b (annotation there, name-fold here) is driven by uniform-vs-varying Time. The alternative offered was Time as level-0 header rows.
- **Δ** Table 1c footnote 'a' text is currently the 1a/1b Day-29-withdrawal sentence, asserted as if printed in 1c.
  - expect: annotation_text for Table_03 marker 'a' should now state that the definition is not printed in the extracted source, with any 1a/1b text clearly labelled as a probable cross-reference rather than source content.
  - rule: Section 6, 'Markers referenced but not defined (source defect)'
- **Δ** No activity in any of the three extraction files carries a source_page field, and the report gives no per-page activity counts for pages 32-36.
  - expect: Every activity should carry source_page, and the new report should state activity rows per page across each declared page range (page 33 and page 35 are footnote pages that may legitimately contribute no rows - the report must say so).
  - rule: Section 4 (source_page + page coverage) and section 7 ('activity rows per page across the declared page range')
- **Δ** Table 1a is a flat level-0 activity list; no indentation provenance is recorded.
  - expect: activity_name_source.indentation_method should appear (assumed_flat for the flat 1a, or font_signal/visual_estimate) where the level does not come from text-layer whitespace.
  - rule: Sections 1e and 4 (indentation_method)
- **Δ** Annotation t1 in Table 1b is a synthesized annotation whose marker_location on the 'Laboratory Assessments' header carries no method field.
  - expect: That marker_location should now carry method: "synthesized"; the new report should list it under method provenance.
  - rule: Sections 1e (marker_locations[].method) and 7 (method provenance)
- **Δ** The collapsed 'Study Visit (Day)' schedule_property records property_type/hierarchical_level with no structure_method.
  - expect: If the type/level are taken from layout rather than printed header labels, structure_method (inferred_from_layout / assumed) should now be set on that schedule_property.
  - rule: Sections 3 and 1e (schedule_property.structure_method)

### NCT03402841

2 table(s): T1 main_soa pp40-41 (18a/19m/8n), T2 main_soa pp42-44 (15a/45m/11n)

- **INV** _all_ Both tables are classified main_soa; the protocol yields exactly two extraction files.
  - check: extracted/ contains exactly NCT03402841_Table_01_extraction.json and NCT03402841_Table_02_extraction.json, each with table_metadata.table_type=='main_soa'.
- **INV** _all_ The reason for two main_soa tables (rather than main_soa + domain/continuation) is that they are two independent schedules with different column structures - screening versus on-study.
  - check: Table_01 has 2 data columns and Table_02 has 7; neither carries continuation_of; the new report/table_metadata.notes states the screening-vs-on-study reasoning.
- **INV** _Table_01_ Table 01 (Screening, Visit 1) spans pages 40-41 with 1 header row, 2 columns labelled 'Before screening period' and '-28 to -1', 18 activities, 19 marks and 8 annotations.
  - check: Table_01: page_start==40, page_end==41, len(schedule_properties)==1, schedule_grid has column_position 2 cell_value 'Before screening period' and column_position 3 cell_value '-28 to -1', len(activities)==18, len(activity_schedule)==19, len(annotations)==8.
- **INV** _Table_02_ Table 02 (Procedures, Visits 2+) spans pages 42-44 with 3 header rows, 7 timepoint columns, 15 activities, 45 marks and 11 annotations.
  - check: Table_02: page_start==42, page_end==44, len(schedule_properties)==3, 7 distinct data column positions in schedule_grid, len(activities)==15, len(activity_schedule)==45, len(annotations)==11.
- **INV** _Table_02_ The three header rows of Table 02 are typed visit / study_day / window in that order.
  - check: Table_02 schedule_properties sorted by row_position have property_type 'visit', 'study_day', 'window'.
- **INV** _Table_02_ Footnote b is a CELL-level marker on the Visit 2 / Day 1 column only, for Physical examination, Vital signs, Haematology and Urinalysis (4 cells).
  - check: Table_02 annotation 'b' has 4 marker_locations, all location_type schedule_cell with column_position 2, on the Physical examination / Vital signs / Haematology-clinical chemistry / Urinalysis rows; the same 4 activity_schedule cells carry annotation_markers 'b'.
- **INV** _Table_02_ Footnote j is a cell marker on the 'Olaparib dispensed/returned' row at Visit 3 and Visit 4 only.
  - check: Table_02 annotation 'j' has exactly 2 schedule_cell marker_locations, both on the 'Olaparib dispensed/returned' row, at column_position 3 and 4.
- **INV** _Table_02_ Footnote a is bound to two specific HEADER cells - the Visit-No.-5 header (row 1, col 5) and the col-4 Day cell - via cell-level locations so it keeps column scope rather than collapsing to the whole header row.
  - check: Table_02 annotation 'a' has 2 marker_locations at (row 1, col 5) and (row 2, col 4); the corresponding schedule_grid cells carry annotation_markers 'a'; no schedule_property row carries 'a' in its annotation_markers.
- **INV** _Table_02_ Footnote c is ONE annotation with three activity_name locations (Physical examination, Vital signs, Urinalysis), not three separate annotations.
  - check: Table_02 has exactly one annotation with annotation_marker 'c' and it has 3 activity_name marker_locations.
- **INV** _all_ No orphan annotations: all 8 Table 01 annotations and all 11 Table 02 annotations carry at least one marker_location.
  - check: For both files, every annotation has len(marker_locations)>=1.
- **SRC** _Table_02_ The source footnote letter sequence for Table 02 skips 'i': it runs a-h then j, k, l. There is no footnote 'i' printed in the protocol.
  - expected handling: Transcribe the letters as printed. No annotation with annotation_marker 'i' may appear, and k/l must not be silently renumbered to i/j. If the new extraction emits an 'i', it fabricated one.
- **SRC** _Table_02_ The activity label in Table 02 row 12 is misspelled in the source: 'restrospective' for 'retrospective'.
  - expected handling: activity_name must remain the literal source string 'Blood sample for restrospective gBRCA test'. A silently corrected spelling is a transcription defect, not an improvement (section 1, 'transcribe, do not infer').
- **SRC** _all_ At v3.0 extraction time NCT03402841_soa.pdf held only Table 2; Table 1 (the screening schedule, protocol pp.40-41) was missing from the excerpt and had to be sourced from the full protocol PDF. The report records this as RESOLVED on 2026-07-12 by regenerating the excerpt to the complete 5-page source.
  - expected handling: The regenerated NCT03402841_soa.pdf is now 5 pages covering protocol pp.40-44 (verified with pdfinfo: 'Pages: 5'). A v3.6.0 run against this PDF must produce BOTH tables from the SoA PDF alone and should NOT need the full protocol. If the new report again says Table 1 is missing from the SoA excerpt, the regeneration has regressed - it is not a new extraction defect.
- **JDG** _Table_01_ The single Table 01 header row was typed property_type 'study_day' even though it mixes a period reference ('Before screening period') with a day range ('-28 to -1').
  - rationale: Recorded as a low-confidence call: the row is heterogeneous, and study_day was chosen for the day-range content.
- **JDG** _Table_02_ Table 02 rows 17 and 18 ('Subsequent cancer therapy following discontinuation...' and 'Time to subsequent therapy and Survival') are extracted as SIBLINGS at indentation_level 1, not as parent/child.
  - rationale: Row 18 reads like a sub-item, but both share the same left margin in the PDF (x=78), so the geometry was followed rather than the reading. Explicitly flagged for review if a parent/child relationship is wanted.
- **JDG** _Table_01_ The unlettered 'Note: MRI/ CT scan more than 28 days prior to Day 1 may be acceptable...' printed under footnote e was captured as a footnote with a synthesized marker 'note1' anchored to Tumour assessment (row 16).
  - rationale: The note has no printed marker; row 16 was chosen because the note concerns scan timing.
- **Δ** No activity in either file carries a source_page field, and the report gives no per-page activity counts.
  - expect: Every activity should carry source_page, and the new report must state activity rows per page for pages 40-41 and 42-44, calling out any page in the range that contributed none.
  - rule: Section 4 (source_page + coverage check) and section 7
- **Δ** Table 01's synthesized marker 'note1' marker_location carries no method field.
  - expect: That location should now carry method: "synthesized" (or "text_match" if bound by word overlap), and the new report should list it under method provenance.
  - rule: Sections 1e and 6 (synthesised note markers) and section 7
- **Δ** table_metadata.notes on both files says only 'Protocol printed page numbers (= PDF page numbers).'; the two-main_soa reasoning lives only in the uncertainty report.
  - expect: The screening-vs-on-study reasoning for classifying both tables main_soa should now also be recorded in table_metadata.notes, not just the report.
  - rule: Section 2, 'For any table_type that is not obvious from the discriminators alone, record the reasoning in table_metadata.notes as well as the report'
- **Δ** All 15 Table 02 activities are at indentation_level 1 with no provenance for how that level was determined (the report cites PDF x-margin geometry, x=78).
  - expect: activity_name_source.indentation_method should now be recorded (visual_estimate / font_signal / assumed_flat) since the level comes from margin geometry rather than text-layer whitespace.
  - rule: Sections 4 and 1e (indentation_method)

### NCT03421379

1 table(s): T1 main_soa pp11-18 (36a/80m/27n)

- **INV** _Table_01_ Exactly one table: main_soa, title 'Study Schedule Protocol I8R-JE-IGBJ' (Section 2), document pages 11-18, 8 data columns at positions 2-9, 36 body rows = 3 section headers + 33 activities, 80 schedule cells (56 X + 24 timing-text), 27 annotations.
  - check: One extraction file; table_type=='main_soa', page_start==11, page_end==18; len(activities)==36 of which 3 have indentation_level 0; len(activity_schedule)==80 with exactly 56 entries whose cell_value=='X'; len(annotations)==27; schedule_grid column positions span 2..9.
- **INV** _Table_01_ The two-row header repeating on each of pages 11-18 is modelled as ONE main_soa with the header encoded once - not as 8 continuation tables.
  - check: Only one extraction JSON exists for this study; no table has table_type=='continuation' or a continuation_of value; len(schedule_properties)==2.
- **INV** _Table_01_ The table is complete: Section 2 runs pages 11-18 and ends at the Abbreviations/footnote block immediately before Section 3 on page 19; no missing pages or tables.
  - check: page_end==18 and no additional table file for page 19+.
- **INV** _Table_01_ Header row 1 (epoch) carries the merged spans Period 1 = columns 3:4 and Period 2 = columns 6:7, and these are the ONLY merges - header merges only, none in the body.
  - check: schedule_grid row 1 has is_merged_cell true with merged_cell_range '3:4' at columns 3 and 4, and '6:7' at columns 6 and 7; no other grid cell has is_merged_cell.
- **INV** _Table_01_ No body mark spans two sub-columns; source_range is empty on every activity_schedule cell.
  - check: No activity_schedule entry has a non-empty source_range.
- **INV** _Table_01_ Header row 2 column 9 ('Additional Follow-up for TE ADA' epoch) has no study-day label in the source - the cell is blank.
  - check: schedule_grid has no non-empty cell_value at row_position 2 / column_position 9.
- **INV** _Table_01_ Both schedule_property names are synthesized and flagged as such: row 1 -> 'Period' (label cell empty), row 2 -> 'Study Day' (the col-1 cell literally reads 'Procedure').
  - check: Both schedule_properties have property_name_source.synthesized==true; row 2's property_name_source.cell_value=='Procedure'.
- **INV** _Table_01_ The right-hand Comments column (source physical column 10) is excluded from the grid; each distinct note became a synthesised annotation c1-c25, of which c5 and c15 are source_note and the rest are footnote.
  - check: No schedule column 10 in schedule_grid; annotations c1..c25 exist; exactly c5 and c15 have annotation_type=='source_note' among the c-series, all other c-series are 'footnote'.
- **INV** _Table_01_ c15 is deduplicated by text and links two rows (22 Clinical Serology Tests and 24 HbA1c); c19 links two rows (27 Ethanol Testing and 28 Urine Drug Screen).
  - check: annotation c15 has 2 activity_name marker_locations at row_position 22 and 24; annotation c19 has 2 at row_position 27 and 28; both rows in each pair carry the marker in activity annotation_markers.
- **INV** _Table_01_ note1 is the synthesised table-wide bottom Note ('If multiple procedures take place at the same time point ... ECG, vital signs, and venipuncture ...'), anchored to schedule_property row 2 for traceability, and is table-scoped by design.
  - check: annotation 'note1' has exactly one marker_location, location_type schedule_property, row_position 2, with no column_position.
- **INV** _Table_01_ Footnote a sits on the 'Additional Follow-up for TE ADA' epoch cell at grid row 1, column 9, and is column-scoped to col 9.
  - check: schedule_grid row 1 / column 9 has cell_value 'Additional Follow-up for TE ADA' and annotation_markers 'a'; annotation 'a' has one marker_location at row 1 column 9.
- **INV** _Table_01_ The Abbreviations list (CRU, ECG, ED, FSH, HbA1c, IMG, min, PD, PG, PK, TE ADA) is deliberately NOT emitted as abbreviation annotations, because the terms carry no in-grid markers and would be orphans.
  - check: No annotation has annotation_type=='abbreviation'.
- **INV** _Table_01_ 24 cells carry post-dose timepoint lists instead of X, transcribed verbatim as cell_value (e.g. the PK (Glucagon) and Plasma Glucose for PD timepoint lists, 'Pre-hypoglycemia induction, ...', Physical Exam '240 min').
  - check: len([c for c in activity_schedule if c['cell_value']!='X'])==24, and their values are timepoint strings, not 'X'.
- **INV** _Table_01_ No orphan annotations: all 27 annotations have at least one marker_location.
  - check: Every annotation has len(marker_locations)>=1.
- **JDG** _Table_01_ Header row 1 was typed property_type 'epoch' rather than 'period', even though it mixes true epochs (Screening, Wash out, Follow-up/ED, Additional Follow-up) with the two crossover treatment periods (Period 1, Period 2).
  - rationale: Chosen as the topmost column-distinguishing row; the report records that 'period' is defensible and flags the call.
- **JDG** _Table_01_ note1 was left table-scoped, anchored to schedule_property row 2, rather than being linked to the specific procedures it names (ECG / Vital Signs / PK / Plasma Glucose).
  - rationale: The note is genuinely table-wide and no element carries the marker, so table scope is the honest scope; the anchor exists only for traceability.
- **JDG** _Table_01_ c16 (Clinical Lab Tests) and c23 (Anti-glucagon Antibodies) were classified 'footnote' and NOT split, even though each embeds a section reference; only the pure references c5 and c15 were classified 'source_note'.
  - rationale: c16 and c23 are primarily explanatory with an embedded reference; c5 ('Refer to Section 9.5.5.1.') and c15 ('See Appendix 2 ... for details.') are pure cross-references.
- **JDG** _Table_01_ c16 was kept as a SEPARATE annotation from c15 even though c15's text is contained in c16's - c16 is the longer Appendix-2 variant with fasting instructions on the Clinical Lab Tests row (23).
  - rationale: They are two genuinely different note cells in the Comments column, not one note split across rows.
- **JDG** _Table_01_ The Abbreviations block was not captured at all, rather than being emitted with synthesized links to the label rows where each term appears.
  - rationale: The terms carry no in-grid markers, so every entry would fail the >=1-marker_location rule and be dropped downstream; consistent with prior extractions. The report explicitly offers the alternative.
- **Δ** The Comments-column notes c1-c25 were bounded without any recorded geometry method; the report describes them only as 'each distinct note became a synthesised annotation'.
  - expect: Each note's TEXT must now be bounded by the notes column's rule-line geometry (vector rules, or raster-recovered rules per 1d). Note boundaries - and therefore the exact text of some c-series annotations, and possibly the count of distinct notes - may legitimately change. If rules are genuinely unrecoverable, annotation_text_source.method must be set to 'proximity_bounded' on each affected note.
  - rule: Section 6, 'Notes / Instructions / Comments column' + section 1d
- **Δ** Every c1-c25 marker is synthesised (the source Comments column prints no markers) but no marker_locations entry carries a method field.
  - expect: Each synthesised c-series marker_location should now carry method: "synthesized"; a location bound by word overlap rather than position should carry method: "text_match" (candidates: the c15 rows 22/24 and c19 rows 27/28 dedup links). Every non-default method must also appear as a line in the new report.
  - rule: Sections 1e (marker_locations[].method) and 6; section 7 method-provenance bullet
- **Δ** c15's text is a strict substring of c16's text - an annotation-containment pair that the v3.0.2 extraction deliberately kept.
  - expect: The v3.6.0 delivery check explicitly rejects containment pairs, so the new run will surface this pair. Expect it to be re-examined and explained in the report. If the new run MERGES c15 and c16, that contradicts an already-reasoned decision (two distinct note cells) and needs human review, not automatic acceptance.
  - rule: Section 8 ('no annotation's text is contained in another's') and section 7 annotation-text-integrity bullet
- **Δ** No activity carries a source_page field, and the report gives no activity-rows-per-page breakdown for pages 11-18.
  - expect: Every activity should carry source_page in the 11-18 numbering, and the new report must break activity rows down per page across all eight pages, calling out any page that contributed none.
  - rule: Section 4 (source_page + coverage check) and section 7
- **Δ** The two synthesized schedule_property names ('Period', 'Study Day') are flagged synthesized:true but carry no structure_method.
  - expect: structure_method (inferred_from_layout / assumed) should now be set where property_type or hierarchical_level do not come from printed header labels - row 1's label cell is empty and row 2's reads 'Procedure', so both qualify.
  - rule: Sections 3 and 1e (schedule_property.structure_method)
- **Δ** The 3 section-header rows (rows 1, 21, 33) and 33 child activities carry indentation_level with no recorded derivation method.
  - expect: activity_name_source.indentation_method should be recorded where the level does not come from text-layer whitespace.
  - rule: Sections 4 and 1e (indentation_method)

### NCT03548935

1 table(s): T1 main_soa pp8-13 (78a/428m/37n)

- **INV** _Table_01_ Exactly one table is extracted and its table_type is main_soa.
  - check: Exactly one file NCT03548935_Table_*_extraction.json exists; table_metadata.table_type == "main_soa".
- **INV** _Table_01_ 78 activity rows, composed of 6 grey section headers + 6 sub-headers + 66 leaf activities.
  - check: len(activities) == 78; count of activities with activity_name_source.indentation_level == 0 is 6.
- **INV** _Table_01_ 25 visit columns, 100 header-grid cells, 428 activity-by-visit marks, 7 footnote annotations.
  - check: len(schedule_grid) == 100; len(activity_schedule) == 428; count of annotations with annotation_type == "footnote" == 7; distinct schedule_grid column_position values == {2..26} (25 columns).
- **INV** _Table_01_ The SoA occupies exactly 6 flowchart pages, document pages 8-13; no page is missing.
  - check: table_metadata.page_start == 8 and table_metadata.page_end == 13.
- **INV** _Table_01_ The header (phase / Visit / Weeks / Window) reprints at every page break but is encoded only once - 4 schedule_property rows, not 4 per page.
  - check: len(schedule_properties) == 4; no duplicated schedule_grid entries for the same (row_position, column_position).
- **INV** _Table_01_ Column model: 25 visit columns, grid col = visit index + 1 (V1 -> col 2 ... V25 -> col 26).
  - check: schedule_grid column_position range is 2..26 with no gaps; the visit-property row's cell_value at column 2 is V1 and at column 26 is V25.
- **INV** _Table_01_ "Dose escalation period" is a merged epoch cell distributed across grid cols 4-11.
  - check: schedule_grid has 8 entries with cell_value "Dose escalation period", column_position 4..11, is_merged_cell true, merged_cell_range "4:11".
- **INV** _Table_01_ "Maintenance period" is a merged epoch cell distributed across grid cols 12-24.
  - check: schedule_grid has 13 entries with cell_value "Maintenance period", column_position 12..24, merged_cell_range "12:24".
- **INV** _Table_01_ Screening, Randomisation, End of treatment and End of trial each occupy a single (non-merged) column.
  - check: schedule_grid epoch-row entries with those cell_values have is_merged_cell falsy / no merged_cell_range.
- **INV** _Table_01_ Randomisation is V2 at week 0 (grid col 3), not V12 as in the sister trial NCT03548987.
  - check: schedule_grid epoch-row cell at column_position 3 has cell_value "Randomisation"; visit-row cell at column 3 is V2 and week-row cell at column 3 is 0.
- **INV** _Table_01_ Six level-0 grey section headers exist with these names: SUBJECT RELATED INFORMATION AND ASSESSMENTS, EFFICACY, SAFETY, OTHER ASSESSMENTS, TRIAL MATERIAL, REMINDERS.
  - check: The set of activity_name values with activity_name_source.indentation_level == 0 equals exactly those six strings.
- **INV** _Table_01_ IWQoL-Lite for CT and PGI-S are TWO separate activity rows (not one merged row), carrying identical marks at V2, V6, V10, V12, V16, V20, V24 (grid cols 3, 7, 11, 13, 17, 21, 25).
  - check: activities[] contains a row whose activity_name starts "Impact of weight on quality of life" AND a separate row "Patient Global Impression of Status (PGI-S)"; the sorted column_position list of activity_schedule for each is [3,7,11,13,17,21,25].
- **INV** _Table_01_ Footnote e is CELL-level on the DEXA scan V1 cell (grid col 2), location_type schedule_cell - not an activity-name footnote.
  - check: annotation with annotation_marker "e" has exactly one marker_location with location_type "schedule_cell" and column_position 2, whose row_position is the DEXA scan row; that activity_schedule entry carries annotation_markers "e".
- **INV** _Table_01_ Footnote g is CELL-level on the "Attend visit fasting" V25 cell (grid col 26), location_type schedule_cell.
  - check: annotation with annotation_marker "g" has a marker_location with location_type "schedule_cell" and column_position 26 on the "Attend visit fasting" row; that activity_schedule entry carries annotation_markers "g".
- **INV** _Table_01_ Footnote b ("For all female subjects.") binds to four activities: Childbearing potential, History of Breast Neoplasm, ICIQ-UI-SF, Breast neoplasms follow-up.
  - check: annotation "b" has 4 marker_locations, all location_type activity_name, resolving to those four activity_name values; each of those activities' annotation_markers contains "b".
- **INV** _Table_01_ Footnote d ("DEXA scan is performed in a sub-population.") is an ACTIVITY-NAME footnote on DEXA scan, distinct from cell-level footnote e on the same row.
  - check: annotation "d" has a marker_location with location_type "activity_name" on the DEXA scan row; the DEXA scan activity's annotation_markers contains "d" but not "e".
- **INV** _Table_01_ No scheduling marks land on section-header or sub-header rows.
  - check: No activity_schedule entry has a row_position belonging to an activity with indentation_level 0, nor to the six named sub-header rows.
- **INV** _Table_01_ Visit windows: V1 "-7 to 0", V2 "+/-0", V3-V24 "+/-3", V25 "0 to +5".
  - check: On the window schedule_property row: col 2 == "−7 to 0", col 3 == "±0", cols 4..25 == "±3", col 26 == "0 to +5".
- **INV** _Table_01_ "First date on trial product" is marked at V3, randomisation-criteria at V2, and the "Evaluation of..." rows at P13 (week 24) plus V24 - visually confirmed against the narrow left columns.
  - check: activity_schedule for "First date on trial product" has column_position 4 (V3); for each "Evaluation of ..." row the column set includes 14 (P13) and 25 (V24).
- **INV** _Table_01_ No orphan annotations: all 7 footnotes are referenced and every marker resolves to a defined annotation.
  - check: Every annotation has len(marker_locations) >= 1; every marker string appearing in any annotation_markers field is defined by an annotation.
- **JDG** _Table_01_ DEXA scan was assigned indentation_level 1 (standalone efficacy item) rather than being nested under the Clinical Outcome Assessments sub-group.
  - rationale: It sits flush-left in the render, but the report explicitly concedes the alternative reading and flags it for review - so a different call in the new extraction is a reviewable change, not an automatic improvement.
- **JDG** _Table_01_ Source spellings and casing were kept verbatim rather than corrected: "PK dairy" (not "PK diary"), "Systolic blood Pressure" (lowercase blood), "Anti-Semaglutide Antibody".
  - rationale: Per the transcribe-do-not-infer principle the printed text is the data; silently correcting them would diverge from the source.
- **JDG** _Table_01_ Duplicate sub-headers were retained as printed: Vital Signs appears twice (under EFFICACY and under SAFETY) and Clinical Outcome Assessments appears twice (9.1.2 efficacy, 9.4.1 safety).
  - rationale: They are printed twice in the source flowchart; de-duplicating them would drop a real row and re-parent its children.
- **JDG** _Table_01_ The two adjacent x-strips that the rotated parser had merged were split into the separate IWQoL-Lite and PGI-S rows.
  - rationale: The merge was a rotation-parser artefact; the split was confirmed against the page-3 render. A fresh extraction that emits one combined row is reproducing the artefact.
- **JDG** _Table_01_ Marks were reconstructed with a rotation-aware bbox parser (activity = page-x strip, 25 visit y-centres from the week numbers) and validated visually against renders of all six pages, because the flowchart is printed landscape (rotated 90 CCW).
  - rationale: The standard row-clustering bbox helper does not apply to a rotated flowchart; the method choice determines the whole mark matrix.
- **Δ** Sub-headers recorded with inline section numbers and "Retained as printed": Body measurements (9.1.1); Vital Signs (9.4.3); Clinical Outcome Assessments (9.1.2 / 9.4.1); Administration of trial product (7.1, 7.5).
  - expect: activity_name must be stripped of the inline reference ("Body measurements", "Administration of trial product"), the reference kept in activity_name_source.cell_text, and each distinct reference emitted as a deduplicated source_note annotation with a synthesised pr-marker added to every citing activity's annotation_markers. Labels carrying two references (7.1, 7.5) split into two notes. Consequence: total annotation count will greatly exceed the report's "7 footnotes" (the current JSON already carries pr1-pr30 alongside footnotes a-g); this is a delta versus the report text, not a regression.
  - rule: §6 - "a section/appendix/attachment reference printed inline in an activity's label (e.g. "Inclusion criteria (6.1)" ... Strip inline references OUT of `activity_name` ... add a synthesised marker (`pr1`, `pr2`, …)"
- **Δ** The report gives whole-table counts only; it does not attribute activity rows to individual document pages 8-13.
  - expect: Every activity should carry source_page, and the new uncertainty report must state activity rows per page across pages 8-13 and call out any page contributing none. The existing JSON has no source_page field on any of the 78 activities.
  - rule: §4 - "**source_page** — record the document page each row was read from ... **Then check coverage before delivering: every page in the declared range must contribute rows.**" and §7 "activity rows per page across the declared page range"
- **Δ** The rotated bbox reconstruction and the indentation reading are described in prose only; no provenance fields exist in the JSON.
  - expect: Non-default methods should now be recorded in schema provenance fields - e.g. activity_name_source.indentation_method (visual_estimate / font_signal) where indentation came from the render rather than text-layer whitespace, and schedule_property.structure_method for the synthesised Study Phase row - with one report line each. Currently the JSON contains no "method" key at all.
  - rule: §1e - "Every interpreted value has a default method; when you arrive at a value any other way, record the method in the schema's provenance fields"; §7 "**Method provenance:** every non-default method recorded (§1e)"
- **Δ** Report lists 7 footnotes a-g with 5 activity-level and 2 cell-level bindings, and states all markers resolve.
  - expect: v3.6.0 additionally requires that every marker in an annotation's marker_locations also appears in that row's annotation_markers string (the field resolve actually reads). Expect this to be asserted explicitly for the two schedule_cell bindings e and g; a location recorded only on the annotation side would now be a defect.
  - rule: §6 - "**`annotation_markers` and `marker_locations` must agree — the first one is what actually binds.**" and §8 "every marker in an annotation's `marker_locations` also appears in that row's `annotation_markers`"

_Notes:_ Report is clean on source defects - it states "## SOURCE ISSUE — none" and "No missing page. **No `_soa.pdf` regeneration needed.**", so source_defects is deliberately empty. Grounding checks run against NCT03548935_Table_01_extraction.json confirm: 78 activities, 100 schedule_grid cells, 428 activity_schedule entries, 4 schedule_properties, 37 annotations (7 footnote + 30 source_note pr1-pr30), merged ranges 4:11 (8 cells) and 12:24 (13 cells), annotation e at schedule_cell row 45 col 2, annotation g at schedule_cell row 82 col 26, rows 40/41 both with columns [3,7,11,13,17,21,25]. The 30 pr source_notes are NOT described in the report - the JSON was evidently updated after the report was written - so the "7 footnotes" count is an invariant on annotation_type footnote only, not on total annotations.

### NCT03548987

1 table(s): T1 main_soa pp8-11 (69a/378m/33n)

- **INV** _Table_01_ Exactly one table, table_type main_soa.
  - check: Exactly one NCT03548987_Table_*_extraction.json; table_metadata.table_type == "main_soa".
- **INV** _Table_01_ 69 activity rows: 58 carry marks, 11 are header/sub-header rows.
  - check: len(activities) == 69; the number of distinct row_position values in activity_schedule == 58; the remaining 11 rows carry no activity_schedule entries.
- **INV** _Table_01_ 25 visit columns, 100 header-grid cells, 378 activity-by-visit marks, 4 footnote annotations.
  - check: len(schedule_grid) == 100; len(activity_schedule) == 378; annotations with annotation_type "footnote" == 4; schedule_grid column_position set == {2..26}.
- **INV** _Table_01_ The SoA occupies exactly 4 flowchart pages, document pages 8-11; nothing is missing.
  - check: table_metadata.page_start == 8 and page_end == 11.
- **INV** _Table_01_ The repeating page header is encoded once - four schedule_property rows total.
  - check: len(schedule_properties) == 4; no duplicate (row_position, column_position) pairs in schedule_grid.
- **INV** _Table_01_ Four header rows in order: Study Phase (epoch, synthesized name), Visit(V)/Phone (P) (visit), Timing of Visit (Weeks) (week), Visit Window (Days) (window). Rows 2-4 take property_name directly from the source label column.
  - check: schedule_properties[0].property_type == "epoch" with property_name_source.synthesized == true; the other three have property_type visit / week / window and synthesized not true.
- **INV** _Table_01_ Column model: 25 visit columns, grid col = visit index + 1 (V1 -> col 2 ... V25 -> col 26).
  - check: schedule_grid column_position range 2..26 contiguous; visit row col 2 == V1, col 26 == V25.
- **INV** _Table_01_ "Run-in" is a merged epoch cell distributed across grid cols 3-12.
  - check: schedule_grid has 10 entries cell_value "Run-in", column_position 3..12, merged_cell_range "3:12".
- **INV** _Table_01_ "Maintenance period" is a merged epoch cell distributed across grid cols 14-24.
  - check: schedule_grid has 11 entries cell_value "Maintenance period", column_position 14..24, merged_cell_range "14:24".
- **INV** _Table_01_ Randomisation is V12 at week 20 and occupies the single grid col 13; Screening, End of treatment and End of trial are likewise single columns. ⚠️
  - check: schedule_grid epoch row: col 13 cell_value "Randomisation" with no merged_cell_range; visit row col 13 == V12, week row col 13 == 20.
- **INV** _Table_01_ Five level-0 grey full-width section headers: SUBJECT RELATED INFORMATION AND ASSESSMENTS, EFFICACY, SAFETY, TRIAL MATERIAL, REMINDERS (note: no OTHER ASSESSMENTS here, unlike the sister trial).
  - check: The set of activity_name values with activity_name_source.indentation_level == 0 has size 5 and equals exactly those names.
- **INV** _Table_01_ Footnotes a-d are ALL activity-level (marker_locations at activity_name); there are no cell-level and no header-cell footnotes in this flowchart.
  - check: No annotation has a marker_location with location_type "schedule_cell" or "schedule_property"; no activity_schedule or schedule_grid entry carries a non-empty annotation_markers for a-d.
- **INV** _Table_01_ Every grid cell value is a plain "X" - no timepoint text, no legend symbols.
  - check: set(entry.cell_value for entry in activity_schedule) == {"X"}.
- **INV** _Table_01_ Footnote b ("For all female subjects") binds to exactly three activities: Childbearing potential, History of Breast Neoplasm, Breast neoplasms follow-up.
  - check: annotation "b" has exactly 3 marker_locations, all location_type activity_name, on those three activity_name values; each of those activities' annotation_markers contains "b".
- **INV** _Table_01_ Footnote c ("If subjects not fulfil randomisation criteria see Section 6.3.2") binds to the "Randomisation criteria and randomisation" row.
  - check: annotation "c" has a marker_location on the activity named "Randomisation criteria and randomisation"; that row's annotation_markers contains "c".
- **INV** _Table_01_ ECG is marked at V2 with Screening (V1) empty; Physical examination is marked at V1; "First date on trial product" is marked at P3 (week 2), the clinically-surprising placement the source actually shows.
  - check: activity_schedule for "ECG" includes column_position 3 and excludes 2; for "Physical examination" includes 2; for "First date on trial product" the only column_position is 4.
- **INV** _Table_01_ The "Evaluation of ..." rows are marked at V13 (grid col 14, week 24) plus V24 (grid col 25), NOT at V12 / Randomisation (grid col 13, which is empty for these rows).
  - check: For each activity whose name starts "Evaluation of", the activity_schedule column_position set contains 14 and 25 and does NOT contain 13.
- **INV** _Table_01_ No scheduling marks land on header or sub-header rows.
  - check: No activity_schedule row_position matches an activity with indentation_level 0 or one of the four named sub-header rows.
- **INV** _Table_01_ No orphan annotations - footnotes a-d are all referenced and every activity marker resolves.
  - check: Every annotation has len(marker_locations) >= 1; every marker token in any annotation_markers field is defined by some annotation.
- **JDG** _Table_01_ Marks were reconstructed from the PDF by clustering words into page-x strips and binning each X to the nearest of 25 visit y-centres; the transposed markdown flowchart was explicitly NOT used for marks.
  - rationale: The flowchart is printed landscape (rotated 90 CCW) so the standard row-clustering bbox helper does not apply; the transposed markdown would have produced a different (and unverified) matrix.
- **JDG** _Table_01_ The SPS-6 label was normalised from the wrapped source text "SPS- 6" to "Stanford Presenteeism Scale (SPS-6)".
  - rationale: The hyphen-space is a line-wrap artefact, not source spelling. A fresh extraction that emits "SPS- 6" is reproducing the wrap artefact; one that renames it differently is a reviewable change.
- **JDG** _Table_01_ The PHQ-9 activity name keeps its source en-dash ("– 9") verbatim, and the stray numeric "9" token from the name was excluded from the cell values.
  - rationale: En-dash is real source typography; the stray "9" token is a text-layer artefact that would otherwise be binned as a grid value.
- **JDG** _Table_01_ The duplicate sub-headers "Vital Signs" and "Clinical Outcome Assessments" were retained as two separate rows each - once under EFFICACY and once under SAFETY.
  - rationale: That is how the source prints them; collapsing them would drop a row and re-parent its children.
- **JDG** _Table_01_ The Study Phase header row's property_name was synthesised because the label cell (col 1) is blank.
  - rationale: The row carries schedule data spanning columns but prints no label; a synthesised name preserves the epoch row rather than dropping it.
- **Δ** Activity and sub-header labels are recorded with their inline section references intact - e.g. the report cites "Vital Signs (6.4.2, 9.4.3)" as the row name, and counts only "4 footnotes".
  - expect: Inline section/appendix references must be stripped out of activity_name into activity_name_source.cell_text, emitted as deduplicated source_note annotations with synthesised pr-markers, and multiple references on one label split into separate notes ("Vital Signs (6.4.2, 9.4.3)" -> pr for 6.4.2 and pr for 9.4.3). Total annotation count will therefore far exceed 4; the current JSON already carries pr1-pr29. Expected delta versus the report, not a regression.
  - rule: §6 - "Strip inline references OUT of `activity_name` (keep them in `activity_name_source.cell_text`), emit each as a `source_note` deduplicated by text ... Split multiple references on one label into separate notes."
- **Δ** Report gives no per-page row attribution for document pages 8-11 and the JSON has no source_page on any of the 69 activities.
  - expect: Each activity should carry source_page, and the new report must state activity rows per page over pages 8-11 and flag any page contributing none.
  - rule: §4 - "**source_page** — record the document page each row was read from ... every page in the declared range must contribute rows"; §7 "activity rows per page across the declared page range"
- **Δ** Study Phase is described as a synthesized property_name; no structure_method is recorded anywhere in the JSON.
  - expect: Where property_type or hierarchical_level come from layout geometry rather than a printed header label, structure_method (inferred_from_layout / assumed) should now be set on the schedule_property, and the report must list every non-default method one line each.
  - rule: §3 - "When `property_type` or `hierarchical_level` come from layout geometry or working assumption rather than printed header labels, set `structure_method`"; §1e / §7 method provenance
- **Δ** Indentation was read from the rendered landscape flowchart; no indentation_method is recorded.
  - expect: activity_name_source.indentation_method should be set (visual_estimate / font_signal) since the three indent levels come from shading and render position, not text-layer whitespace.
  - rule: §4 - "When the level does not come from text-layer whitespace, set `activity_name_source.indentation_method` (`font_signal` / `visual_estimate` / `assumed_flat` for flat tables)"

_Notes:_ No source defects: the report has an explicit "## SOURCE ISSUE — none" section stating "No missing page. The full flowchart is present." Grounding checks against NCT03548987_Table_01_extraction.json confirm 69 activities, 100 schedule_grid cells, 378 activity_schedule entries, 4 schedule_properties (Study Phase synthesized true), 33 annotations (4 footnote a-d + 29 source_note pr1-pr29), merged ranges 3:12 (10 cells) and 14:24 (11 cells), "First date on trial product" sole column 4, ECG columns [3,13,25], Physical examination [2,13,25], the three "Evaluation of" rows all containing 14 and 25 and none containing 13. As with the sister trial, the pr source_notes post-date the report.

### NCT03637764

1 table(s): T1 main_soa pp18-21 (29a/159m/11n)

- **INV** _Table_01_ Exactly one table, table_type main_soa, Section 1.3, document pages 18-21 (soa PDF pp.1-4).
  - check: One extraction file; table_metadata.table_type == "main_soa"; page_start == 18 and page_end == 21.
- **INV** _Table_01_ Three header property rows: Phase (epoch), Sub-phase (period), Timing (study_day).
  - check: len(schedule_properties) == 3 with property_type values epoch, period, study_day in that order.
- **INV** _Table_01_ 10 schedule columns (col2-col11): Screening D-28->D-15, Screening D-14->D-1, Cycle 1 D1/D8/D15, Cycle 2+ D1, EOT, Safety At-60, Safety At-90, Survival Every-90. The rightmost Notes column is EXCLUDED from the grid and captured as annotations.
  - check: schedule_grid column_position set == {2..11} (30 cells = 3 properties x 10 columns); no activity_schedule entry has column_position > 11; no activity named "Notes"/"Comments".
- **INV** _Table_01_ 29 activities. Two organisational headers - Laboratory Assessments (r8) and Disease Assessment (r17) - carry no marks.
  - check: len(activities) == 29; activities at row_position 8 and 17 are "Laboratory Assessments" and "Disease Assessment"; no activity_schedule entry has row_position 8 or 17.
- **INV** _Table_01_ r7 12-Lead ECG: "As clinically indicated" spans c7:c8 (Cycle 2 + EOT) - a correction over the prior Excel-first raw which had c7 only.
  - check: activity_schedule row_position 7 has two entries cell_value "As clinically indicated" at column_position 7 and 8, both source_range "7:8".
- **INV** _Table_01_ r13 Coagulation (HCC/SCCHN/EOC): "As clinically indicated" spans c7:c8, and Cycle 1 (c4-c6) is grey with NO marks - corrected from the prior [4:7].
  - check: activity_schedule row_position 13: entries only at column_position 3, 7, 8; the 7 and 8 entries have cell_value "As clinically indicated" and source_range "7:8"; no entries at 4, 5, 6.
- **INV** _Table_01_ r23 AE/SAE Assessment: "X (ongoing related AEs...)" spans c9:c11 including Survival - corrected from the prior [9:10].
  - check: activity_schedule row_position 23 has three entries at column_position 9, 10, 11 whose cell_value starts "X (ongoing related AEs" and whose source_range is "9:11".
- **INV** _Table_01_ r24 Prior/Concomitant Medication: "X (related to AE/SAEs listed above)" spans c9:c11 - corrected from the prior [9:10].
  - check: activity_schedule row_position 24 has entries at column_position 9, 10, 11 with cell_value "X (related to AE/SAEs listed above)" and source_range "9:11".
- **INV** _Table_01_ Ten rows carry a merged screening X spanning [2:3]: r1 Informed consent, r2 Demography, r4 Height, r5 Vital Signs, r6 Resting O2, r7 12-Lead ECG, r15 Serology, r18 CT/MRI, r23 AE/SAE, r24 Prior/Concom.
  - check: For each of row_position 1,2,4,5,6,7,15,18,23,24 there are activity_schedule entries at BOTH column_position 2 and 3 with source_range "2:3".
- **INV** _Table_01_ Eight rows carry a SINGLE col3 screening mark, not a merged [2:3]: r3 Physical exam, r10 Blood chem, r11 Hematology, r12 Coag-GBM, r13 Coag-HCC, r16 Urinalysis, r9 Pregnancy, r19 Brain MRI - distinguished by bbox x-position (x~198 vs merged-boundary x~184).
  - check: For each of row_position 3,9,10,11,12,13,16,19 there is an activity_schedule entry at column_position 3 and NO entry at column_position 2.
- **INV** _Table_01_ r16 Urinalysis carries "As clinically indicated" spanning [5:7].
  - check: activity_schedule row_position 16 has entries at column_position 5, 6, 7 with cell_value "As clinically indicated" and source_range "5:7".
- **INV** _Table_01_ "Continuously throughout period" spans [4:8] on both r23 AE/SAE and r24 Prior/Concom.
  - check: rows 23 and 24 each have five activity_schedule entries at column_position 4..8 with cell_value "Continuously throughout period" and source_range "4:8".
- **INV** _Table_01_ r18 CT/MRI, r19 Brain MRI and r20 AFP/CA125 carry "X (Weeks ...)" at c7, "X (if necessary)" at c8, and "X (until PD is confirmed ...)" spanning [10:11]; c9 (At-60) is empty for these rows - confirmed.
  - check: For row_position 18, 19, 20: entries at column_position 10 and 11 with source_range "10:11"; NO entry at column_position 9.
- **INV** _Table_01_ r14 Blood Typing Interference Test carries "Cycle 2 Day 1 only" in the single wide Cycle-2 column c7.
  - check: activity_schedule row_position 14 has an entry at column_position 7 with cell_value "Cycle 2 Day 1 only".
- **INV** _Table_01_ "See Pharmacokinetics and immunogenicity Flow Chart" is distributed across [2:11] on r25 PK and r26 ADA; "See Biomarker Flow Chart" across [2:11] on r27 Tumor Biopsy.
  - check: rows 25, 26, 27 each have exactly 10 activity_schedule entries at column_position 2..11 with source_range "2:11" and the corresponding cell_value text.
- **INV** _Table_01_ 11 annotations, all resolving, no orphans: a, b, c (printed footnote letters) plus n1-n8.
  - check: len(annotations) == 11; annotation_marker set == {a,b,c,n1..n8}; every annotation has len(marker_locations) >= 1.
- **INV** _Table_01_ Annotation a ("A cycle is 21 days") binds to the Treatment-Phase header cells c4-c7, i.e. per-column header cells, not the whole property row.
  - check: annotation "a" has 4 marker_locations with column_position 4,5,6,7; the schedule_grid cells at row_position 1 columns 4-7 (cell_value "Treatment Phase", merged_cell_range "4:7") each carry annotation_markers "a".
- **INV** _Table_01_ Annotation b (WOCBP negative pregnancy test) binds to the Pregnancy test activity label (r9).
  - check: annotation "b" has one marker_location location_type activity_name row_position 9; that activity's annotation_markers == "b".
- **INV** _Table_01_ Annotation c ("evaluation not applicable for Cohort E") binds to exactly 16 schedule_cell locations: rows 3, 4, 5, 6, 10, 11, 12, 21 crossed with columns 5 and 6.
  - check: annotation "c" has exactly 16 marker_locations, all location_type schedule_cell, with (row_position, column_position) == the 8x2 cross product of {3,4,5,6,10,11,12,21} x {5,6}.
- **INV** _Table_01_ n1-n7 are Notes-column section cross-references typed source_note (8.2.1, 8.2.2, 8.2.3, 10.3 Table 12, 10.3, "10.3 Before each transfusion", 8.1); n8 ("Informed consent may be signed prior to D-28") is a footnote, not a source_note.
  - check: annotations n1..n7 have annotation_type "source_note"; n8 has annotation_type "footnote" and text about informed consent prior to D-28.
- **INV** _Table_01_ A Notes cell spanning several activity rows is ONE annotation with a marker_location per covered row - e.g. n5 "Section 10.3" carries locations on rows 11, 12, 13, 15, 16 rather than being duplicated as five annotations. ⚠️
  - check: No two annotations share identical annotation_text; n5 has >1 marker_location; each row cited by n5 carries "n5" in its annotation_markers.
- **INV** _Table_01_ All 25 activities other than the four corrected rows reproduced the prior raw's marks exactly, having been independently re-derived from the PDF.
  - check: Diff the new activity_schedule against NCT03637764_Table_01_extraction.json; only rows 7, 13, 23, 24 should have been points of historical divergence - any NEW divergence on the other 25 rows needs justification.
- **INV** _Table_01_ Column boundaries were fixed from pdftotext -bbox header day-labels and confirmed by detected vertical rule-line geometry - 11 column boundaries for cols 2-11 plus the excluded Notes column.
  - check: New report must state the same bbox/rule-line method for column boundaries and produce the same 10 schedule columns.
- **SRC** _Table_01_ The Notes column in the source prints no footnote marker letters at all, so the n1-n8 markers do not exist in the PDF - they were synthesised by the extraction.
  - expected handling: The new extraction must again synthesise markers for the Notes-column entries, link them via marker_locations to the rows they sit beside, set method "synthesized" on those locations (§1e/§6), and record the synthesised markers in the report. It must NOT present them as printed source markers, and must not drop the notes for lack of a marker.
- **SRC** _Table_01_ PDF page 5 of NCT03637764_soa.pdf (document page 22, printed "Page 22") is a schedule page inside the SoA PDF that belongs to no extraction - flagged by soa2usdm-row-audit.
  - expected handling: The new extraction must again account for this page explicitly in the uncertainty report (either extract it or state why it is out of scope). Silently ignoring it, or silently absorbing its rows into the main SoA, are both regressions.
- **JDG** _Table_01_ The PK (r25), ADA (r26) and Tumor Biopsy (r27) flow-chart pointers were modelled as distributed cell_values across [2:11] per prompt §5, and the prior raw's n9/n10 "See ... Flow Chart" source_note annotations were REMOVED.
  - rationale: They are merged text cells spanning all schedule columns, so §5's merged-text-cell rule applies; the report explicitly names the alternative §6 source_note reading and flags the choice for human review.
- **JDG** _Table_01_ The PHARMACOKINETICS AND IMMUNOGENICITY FLOW CHART on document page 22 was deliberately left out of scope, as was the Biomarker Flow Chart.
  - rationale: Its rows are sample types and its cells carry sample IDs and dosing-relative time windows ("SOI", "EOI +30 min", "S00", "P00", "AS00"), i.e. study timing rather than a schedule of activities, which the three-layer model does not carry today.
- **JDG** _Table_01_ The rightmost Notes column was excluded from the schedule grid and its content captured as annotations instead of as schedule columns or activity rows.
  - rationale: A notes column is not a schedule column and not an activity; each non-empty note becomes an annotation.
- **JDG** _Table_01_ Merged cell spans were resolved from per-row vertical rule-line detection (a missing internal boundary = a merge), cross-checked against direct visual reads, with the two "As clinically indicated" rows and the AE/SAE and Prior right-hand cells additionally verified on high-zoom crops - rather than from where the glyph visually sits.
  - rationale: Glyph position centres a merged mark on one column and destroys the real span; rule-line geometry is the evidence. This method choice produced the four corrections over the Excel-verified prior raw.
- **Δ** n1-n8 are synthesised markers, but the JSON records no method on any marker_location (no "method" key exists anywhere in the file).
  - expect: Every synthesised Notes-column marker location should now carry method: "synthesized"; a binding established by word overlap gets "text_match"; an undeterminable target gets location_type "unresolved" instead of a guess. The report must list each non-default method one line each.
  - rule: §6 - "If the source gives the note no marker, synthesise one and link it via `marker_locations` to the row it sits beside ... with `method: \"synthesized\"` on the location"; §1e and §7 method provenance
- **Δ** Annotation texts n4 "See Section 10.3 Table 12", n5 "Section 10.3" and n6 "Section 10.3  Before each transfusion." - n5's text is a substring of both n4's and n6's.
  - expect: v3.6.0 treats a containment pair as evidence that one note cell was split across rows, and forbids it at delivery. Expect the new extraction to either re-bound these notes from the Notes column's horizontal rule-line geometry (producing different note boundaries / different row bindings for rows 10-16) or to explicitly justify the containment in the report. Different n-numbering or a different rows-per-note split here is an expected delta, not a regression - but the union of covered rows {10,11,12,13,14,15,16} should still be covered.
  - rule: §6 - "**Bound each note's TEXT by the cell's rule-line geometry, not by proximity**"; §8 - "no annotation's text is contained in another's — a containment pair means one note cell was split across rows (§6)"; §7 "any pair of annotations whose text substantially overlaps"
- **Δ** The flow-chart-pointer modelling was flagged as an open judgement call: "Alternative reading (§6) would keep them as `source_note` cross-references on the activity label. Flagging for your call."
  - expect: v3.6.0 §5 now settles this by rule in favour of the distributed cell_value reading, so it should no longer appear as an open judgement call. Re-introducing n9/n10 "See ... Flow Chart" source_note annotations, or collapsing the [2:11] span, would now be a rule violation rather than an alternative reading. Note that §6's source_note definition covers section/appendix references, not flow-chart pointers.
  - rule: §5 - "The same applies to merged text cells such as \"See instructions\" / \"See Section x.y\": one entry per covered column, `source_range` set."
- **Δ** The report states the table spans document pp.18-21 but gives no per-page activity attribution, and the JSON has no source_page on any of the 29 activities.
  - expect: Each activity should carry source_page, and the report must state activity rows per page across 18-21, calling out any page that contributed none.
  - rule: §4 - "**source_page** — record the document page each row was read from ... every page in the declared range must contribute rows"; §7 "activity rows per page across the declared page range"
- **Δ** All three schedule_properties in the JSON have property_name_source.synthesized true, but the report describes them only as "Header: 3 property rows — Phase (`epoch`), Sub-phase (`period`), Timing (`study_day`)" without noting synthesis or structure method.
  - expect: Synthesised property names must be documented in the report, and structure_method (inferred_from_layout / assumed) set where property_type or hierarchical_level do not come from printed header labels.
  - rule: §3 - "If the label cell is empty but the row clearly carries schedule data spanning columns, synthesise `property_name` and set `property_name_source.synthesized: true`. Synthesised names are fine; document them in the report." and the structure_method bullet; §7 "**Synthesised:** any synthesised `property_name` values"
- **Δ** by_type distribution: 7 of 11 annotations are source_note (n1-n7), 4 are footnote.
  - expect: v3.6.0 warns that a notes/comments column should yield footnotes and that an all-source_note by_type is degenerate. The check only bites above 20 annotations, so 11 annotations at 7 source_note / 4 footnote does not trip it - but if the re-extraction pushes annotation count past 20, expect the type mix to be scrutinised and possibly re-typed. Flagging so a type-mix change is not read as a regression.
  - rule: §8 - "`by_type` is not degenerate across > 20 annotations — in particular NOT all `source_note`: a notes / comments column yields `footnote`s (§6). All-`footnote` IS normal."

_Notes:_ This report is explicitly a checkpoint: "**Checkpoint. Nothing committed / pipeline not run yet.** Preview raw in scratch, awaiting approval." and describes itself as a "single-pass v3.1.0 re-extraction" superseding a prior v2.8/v2.4 PDF->Excel->JSON raw. Grounding checks against NCT03637764_Table_01_extraction.json confirm: 29 activities, 3 schedule_properties, 30 schedule_grid cells (3 x cols 2-11), 159 activity_schedule entries, 11 annotations (4 footnote a/b/c/n8 + 7 source_note n1-n7), annotation c with exactly 16 schedule_cell locations, annotation a on schedule_grid row 1 cols 4-7 (merged_cell_range "4:7") with annotation_markers "a" already on the grid cells, rows 25/26/27 each with 10 entries source_range "2:11", rows 7 and 13 with "As clinically indicated" at cols 7-8 source_range "7:8", row 16 at cols 5-7 source_range "5:7", rows 23/24 with "Continuously throughout period" cols 4-8 and the right-hand cells at cols 9-11 source_range "9:11", row 14 "Cycle 2 Day 1 only" at col 7. Note n8 is typed footnote in the JSON although it sits in the n-series, matching the report.

### NCT03693430

1 table(s): T1 main_soa pp9-12 (63a/470m/30n)

- **INV** _Table 01_ Exactly one SoA table, classified main_soa, covering doc pages 9-12 (page_start=9, page_end=12).
  - check: Exactly one NCT03693430_Table_NN_extraction.json exists; table_metadata.table_type == "main_soa"; table_metadata.page_start == 9 and page_end == 12.
- **INV** _Table 01_ Section 2 Flowchart is the only SoA in the protocol; no second/subsidiary/continuation table should appear.
  - check: Count of *_Table_*_extraction.json files for NCT03693430 == 1.
- **INV** _Table 01_ 34 visit columns occupying schema column positions 2-35.
  - check: max(column_position) over schedule_grid == 35 and min == 2; distinct column_position count == 34.
- **INV** _Table 01_ Epoch row assignment: Screening col 2, Randomisation col 3, Dose escalation cols 4-11, Maintenance cols 12-33, End of treatment col 34, End of trial col 35.
  - check: schedule_grid row_position 1: cell_value at column_position 2 == "Screening", 3 == "Randomisation", 34 == "End of treatment", 35 == "End of trial".
- **INV** _Table 01_ Four header rows with property_type epoch / visit / week / window in that top-down order; row 1 property_name is synthesised.
  - check: len(schedule_properties) == 4; property_type values in row order == [epoch, visit, week, window]; schedule_properties[0].property_name_source.synthesized is true.
- **INV** _Table 01_ 63 activity rows: 5 ALL-CAPS section headers at indentation_level 0 (mark-free), 4 sub-parents at level 1 (mark-free), their children at level 2, all other rows level 1.
  - check: len(activities) == 63; exactly 5 activities with activity_name_source.indentation_level == 0; those 5 plus rows named Body measurements / Vital signs / Vital Signs / Administration of trial product have zero activity_schedule entries; Height, Body weight, Waist circumference, Systolic/Diastolic Blood Pressure, Pulse, Dispensing visit, Drug accountability at indentation_level 2.
- **INV** _Table 01_ Approximately 470 schedule marks in total (prior file has exactly 470 activity_schedule entries).
  - check: len(activity_schedule) is within a few percent of 470; any large drop means whole rows or a page were lost.
- **INV** _Table 01_ No scheduling marks sit on organizational (indentation_level 0) header rows, and there are no orphan annotations.
  - check: No activity_schedule entry whose row_position matches an activity with indentation_level == 0; every annotation has len(marker_locations) >= 1.
- **INV** _Table 01_ Control of Eating Questionnaire (CoEQ) carries exactly 4 marks, at V2, V12, V20 and V33 (schema columns 3, 13, 21, 34).
  - check: activity_schedule entries for the row whose activity_name starts "Control of Eating Questionnaire" == exactly column_position {3,13,21,34}.
- **INV** _Table 01_ Fasting serum insulin has exactly 2 marks, at V2 (Randomisation) and V33 (End of treatment) - it is genuinely sparser than the other quarterly labs and must NOT be pattern-completed.
  - check: activity_schedule for activity_name == "Fasting serum insulin" has exactly 2 entries, at column_position 3 and 34.
- **INV** _Table 01_ Quarterly labs mark clinic visits V12/V20/V28 while the three 'Evaluation of ...' rows mark the following phone visits P13/P21/P29 - the one-column offset is real, not a mis-binning.
  - check: Marks for HbA1c and for "Evaluation of lipid-lowering treatment" fall on different column_positions; the Evaluation rows' columns are the ones whose schedule_grid row 2 cell_value starts with "P" (P13/P21/P29) and row 3 weeks are 24/56/88.
- **INV** _Table 01_ Breast neoplasms follow-up and Colon neoplasms follow-up each carry marks only at End of treatment (V33, col 34) and End of trial (V34, col 35).
  - check: activity_schedule for "Breast neoplasms follow-up" and "Colon neoplasms follow-up" each == exactly column_position {34,35}.
- **INV** _Table 01_ The SoA PDF is genuinely image-based - no usable text layer - so marks must be reconstructed from the image, not parsed.
  - check: The new uncertainty report must state an image/raster mark-detection method (not a pdftotext -bbox text-layer method) for this study.
- **INV** _Table 01_ Mark detection used rule-line grid geometry plus a per-cell dark-pixel count, validated against direct visual reads on representative rows.
  - check: New report states the detector method and names the rows it validated against visual reads.
- **SRC** _Table 01_ The V33 (End of treatment) visit window is printed inconsistently in the repeated header: +/-3 on doc pages 9-10 and +/-5 on pages 11-12. Verified 2026-07-21 as an unresolvable source contradiction, not a scan artifact.
  - expected handling: The new extraction must still surface this contradiction in its uncertainty report and must not silently emit a single un-flagged window value. Mechanically: schedule_grid row_position 4 / column_position 34 cell_value should remain "±3" (first occurrence). If the new run emits "±5", or emits "±3" with no mention of the disagreement, that is a regression - a silent resolution of a real source defect.
- **SRC** _Table 01_ A redaction box covers the running-head document title at the top-right of every page. It is cosmetic and outside the table body.
  - expected handling: Must be recognised as running-head redaction, NOT as table content: no annotation should be created for it and no '[remainder redacted in source]' text should appear on any annotation. The report should still note it so a reviewer knows it was seen and dismissed deliberately.
- **SRC** _Table 01_ The protocol markdown carries no usable text version of the flowchart, so markdown cannot be used to confirm the row set or the grid.
  - expected handling: All 63 rows and all marks must come from the PDF image. If the new report claims markdown corroboration of the grid for this study, that claim is unfounded.
- **JDG** _Table 01_ The lowercase "x" used by the CoEQ row was transcribed literally as cell_value "x" rather than normalised to "X".
  - rationale: No legend distinguishes x from X in this table, so the case difference was judged stylistic but was preserved rather than silently normalised.
- **JDG** _Table 01_ Body measurements, Vital signs (x2) and Administration of trial product were placed at indentation_level 1 as mark-free sub-parents, with their children at level 2.
  - rationale: The levels were inferred from grey shading plus indentation and cross-checked against sister trials NCT03548987 / NCT03548935, not read from explicit numbering.
- **JDG** _Table 01_ The 'Breast neoplasms follow-up' row, which is physically laid out between the repeated epoch band and the Visit row on page 3, was kept as an ordinary SAFETY activity in reading order rather than treated as a header artefact.
  - rationale: Its odd vertical position is a repeated-header layout accident, not a change of role; dropping or re-ordering it would lose a real activity row.
- **JDG** _Table 01_ The 4-row header that reprints on doc pages 9-12 was de-duplicated and encoded once in a single table file.
  - rationale: One logical table spanning four pages, not four tables; the repeat is pagination.
- **JDG** _Table 01_ The V33 window was encoded as +/-3, the first-printed occurrence, and the ambiguity pushed downstream rather than being resolved.
  - rationale: Both values are legibly printed and the protocol body never restates the EOT window, so first-occurrence was chosen as a deterministic, defensible tie-break.
- **Δ** The report states that inline section/appendix references were kept inside activity_name and explicitly NOT modelled as source_note annotations.
  - expect: v3.6.0 requires stripping inline references OUT of activity_name (keeping them in activity_name_source.cell_text), emitting one deduplicated source_note per distinct reference, and adding synthesised pr1, pr2, ... markers to each citing activity. So activity_name should read "Inclusion criteria" not "Inclusion criteria (6.1)", and ~26 source_note annotations should appear. NOTE: the extraction JSON currently on disk (extractor string 'PDF->JSON v3.1.0 ... inline refs -> source_note', pr1-pr26 present) has ALREADY applied this rule - the report text is stale on this point. Judge the new output against the JSON, not against this report line.
  - rule: §6 - "A `source_note` is a cross-reference to elsewhere in the protocol ... **and** a section/appendix/attachment reference printed inline in an activity's label (e.g. \"Inclusion criteria (6.1)\", \"HbA1c (Appendix 2)\") ... Strip inline references OUT of `activity_name` ... and add a synthesised marker (`pr1`, `pr2`, …)"
- **Δ** Marks were produced by image mark-detection but the JSON records no method provenance anywhere (0 occurrences of "method", indentation_method, structure_method, activity_name_source.method).
  - expect: v3.6.0 should add non-default method fields: activity_schedule cell method = "raster_pixel_detection"; activity_name_source.method = "visual_transcription" and indentation_method = "visual_estimate" (or font_signal); schedule_property.structure_method = "inferred_from_layout" for the synthesised "Study Phase" row. Appearance of these fields is an expected addition, not a diff regression.
  - rule: §1e - "`activity_schedule` / `schedule_grid` cell `method` — `raster_pixel_detection` (§1a) / `visual_read`" and "`activity_name_source.method` ... `activity_name_source.indentation_method`"
- **Δ** No per-activity source_page is recorded and the report does not give activity rows per page across pages 9-12.
  - expect: v3.6.0 should record source_page on every activity in doc-page numbering (9-12) and the new report should state activity rows per page, calling out any page in the declared range that contributed none.
  - rule: §4 - "**source_page** — record the document page each row was read from ... **Then check coverage before delivering: every page in the declared range must contribute rows.**" and §7 "**activity rows per page across the declared page range**"
- **Δ** The report recommends a manual spot-check of the resolved grid because ~470 marks were detector-read.
  - expect: v3.6.0 §1a/§1d formalise the detector (200 dpi raster, near-black count threshold not fraction, rule lines recovered from the raster, one method for the whole table) and §7 requires the mechanical mark-check and any visual/mechanical disagreement to be reported explicitly. Expect a more structured method statement, with the same 470-mark result.
  - rule: §1a - "flag a cell as marked by **counting near-black pixels** (intensity < ~90) inside it against an absolute **count threshold** — use a count, NOT a dark-pixel *fraction*"; §1d raster rule-line recovery

_Notes:_ Report read in full. Counts cross-checked against NCT03693430_Table_01_extraction.json: 63 activities, 4 schedule_properties, 136 schedule_grid cells, 470 activity_schedule entries (466 'X' + 4 'x'), 30 annotations (4 footnote a-d + 26 source_note pr1-pr26), 9 mark-free rows (the 5 level-0 headers + the 4 sub-parents). The JSON is NEWER than the report on the inline-reference question.

### NCT03817853

1 table(s): T1 main_soa pp100-102 (27a/89m/29n)

- **INV** _Table 01_ One table only, classified main_soa, with 4 header rows, 27 activities (one of which is a section header), 89 marks and 29 annotations.
  - check: Exactly one Table file; table_type == "main_soa"; len(schedule_properties) == 4; len(activities) == 27; len(activity_schedule) == 89; len(annotations) == 29.
- **INV** _Table 01_ This protocol has a single SoA - no additional tables.
  - check: Count of NCT03817853_Table_*_extraction.json == 1.
- **INV** _Table 01_ The grid is on soa.pdf page 1 = protocol p.100; pages 2-3 = protocol pp.101-102 hold footnotes, general Notes and the abbreviation list, all of which were captured.
  - check: table_metadata.page_start == 100 and page_end == 102; all footnote/Notes/abbreviation content from pp.101-102 present in annotations.
- **INV** _Table 01_ 11 timepoint columns at schema positions 2-12; column 1 is the 'Day' label column and is excluded from the grid.
  - check: distinct schedule_grid column_position values == {2..12}; no column_position 1 in schedule_grid or activity_schedule.
- **INV** _Table 01_ Column assignment was confirmed mechanically by matching body-mark x-coordinates to the day-header word centers (pdftotext -bbox text layer, not markdown).
  - check: New report states a bbox column-binning mark-check (§1b) for this study, not a visual-only or markdown-derived grid.
- **INV** _Table 01_ Four-level header: L1 epoch (Screening 2-3, Treatment 4-11, Follow-up 12), L2 period, L3 cycle, L4 study_day.
  - check: schedule_properties row 1 property_type == "epoch", hierarchical_level 1; rows 2/3/4 property_type == period/cycle/study_day with hierarchical_level 2/3/4.
- **INV** _Table 01_ L2 row content: Induction (6-8 cycles) merged over cols 4-8, then EOI, Maintenance, EOM.
  - check: schedule_grid row 2: cols 4-8 all cell_value "Induction (6–8 cycles)"; col 9 "EOI"; col 10 Maintenance...; col 11 "EOM".
- **INV** _Table 01_ L3 row content: Cycle 1 merged over cols 4-6, Cycle 2 at col 7, Cycles 3-6/8 at col 8.
  - check: schedule_grid row 3: cols 4,5,6 == "Cycle 1"; col 7 == "Cycle 2"; col 8 == "Cycles 3–6/8"; nothing at cols 2,3,9-12.
- **INV** _Table 01_ The L4 label cell in column 1 literally reads "Day" and is taken from the source, not synthesised.
  - check: schedule_properties row 4 property_name == "Day" and property_name_source.synthesized is absent/false, while rows 1-3 have synthesized true.
- **INV** _Table 01_ Merged header spans are exactly Screening 2:3, Treatment 4:11, Induction 4:8, Cycle 1 4:6, each distributed to every covered column with is_merged_cell=true.
  - check: schedule_grid: 2 cells with merged_cell_range "2:3", 8 with "4:11", 5 with "4:8", 3 with "4:6"; all have is_merged_cell true.
- **INV** _Table 01_ There are no merged marks in the table body - every activity mark sits in a single column.
  - check: No activity_schedule entry carries a source_range / span; count of activity_schedule == 89 with one column_position each.
- **INV** _Table 01_ No orphan annotations: all 29 annotations carry at least one marker_location and all 27 lettered markers (a-z, aa) resolve to a defined annotation.
  - check: Every annotation has len(marker_locations) >= 1; the set of markers appearing in activity annotation_markers and schedule_cell annotation_markers is a subset of the defined annotation_marker set.
- **INV** _Table 01_ The chemotherapy row (footnote s) carries marks at exactly C1 D1, C2 D1 and Cycles 3-6/8 D1 - schema columns 4, 7 and 8.
  - check: activity_schedule for activity_name == "chemotherapy" == exactly column_position {4,7,8}.
- **INV** _Table 01_ Marks and cell-level footnote markers were read from the PDF text layer via pdftotext -bbox; markdown was not used for the grid.
  - check: New report names a text-layer bbox method for the grid; any claim that the grid came from markdown is a regression.
- **JDG** _Table 01_ Header row 2 was classified property_type = period even though it mixes sub-phases (Induction, Maintenance) with end-of-phase milestone visits (EOI, EOM).
  - rationale: The row's dominant content is sub-phase level; EOI/EOM were acknowledged as an alternative 'visit' reading and the ambiguity was recorded rather than hidden.
- **JDG** _Table 01_ 'Study drug administration' was modelled as an indentation_level 0 section header with obinutuzumab and chemotherapy as level 1 children; every other activity is a flat list at level 1.
  - rationale: It is a merged row label spanning the two drug sub-rows, so it groups rather than schedules.
- **JDG** _Table 01_ Footnote markers that sit on a specific cell mark were kept as cell-level (schedule_cell) markers rather than promoted to activity level: f on Informed consent col 2; c on obinutuzumab C1 D1/D8/D15 and d on C2 D1 / Cycles 3-6/8 D1 / Maintenance; u and w on the first three columns of Concomitant medications / Adverse events; x on Provider-reported col 8.
  - rationale: Promoting them to activity scope would lose which visits each footnote governs; u and w additionally sit on the activity name, so those annotations carry both activity_name and schedule_cell locations.
- **JDG** _Table 01_ Per-column header markers a, b, e and aa use location_type="schedule_cell" pointing at the header grid cell.
  - rationale: schedule_cell is the only location type that carries a column, so it preserves which column each header footnote governs instead of collapsing the note onto the whole header row.
- **JDG** _Table 01_ Header footnote markers on merged cells were placed on EVERY covered cell (a on cols 2-3; b on cols 4-8), each covered cell being its own marker_location.
  - rationale: Consistent with distributing the merged cell itself across all covered columns, so the footnote resolves for every column in the span.
- **JDG** _Table 01_ property_name for the three upper header rows was synthesised as "Phase" (L1), "Treatment sub-phase" (L2) and "Cycle" (L3) because their column-1 label cells are blank.
  - rationale: The rows clearly carry schedule data spanning columns but have no printed label, so names were synthesised and flagged rather than left null.
- **JDG** _Table 01_ Only the table-wide general Notes block (note1) and the abbreviation list (abbr) received synthesised markers, anchored nominally to schedule_property row 1; every other note carries a real printed letter.
  - rationale: These two have no in-cell anchor in the source, so a nominal header anchor was used to keep them resolvable rather than leaving them orphaned.
- **Δ** The abbreviation list is emitted as an annotation (marker 'abbr', type abbreviation) anchored nominally to schedule_property row 1, with no in-grid marker of its own.
  - expect: v3.6.0 forbids emitting a standalone abbreviation/legend list whose terms carry no in-grid marker. The 'abbr' annotation may legitimately disappear, taking the annotation count from 29 to 28. Do not score its absence as lost content - but do check that no real lettered footnote was dropped with it.
  - rule: §6 - "Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker — every annotation needs ≥1 `marker_location` (§7), so an unreferenced list entry is an orphan and is dropped downstream."
- **Δ** note1 (and abbr) carry synthesised markers anchored to schedule_property row 1 with no method recorded on the marker_location.
  - expect: v3.6.0 requires method: "synthesized" on such marker_locations so the validator can see the binding was invented rather than printed. Expect a new method field on these locations.
  - rule: §6 - "If the source gives the note no marker, synthesise one and link it via `marker_locations` to the row it sits beside ... with `method: \"synthesized\"` on the location"; §1e
- **Δ** Judgement call 4 records 'Header footnote location_type' as a low-confidence interpretation.
  - expect: Under v3.6.0 this is now a hard rule, not a judgement call: per-column header markers MUST be annotation_markers on that column's schedule_grid cell. The DATA should be unchanged (a on cols 2-3, b on cols 4-8, e on col 10, aa on col 12); what should change is that this stops being listed as low-confidence. Any move of these markers onto the schedule_property row's annotation_markers is a regression.
  - rule: §6 - "**Header-cell footnotes (per-timepoint).** ... encodes as `annotation_markers` on **that column's `schedule_grid` cell** ... Do NOT put it on the `schedule_property` row's `annotation_markers`"
- **Δ** No source_page is recorded on activities, and the declared page range 100-102 includes two pages that hold only footnotes.
  - expect: v3.6.0 should record source_page = 100 on all 27 activities and the report must explicitly say that pp.101-102 contribute no activity rows because they are footnote/abbreviation pages.
  - rule: §4 - "If a page in the range genuinely has no activity rows (a footnote or abbreviation page), say so in the report."; §7 activity rows per page
- **Δ** No method provenance fields are recorded anywhere in the JSON.
  - expect: v3.6.0 is exception-based here: for a clean text-layer table most method fields should still be ABSENT. Expect at most schedule_property.structure_method on the three synthesised header rows and method "synthesized" on the note1/abbr locations. A flood of method fields on a text-layer table would itself be wrong.
  - rule: §1e - "Every interpreted value has a default method; when you arrive at a value any other way, record the method in the schema's provenance fields. Absent = default — most extractions record nothing here."

_Notes:_ Report read in full. Cross-checked against NCT03817853_Table_01_extraction.json: 27 activities at row_position 5-31 (header occupies rows 1-4), 89 activity_schedule entries all with cell_value 'x', 31 schedule_grid cells, 29 annotations (a-z, aa, note1, abbr), page_start 100 / page_end 102. Report declares no source defects and no orphan risk, so source_defects is legitimately empty.

### NCT04004988

2 table(s): T1 main_soa pp10-10 (17a/70m/12n), T2 continuation pp11-11 (3a/20m/9n)

- **INV** _Table 01_ Table 01 is main_soa on protocol page 10 with 14 timepoint columns (Comments column excluded), 17 activities, 70 marks and 12 annotations.
  - check: Table_01: table_type == "main_soa"; page_start == page_end == 10; len(activities) == 17; len(activity_schedule) == 70; len(annotations) == 12; distinct schedule_grid column_position == {2..15}.
- **INV** _Table 02_ Table 02 is a continuation of Table 01 on protocol page 11 with 3 activities (Immunogenicity, Blood glucose monitoring, PK Sampling), 20 marks and 9 annotations.
  - check: Table_02: table_type == "continuation", continuation_of == 1, page_start == page_end == 11; activity_name set == {Immunogenicity, Blood glucose monitoring (hours), PK Sampling (hours)}; len(activity_schedule) == 20.
- **INV** _Table 02_ Table 02's continuation classification has a stated reason: byte-identical column structure to Table 01 plus a physically repeated header row.
  - check: Table_02 table_metadata.notes (or the new report) states this reasoning; the two tables' schedule_grid column sets and cell_values match exactly.
- **INV** _Table 01, Table 02_ Column model for both tables: col 1 Procedure (label, excluded), cols 2-14 Screening through D36, col 15 ED, col 16 Comments (excluded). ED has no day label - its 'ED' header sits in the epoch row.
  - check: schedule_grid row 1 has a cell at column_position 15 with cell_value "ED"; schedule_grid row 2 has NO cell at column_position 15; no column_position 1 or 16 anywhere.
- **INV** _Table 01, Table 02_ The epoch header 'Periods 1 and 2 Study Days ...' is merged over cols 3-14, distributed to 12 schedule_grid cells with merged_cell_range "3:14"; ED (col 15) is outside the span.
  - check: Exactly 12 schedule_grid cells in row 1 with is_merged_cell true and merged_cell_range "3:14" (cols 3-14); the col 15 cell is not merged.
- **INV** _Table 01, Table 02_ There are no merged marks in the table body - each activity mark sits in a single column.
  - check: No activity_schedule entry carries a source_range spanning multiple columns in either table.
- **INV** _Table 01_ Outpatient Visit carries exactly 8 marks, at D5, D6, D7, D8, D15, D21, D36 and ED - schema columns 8, 9, 10, 11, 12, 13, 14, 15 - as read from PDF coordinates.
  - check: Table_01 activity_schedule for activity_name == "Outpatient Visit" == exactly column_position {8,9,10,11,12,13,14,15}. If it comes back as D4-D36 with ED blank, the markdown grid was trusted over the PDF - a regression.
- **INV** _Table 01, Table 02_ All marks were taken from PDF word x-coordinates mapped to day-header column centers; markdown was used only for activity-name spelling, footnote/abbreviation text and the Comments column.
  - check: New report states PDF-authoritative mark placement for this study and re-flags the markdown disagreement.
- **INV** _Table 01, Table 02_ No orphan annotations: all 12 (Table 01) and 9 (Table 02) annotations carry at least one marker_location, and every marker appearing in a cell (a, b, c, n1...n9) resolves to a defined annotation.
  - check: Every annotation in both files has len(marker_locations) >= 1; the marker set in activity annotation_markers and schedule_grid annotation_markers is a subset of the defined annotation_marker set.
- **INV** _Table 01, Table 02_ Footnote b is bound to header row 2 columns 3, 4 and 14 (D-1, D1, D36); footnote c is bound to header row 1 column 15 (ED).
  - check: Annotation 'b' has exactly 3 marker_locations of type schedule_cell at (row 2, cols 3/4/14); annotation 'c' has one at (row 1, col 15); the corresponding schedule_grid cells carry those markers in annotation_markers.
- **SRC** _Table 01, Table 02_ NCT04004988_soa.pdf was originally a 2-page excerpt (page 9 section title + page 10 table) that omitted protocol page 11, which holds the continuation rows and ALL footnote definitions (a, b, c), the abbreviation list and the two general Notes. Page 11 had to be sourced from the full protocol PDF.
  - expected handling: This defect was RESOLVED on 2026-07-12 by regenerating the SoA source to 3 pages (protocol printed pages 9-11). A fresh v3.6.0 extraction should therefore find page 11 inside _soa.pdf and should NOT need to reach into NCT04004988.pdf, and should NOT re-flag the excerpt as incomplete. What must NOT happen is the opposite failure: silently dropping the page-11 continuation rows or the a/b/c definitions. Check Table_02 still exists with its 3 activities and that annotations a, b, c carry real text.
- **SRC** _Table 01_ The protocol markdown pipe-table grid is column-shifted for some rows and cannot be trusted for mark placement; the clearest case is the Outpatient Visit row.
  - expected handling: The new extraction must again take all marks from PDF word coordinates and must re-flag the PDF/markdown disagreement in its uncertainty report. Silently emitting the markdown placement (Outpatient Visit at D4-D36 with ED blank), or emitting the PDF placement with no mention of the disagreement, both count as failures to flag a known source-material defect.
- **JDG** _Table 01, Table 02_ Header row 1 was classified property_type = epoch even though it mixes an epoch (Screening), a period-level label ('Periods 1 and 2 Study Days ...') and an epoch (ED) on one row.
  - rationale: epoch was chosen as the coarsest phase level present on the row; 'period' was acknowledged as a defensible alternative.
- **JDG** _Table 01, Table 02_ property_name for header row 2 was synthesised as "Study Day" because the physical column-1 cell holds "Procedure" (the activity-column header), which was preserved in property_name_source.cell_value.
  - rationale: The printed label belongs to the activity column, not the day row, so reusing it would mislabel the property; the raw value was kept for traceability.
- **JDG** _Table 01, Table 02_ Every non-empty Comments-column cell was turned into a footnote annotation with a synthesised marker (n1...n9 in Table 01, n1...n3 in Table 02) added to that activity's annotation_markers.
  - rationale: The right-hand Comments column is not a schedule column and not an activity; making each cell a linked footnote keeps the content without inventing a schedule column.
- **JDG** _Table 02_ The page-11 table-wide annotations with no in-cell marker - abbr, note1, note2 - were anchored nominally to schedule_property row 1 and explicitly flagged for review.
  - rationale: There is no specific cell they mark, so a nominal header anchor was the only way to keep them non-orphaned.
- **JDG** _Table 02_ Table 02 repeats the full header (schedule_properties + schedule_grid) rather than deferring to Table 01.
  - rationale: The header is physically present on page 11, so it was transcribed; the risk of downstream double-counting if consolidation does not dedupe by continuation_of was flagged rather than pre-empted.
- **JDG** _Table 01_ The full texts of footnotes a, b and c were duplicated into Table 01's annotations even though their definitions are printed on page 11 (Table 02's page).
  - rationale: Their markers appear in Table 01 cells (ECG^a, Pharmacogenetic^a, D-1^b, D1^b, D36^b, ED^c), so including the texts keeps each table file self-contained and resolvable on its own.
- **JDG** _Table 01, Table 02_ All activities in both tables were assigned indentation_level = 1 as a flat list, with no section headers.
  - rationale: No section headers or sub-grouping exist in this table; level 1 (procedure level) matches prior verified extractions.
- **Δ** Comments-column notes were bound to activity rows and given synthesised markers n1...n9, but the report does not say how each note's text was bounded and no annotation_text_source is recorded.
  - expect: v3.6.0 requires each note's TEXT to be bounded by the notes-column rule-line geometry, not by vertical-gap proximity, and requires annotation_text_source.method = "proximity_bounded" to be recorded if rules were genuinely unrecoverable. Expect either identical note texts with no method field (rule-bounded) or explicit proximity_bounded flags. Also expect the note boundaries to be re-checked - any note text that changes at a cell boundary should be inspected as a possible fix to a prior split/merge, not assumed a regression.
  - rule: §6 - "**Bound each note's TEXT by the cell's rule-line geometry, not by proximity** ... do NOT fall back to vertical-gap proximity, which fails in both directions"
- **Δ** The synthesised n1...n9 / n1...n3 marker_locations carry no method field.
  - expect: v3.6.0 requires method: "synthesized" on each such marker_location (and "text_match" where the binding came from word overlap). Expect new method fields on these locations.
  - rule: §6/§1e - "synthesise one and link it via `marker_locations` to the row it sits beside (`activity_name` or `schedule_property`), with `method: \"synthesized\"` on the location"
- **Δ** Table 02 emits an 'abbr' abbreviation annotation whose terms carry no in-grid marker, anchored nominally to schedule_property row 1.
  - expect: v3.6.0 forbids standalone abbreviation lists with no in-grid marker, so 'abbr' may legitimately disappear, taking Table 02's annotation count from 9 to 8. Its absence is an expected delta; the loss of note1/note2 or of a/b/c would not be.
  - rule: §6 - "Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker"
- **Δ** Table 01 declares page_start = page_end = 10 and no source_page is recorded on any activity.
  - expect: v3.6.0 requires source_page per activity row and a per-page coverage check. If the regenerated 3-page _soa.pdf leads the new run to declare a wider range (e.g. 9-11), the report must explicitly say that page 9 is a section-title page contributing no activity rows. A widened page range with no such statement is a §4 violation.
  - rule: §4 - "**Then check coverage before delivering: every page in the declared range must contribute rows.** ... If a page in the range genuinely has no activity rows (a footnote or abbreviation page), say so in the report."
- **Δ** Judgement call 2 records the per-timepoint header footnote placement (b, c on schedule_grid header cells) as a low-confidence interpretation, noting schedule_cell is 'nominally an activity x timepoint type'.
  - expect: Under v3.6.0 this is a hard rule, so the same placement should be produced but no longer flagged as low-confidence. The data should be unchanged: b on row 2 cols 3/4/14, c on row 1 col 15. Moving these onto the schedule_property row would be a regression.
  - rule: §6 - "**Header-cell footnotes (per-timepoint).** ... Do NOT put it on the `schedule_property` row's `annotation_markers` — that scopes it to the whole row, and the footnote loses which visit/encounter it governs."
- **Δ** Non-'X' cell values such as 'Predose', '0 hour', 'Predose, 12', '24', '48', '72', '336', '480' are carried in the grid as literal cell_values.
  - expect: v3.6.0 §5 explicitly sanctions this (transcribe literally; qualified marks keep their qualifier in cell_value when not expressible as columns), so these should survive unchanged. If the new run converts them to plain 'X' or drops them, that is a regression, not a normalisation.
  - rule: §5 - "**Qualified marks.** ... if it is a condition not expressible as columns, keep the qualifier literally in `cell_value`." and §1 "Transcribe each cell literally as it appears"

_Notes:_ Both reports' tables cross-checked against NCT04004988_Table_01_extraction.json (17 activities, 70 activity_schedule entries, 12 annotations a/b/c/n1-n9, 27 schedule_grid cells, page 10) and NCT04004988_Table_02_extraction.json (3 activities, 20 activity_schedule entries, 9 annotations a/b/c/n1-n3/abbr/note1/note2, continuation_of 1, page 11). Outpatient Visit confirmed at columns 8-15 in the JSON, matching the PDF-authoritative reading. Neither file records any source_page or method provenance field.

### NCT04184622

2 table(s): T1 main_soa pp18-21 (54a/414m/27n), T2 track pp22-24 (39a/311m/18n)

- **INV** _Table 01_ Table 01 is table_type main_soa with exactly 54 activities and 24 visit data columns (V1-V21, V99, ED, V801), covering document pages 18-21.
  - check: NCT04184622_Table_01_extraction.json: table_metadata.table_type == 'main_soa', len(activities) == 54, max(column_position) over schedule_grid == 25 (24 data columns starting at position 2), page_start 18 / page_end 21.
- **INV** _Table 02_ Table 02 is table_type track with track_label 'Prediabetes', 39 activities and 19 visit data columns (V101-V116, V199, ED, V802), pages 22-24.
  - check: NCT04184622_Table_02_extraction.json: table_metadata.table_type == 'track', table_metadata.track_label == 'Prediabetes', len(activities) == 39, 19 distinct data column_positions (2..20), page_start 22 / page_end 24.
- **INV** _Table 01_ Table 01 has 5 header schedule_properties (Visit, Week of Treatment, Allowable Deviation window, Fasting Visit condition, Telephone Visit modality) and 27 annotations n1-n27.
  - check: Table 01 JSON: len(schedule_properties) == 5 with property_name values Visit / Week of Treatment / Allowable Deviation (days) / Fasting Visit / Telephone Visit; len(annotations) == 27.
- **INV** _Table 02_ Table 02 carries 18 annotations.
  - check: Table 02 JSON: len(annotations) == 18.
- **INV** _Table 01_ Exactly 5 lab rows (Urinary albumin/creatinine, Cystatin-c, Calcitonin, Hematology, Thyroid-stimulating hormone) carry a FOOTNOTED mark (X*) in the Visit 1 / Screening column - the mark is present AND carries an annotation marker; the current raw binds all five to n22.
  - check: Table 01 JSON: for each of the five activity_name values, activity_schedule has an entry at the Screening column (column_position 2) with cell_value 'X' and a non-empty annotation_markers; the same footnote's marker_locations list five schedule_cell entries at column_position 2. If the re-extraction emits a bare 'X' with no marker on these rows, the footnoted-mark regex of prompt section 1b was not applied.
- **INV** _both_ Both tables' page ranges are unchanged: 18-21 for Table 01 and 22-24 for Table 02.
  - check: table_metadata.page_start/page_end == 18/21 (Table 01) and 22/24 (Table 02).
- **JDG** _Table 01_ Fasting Visit and Telephone Visit are modelled as schedule_properties (property_type condition and modality respectively), not as activities, and their repeats on continuation pages are de-duplicated so they are counted once.
  - rationale: They are header bands that reprint on every continuation page; modelling them as activities or counting each reprint would double-count rows and marks.
- **JDG** _both_ Parentheticals in activity labels - '(3 sitting BP and HR)', '(includes PK sample)', '(Baseline/Screening Version)', '(include Cr for eGFR ...)' - are kept inside activity_name; they were adjudicated as assay/version qualifiers, NOT section/appendix references.
  - rationale: Prompt section 6 only strips section/appendix/attachment cross-references out of activity_name; these parentheticals name assay content or instrument versions.
- **JDG** _Table 01_ The introduction's 'Section 10.10 Appendix 10' reference is treated as a general SoA note, not as an inline reference bound to any activity label.
  - rationale: It is not printed inside an activity's label cell, so it has no citing activity to attach a synthesised marker to.
- **JDG** _both_ Annotation semantics for n1-n27 were carried over unchanged from the prior user-verified raw and were deliberately NOT re-adjudicated in this pass.
  - rationale: The prior raw was Excel-verified by the reviewer; the re-extraction scoped itself to the mark matrix.
- **Δ** The current extraction JSONs contain no source_page field on any activity (0 occurrences in both Table 01 and Table 02), and the report gives only whole-table page ranges (pp.18-21 / pp.22-24).
  - expect: Every activity should now carry source_page, and the uncertainty report should state activity rows per page across pages 18-21 and 22-24, calling out any page in the range that contributed none.
  - rule: Section 4: 'source_page — record the document page each row was read from ... Then check coverage before delivering: every page in the declared range must contribute rows.' plus section 7 'activity rows per page across the declared page range'.
- **Δ** All 54 Table 01 activities and all 39 Table 02 activities currently have indentation_level null and no activity_name_source.indentation_method.
  - expect: v3.6.0 should record activity_name_source.indentation_method (most likely 'assumed_flat' for these flat tables) wherever indentation_level is not derived from text-layer whitespace.
  - rule: Section 4 / section 1e: 'When the level does not come from text-layer whitespace, set activity_name_source.indentation_method (font_signal / visual_estimate / assumed_flat for flat tables)'.
- **Δ** The report documents the bbox mark-check method in prose only; the JSON records no method provenance fields.
  - expect: For this text-layer table the bbox route is the DEFAULT, so absent method fields remains correct - do not treat newly-appearing method fields on ordinary cells as required. Only non-default methods (and any location_type 'unresolved') should appear.
  - rule: Section 1e: 'Every interpreted value has a default method; when you arrive at a value any other way, record the method in the schema's provenance fields. Absent = default — most extractions record nothing here.'

### NCT04320615

3 table(s): T1 main_soa pp77-80 (28a/56m/21n), T2 main_soa pp81-83 (17a/220m/12n), T3 main_soa pp84-85 (14a/32m/8n)

- **INV** _Table 01_ Table 01 = Appendix 1 (Days 1 and 2), table_type main_soa, pages 77-80, 28 body rows of which 1 is a section header and 27 are activities, 56 populated cells, 21 annotations, 5 data columns.
  - check: NCT04320615_Table_01_extraction.json: table_type == 'main_soa', page_start/end 77/80, len(activities) == 28, len(activity_schedule) == 56, len(annotations) == 21, distinct data column_positions == {2,3,4,5,6}.
- **INV** _Table 01_ The single section-header row is 'Central Labs' and it carries no scheduling marks; no section-header row anywhere carries marks.
  - check: Table 01 JSON: activities contains a row with activity_name 'Central Labs' (currently row_position 21) and activity_schedule contains NO entry with that row_position. Also: every annotation has len(marker_locations) >= 1 in all three tables.
- **INV** _Table 02_ Table 02 = Appendix 2 (Days 3-28), table_type main_soa, pages 81-83, 17 rows, 220 cells, 12 annotations, 27 data columns (Days 3-28 plus Study Completion/Discontinuation).
  - check: Table 02 JSON: len(activities) == 17, len(activity_schedule) == 220, len(annotations) == 12, distinct data column_positions == 2..28.
- **INV** _Table 03_ Table 03 = Appendix 3 (After Day 28), table_type main_soa, pages 84-85, 14 rows, 32 cells, 8 annotations, 3 data columns (Day 35, Day 45, Day 60/Study Completion).
  - check: Table 03 JSON: len(activities) == 14, len(activity_schedule) == 32, len(annotations) == 8, distinct data column_positions == {2,3,4}.
- **INV** _Table 01_ In Appendix 1 the cell-level footnote markers are: 'o' on the Serum PD Day-1 cells (columns 3 and 4), 'q' on the Serum PK Day-1 cells (columns 3 and 4), and 'p' on the Serum PK activity NAME (not on a cell).
  - check: Table 01 JSON: annotation 'o' has exactly two marker_locations of location_type 'schedule_cell' at column_position 3 and 4 on the 'Serum PD (CRP, IL-6, sIL-6R)' row; annotation 'q' likewise on the 'Serum PK' row; annotation 'p' has a single marker_location of location_type 'activity_name' on the 'Serum PK' row.
- **INV** _Table 01_ Appendix 1 header footnotes 'a' and 'b' are both bound to the Screening header cell at grid column 2, i.e. column-scoped rather than row-scoped.
  - check: Table 01 JSON: schedule_grid cell at row_position 1 / column_position 2 (cell_value 'Screening') has annotation_markers containing both 'a' and 'b'; no schedule_property carries 'a' or 'b' in its annotation_markers.
- **INV** _Table 03_ Appendix 3 footnote 'a' resolves column-scoped to the Day 35 and Day 45 columns (columns 2 and 3), not to Day 60.
  - check: Table 03 JSON: annotation 'a' has exactly two marker_locations at column_position 2 and 3 on the Study Day header row; the schedule_grid cells '35 (+/-3 days)' and '45 (+/-3 days)' both carry marker 'a' and the Day 60 cell does not.
- **INV** _all_ Within each appendix, a footnote that governs two activities is ONE annotation with two activity locations: App 1 'h' (SpO2 + Vital signs), App 2 'b' (Vital signs + SpO2), App 3 'c' (Vital signs + SpO2).
  - check: Table 01: annotation 'h' has exactly 2 marker_locations of location_type 'activity_name' (SpO2 row and Vital signs row). Table 02: annotation 'b' likewise. Table 03: annotation 'c' likewise. No duplicate annotation objects with the same text.
- **INV** _all_ Marks were placed from pdftotext -bbox word coordinates treated as authoritative, with column x-centres taken from the Study Day header row.
  - check: The new uncertainty report must name the same mechanical mark-check (bbox column-binning, section 1b) and report any cell where the mechanical matrix disagreed with the visual read. Cell totals 56 / 220 / 32 are the check on the matrix itself.
- **JDG** _all_ The three appendices are modelled as three sequential main_soa tables, not as domain / continuation / track tables.
  - rationale: They cover non-overlapping day ranges with different column structures - independent schedules per the taxonomy - while representing consecutive phases of one participant journey. The report explicitly invites a different grouping.
- **JDG** _Table 01 and Table 02_ The 'Optional' merged cell on PaO2/FiO2 is distributed across its span: App 1 columns 3-6 with source_range '3:6'; App 2 columns 2-27 with source_range '2:27' PLUS a standalone 'Optional' in the Study Completion column (28) with no source_range. App 3 has no PaO2/FiO2 row.
  - rationale: The source prints an arrow-spanned '<- Optional ->' over the post-baseline columns; the merged-mark rule distributes rather than centres, and the Study Completion cell is a separate printed cell.
- **JDG** _all_ Each appendix's stacked header bands are split into separate schedule_properties (App 1: Epoch + Study Day + Timepoint; App 2: Epoch + Study Day; App 3: Epoch + Study Day), and columns with no printed epoch label are left with an EMPTY epoch rather than an inferred one.
  - rationale: Transcribe, do not infer - App 1 timepoint columns 4-6 and App 3 Days 35/45 carry no epoch label in the source.
- **JDG** _Table 02_ App 2 footnote 'a' sits on the MERGED 'Days 3-28' phase header; it was placed on the representative column-2 cell so it resolves column-scoped to column 2, even though the footnote governs the whole Days 3-28 phase. The report explicitly flags this.
  - rationale: The marker has one printed position on a merged header band; the extraction chose the representative covered column rather than replicating the marker across all 26 covered columns.
- **JDG** _Table 01 and Table 02_ The general notes under App 1 ('all assessments prior to dosing') and App 2 ('discharged patients within +/-3 days') are captured as a SYNTHESIZED marker 'note1' scoped to the table via a schedule_property location. App 3 has no general note.
  - rationale: The notes carry no printed marker, so a marker was synthesised to keep them resolvable rather than dropped as orphans.
- **JDG** _all_ Repeated footnote wording is intentionally NOT cross-deduplicated across the three appendices; each appendix is a separate extraction file. App 2 and App 3 vitals/hematology/chemistry footnotes additionally carry a telephone-visit clause absent from App 1 and were kept as distinct text.
  - rationale: Deduplication is scoped per table; the texts are genuinely different between App 1 and App 2/3.
- **JDG** _all_ Per-appendix abbreviation lists are NOT emitted as abbreviation annotations, because their terms carry no in-grid marker and would be orphans.
  - rationale: Every annotation needs at least one marker_location; unreferenced list entries are dropped downstream.
- **Δ** No activity in any of the three tables carries source_page, and the report gives only whole-table page ranges.
  - expect: Every activity should carry source_page, and the report must give activity rows per page. Note Table 03 declares pages 84-85 while table_metadata.notes says 'table page 84, footnotes pages 84-85' - page 85 contributes no activity rows, so v3.6.0 requires the report to say so explicitly rather than leaving the gap silent.
  - rule: Section 4: 'every page in the declared range must contribute rows ... If a page in the range genuinely has no activity rows (a footnote or abbreviation page), say so in the report.' Section 8 repeats it as a delivery check.
- **Δ** All activities in all three tables currently have indentation_level null, including the 'Central Labs' section header which the report identifies as a section-header row.
  - expect: v3.6.0 should assign indentation_level 0 to the 'Central Labs' section header and 1 to its children (or record activity_name_source.indentation_method when the level is not read from whitespace). A level-0 header must still carry no marks.
  - rule: Section 4: 'indentation_level from visual indentation / shading / bold: section header = 0, child = 1 ... Organizational / section-header rows (indentation_level 0 that group child activities) carry NO scheduling marks.'
- **Δ** The uncertainty report documents the three-appendices-as-main_soa call and the merged-cell distributions in prose; table_metadata.notes already records the appendix structure.
  - expect: v3.6.0 requires the table_type reasoning to live in table_metadata.notes as well as the report - expect the notes field to state explicitly why each appendix is main_soa rather than continuation/domain.
  - rule: Section 2: 'For any table_type that is not obvious from the discriminators alone, record the reasoning in table_metadata.notes as well as the report.'

### NCT04557384

3 table(s): T1 main_soa pp16-22 (25a/234m/26n), T2 track pp23-23 (3a/3m/4n), T3 reference pp24-24 (15a/20m/0n)

- **INV** _Table 01_ Table 01 is table_type main_soa, section 1.3, pages 16-22 (7 pages), with 25 activities and 15 visit columns (Screening <=28/<=7, Cycle 1-3 D1/D8/D15/D22, DX, V801).
  - check: NCT04557384_Table_01_extraction.json: table_type == 'main_soa', page_start/end 16/22, len(activities) == 25, 15 distinct data column_positions.
- **INV** _Table 02_ Table 02 is table_type track with track_label 'Continued Access', page 23, 3 activities and 2 columns (Study Treatment 501-5XX, Follow-Up 901), 4 annotations.
  - check: Table 02 JSON: table_type == 'track', track_label == 'Continued Access', len(activities) == 3, 2 data columns, len(annotations) == 4. track_label must be set on Table 02 only.
- **INV** _Table 03_ Table 03 (page 24) is the PK Sampling Schedule: 15 rows (Sample 1-14 plus End of treatment) x 2 collection columns (Ramucirumab PK, Immunogenicity), with 0 annotations.
  - check: Table 03 JSON: len(activities) == 15 (14 'Sample n ...' rows plus an End of treatment row), 2 data columns, len(annotations) == 0.
- **INV** _Table 01_ Merged single 'X' is distributed across the On-Treatment span [4:15] for Concomitant medication and AE collection - one activity_schedule entry per covered column with source_range '4:15'.
  - check: Table 01 JSON: the 'Concomitant medication' and 'AE collection' rows each have 12 activity_schedule entries at column_positions 4..15, every one cell_value 'X' and source_range '4:15'. A single centred entry would be a merged-mark regression.
- **INV** _Table 01_ 'See instructions' merged text spans are: Vital signs [4:6]; ECG, Pregnancy test, Thyroid panel, Radiologic imaging, Injection site assessments (spontaneous), Participant diary and Administer ramucirumab all [4:15]; Injection site assessments (solicited) [4:6].
  - check: Table 01 JSON: each named activity has activity_schedule entries with cell_value 'See instructions' covering exactly its stated column span and source_range set to that span ('4:6' or '4:15').
- **INV** _Table 01_ 'See Section 1.3.1' spans columns [4:16] on both the PK and the IG rows.
  - check: Table 01 JSON: the 'PK' and 'IG' rows each have 13 activity_schedule entries at column_positions 4..16 with cell_value 'See Section 1.3.1' and source_range '4:16'.
- **INV** _Table 01_ Table 01 has 26 annotations including footnote 'a' defining Short-term follow-up and the 23 Instructions-column notes i1-i23; every marker is defined and resolves with no orphans.
  - check: Table 01 JSON: len(annotations) == 26, markers include 'a' and i1..i23, and every annotation has len(marker_locations) >= 1. Table 02: len(annotations) == 4 (a, i1, i2, i3).
- **INV** _all_ Page ranges are unchanged: 16-22 / 23 / 24.
  - check: table_metadata.page_start/page_end == 16/22, 23/23, 24/24 across the three files.
- **SRC** _all_ The entire SoA is image-only: there is no text layer on any of the 9 SoA pages, so the grid cannot be read with pdftotext and must be read from rendered images.
  - expected handling: The new extraction must FLAG this in the report and state the image-based method used (section 1a: rule-line geometry plus near-black pixel COUNT threshold, validated cell-for-cell against direct visual reads on at least one dense and one sparse row), and recommend a spot-check of the resolved grid. If the new report describes a pdftotext/bbox text-layer method for this protocol, or is silent about the missing text layer, the extraction is not grounded in the source. Mechanically: extraction_metadata.extractor / the report must name an image or raster method, and cell-level method provenance should be raster_pixel_detection or visual_read (section 1e).
- **SRC** _Table 01_ Grey shading in the grid means Not Applicable; those cells print no mark and are left empty. The DX column (column 11) is grey inside the Administer combination medications span.
  - expected handling: Grey cells must stay EMPTY - shading is a formatting signal and is never a reason to write a cell value, and never a reason to bridge a merged span across it. Check: no activity_schedule entry exists at the grey positions, and the Administer combination medications span remains split rather than filled through column 11.
- **JDG** _Table 03_ Table 03 (PK Sampling Schedule) was typed 'reference' on the ground that its rows are samples rather than activities performed on subjects.
  - rationale: The reference-test-first discriminator: rows read 'Sample 1 ... Sample 14', so they were judged not to be subject activities.
- **JDG** _Table 01_ Instruction-only overflow rows - the injection-site timepoint detail on page 20 and other wrapped instruction cells - are NOT modelled as activities.
  - rationale: They carry only instruction text, not a procedure performed on subjects; modelling them would inflate the activity count above 25.
- **JDG** _Table 01_ 'Administer combination medications' is split into TWO spans, [4:10] and [12:15], because the DX column (11) is grey/Not Applicable between them.
  - rationale: The merged span is genuinely interrupted in the source; bridging it would fabricate a visit.
- **JDG** _Table 01 and Table 02_ Section/appendix cross-references (Appendix 2, Section 10.3, 8.2.5, 1.3.1, 6.1) live in the right-hand Instructions column and are modelled as annotations (i1-i23 in Table 01, i1-i3 in Table 02), NOT inlined into activity names; and parentheticals like '(solicited)', '(spontaneous)', '(Cohorts B and C only)' stay in activity_name as qualifiers.
  - rationale: The references are printed in a notes column, not inside the activity label, so section 6's inline-reference stripping does not apply; the parentheticals are descriptors, not references.
- **Δ** Table 03 is typed 'reference' with the stated reason that its rows are samples, not subject activities.
  - expect: v3.6.0 is likely to re-type Table 03 as 'subsidiary' - it breaks a single main-SoA activity (PK sampling, which appears as the 'PK'/'IG' rows in Table 01) into per-sample timing rows. Expect table_type 'subsidiary' with the reasoning recorded in table_metadata.notes. This is an expected delta, not a regression - but confirm the notes field explains it.
  - rule: Section 2: 'Note on the PK-sampling ambiguity: a table that breaks a single main-SoA activity (e.g. "PK sampling") into per-sample timing rows satisfies the subsidiary definition even though its rows read "Sample n". Classify by function ... and record the call in the report.'
- **Δ** Table 01 currently has 26 annotations of which 25 carry annotation_type 'source_note' (i1-i23 plus two others); Table 02 has 3 of 4 as 'source_note'. The report describes them as 'source_note/footnote annotations'.
  - expect: v3.6.0 should re-type the Instructions-column notes as 'footnote'. A 26-annotation table that is all/nearly-all source_note is an explicit delivery-check failure under v3.6.0.
  - rule: Section 6: 'A right-hand notes column is NOT a schedule column and is NOT an activity. Each non-empty note becomes a footnote annotation.' Section 8: 'by_type is not degenerate across > 20 annotations — in particular NOT all source_note: a notes / comments column yields footnotes.'
- **Δ** The Instructions-column notes i1-i23 were read from rendered images at 170 dpi with a rule-line/dark-pixel detector; the JSON records no annotation_text_source and no marker_location method.
  - expect: v3.6.0 should bound each Instructions-column note by rule-line geometry recovered from the RASTER at 200 dpi (not proximity), and record annotation_text_source.method ('raster_band_cells' or 'visual_transcription') on each note plus method 'synthesized' on each synthesised i-marker location. A note cell spanning several activity rows must stay ONE annotation with one marker_location per covered row. Expect note boundaries - and therefore the i1..i23 text split - to shift; check any new containment pair (one annotation's text inside another's) as a real defect.
  - rule: Section 6 notes-column rule ('Bound each note's TEXT by the cell's rule-line geometry, not by proximity ... When the page has no vector rule lines, recover them from the raster (1d)'), section 1d ('Render at 200 dpi'), section 1e provenance fields.
- **Δ** Footnote 'a' (Short-term follow-up definition) is currently recorded BOTH on the schedule_grid cell at the Short-term follow-up column and in the 'Cycle' schedule_property's annotation_markers; Table 02 does the same with 'a' on the 'Period' schedule_property and on the Follow-Up header cell.
  - expect: v3.6.0 should keep the marker on the specific header/timepoint schedule_grid cell only and REMOVE it from the schedule_property's annotation_markers, so the footnote resolves to its column rather than the whole header row.
  - rule: Section 6: 'Header-cell footnotes (per-timepoint). A marker on a specific header/timepoint cell ... encodes as annotation_markers on that column's schedule_grid cell ... Do NOT put it on the schedule_property row's annotation_markers — that scopes it to the whole row.'
- **Δ** No activity carries source_page, although Table 01 spans 7 pages (16-22) and the report only gives the aggregate range.
  - expect: Every activity should carry source_page, and the report must give activity rows per page for pages 16-22, naming any page that contributed none. With only 25 activities over 7 pages this is the highest-value coverage check in this study.
  - rule: Section 4: 'source_page — record the document page each row was read from ... Then check coverage before delivering: every page in the declared range must contribute rows.'
- **Δ** All 25 / 3 / 15 activities have indentation_level null and no activity_name_source method fields, even though the source is image-only and names were transcribed visually.
  - expect: v3.6.0 should record activity_name_source.method 'visual_transcription' and indentation_method 'visual_estimate' or 'assumed_flat', plus cell-level method 'raster_pixel_detection' / 'visual_read' on activity_schedule and schedule_grid entries, and list every non-default method in the report.
  - rule: Section 1e: 'activity_name_source.method (glyph_reconstruction / visual_transcription) and activity_name_source.indentation_method (font_signal / visual_estimate / assumed_flat)' and 'activity_schedule / schedule_grid cell method — raster_pixel_detection (1a) / visual_read'; section 7 'Method provenance: every non-default method recorded'.

### NCT04573309

2 table(s): T1 main_soa pp14-16 (43a/212m/24n), T2 subsidiary pp17-17 (1a/8m/3n)

- **INV** _Table 01_ Table 01 is main_soa with 43 activity rows (8 section headers + 35 activities), 212 X cells and 24 footnotes lettered a-x.
  - check: NCT04573309_Table_01_extraction.json: table_metadata.table_type == 'main_soa'; len(activities) == 43; len(activity_schedule) == 212; len(annotations) == 24 and the set of annotation_marker values is exactly {a..x}.
- **INV** _Table 01_ Table 1 spans document pages 14-16 and is emitted as ONE main_soa file, not a parent + continuation pair, even though the header reprints on p15.
  - check: Exactly one extraction JSON exists whose table_title is 'Table 1: Schedule of Activities'; its table_metadata.page_start == 14, page_end == 16, table_type == 'main_soa', and no file has table_type 'continuation' with continuation_of pointing at it.
- **INV** _Table 01_ The grid has 24 data columns at positions 2-25 with the stated epoch blocks: Screening 2-3, C-I 4, Inpatient Period 1 5-12, OP 13, Day 23 at 14, Inpatient Period 2 15-23, UNS 24, EOS/ET 25.
  - check: schedule_grid column_position values run 2..25 with no gaps and max == 25; the Epoch property row carries the epoch labels at exactly those position blocks.
- **INV** _Table 01_ Epoch footnote markers a, b, c, d, e are column-scoped on grid columns 2, 4, 13, 24 and 25 respectively.
  - check: For markers a,b,c,d,e each annotation has a marker_location on the epoch header row with column_position 2,4,13,24,25 respectively (order as listed).
- **INV** _Table 01_ Footnote g is cell-scoped on three column-13 cells (Outpatient visit, Chemistry, Urinalysis).
  - check: annotation with marker 'g' has exactly 3 marker_locations, all location_type schedule_cell with column_position 13, on the rows named 'Outpatient visit or phone call', 'Chemistry, hematology, Coagulation' and 'Urinalysis'.
- **INV** _Table 01_ Footnote r is cell-scoped on Chemistry columns 7 and 17; footnote p on PK/PD cells at columns 8, 16, 18, 22; footnote n on the Study intervention compliance column-13 cell.
  - check: marker 'r' -> 2 schedule_cell locations at column_position 7 and 17 on the Chemistry row; marker 'p' -> 4 schedule_cell locations at column_position 8,16,18,22 on the PK/PD row; marker 'n' -> 1 schedule_cell location at column_position 13 on 'Study intervention compliance'.
- **INV** _Table 01_ Footnote j is shared (deduplicated) across the WD history and Prior WD treatment rows; footnote s across the pregnancy-test row and the menstruation-check row. One annotation each, two locations each.
  - check: Exactly one annotation with marker 'j' and one with marker 's'; each has 2 marker_locations of type activity_name, on ('WD history','Prior WD treatment') and ('Urine/serum pregnancy test','Urination and bowel movement monitoring, menstruation check') respectively.
- **INV** _Table 02_ Table 02 is classified subsidiary and holds a single combined PK/PD activity row with 8 schedule cells and 3 annotations.
  - check: NCT04573309_Table_02_extraction.json: table_metadata.table_type == 'subsidiary'; len(activities) == 1; len(activity_schedule) == 8; len(annotations) == 3.
- **INV** _both_ Both tables are schema-valid with no orphan annotations, every element marker resolving, and no scheduling marks on section-header rows.
  - check: Every annotation has len(marker_locations) >= 1; no activity_schedule entry references the row_position of a section-header activity (rows 1, 12, 18, 22, 26, 28, 42 in the prior Table 01 output).
- **INV** _both_ The abbreviation lists on pages 16 and 17 are deliberately NOT emitted as abbreviation annotations, because their terms carry no in-grid marker and would be orphans.
  - check: No annotation in either file has annotation_type == 'abbreviation'.
- **SRC** _Table 01_ Grid column 14 (Day 23) carries no epoch label in the source header band - it sits between OP (col 13) and Inpatient Period 2 (cols 15-23) and the source prints nothing above it.
  - expected handling: The Epoch header cell at column_position 14 must remain empty (no fabricated 'Inpatient Period 2' or 'OP' value) and the new uncertainty report must flag it. Silently filling column 14 with a neighbouring epoch is a fabrication, not a fix.
- **SRC** _Table 01_ The source disagrees with itself about the Cu/Mo-controlled meals span: the grid marks cols 5-11 (Day -7 to 8) and 14-22 (Day 23 to 39), while footnote v describes 'inpatient Period 1 (Day -8 to Day 9)' and 'Period 2 (Day 23 to Day 40)'.
  - expected handling: Transcribe the grid as printed (marks only at cols 5-11 and 14-22 on the Cu/Mo-controlled meals row) and keep footnote v's wording verbatim as its own annotation. The new report must flag the grid/footnote disagreement; extending the marks to match footnote v would be inference.
- **JDG** _Table 01_ The two stacked partial epoch header bands were collapsed into ONE Epoch schedule_property at hierarchical_level 1, with Days as level 2 - two properties total, not three.
  - rationale: The two bands are complementary halves of one epoch dimension rather than a clean two-level hierarchy, so a two-level Epoch/Epoch model would misrepresent the source. Check: exactly 2 schedule_properties, epoch level 1 + study_day level 2.
- **JDG** _Table 01_ The PK/PD blood-sampling label that wraps across the p14/p15 page break is modelled as a SINGLE activity carrying the page-14 marks, not two activities.
  - rationale: The PD continuation line is one table row split by pagination and carries no marks of its own. Check: activities[] contains exactly one row whose activity_name starts 'Blood sampling for PK: Plasma total Mo and PUF-Mo' and also contains the 'PD: Plasma total and PUF-Cu' text; no separate activity begins 'PD: Plasma total and PUF-Cu'.
- **JDG** _Table 01_ The right-arrows trailing the two 'Discontinue ...' marks were captured as the single starting X only, with no marks emitted in the spanned columns.
  - rationale: Deliberate choice not to fabricate marks across the arrow's span; the report explicitly invites reconsideration. Check: activity_schedule entries for 'Discontinue chelation therapy' and 'Discontinue zinc therapy' - prior output has exactly one each (col 7 and col 3). Any change is the v3.6.0 arrow rule firing and needs human sign-off.
- **JDG** _Table 02_ Table 02 classified subsidiary; its general Note captured as a synthesised table-scoped marker 'note1'; marker 'a' scoped to the timepoint header (schedule_property) and 'b' to the 24-hour cell.
  - rationale: Finer within-visit PK/PD timing (hours -0.5 to 24) for an activity that already exists in Table 1 is the textbook subsidiary case. Check: markers a, b, note1 present; 'a' has a schedule_property location; 'b' a schedule_cell location at the last timepoint column (column_position 12 in the prior output); 'note1' synthesised and property-scoped.
- **Δ** Judgement call 4: the 'Discontinue chelation therapy' / 'Discontinue zinc therapy' trailing arrows were captured as the single starting X only, with no marks in the spanned columns.
  - expect: v3.6.0 should distribute each arrow across every column it covers - one activity_schedule entry per covered column with the arrow glyph as cell_value and source_range set. Expect the Table 01 cell count to rise above 212 on these two rows. Expected delta, not fabrication - but the arrow extents must be confirmed visually.
  - rule: §5 'Arrows spanning columns. A horizontal arrow (`↔`, `→`) drawn across N columns denotes a continuous activity over that span — distribute like a merged mark: one `activity_schedule` entry per covered column, `cell_value` the arrow glyph, `source_range` the span.'
- **Δ** Table 02's general Note captured as synthesized marker 'note1'; Table 01's epoch/day header structure inferred from two collapsed layout bands.
  - expect: New provenance fields should appear that the old output lacks: marker_locations[].method == 'synthesized' on note1's location, and schedule_property.structure_method == 'inferred_from_layout' on the collapsed Epoch property.
  - rule: §1e '`marker_locations[].method` — a scope not established by a printed marker: `synthesized` (§6 conventions)' and '`schedule_property.structure_method` — `inferred_from_layout` / `assumed`, when `property_type`/`hierarchical_level` do not come from printed header labels.'
- **Δ** The report states footnotes run on pages 15-16 and abbreviation lists on p16, but gives no per-page activity-row counts across the declared range 14-16.
  - expect: The new report must give activity rows per page for 14, 15 and 16 and explicitly state that p16 contributes no activity rows because it is a footnote/abbreviation page. Absence of this statement is a v3.6.0 compliance gap, not a data change.
  - rule: §4 'Then check coverage before delivering: every page in the declared range must contribute rows. ... If a page in the range genuinely has no activity rows (a footnote or abbreviation page), say so in the report.'
- **Δ** Marks placed from pdftotext -bbox word coordinates with column x-centres from the Days header row and each X assigned by nearest centre.
  - expect: This is now the prescribed default, so no provenance fields should be added for it - but merged spans must now be resolved from per-row rule-line geometry rather than nearest-centre alone, and the new report must state the bbox-vs-visual diff result cell-for-cell.
  - rule: §1b 'Resolve merged spans from per-row rule-line geometry: a missing internal vertical boundary between two adjacent column centres means the cell is merged across them' and §7 'Mechanical mark-check: the method used ... and any cell where the mechanical matrix disagreed with the visual read.'

_Notes:_ Grounded against NCT04573309_Table_01_extraction.json (43 activities, 24 annotations, 212 activity_schedule entries, 2 schedule_properties) and NCT04573309_Table_02_extraction.json (1 activity; annotations a on schedule_property row 1, b on schedule_cell row 1 col 12, note1 on schedule_property row 1). The report's closing sign-off gate is marked superseded 2026-07-21 and is not an acceptance item.

### NCT04677179

4 table(s): T1 main_soa pp17-23 (59a/158m/31n), T2 track pp24-32 (36a/180m/14n), T3 track pp33-42 (36a/211m/14n), T4 track pp43-46 (34a/54m/15n)

- **INV** _all_ Four tables with fixed classifications: Table 1 main_soa (doc pp.17-23); Table 2 track 'Maintenance (responders)' (pp.24-32); Table 3 track 'Extension (nonresponders)' (pp.33-42); Table 4 track 'Early Termination / Unscheduled / Post-Treatment' (pp.43-46).
  - check: Four extraction JSONs exist; table_metadata.table_type is main_soa, track, track, track for tables 1-4; track_label set on tables 2/3/4 only with the exact strings above; page_start/page_end are 17/23, 24/32, 33/42, 43/46.
- **INV** _all_ Page numbers are doc/PDF pages, one higher than the printed footer (doc p.43 = printed 42); page_start/page_end use doc pages.
  - check: Table 1 page_start == 17 (not 16) and Table 4 page_end == 46 (not 45); every activity source_page falls inside those doc-page ranges.
- **INV** _all_ 165 source activity rows across the four tables, consolidating to 60 unified activities, with schedule_matrix 603 cells.
  - check: Sum of len(activities) across the four new extraction JSONs == 165 (prior split 59 / 36 / 36 / 35). Any drop below 165 means rows were lost again.
- **INV** _Table 4_ Table 4's last row on doc p.46 is 'Dosing', printed under the 'Randomization and Dosing' header, carrying the note 'No dosing at ETV, V997, or post-treatment follow-up visits.' and NO marks in any of the four visit columns.
  - check: Table_04 activities[] contains a row with activity_name == 'Dosing' immediately after 'Randomization and Dosing'; the annotation whose text is 'No dosing at ETV, V997, or post-treatment follow-up visits.' has its marker_location on THAT row, not on 'Urine pregnancy (local)'; no activity_schedule entry exists for the Dosing row.
- **INV** _Table 4_ Table 4's first body page (doc p.43) carries 14 activity rows and 26 marks - it was missed entirely in the original pass and its restoration took schedule_matrix from 577 to 603.
  - check: Table_04 activities with source_page == 43 number 14, and the activity_schedule entries on those rows number 26. Zero rows on p.43 is the exact regression this study is known for.
- **INV** _Tables 2, 3, 4_ A 'Genetics sample' row is printed on every tile of Tables 2/3/4 and must be present in all three; it carries no marks in those tables, and the DNA-pharmacogenetics note binds to that row alone rather than spanning three activities.
  - check: Each of Table_02/03/04 activities[] contains a row with activity_name == 'Genetics sample' having no activity_schedule entries; the DNA-pharmacogenetics annotation has exactly one marker_location per table, on that row.
- **INV** _Tables 2 and 3_ Tables 2 and 3 are horizontally two-tiled (V10-V19 tile plus a 'V20-V29 (continued)' tile) and the recurring body rows appear in BOTH tiles; marks must be the union across tiles.
  - check: For Tables 2 and 3, every recurring activity row carrying marks in V20-V29 columns also carries its V10-V19 marks; total activity_schedule counts must not fall below 180 (Table 2) and 211 (Table 3).
- **INV** _all_ A full row audit against all 30 pages found no missing activity rows; the only page labels absent from the extraction are four section headers, omitted deliberately.
  - check: Re-run soa2usdm-row-audit against the new extraction; the only unmatched page labels permitted are the four named section headers.
- **INV** _Tables 1-4_ The PK-samples note legitimately prints twice per table - once on 'PK samples' and once on the CCI row below it. Two identical-text notes there are source-faithful, not a duplication defect.
  - check: In each table the PK-samples note resolves to two rows (PK samples plus the adjacent CCI row); confirm the new extraction does not dedupe it to a single location nor flag it as a containment defect.
- **SRC** _all_ 20 of the 30 SoA pages are full-page raster images with a one-glyph-per-token text layer ('V i t a l s i g n s') and no vector rule lines; only doc p.17 carries a vector table.
  - expected handling: The new report must state that the source is glyph-spread, name which fields were reconstructed, and state that rule lines were recovered from the 200 dpi raster rather than the empty vector layer. Silence here means the run fell back to proximity, which is what produced this study's fragmented-then-over-merged annotations twice before.
- **SRC** _all_ Several body rows are CCI black-bar redactions: marks are readable but activity names are not recoverable, and multiple CCI rows within one table cannot be merged by name.
  - expected handling: CCI rows must survive as distinct activities with their marks intact and placeholder names (e.g. 'CCI', 'CCI (redacted)'), never with an invented clinical activity name and never merged with each other. A CCI row that acquires a plausible-sounding name is a fabrication.
- **SRC** _Tables 1-4_ Four corrupt abbreviation-key fragments (T1 c23, T2 c13, T3 c13, T4 c12) come from the multi-column abbreviation block under each table (doc pp.23/32/42/46) - the column clip interleaved two text columns, e.g. 'Srs=columbia-suicide severity rating scale; Bs urface antigen'.
  - expected handling: If these are still emitted, their text must remain the visibly interleaved source text - never silently repaired into a clean abbreviation list, which would assert content the clip never produced. Dropping them per §6 or keeping them verbatim are both acceptable; inventing corrected text is not.
- **SRC** _Table 4_ A Comment cell on Table 4's 'Weeks from randomization' row (doc pp.43-45) carries the ETV<->V801/V802 interval rule and was deliberately left unextracted as property-scope content.
  - expected handling: If the new extraction now captures it, it must be a footnote annotation bound to the 'Weeks from randomization' schedule_property, not to an activity row. Appearance is an acceptable change; misbinding to an activity is not.
- **JDG** _Tables 2 and 3_ Tables 2 and 3 modelled as two separate track timelines rather than domain tables, despite sharing the V10-V29 visit numbering.
  - rationale: They split the population (responders vs nonresponders at Week 12) into different treatment phases, which is the track discriminator, not a different activity category on a shared timeline. Check: both have table_type 'track' with track_label 'Maintenance (responders)' and 'Extension (nonresponders)'; neither is 'domain' or 'continuation'.
- **JDG** _all_ Section-header rows are omitted from the activity list in all four tables - specifically 'Patient-Reported Outcomes (Electronic)', 'Clinician-Administered Questionnaires (Paper)', 'Laboratory Tests and Sample Collections' and 'Stool Samples'.
  - rationale: A deliberate, consistently applied convention; the row audit confirmed these are the only page labels absent. Check: activities[] in each table contains none of those four names. If v3.6.0 emits them as indentation_level 0 rows, counts rise above 165 - a convention change needing human sign-off, not an automatic improvement.
- **JDG** _all_ Schedule property values (Weeks / Study day / tolerance) were read once from the clean header pages and hardcoded per table rather than re-read from each raster page.
  - rationale: The raster pages cannot be trusted for header text; the clean header pages give the same values. Check: schedule_properties carry values identical to the prior verified extraction; any change needs page verification against the clean header page.
- **JDG** _all_ Corrections sidecars were emptied: after the 2026-07-28 re-extraction the fresh raw extraction is treated as ground truth with all fixes baked in, provenance living in git history.
  - rationale: This means the v3.6.0 output must be judged as a standalone raw extraction - do not credit it for content that only ever existed in a sidecar. Note the Table 4 sidecar (corr-001..003) is currently NON-empty and is what supplies the Dosing row.
- **Δ** The Dosing row on doc p.46 exists only via the Table 4 corrections sidecar (corr-001, corr-002, corr-003); in the raw extraction c11 is bound to 'Urine pregnancy (local)' at row 26.
  - expect: v3.6.0's page-coverage check should produce the Dosing row in the RAW extraction, making the sidecar redundant. Expect Table 4 raw activities to go from 34 to 35 with c11 bound to Dosing directly. The sidecar becoming empty is the success signal, not a loss.
  - rule: §4 'Then check coverage before delivering: every page in the declared range must contribute rows. ... on NCT04677179 the whole first body page of Table 4 was missed, taking 14 activities and 26 marks with it'
- **Δ** T1 c21_2 reads 'Addition alc. Difficile testing ...' where doc p.23 prints 'Additional C. difficile testing ...' - the italic run broke word re-segmentation and the text was preserved verbatim because rework never regenerates text.
  - expect: A fresh v3.6.0 pass regenerates annotation text with deglyph reconstruction, so this note should now read 'Additional C. difficile testing ...'. Expected correction, but it must be declared in the new report as a reconstructed field.
  - rule: §1c 'Rebuild words from the glyph stream ... apply the reconstruction to every text field — activity labels, header labels, and `annotation_text`. Annotation text is the field that gets skipped'
- **Δ** Note boundaries and row bindings were made geometric only in the 2026-07-30 rev2 rework (raster rule-line detection; 12 over-merged notes split, 6 bindings corrected, longest duplicated block 145 -> 0 chars).
  - expect: v3.6.0 should reach the geometric result in the FIRST pass: no proximity-bounded notes, longest duplicated sentence block 0 chars, no containment pairs. Any note that genuinely had to fall back to proximity must carry annotation_text_source.method == 'proximity_bounded' so the validator flags it.
  - rule: §6 'Bound each note's TEXT by the cell's rule-line geometry, not by proximity ... When the page has no vector rule lines, recover them from the raster (§1d); do NOT fall back to vertical-gap proximity' and §1e 'proximity_bounded (only when rules are genuinely unrecoverable — the validator flags these for page verification)'
- **Δ** The 2026-07-28 rework re-read notes via pdftotext -bbox plus de-glyph word re-segmentation, but the extraction JSON records no method provenance for it.
  - expect: Expect new annotation_text_source.method fields ('deglyph_reconstruction' or 'raster_band_cells') on notes from the 20 raster pages, plus activity_name_source.method and indentation_method on image-page rows. These fields are absent from the old output - their appearance is compliance, not drift.
  - rule: §1e 'Every interpreted value has a default method; when you arrive at a value any other way, record the method in the schema's provenance fields.'
- **Δ** The V10-V19 tile marks on Tables 2 and 3 were lost in the original pass (extractor kept only the '(continued)' tile) and had to be restored via sidecars (+34 / +38 cells).
  - expect: v3.6.0's tiled-table union rule should give Tables 2 and 3 their full mark counts (180 and 211) in the first pass, with no sidecar needed.
  - rule: §5 'Horizontally tiled wide tables — union rows across tiles ... Do NOT assume a recurring row prints in only one tile and keep only that tile's marks — that silently drops the other tile's visits.'
- **Δ** Four corrupt abbreviation-key fragments (T1 c23, T2 c13, T3 c13, T4 c12) are currently emitted as footnote annotations bound to activity rows, though they are abbreviation-block text with no in-grid marker.
  - expect: v3.6.0 may legitimately drop these, since a standalone abbreviation list whose terms carry no in-grid marker must not be emitted. Expect raw annotation counts to fall by one per table (T1 31->30, T2 14->13, T3 14->13, T4 15->14). Rule-driven disappearance, not lost data.
  - rule: §6 'Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker — every annotation needs ≥1 `marker_location` (§7), so an unreferenced list entry is an orphan and is dropped downstream.'
- **Δ** CCI black-bar redaction rows nearly vanished from the raster band list because a redaction bar fills its cell edge to edge and reads as a horizontal rule.
  - expect: v3.6.0 requires taking row boundaries from a text-bearing column (the notes column), so CCI rows and their marks should survive band detection. Any CCI row losing marks in the new output is a regression against a rule the prompt names by study.
  - rule: §1d 'Take the row boundaries from a column that holds text, never from a redacted one. A black redaction bar fills its cell edge to edge, reads as a horizontal rule, and makes that row vanish from the band list — on NCT04677179 this nearly dropped a CCI row that carries three marks.'
- **Δ** Per-row annotation_markers had to be regenerated from marker_locations in the 2026-07-30 rework (24 stale rows), because resolve reads annotation_markers while marker_locations held the corrections.
  - expect: v3.6.0 requires the two sides to agree at delivery time, so no post-hoc regeneration should be needed. Verify mechanically: every marker in an annotation's marker_locations also appears in that row's annotation_markers.
  - rule: §6 '`annotation_markers` and `marker_locations` must agree — the first one is what actually binds. ... a location recorded on one side and not the other is silently dropped, with nothing failing anywhere in the pipeline.'

_Notes:_ Counts cross-checked against the extraction JSONs: Table 1 59 activities / 31 annotations / 158 cells; Table 2 36 / 14 / 180; Table 3 36 / 14 / 211; Table 4 raw 34 activities (verified.json 35, with the restored Dosing row at row_position 40) / 15 annotations / 54 cells. 59+36+36+34 = 165 matches the report's source-activity count. Table 4's corrections sidecar is the only non-empty one; the other three are empty stubs.

### NCT04730349

3 table(s): T1 main_soa pp28-30 (21a/17m/18n), T2 main_soa pp31-38 (27a/84m/23n), T3 main_soa pp39-42 (19a/51m/15n)

- **INV** _Table 2-1_ Table 2-1 (Screening Procedural Outline) is main_soa with 1 schedule column, 21 activities (17 procedures + 4 headers) and 18 annotations, doc pages 28-30.
  - check: NCT04730349_Table_01_extraction.json: table_type == 'main_soa'; len(activities) == 21; len(annotations) == 18; one schedule_property; page_start 28, page_end 30.
- **INV** _Table 2-2_ Table 2-2 (On-treatment Procedural Outline) is main_soa with 6 schedule columns (C1 D1/3/5/8; C2+ D1/D3-5), 27 activities (21 procedures + 6 headers) and 23 annotations, doc pages 31-38.
  - check: NCT04730349_Table_02_extraction.json: table_type == 'main_soa'; len(activities) == 27; len(annotations) == 23; schedule_grid column_position values run 2..7; page_start 31, page_end 38.
- **INV** _Table 2-3_ Table 2-3 (Long-term Follow-up Period) is main_soa with 4 schedule columns (Safety FU V1/2/3; Survival FU), 19 activities (14 procedures + 5 headers) and 15 annotations, doc pages 39-42.
  - check: NCT04730349_Table_03_extraction.json: table_type == 'main_soa'; len(activities) == 19; len(annotations) == 15; column_position values 2..5; page_start 39, page_end 42.
- **INV** _all_ Doc p27 is the SoA section-intro page and is excluded from page_start; the three tables cover doc 28-30, 31-38 and 39-42 with nothing missing or extraneous.
  - check: No table has page_start == 27; the union of the three declared page ranges is exactly 28..42.
- **INV** _Table 2-2_ Ten Table 2-2 rows carry one merged text cell spanning columns 3-7 with source_range '3:7' (Adverse Events, Concomitant Med Use, Body/Brain imaging blocks, CSF/Bone Marrow x4, PK Plasma, Nivolumab PK, Immunogenicity, PRO) - the span starts at column 3, not column 2.
  - check: Table_02 activity_schedule: each merged-text row has 5 entries at column_position 3,4,5,6,7 with source_range == '3:7', and no entry with that text at column_position 2.
- **INV** _Table 2-3_ Table 2-3 merged text cells span all four schedule columns with source_range '2:5' (CSF, Bone marrow, PK, Immunogenicity), while 'If toxicities are present.' / 'If toxicities are present' on Lab Tests Visits 2 and 3 are individual cells transcribed verbatim including the period difference.
  - check: Table_03: the CSF / Bone marrow / PK / Immunogenicity text entries each appear 4 times with source_range '2:5'; the two 'If toxicities are present' cells have no source_range and differ by the trailing period.
- **INV** _Table 2-2_ Footnote 'e' rides the 'Pharmacokinetic (PK)/Immunogenicity Assessments' section-header row and is activity-scoped on that header - a marker on an organizational header is allowed because it is not a scheduling mark.
  - check: Table_02 annotation with marker 'e' has one marker_location of location_type 'activity_name' on the row named 'Pharmacokinetic (PK)/Immunogenicity Assessments'; that row has no activity_schedule entries.
- **INV** _Table 2-2_ Footnote '*' ('At Day 8 visits collect vital signs only.') is cell-scoped on the Targeted Physical Day-8 cell, printed as X*.
  - check: Table_02 annotation with marker '*' has a marker_location of location_type 'schedule_cell' on the Targeted Physical row at the Cycle-1 Day 8 column (column_position 5 in the prior output), and that cell_value is clean 'X'.
- **INV** _all_ Header-cell footnotes are column-scoped, not row-scoped: T2-1 'a' on Screening Visit; T2-2 'a,b' on the Cycle 1 band and 'a,b,c' on the Cycle 2+ band (marker on the first cell of each merged band), 'd' on the Cycle-1 Day 3 cell; T2-3 'a' on Visits 1/2/3 and 'b' on Survival Follow-up.
  - check: Each marker carries a column_position: T2-2 a and b at columns 2 and 6, c at column 6 only, d at column 3; T2-3 a at columns 2,3,4 and b at column 5. A header-row marker with no column_position is a regression.
- **INV** _Table 2-3_ The 'Pregnancy Test' row (X at Visits 1-3, plus its note) is present in the PDF and must be extracted from the PDF; the markdown extraction dropped it.
  - check: Table_03 activities[] contains a row with activity_name == 'Pregnancy Test' carrying X at column_position 2, 3 and 4.
- **INV** _all_ Abbreviation lists in all three tables are NOT captured, because their terms carry no in-grid marker and would resolve as orphans.
  - check: No annotation in any of the three files has annotation_type == 'abbreviation'.
- **SRC** _Table 2-1_ Four screening notes (CSF-Solid, Bone Marrow-Solid, CSF-Leukemia, Bone Marrow-Leukemia) end at 'See Section 9.1[.2.5].' followed by a black redaction box - the trailing text is not recoverable.
  - expected handling: Those four annotations must end with an explicit redaction marker and no invented continuation. Any version that completes the sentence has fabricated hidden content.
- **SRC** _Table 2-1_ A larger redaction box below the last activity on doc p30 may hide additional activity rows; whether it does cannot be determined from the source.
  - expected handling: The new report must again flag the p30 redaction box as possibly concealing rows; Table_01 activity count stays at 21 unless new rows are visually evidenced. Neither inventing rows nor dropping the flag is acceptable.
- **SRC** _Table 2-2_ Footnote 'e' has a PDF redaction between '...will likely be for' and 'pharmacokinetic assessments'; the markdown shows continuous text with no gap, so the markdown wording was used - one or more words may be redacted.
  - expected handling: Keep the markdown wording but re-flag in the report that the PDF has a redaction at that point and the markdown may be silently filling it. Presenting the markdown text as complete PDF content without the flag loses the defect.
- **SRC** _Table 2-2_ Four Efficacy notes end with redaction boxes, and a large redaction box below Immunogenicity Samples on doc pp35-36 may hide additional activity rows.
  - expected handling: The four Efficacy notes must carry a redaction marker and no invented tail; the pp35-36 box must be re-flagged in the report as possibly concealing rows.
- **SRC** _Table 2-3_ A redaction box below the Pregnancy Test row on doc p40 may hide additional activity rows.
  - expected handling: Re-flag the doc p40 box in the report; Table_03 activity count stays at 19 unless new rows are visually evidenced. Do not invent rows and do not drop the flag.
- **SRC** _all_ The protocol markdown is lossy relative to the PDF: it dropped the Table 2-3 Pregnancy Test row entirely, lost several '±' symbols (rendered as spaces) and merged 'See'+'Section'.
  - expected handling: PDF stays authoritative for the row set and for symbols/spellings, and every PDF/markdown disagreement must be flagged in the new report. Check: Table_02 Day cell_values contain literal '±' (e.g. '(± 1 day)') and cross-reference text reads 'See Section', not 'SeeSection'.
- **JDG** _all_ All three tables classified main_soa - not domain, not continuation, not track.
  - rationale: Each is an independent schedule with its own column structure; domain/continuation are ruled out by the different columns and track by the same population/phase progression of one study. Three main_soa tables in one study is unusual - a fresh extraction that reclassifies any of them needs human review against this reasoning.
- **JDG** _Table 2-2_ Oral Hydration Follow-up's single 'X (Day 3-5)' mark, printed centred over the Cycle-1 Day3/Day5 region, was distributed to columns 3-4 with source_range '3:4' and cell_value 'X'; the '(Day 3-5)' label is not separately stored because it equals the distributed span.
  - rationale: The parenthetical names a span of the table's own columns, so it is expressible as a column span rather than a condition; v3.6.0 §5 now codifies exactly this case by name. Check: exactly two entries on that row, at column_position 3 and 4, cell_value 'X', source_range '3:4'.
- **JDG** _Table 2-2_ 12-lead ECG column 7 kept literally as cell_value 'X (Cycle 5 only)' rather than split into 'X' plus a separate condition.
  - rationale: The Cycle-5 condition is not expressible as a span of the table's columns, so the qualifier stays in the cell text; v3.6.0 §5 cites this exact string as its example. Check: entry on '12-lead Electrocardiogram (ECG)' at column_position 7 with cell_value exactly 'X (Cycle 5 only)' and no source_range.
- **JDG** _Table 2-3_ Footnote 'c', printed on the Notes-column header ('Notes^c'), is modelled table-scope: one schedule_property marker_location for traceability, with the marker NOT placed on any element's annotation_markers.
  - rationale: The Notes column is not a modelled schedule element, so there is no element for the marker to bind to; it resolves unlinked/table-wide. v3.6.0 §6 now codifies this treatment. Check: marker 'c' has exactly one schedule_property location with no column_position, and no element lists 'c' in annotation_markers.
- **JDG** _Table 2-2_ The 'Cycle = 3 wks' / 'Each cycle = 3 wks' caption is folded into the Cycle property_comment rather than emitted as a separate schedule_property row.
  - rationale: The cycle length is uniform for both bands, so it does not distinguish one column from another. Check: Table_02 has exactly 2 schedule_properties (Cycle level 1, Study Day level 2) and the Cycle property_comment mentions the 3-week cycle length.
- **JDG** _Table 2-2_ Visit windows '(± 1 day)' / '(- 1 day)' are kept inline in each Day cell_value as faithful transcription, not split out into a separate window property row.
  - rationale: Faithful transcription of the printed header cell. Check: Study Day schedule_grid cell_values contain the parentheticals and no schedule_property has property_type == 'window'.
- **JDG** _Table 2-3_ Column 5 'Survival Follow-up Every 3 Months (± 14 Days)' is modelled as one more column value of the single visit property, despite being a different phase, with the reasoning noted in the property comment.
  - rationale: The source presents it as one more column in the same header row. Check: Table_03 has exactly one schedule_property covering columns 2..5, column 5's cell_value is the Survival Follow-up label, and no separate phase/epoch property exists.
- **JDG** _Table 2-2 and Table 2-3_ Both property_names for Table 2-2's two-level header ('Cycle', 'Study Day') and Table 2-3's visit row ('Follow-up Visit') are synthesised; Table 2-1's 'Screening Visit' is taken directly.
  - rationale: In T2-2 both label cells hold the spanning 'Procedure' activity-column header, so no property name is printed. Check: Table_02 both properties have property_name_source.synthesized true with names 'Cycle' and 'Study Day'; Table_03's is synthesized true with 'Follow-up Visit'; Table_01's is not synthesised.
- **JDG** _all_ The right-hand Notes/Comments column is turned into footnote/source_note annotations with synthesised markers (n1..., s1...) linked to the activity or property row; explanatory notes typed 'footnote', pure cross-references typed 'source_note'.
  - rationale: The Notes column is not a schedule column and not an activity. Check on annotation_text, not marker string: the report names T2-3's source_notes 's1'/'s2' while the JSON actually uses 's6'/'s8', so synthesised marker names are already known to be unstable identifiers.
- **JDG** _Table 2-2_ The merged-text span was fixed at columns 3-7, not 2-7, confirmed two independent ways.
  - rationale: A cell border at the Day1|Day3 boundary was visible in the zoomed image, and the markdown shows Day 1 empty. Check: no Table_02 merged-text entry has source_range '2:7' or a column_position 2 entry carrying merged text. A v3.6.0 output that widens these to 2:7 contradicts a doubly-confirmed geometry read and needs review.
- **Δ** Header-cell footnotes are recorded as marker_locations of location_type 'schedule_property' carrying a column_position (T2-1 a; T2-2 a,b,c,d; T2-3 a,b).
  - expect: v3.6.0 requires a per-timepoint header marker to be encoded as annotation_markers on THAT column's schedule_grid cell rather than on the schedule_property row. Expect these locations to move to the schedule_grid/schedule_cell level, with the marker cleaned out of cell_value. The column bindings themselves must not change.
  - rule: §6 'Header-cell footnotes (per-timepoint). A marker on a specific header/timepoint cell — "V2ᵃ", "ETVᵇ", "V997ᶜ" — encodes as `annotation_markers` on that column's `schedule_grid` cell (the exact column it sits on) ... Do NOT put it on the `schedule_property` row's `annotation_markers`'
- **Δ** T2-3 footnote 'c' is modelled table-scope with one schedule_property marker_location and no element marker; the report asks for confirmation.
  - expect: v3.6.0 codifies this exact treatment and adds a required provenance field: expect the marker_location to now carry method: 'synthesized'. The treatment itself is confirmed by rule, so the 'please confirm' item is closed rather than open.
  - rule: §6 'A footnote marker printed on the Notes-column *header* itself (e.g. "Notesᶜ") has no modelled element to attach to — treat it as table-scope: give the annotation one `schedule_property` `marker_location` with `method: "synthesized"` for traceability and do NOT put the marker on any element'
- **Δ** Notes-column annotations use synthesised markers n1..., s1... linked by position, with no method field recorded on the locations.
  - expect: Expect marker_locations[].method == 'synthesized' on every Notes-column-derived location (and 'text_match' where a binding came from word overlap). Also expect synthesised marker NAMES to shift between runs (v3.6.0 adds a pr1/pr2 series for inline references), so acceptance must key on annotation_text plus bound row_position, never on the marker string.
  - rule: §6 'If the source gives the note no marker, synthesise one and link it via `marker_locations` to the row it sits beside (`activity_name` or `schedule_property`), with `method: "synthesized"` on the location; a binding established by word overlap rather than position gets `method: "text_match"`'
- **Δ** Redaction truncations are marked with the string '[Remainder of note redacted in source.]'.
  - expect: v3.6.0 prescribes the literal string '[remainder redacted in source]'. Expect the marker wording to change on the four T2-1 screening notes and the four T2-2 Efficacy notes. Wording change only - the set of truncated notes must be identical.
  - rule: §6 'transcribe the visible portion, append "[remainder redacted in source]" to `annotation_text`, and never fabricate the hidden text'
- **Δ** T2-2's Cycle and Study Day property_type / hierarchical_level were derived from the two-band layout geometry rather than printed property labels (both label cells hold the spanning 'Procedure' header).
  - expect: Expect schedule_property.structure_method == 'inferred_from_layout' on both T2-2 properties and on T2-3's synthesised 'Follow-up Visit' property. New field, absent from the old output.
  - rule: §3 'When `property_type` or `hierarchical_level` come from layout geometry or working assumption rather than printed header labels, set `structure_method` (`inferred_from_layout` / `assumed`) — see §1e.'
- **Δ** The report gives per-table activity totals but no per-page activity-row counts across the declared ranges (28-30, 31-38, 39-42).
  - expect: The new report must list activity rows per page for every page in each declared range and call out any page contributing none - Table 2-2's eight-page range 31-38 is the one at risk. Absence of this breakdown is a compliance gap, not a data change.
  - rule: §4 'Then check coverage before delivering: every page in the declared range must contribute rows.' and §7 'activity rows per page across the declared page range — call out any page in the range that contributed none'
- **Δ** Cross-references appear only as Notes-column source_notes; no handling is described for section references printed inline in an activity label.
  - expect: If any activity label carries an inline section/appendix reference, v3.6.0 will strip it out of activity_name (keeping it in activity_name_source.cell_text), emit it as a deduplicated source_note, and add a pr1/pr2 synthesised marker to each citing row. Expect possible activity_name shortening and new pr-series annotations - check any such change against the printed label rather than treating it as a regression.
  - rule: §6 'a section/appendix/attachment reference printed inline in an activity's label ... Strip inline references OUT of `activity_name` (keep them in `activity_name_source.cell_text`), emit each as a `source_note` deduplicated by text ... and add a synthesised marker (`pr1`, `pr2`, …) to every citing activity's `annotation_markers`'

_Notes:_ Counts verified against the extraction JSONs: Table_01 21 activities / 18 annotations / 1 property ('Screening Visit', visit, level 1); Table_02 27 / 23 / 2 properties (Cycle-cycle-level1, Study Day-study_day-level2), with 12-lead ECG at row 3 col 7 cell_value 'X (Cycle 5 only)' and Oral Hydration Follow-up at row 27 cols 3-4 source_range '3:4'; Table_03 19 / 15 / 1 property ('Follow-up Visit', visit, level 1) with marker 'c' at location_type schedule_property and no column_position. One report/data discrepancy for the acceptance checklist: the report calls T2-3's two source_notes 's1' and 's2' while the JSON uses 's6' and 's8'.

### NCT05176314

1 table(s): T1 main_soa pp10-11 (24a/122m/8n)

- **INV** _Table 01_ Exactly one table is extracted, classified main_soa, covering protocol pages 10-11.
  - check: Exactly one NCT05176314_Table_*_extraction.json exists; table_metadata.table_type == "main_soa"; page_start == 10 and page_end == 11.
- **INV** _Table 01_ The table has 24 activities and 122 activity-schedule cell values.
  - check: len(activities) == 24 and len(activity_schedule) == 122.
- **INV** _Table 01_ Two header rows over 21 timepoint columns, i.e. 42 schedule_grid cells.
  - check: len(schedule_properties) == 2 and len(schedule_grid) == 42; distinct column_position values in schedule_grid == {2..22}.
- **INV** _Table 01_ The page-2 header repeat is encoded once - a single table, NOT a continuation table.
  - check: No table has table_type == "continuation" and no continuation_of field is set; only one extraction JSON is emitted.
- **INV** _Table 01_ Column model: col 2 = Screening (D-42 to -2), col 3 = Day -1, cols 4-21 = Days 1-18, col 22 = FU/ED (Day 24 +/- 2 days).
  - check: schedule_grid row_position 2 has cell_value "18" at column_position 21 and the FU/ED label at column_position 22; column_position 3 holds "-1".
- **INV** _Table 01_ Header footnote a sits on the Day 18 header cell and b on the FU/ED header cell (column-scoped, not row-scoped).
  - check: schedule_grid cell (row 2, col 21) has annotation_markers containing "a"; schedule_grid cell (row 1, col 22) has annotation_markers containing "b"; neither marker appears on a schedule_property's annotation_markers.
- **INV** _Table 01_ Footnote markers bind as: d on Supine vital signs, g on Rosuvastatin PK samples, f on the Day-6 rosuvastatin PK cell.
  - check: Annotation d has an activity_name marker_location on the "Supine vital signs (PR and BP)" row; annotation g on the "Rosuvastatin PK samples" row; annotation f has a schedule_cell marker_location at the Rosuvastatin PK samples row, column_position 9 (Day 6), and that activity_schedule cell carries annotation_markers "f".
- **INV** _Table 01_ Legend-defined in-grid P and the postdose-hour timepoints stay as cell_value, never converted to annotations.
  - check: activity_schedule contains cells with cell_value exactly "P" (e.g. 12-lead ECG and Clinical laboratory tests rows) and cells with values such as "24 h", "48 h", "120 h"; no annotation has annotation_text defining P as an in-grid mark replacement for those cells.
- **INV** _Table 01_ The Day-1/6/13 rosuvastatin PK cells carry the full serial-sampling list as one literal cell value.
  - check: activity_schedule on the Rosuvastatin PK samples row has cell_value "P, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 12 h" at exactly three columns (4, 9, 16).
- **INV** _Table 01_ No orphan annotations: every annotation carries at least one marker_location and every used marker a-g resolves.
  - check: Every annotation has len(marker_locations) >= 1; the set of markers appearing in any annotation_markers string is a subset of the defined annotation_marker values.
- **SRC** _Table 01_ Two activity rows print only as "CCI" in the source: their real names and their entire mark rows are redacted. They must be captured as activities named CCI with no schedule marks - never named or marked by inference.
  - expected handling: activities contains exactly two rows with activity_name "CCI", positioned immediately before and after the "Rosuvastatin PK samples" row; no activity_schedule entry exists for either CCI row_position. Any invented activity name or any mark on a CCI row is a fabrication, not a fix.
- **SRC** _Table 01_ Footnote texts for markers d, f and g are redacted in the source (CCI); the markers themselves are printed and intact.
  - expected handling: Annotations d, f, g exist with marker_locations preserved, and annotation_text states plainly that the definition is redacted in source (per prompt s6 'Redacted / illegible content'). Any substantive footnote wording supplied for d, f or g is fabricated.
- **JDG** _Table 01_ The 'Treatment Period (Study Days)' header band was modelled as merged over cols 3-21, so Day -1 (admission) is grouped inside the treatment period.
  - rationale: Matches the drawn header band as the source presents it, rather than re-deriving the epoch boundary clinically.
- **JDG** _Table 01_ The two CCI rows were kept in sequence at row positions 22 and 24 rather than dropped or collapsed.
  - rationale: Preserves row order and downstream traceability even though their content is redacted.
- **JDG** _Table 01_ Flat activity list with all indentation_level = 1 (no level-0 section headers).
  - rationale: No section headers are present in the table.
- **JDG** _Table 01_ Both header-row property_names were synthesized: 'Study Phase' (L1) and 'Study Day' (L2).
  - rationale: The col-1 label cell holds the activity-column header 'Study Procedure', not a header-row name.
- **JDG** _Table 01_ Header footnotes a and b were bound to their specific header grid cells via schedule_cell locations, and f to the Day-6 PK cell (row 23, col 9).
  - rationale: Column-scoped placement keeps each footnote attached to the visit it governs rather than the whole header row.
- **Δ** Abbreviation list captured as one `abbreviation` annotation anchored nominally to `schedule_property` row 1 (no in-cell marker).
  - expect: v3.6.0 forbids emitting a standalone abbreviation list whose terms carry no in-grid marker, so this annotation is expected to disappear - annotation count drops from 8 to 7 and the abbreviation content moves to the report rather than the JSON. Do not treat the missing abbreviation annotation as a regression; DO treat a silently dropped footnote a-g as one.
  - rule: s6: "Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker"
- **Δ** Extraction JSON carries no method provenance fields at all (verified: the string "method" does not occur in NCT05176314_Table_01_extraction.json).
  - expect: v3.6.0 adds exception-based provenance: expect activity_name_source.indentation_method (assumed_flat for this flat list), schedule_property.structure_method (inferred_from_layout / assumed) on the two synthesized header rows, and a report line for every non-default method. Absent = default is still legal, so new fields are additive, not a diff to reject.
  - rule: s1e Method provenance - record HOW, exception-based; s7 "Method provenance: every non-default method recorded"
- **Δ** Activities carry no source_page field and the report gives no per-page activity-row counts.
  - expect: v3.6.0 requires source_page per activity row and a per-page coverage check across page_start..page_end (10-11), with the report calling out any page in the range contributing zero rows. Expect new source_page values and a per-page count line in the new report.
  - rule: s4: "**source_page** - record the document page each row was read from" and s7 "activity rows per page across the declared page range"
- **Δ** Report states the redacted-footnote annotation_text as "Redacted in source (CCI — confidential commercial information)."
  - expect: v3.6.0 prescribes transcribing the visible portion and appending "[remainder redacted in source]"; the exact wording of the redaction note may therefore change. The wording is free, the non-fabrication is not - any newly supplied text for d/f/g is a regression.
  - rule: s6: "transcribe the visible portion, append \"[remainder redacted in source]\" to `annotation_text`, and never fabricate the hidden text"

_Notes:_ Counts in the invariants were re-verified against NCT05176314_Table_01_extraction.json: 24 activities (row_positions 3-26, CCI at 22 and 24), 122 activity_schedule entries, 42 schedule_grid entries, 8 annotations, zero cells with source_range (no merged/arrow marks in this table), no method fields present.

### NCT05259917

1 table(s): T1 main_soa pp17-18 (24a/61m/19n)

- **INV** _Table 01_ One SoA table only (Table 1: Schedule of Events); Table 3 'Sample Randomization Schedule' is not a SoA and must not be extracted as one.
  - check: Exactly one extraction JSON exists for this study; no table has table_title containing "Sample Randomization Schedule".
- **INV** _Table 01_ Declared page range is document pages 17-18.
  - check: table_metadata.page_start == 17 and table_metadata.page_end == 18.
- **INV** _Table 01_ Classified main_soa and flat: 24 activity rows, all level-0, every one carrying marks (documented flat-table exception to the 'no marks on header rows' rule).
  - check: table_metadata.table_type == "main_soa"; len(activities) == 24; every activity has activity_name_source.indentation_level == 0; no activity row is mark-free.
- **INV** _Table 01_ The SoA PDF is text-layer based, not image-based - the only embedded image is the sponsor logo.
  - check: extraction_metadata / report states a bbox text-layer method (s1b), not a raster pixel-detection method (s1a); cell method fields, if present, are not raster_pixel_detection.
- **INV** _Table 01_ 19 footnotes a-s, all typed footnote, defined on document page 18.
  - check: len(annotations) counting footnotes == 19 and the set of annotation_marker values == {a..s}; every one has annotation_type "footnote".
- **INV** _Table 01_ Header-cell (column-scope) footnotes: a on Randomization (col 3), b on each of the three attack columns (cols 4-6), c on Final Visit/ET (col 7).
  - check: schedule_grid cell (row 1, col 3) annotation_markers contains "a"; (row 1, col 7) contains "c"; (row 2, cols 4,5,6) each contain "b"; annotation b has three schedule_property/schedule_grid marker_locations at columns 4, 5, 6.
- **INV** _Table 01_ Footnote r is deduplicated: one annotation with four activity_name marker_locations (PGI-S, PGI-C, VAS, GA-NRS).
  - check: Exactly one annotation whose text references the timed assessments; len(its marker_locations) == 4 covering the PGI-S, PGI-C, VAS and GA-NRS rows; those four activities each have annotation_markers containing "r".
- **INV** _Table 01_ Three continuous-activity arrow rows with fixed spans: Conventional on-demand treatment washout cols 4-6; Concomitant Medication Review cols 2-7; Adverse Event Review cols 2-7.
  - check: The washout row has 3 activity_schedule cells at cols 4,5,6 with source_range "4:6"; Concomitant Medication Review and Adverse Event Review each have 6 cells at cols 2-7 with source_range "2:7" (15 source_range cells total).
- **INV** _Table 01_ Adverse Event Review's arrow is transcribed full-width cols 2-7 as drawn, not narrowed to the footnote-s window.
  - check: Adverse Event Review row has arrow cells at every column 2 through 7, including col 2 (Screening) and col 3 (Randomization).
- **INV** _Table 01_ The abbreviation list (C1-INH, ECG, eDiary, ET, GA-NRS, HAE, IMP, PGI-C, PGI-S, RTSM, VAS) is deliberately NOT captured because its terms carry no in-grid markers.
  - check: No annotation has annotation_type "abbreviation"; annotation count remains 19.
- **INV** _Table 01_ Two header rows: row 1 property_name 'Visit' taken from the col-1 label; row 2 is a synthesised name for the three treatment-attack columns.
  - check: schedule_properties[0].property_name == "Visit" with property_name_source.synthesized not true; schedule_properties[1].property_name_source.synthesized == true and property_type == "visit", hierarchical_level 2.
- **JDG** _Table 01_ The single vertically-merged Randomization X (col 3) was transcribed onto BOTH the In-clinic and TeleVisit activity rows.
  - rationale: The schema has no vertical-merge concept, and footnote a says the Randomization Visit may be either modality, so the shared mark is duplicated to both activities.
- **JDG** _Table 01_ Horizontal double-headed arrows represented as cell_value "↔" distributed per covered column with source_range, rather than a single cell or a synthesized annotation.
  - rationale: Arrow extents were confirmed by zoomed image crops plus pixel analysis; the glyph is the extractor's chosen representation.
- **JDG** _Table 01_ Header row 1 typed property_type = epoch despite mixing phases and point visits (Screening / Randomization / Treatment Period / Final Visit/ET).
  - rationale: Treatment Period is the spanning band, so epoch was taken as the dominant phase framing; the report records that `visit` would also be defensible.
- **JDG** _Table 01_ Table S1 'Frequency of Patient Assessment' (also printed as Table 4) is out of scope; footnote r carries the cross-reference instead.
  - rationale: It is not in the _soa.pdf excerpt, it sits in the trial-procedures narrative, and its rows are time-periods/frequencies rather than an activity x timepoint grid.
- **Δ** The vertically-merged Randomization X duplicated onto In-clinic and TeleVisit was flagged as a judgement call for review.
  - expect: v3.6.0 makes this a rule, so the same output is now expected by construction rather than as a discretionary call. The mark must still appear on both rows; only its framing in the new report should change from judgement call to rule application.
  - rule: s5: "**Vertically-merged marks.** A single mark centred across two or more *activity rows* applies to every covered row. The schema has no vertical merge, so emit the mark on each covered activity's cell."
- **Δ** Arrow glyph rendered as "↔" (this study) vs "←→" on NCT05324124.
  - expect: v3.6.0 says only 'cell_value the arrow glyph' and does not canonicalise a token, so the new run may emit either glyph. A change of glyph is an expected delta; a change of SPAN (4:6 / 2:7 / 2:7) or a collapse to a single centred cell is a regression.
  - rule: s5: "**Arrows spanning columns.** ... distribute like a merged mark: one `activity_schedule` entry per covered column, `cell_value` the arrow glyph, `source_range` the span."
- **Δ** Extraction JSON carries no method provenance fields (verified: the string "method" does not occur in NCT05259917_Table_01_extraction.json).
  - expect: Expect new s1e fields: activity_name_source.indentation_method "assumed_flat" for this flat table, schedule_property.structure_method on the synthesised row-2 property, and a report line per non-default method. Additive, not a regression.
  - rule: s1e; s4: "set `activity_name_source.indentation_method` (`font_signal` / `visual_estimate` / `assumed_flat` for flat tables)"
- **Δ** Activities carry no source_page and the report gives no per-page activity-row counts for pages 17-18.
  - expect: Expect source_page on every activity and an explicit per-page row count in the new report, including a statement if the footnote page 18 contributes no activity rows.
  - rule: s4 source_page + coverage check; s7 "activity rows per page across the declared page range"
- **Δ** Abbreviation list intentionally not captured (recorded as a judgement in the old report).
  - expect: v3.6.0 now mandates this outcome, so it should persist without being framed as a discretionary omission. If the new extraction ADDS an abbreviation annotation with no in-grid marker, that is a rule violation, not an improvement.
  - rule: s6: "Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker"

_Notes:_ Verified against NCT05259917_Table_01_extraction.json: 24 activities (row_positions 1-24), 19 annotations all with >=1 marker_location, 9 schedule_grid cells, 61 activity_schedule cells of which 15 carry source_range, header markers a/c on schedule_grid row 1 cols 3/7 and b on row 2 cols 4-6, X present at col 3 on both row 1 (In-clinic) and row 2 (TeleVisit). The report records no PDF-level defect (no redactions, no illegible regions, no missing pages), so source_defects is intentionally empty.

### NCT05324124

1 table(s): T1 main_soa pp9-12 (20a/77m/9n)

- **INV** _Table 01_ One table, table_type main_soa, spanning Document pages 9-12; the repeating header is encoded once, not as a continuation table.
  - check: Exactly one extraction JSON; table_type == "main_soa"; page_start == 9 and page_end == 12; no table_type "continuation" and no continuation_of.
- **INV** _Table 01_ Counts: 20 activities, 41 schedule-grid (header) cells, 77 activity x timepoint cells.
  - check: len(activities) == 20, len(schedule_grid) == 41, len(activity_schedule) == 77.
- **INV** _Table 01_ Source completeness verified - the _soa.pdf contains exactly the 4 SoA pages, with no missing continuation page or separate screening table.
  - check: The new report must not claim a missing page; every page 9-12 contributes activity rows (s4 coverage check).
- **INV** _Table 01_ Column model: col 2 Screening, cols 3-14 Days -1..11, col 15 ED, col 16 Follow-Up phone call, col 17 Comments excluded from the grid.
  - check: Max column_position in schedule_grid and activity_schedule is 16; schedule_grid row 3 has "ED" at col 15 and the follow-up window text at col 16; no schedule column carries free-text note content.
- **INV** _Table 01_ There is a SINGLE ED column (the markdown's doubled ED|ED is a markdown rendering artifact; bbox is authoritative).
  - check: Exactly one schedule_grid cell has cell_value "ED" in the study-day row; the grid has 16 columns, not 17 schedule columns.
- **INV** _Table 01_ Genetic sample carries its X at Day 1 (col 4), NOT at Screening - a deliberate column-shift correction of the markdown grid.
  - check: The "Genetic sample" row has exactly one activity_schedule cell, at column_position 4, cell_value "X"; there is no cell at column_position 2 for that row.
- **INV** _Table 01_ AE/Serious AE review and Concomitant medication review carry a distributed arrow across cols 4-14 plus discrete X at Screening (col 2), Day -1 (col 3) and ED (col 15).
  - check: Each of those two rows has 11 cells at cols 4-14 with source_range "4:14" and an arrow cell_value, plus cell_value "X" at cols 2, 3 and 15 (14 cells per row; 22 source_range cells in total).
- **INV** _Table 01_ 'Treatment Period' (header row 1) and 'Days' (header row 2) are each distributed across cols 3-14 with is_merged_cell true and merged_cell_range "3:14" on every covered position.
  - check: schedule_grid rows 1 and 2 each have 12 cells at cols 3-14 with is_merged_cell true and merged_cell_range "3:14".
- **INV** _Table 01_ The Comments column becomes per-row annotations with synthesized markers n1-n8, each linked to its activity row - it is not a schedule column and not an activity.
  - check: Annotations with markers n1..n8 exist, each with an activity_name marker_location (n1 discharge, n2 medical assessment, n3 height/weight, n4 pregnancy test, n5 12-lead ECG, n6 vital signs, n7 clinical laboratory tests, n8 selpercatinib administration), and each cited activity row carries the marker in annotation_markers.
- **INV** _Table 01_ n7 (Clinical laboratory tests -> 'See Appendix 10.2, ...') is typed source_note, not footnote, because it is a pure cross-reference.
  - check: The annotation on the "Clinical laboratory tests" row has annotation_type == "source_note"; the other Comments-column annotations are "footnote".
- **INV** _Table 01_ Dosing falls on Day 1 (col 4) and Day 8 (col 11), with 24h reads on Day 2 (col 5) and Day 9 (col 12).
  - check: The "Selpercatinib administration" row has marks at column_position 4 and 11; schedule_grid row 3 has cell_value "1" at col 4 and "8" at col 11.
- **SRC** _Table 01_ A fully redacted (black block) activity row on page 12, between 'Genetic sample' and 'Selpercatinib administration'. The block is roughly three row-heights tall and may conceal more than one activity row - unknowable from the source.
  - expected handling: activities contains a row with activity_name "CCI" between Genetic sample and Selpercatinib administration, with zero activity_schedule cells, and the new report must again flag that the block may hide more than one row. Naming the concealed activity, adding marks to it, or dropping the flag would be fabrication.
- **SRC** _Table 01_ The abbreviations line is truncated by a CCI redaction immediately after 'h = hour;'.
  - expected handling: Only the visible abbreviations (CRU, ECG, ED, h) may be recorded, with an explicit remainder-redacted note per prompt s6. Any abbreviation beyond 'h = hour;' appearing in the new output is fabricated. Note that under v3.6.0 the abbreviation annotation itself may legitimately be dropped (see expected changes) - but the redaction must still be reported.
- **SRC** _Table 01_ Page 12's text layer is character-spaced/mangled, so it required a render to confirm.
  - expected handling: The new report must again state that page 12's text layer is degraded and how it was read (s1c glyph-spread reconstruction and/or s1a visual confirmation). Silently transcribing page-12 text with no method statement, or delivering letter-spaced text in any field, is a defect.
- **JDG** _Table 01_ Header row 2 ('Days') typed property_type "other" rather than study_day.
  - rationale: It is a label/unit band, not day values - the numeric days live in row 3; `other` avoids duplicating study_day semantics.
- **JDG** _Table 01_ Header row 3 typed study_day even though it mixes day numbers with date windows (screening window, ED, follow-up window).
  - rationale: Classified for the dominant numeric values.
- **JDG** _Table 01_ The tall redaction block was recorded as a SINGLE CCI activity row.
  - rationale: How many rows it hides is unknowable from the source; one row preserves the position without inventing rows.
- **JDG** _Table 01_ Continuous double-headed arrow represented by the token "←→".
  - rationale: Faithful to the merged-mark distribution rule; the report notes downstream may prefer a different canonical continuous token.
- **JDG** _Table 01_ In-grid P and hour timepoints transcribed literally as cell_value, and P was NOT made an annotation.
  - rationale: No explicit 'P = predose' legend appears in this excerpt, so there is no legend entry to anchor.
- **JDG** _Table 01_ The abbreviation annotation ab1 was kept as an intentional orphan, anchored to schedule_property row 1 rather than to any cell.
  - rationale: Abbreviation lists anchor to the header row per the then-current convention; they are not placed in a cell.
- **Δ** `ab1` is intentionally "unused" as a cell marker (orphan by design) - abbreviation annotation anchored to schedule_property row 1.
  - expect: v3.6.0 explicitly forbids a standalone abbreviation list with no in-grid marker, so ab1 is expected to disappear and the annotation count to drop from 9 to 8. Expected delta, not a regression - but the CCI truncation of the abbreviations line must still be flagged in the new report.
  - rule: s6: "Do NOT emit a standalone abbreviation/legend *list* whose terms carry no in-grid marker ... an unreferenced list entry is an orphan and is dropped downstream"
- **Δ** Comments-column notes n1-n8 were bound to rows by row alignment; no bounding method or marker_location method is recorded.
  - expect: v3.6.0 requires each note's TEXT to be bounded by the cell's rule-line geometry (raster-recovered if the vector layer is empty) and each synthesised marker's location to carry method "synthesized". Expect method fields on the n1-n8 marker_locations and a report line on how the note cells were bounded; note boundaries themselves may shift if the old binding was proximity-based.
  - rule: s6 "Notes / Instructions / Comments column ... **Bound each note's TEXT by the cell's rule-line geometry, not by proximity**"; s1e marker_locations[].method "synthesized"
- **Δ** The tall CCI redaction block was left as 'unknowable from the source'.
  - expect: v3.6.0 s1d prescribes taking row boundaries from a text-bearing column (never a redacted one) when recovering rules from the raster, which is exactly this situation. The new run may therefore report a rule-line-derived band count for the block. If it still cannot determine the count, it must remain flagged as possibly >1 row - a confident single-row claim with no stated method, or invented extra rows, is a regression.
  - rule: s1d: "**Take the row boundaries from a column that holds text, never from a redacted one.** A black redaction bar fills its cell edge to edge, reads as a horizontal rule, and makes that row vanish from the band list"
- **Δ** Page 12 read with a character-spaced/mangled text layer; no provenance recorded in the JSON (the string "method" does not occur in NCT05324124_Table_01_extraction.json).
  - expect: Expect s1c/s1e outputs: activity_name_source.method (glyph_reconstruction / visual_transcription) on page-12 rows, annotation_text_source.method where note text was not read from a rule-line-bounded cell, and an explicit report statement that the source was glyph-spread and which fields were reconstructed - including annotation_text.
  - rule: s1c "apply the reconstruction to **every** text field - activity labels, header labels, **and `annotation_text`**"; s1e method provenance
- **Δ** Activities carry no source_page; the report gives no per-page activity-row counts across pages 9-12.
  - expect: Expect source_page on every activity plus a per-page count in the new report, with any zero-contribution page called out explicitly.
  - rule: s4: "**Then check coverage before delivering: every page in the declared range must contribute rows.**"; s7
- **Δ** Arrow token "←→" chosen; report notes downstream may prefer a different canonical token.
  - expect: v3.6.0 does not canonicalise the arrow glyph, so the token may change (and may differ from NCT05259917's "↔"). Only a change to the span 4:14, or a collapse of the arrow onto a single column, is a regression.
  - rule: s5 "**Arrows spanning columns.** ... `cell_value` the arrow glyph, `source_range` the span"

_Notes:_ Verified against NCT05324124_Table_01_extraction.json: 20 activities (row_positions 4-23, CCI at 20 with no activity_schedule entries), 41 schedule_grid cells, 77 activity_schedule cells of which 22 carry source_range "4:14" (rows 22 and 23), 9 annotations (n1-n8 plus ab1; n7 = source_note anchored to row 18), Genetic sample (row 19) has a single cell at column 4, no method fields present. No activity label in any of the three studies contains an inline section/appendix reference, so the v3.6.0 s6 inline-reference-to-source_note rule (pr1, pr2, ...) is not expected to change these three extractions - except for the already-source_note n7.

## 8. Per-table promotion gate

A re-extracted table is promoted into the corpus only when all of these pass. Run in order —
later checks assume earlier ones held.

1. **Schema valid** against `soa-table-extraction.schema.json`, `schema_version` 1.0,
   `extraction_status` `ready_for_resolution`.
2. **No orphan annotations** — every annotation has ≥1 `marker_locations` entry.
3. **Markers agree both ways** — every marker in an annotation's `marker_locations` also appears in
   that row's `annotation_markers` (§5.4; run the `resolve.py` detector, do not eyeball).
4. **No containment pairs** — no annotation's text is contained in another's (means one note cell
   was split across rows).
5. **Typing not degenerate** — `by_type` across >20 annotations is not all `source_note`.
6. **Page coverage** — every page in `page_start..page_end` contributed activity rows, or the
   report says why not.
7. **Counts vs §2** — `marks` and `acts` compared to baseline; every delta bucketed
   (expected / regression / new finding).
8. **Row audit** — re-run; 33 on-page-not-extracted must not rise (§3).
9. **Study criteria** — §7 invariants reproduced, §7 source defects still flagged, §5
   adjudicated findings not re-litigated.
10. **Corrections** — sidecar retired, re-authored, or confirmed contingent (§4); the `add`
    duplication trap checked (§4.4).
11. **Deterministic layers** — ApplyCorrections → Resolve → Consolidate runs with 0 errors.

## 9. Rules for the extraction agents

Binding constraints for the Phase 2 fan-out, over and above the extraction prompt:

- **Write only into the staging area.** Never into `collections/*/protocols/*/SoA2USDM/`, and
  never anywhere under `tests/`. Promotion is a separate gated step.
- **`tests/fixtures/negative/` is untouchable.** Those five files are deliberately defective
  historical snapshots — the negative controls each detector must fire on. Regenerating them from
  clean output silently deletes the entire negative-control set while the suite still passes green.
- **An honest `unresolved` beats a guess.** Where a marker's target cannot be determined, keep the
  location with the `row_position` where the marker is printed and set
  `location_type: "unresolved"`. A guessed target is a defect that surfaces weeks later.
- **Never repair the source.** Undefined footnotes, redactions and contradictions are data. §5.3
  lists the known ones; a fresh "resolution" of any of them is fabrication.
- **Quote fidelity is mechanical.** Any quotation offered as evidence in the uncertainty report
  must be a verbatim substring of the source. This checklist's own mining pass produced 2
  composed quotes out of 422 — plausible, well-formatted, and not in the document. Verify, do not
  trust.
- **Record method, not confidence** (§1e). A method names a re-derivable procedure that can be
  checked against the PDF; a confidence number cannot.

## 10. What this checklist cannot tell you

Stated so the gate is not mistaken for a proof:

- It cannot detect a row that is missing from **both** the baseline and the new extraction. The
  row audit covers this for text-layer pages, but 3 protocols have no text layer at all
  (NCT02291289, NCT03693430, NCT04557384) and 2 are rotated (NCT03548935, NCT03548987).
- It cannot validate a mark that is wrong in the same way in both versions.
- Baseline counts are not correctness. They are the previous best effort, produced by prompt
  v3.0.2–v3.1.0. Where v3.6.0 legitimately disagrees, the baseline is what changes.
- The 110 judgement calls in §7 are recorded so a different decision gets **reviewed**, not so it
  gets rejected. Several may well be improved by v3.6.0's explicit rules.
