# USDM Instantiation

The architecture in `README.md` has three layers: Extraction, Resolution, Consolidation.
It stops at *USDM-ready data*. This document describes USDM Instantiation — turning the
consolidated table into an actual USDM v4 document — and the study shell that has to exist
around it. It is the USDM side the repo is named after, not a fourth SoA layer.

Everything here was measured against DDF-RA `v4.0.0`, the 24 protocols in
`soa2usdm-collections`, and three protocol PDFs. Claims are stated with the check that
produced them, so they can be re-run rather than trusted.

Written 2026-09-03 as "Layer 4 — USDM generation". Renamed 2026-09-29: Layer 4 → USDM
Instantiation, Level 1 → minimal build, Level 2 → enriched build, floor/placeholder → not
stated. Measurements and file names from 2026-09-03 are left as they were.

---

## Running it

USDM Instantiation is a documented manual step, not a pipeline step (decided 2026-09-29).
A USDM document exists only for a protocol someone chose to build, and every build is
reviewed by the person who wrote its manifest.

1. **Pick a protocol** whose consolidated SoA carries an epoch property (§4).
2. **Write the manifest**, `<ID>_usdm_manifest.yaml`, against
   `schemas/usdm-manifest.schema.json`: study identity, organizations (each with a `ref`
   if stated in the protocol, a `flag` if not), identifiers, titles, epochs, terms and
   `epochAxis`; `timingAxis` and `encounterAxis` only where the SoA supports them. Every
   judgement goes in a comment next to the value. Terminology codes are checked against the
   CT package named in `study.ctVersion`.
3. **Generate**:
   `python -m soa2usdm.usdmgen <manifest> <consolidated.json> <outdir>` writes
   `<ID>_usdm.json` and `<ID>_usdm_decisions.json`.
4. **Gate**: `python3 tools/usdm_gate.py <manifest> <outdir>/<ID>_usdm.json`. Needs the
   `usdm-gate` extra and the usdm-rdf checkout at the pinned release (§7).
5. **Read what the gate cannot judge**: the decisions log (`epoch-unbound` and
   `timing-skipped` entries above all), terminology warnings, and any code the gate reports
   as a non-member of an extensible codelist (§11).
6. **Commit** manifest, document and decisions log together, in the collection under
   `<ID>/SoA2USDM/usdm/`.

---

## 1. What USDM Instantiation has to produce

A USDM v4 `Study` document that carries the Schedule of Activities and conforms to the
published model.

The obstacle is that USDM has no standalone SoA serialization. A `ScheduleTimeline` hangs
under a `StudyDesign`, which hangs under a `StudyVersion`, which hangs under a `Study` —
and `StudyDesign` mandates arms, cells, elements, population, eligibility criteria and a
model, none of which a Schedule of Activities contains.

So USDM Instantiation is two pieces:

- **the shell** — the study structure the SoA hangs inside, generated from a manifest
  of facts read off the protocol;
- **the SoA lifting** — the consolidated table rendered as timelines, instances,
  timings, activities and encounters.

They meet at exactly one attribute (§3).

---

## 2. Four levels of output

Not a single target. The levels differ in how much protocol reading they require.

| Level | Output | Protocol reading |
|---|---|---|
| 0 | SoA core alone | none — but not a standalone USDM document |
| **minimal build** | not-stated objects + real epochs + SoA | ~6 facts: identifier, title, sponsor, epoch list |
| **enriched build** | full shell + SoA | ~20–30 facts: real arms, cohorts, elements, interventions, population |
| 3 | + objectives, endpoints, estimands, narrative content, amendments, BC bindings | the whole document |

**The minimal build** is a valid, conformant USDM document carrying a complete SoA, with nine
not-stated objects clearly flagged. 37 shell objects plus the schedule.

**The enriched build** is what the three worked examples produce. Better output, but enrichment
rather than a prerequisite — nothing in the SoA breaks without it.

**Level 3 is out of scope.** Worth stating explicitly, because it is where comparable
efforts have gone and not returned.

The working goal: *a valid USDM document whose SoA is complete and whose study context is
as real as the protocol cheaply allows.* The minimal build as the guaranteed baseline, the
enriched build as the default when someone does the reading.

---

## 3. The seam is nine edges

Exhaustive search of every attribute in `dataStructure.yml` v4.0.0 for edges crossing
between the schedule classes, the shell classes, and the rest.

**SoA → shell:** one attribute.

- `ScheduledInstance.epochId → StudyEpoch` `[0..1]`

**SoA → the rest of the protocol:** four attributes.

- `Activity.biomedicalConceptIds`, `bcSurrogateIds`, `bcCategoryIds` `[0..*]`
- `Procedure.studyInterventionId → StudyIntervention` `[0..1]`

**The rest → SoA:** one class, four target pairs.

- `Condition.contextIds → Activity | ScheduledActivityInstance`
- `Condition.appliesToIds → Activity | Procedure`

Every crossing edge is a `Ref`, never a `Value`; all containment runs through
`StudyDesign` and `StudyVersion`. Merging is therefore mechanical: put arrays in the right
place and make ids resolve.

Two consequences:

- **Build order is shell → SoA → annotation.** `Condition` can only be written once
  activities and instances exist, and it is the class that carries cell-scoped footnotes.
- **Only the merged document is checkable.** Every crossing edge is optional, so a
  half-assembled document passes structural SHACL because the reference simply is not
  there. The merge should be a pipeline step with the RDF lifting as its gate.

### Nothing else in the schedule reaches the design

Exhaustive BFS from every schedule class, following outgoing attributes to depth 4:
**zero paths** to `StudyArm`, `StudyCohort`, `StudyDesignPopulation`, `StudyCell` or
`StudyElement`.

`StudyArm.populationIds [0..*] → PopulationDefinition` does accept a `StudyCohort`, so
arm-to-cohort is expressible — verified by SPARQL on the MO29112 shell, 4 of 4 reachable.
But that edge runs arm → cohort. Nothing runs schedule → either.

Tested against a track-structured SoA (NCT02291289: main schedule plus four
cohort-specific maintenance appendices, built as 5 timelines / 6 epochs / 22 instances /
35 activities / 4 cohorts, 137 objects, both SHACL layers conforming). Decisive query —
`StudyCohort` objects referenced by any schedule object: **0 of 4**. Cohort identity
survives only in `ScheduleTimeline.name`/`label`, in the free-text
`ConditionAssignment.condition`, and in an `ExtensionAttribute`.

---

## 4. The epoch list is the load-bearing fact

Since `epochId` is the only edge, the epoch list is the only part of the shell the SoA
genuinely needs. Everything else exists to satisfy containment.

### How often the SoA supplies it

Across all 24 protocols in `soa2usdm-collections`:

| | count |
|---|---|
| `epoch` property in the SoA header | 15 / 24 |
| of those, every column bound | 12 / 15 |
| epoch axis present but typed as something else | 4 |
| nothing usable — needs the protocol | 5 |

The four recoverable ones carry an epoch-shaped value under a different `property_type`:

| Protocol | typed as | values |
|---|---|---|
| NCT04573309 | `period` | Screening, C-I, Inpatient Period 1, OP, Inpatient Period 2 |
| NCT01847274 | `cycle` | Screening, 1, 2, Subsequent Cycles, Study Treatment Discontinuation, Post Treatment Assessments |
| NCT05259917 | `visit` | Screening, Randomization, Treatment Period, 1st/2nd/3rd eligible HAE attack, Final Visit/ET |
| NCT04730349 | `visit` | Screening Visit, Safety Follow-up Visit 1–3, Survival Follow-up Every 3 Months |

These need one manifest line naming which column property carries the epoch axis, plus a
value-to-epoch mapping over a handful of distinct values. **This field does not exist
yet** — see §8.

### When the protocol has to supply it

Scanning protocol text for period declarations with a visit/week/day anchor within ~300
characters:

| Protocol | hits | verdict |
|---|---|---|
| NCT04677179 | 12 over 5 phrases | real boundaries ("responders at Week 12") |
| NCT04573309 | 12 over 2 phrases | real (Run-in Day −7 to −5, titration Day 29) |
| NCT04730349 | 2 | weak; one is an exclusion-criteria false positive |
| NCT05259917 | 0 | nothing |
| CDISC_Pilot | 1 | **false positive** — the SoA table bleeding into the text layer |

CDISC_Pilot is the control and it fails cleanly: the protocol never states the
treatment/follow-up boundary. It was derived from where medication dispensing stops
(Section 3.1 lists dispensing at Visits 3–12 only), and flagged as a judgement.

**Conclusion: a column-to-epoch map cannot be generated from the protocol in general.**
The correlation runs the wrong way — protocols that are hard to derive are hard for the
same reason they never printed the epoch row.

---

## 5. The shell generator

`shellgen.py`, 264 lines, one class, no protocol-specific branches. Input is a hand-written
YAML manifest (`schemas/usdm-manifest.schema.json`); output is a USDM v4 document with
`activities`, `encounters` and `scheduleTimelines` empty.

### Evidence it is mechanical

**Test 1 — regenerate two hand-built shells from lifted manifests.** Identical object
counts (198 and 687) and identical class counts. Remaining diffs: provenance phrasing, a
deliberate criterion id-scheme change, and 54/190 places where the generator is *more*
correct than the hand build.

**Test 2 — a third protocol, manifest-first, generator untouched** (`md5sum` verified).
J1P-MC-KFAH(b), adaptive two-stage design with outcome-driven paths. Passed first time:
335 objects, 0 duplicate ids, **0 unmapped keys**, 0 off-base subjects, both SHACL layers
conforming.

**Scaffolding ratio, stable across two very different protocols:**

| | LZZT | MODUL |
|---|---|---|
| Objects | 198 | 687 |
| Scaffolding (cells, codes, chains, provenance, containment) | 129 (65%) | 444 (65%) |
| Protocol reads | 43 | 132 |
| — of which criteria | 26 | 101 |
| — **everything else** | **17** | **31** |

Criteria are 60–77% of all the reading and contribute nothing to SoA interpretation.
Strip them to the floor and the manifests are roughly 90 and 130 lines.

**Three numbering conventions absorbed without schema change:** `[n]` flat (LZZT), `n.`
restarting per cohort group (MODUL), `n.` continuous across inclusion and exclusion
(KFAH).

### The three rules that are judgements, not mechanics

These are currently implicit in the code and should be documented as decisions:

1. **Which classes chain.** `previousId`/`nextId` exist on six classes in v4.0.0:
   `Activity`, `EligibilityCriterion`, `Encounter`, `NarrativeContent`, `StudyAmendment`,
   `StudyEpoch`. The `CHAINED` set is a rule.
2. **Criterion chaining scope.** Within a group, never across group boundaries. The only
   defensible reading when numbering restarts.
3. **Population vs cohort criteria.** Shared criteria on
   `StudyDesignPopulation.criterionIds`, cohort-specific on `StudyCohort.criterionIds`.

### Known defect

**Rule 3 is not implemented.** The generator puts *all* criteria on the population
(MO29112: 101 instead of 40). The hand build was correct. Found by test 1; fix before
relying on the population's criterion list.

---

## 6. What USDM cannot hold

Recorded here because it bounds what USDM Instantiation can promise. These are findings about USDM
v4.0.0, not about this pipeline.

Each was re-verified against `dataStructure.yml` and the bound codelists after first being
written down. One was withdrawn and four were downgraded, so read the severity, not just
the heading.

### Verified, no mechanism at any depth

- **Arm, cohort and population are unreachable from the schedule.** BFS from every
  schedule class across all 86 classes at depth 6: zero paths to `StudyArm`,
  `StudyCohort`, `StudyDesignPopulation`, `StudyCell` or `StudyElement` (§3). Corroborated
  by the NCT02291289 build: 5 timelines, 4 `StudyCohort` objects, 0 references from any
  schedule object, SPARQL-verified. This is the one with weight.
- **Two-anchor timings.** `Timing.relativeFromScheduledInstanceId` is `1`. An *alternative*
  anchor — NCT04677179 V801/V802, "Week 58 or ETV + 8 weeks after last dose" — has no
  representation. Narrow; one protocol.

### Expressible, but not with the right semantics

- **Mark value and non-conditional cell footnotes.** `Condition.contextIds` ×
  `appliesToIds` addresses a single cell and `Condition.text` is free text, so "P =
  practice only" and "and via telephone interview 2 weeks following this visit" *can* be
  carried — as Conditions, which they are not. The accurate claim is narrower: USDM has no
  cell-scoped annotation that is not a `Condition`. A feature request, not a gap.
  This package carries the 4 affected CDISC Pilot cells in an `ExtensionAttribute` instead.
- **`period` and `cycle`.** A repeating cycle is representable as a nested
  `ScheduleTimeline` via `Activity.timelineId` / `ScheduledActivityInstance.timelineId`.
  What is missing is the header-axis semantics, not the capability. They appear in 5 and 4
  protocols, usually *alongside* `epoch`.
- **Cohort status.** MO29112 §3.1.2.4 records Cohort 4 accrual closed in July 2018.
  `StudyAmendment` has `changes`, `impacts` and `enrollments`, so this is representable
  indirectly. What is absent is any attribute on `StudyCohort` itself. Weak.
- **Open-ended ranges.** `Range` requires both `minValue` and `maxValue` at cardinality 1,
  so "at least 50 years of age" cannot be expressed as `plannedAge`. Low severity: the
  constraint itself lives in the eligibility criterion, and `plannedAge` is a summary
  attribute. Nothing is lost.

### Withdrawn

- **Adaptive design.** *This was wrong.* `StudyDesign.characteristics [0..*] → Code` binds
  to codelist `C207416`, which contains **C98704 "Adaptive Design"** (and `C207613`
  "Extension Study Design", relevant to extension-period tracks). It is fully expressible.
  The gap was reported because `characteristics` was omitted as optional and the absence
  mistaken for a limitation — a defect in this package, not in USDM. See §8 item 9.
- **`Encounter` name collisions.** In NCT04677179, V10–V29 appear in both the Responder
  and Nonresponder tracks at identical weeks and study days. Not a gap: two `Encounter`
  objects may share a `name`, ids are distinct, and nothing requires uniqueness. A
  readability and round-trip nuisance in this pipeline only.
- **Segment type `domain`.** NCT03283098 has 40 `domain` columns — same timeline, different
  activity class. Arguably a presentation dimension outside USDM's scope; not verified
  hard enough to claim as a gap.

### If any of this is ever raised with CDISC

Check the DDF-RA issue tracker first. As of 2026-09-03:

- The `C207646` / `C94108` conflict is **already reported** — issue #700, opened
  2025-10-28, labelled `MOVED TO UGG JIRA`, with the same two codes named. The only thing
  not in it is that the divergence makes the published CDISC Pilot USDM example
  non-conformant against its own terminology.
- Issue #592 "Handling of multiple co-existing timelines" (open, 0 comments,
  `Nice to Have`) is the closest home for the schedule-to-cohort finding. It asks whether
  sub-timelines may reference encounters and epochs — both of which *are* referenceable.
  The unreachability of arm, cohort and population is the missing half of that question.
- Issue #691 asks how to populate `value` / `valueLabel` for fixed-reference timings, and
  notes the example files diverge (`P1D` / `PT0M`). This package emits a third variant.
- Read before proposing anything: issue #609 (closed) points at the IG page
  *Schedule of Activity Views*; and the DDF-RA discussion "1 to many relationship between
  Condition and Activity?" bears on the cell-scoped annotation point.

---

## 7. Dependencies and conventions

### usdm-rdf is a pinned dependency, never a write target

Pinned at release `v0.7.1` — the checker notebook and the four deliverables, by content
hash, in `tools/usdm_gate.py`. (Until 2026-09-29: deliverables `v0.7.0`, checker `d7bb3e3`;
v0.7.1 has the same shapes and context.) It changes only when this
work finds a defect in what it publishes. That direction of traffic is what makes this an
independent consumer — which is what the "no false positives across 6,620 triples from an
independent generator" line in the usdm-rdf dossier rests on.

Four findings from this work already landed there: decision D7 (instance IRIs), the
pre-lift duplicate-id scan, the context-check limitation note, and the terminology-coverage
statement (the 20 borrowed codelist bindings, published as deactivated shapes in v0.7.0).

### Instance IRIs (usdm-rdf decision D7)

The caller mints the instance namespace. `@base` in a *remote* JSON-LD context is ignored
by JSON-LD 1.1, so the published context cannot fix this. Supply a `BASE_IRI` ending in
`/`; convention `<sponsor namespace>/<study identifier>/`.

Measured: the same 3,553-triple study lifted from two locations produces 7,106 triples
when merged — nothing merges, every node duplicates.

Note the testing trap: merging the context *into* the document makes it a local context,
where `@base` **is** honoured. Anyone testing that way gets a false pass.

### Object ids must be unique before lifting

JSON tolerates two objects with the same `id` in different arrays; RDF merges them into
one node and the structural layer then reports a `maxCount` violation that reads nothing
like "duplicate id". Hit for real: the shell builder and the SoA builder both emitted
`Code_1..n`.

**Convention: prefix ids by producing stage** (`SHELL_`, `SOA_`). Traceable ids also help
— `Activity_xact-001`, `SAI_xcol-003`, `EligibilityCriterion_EX_Cohort2_07` make the
decisions log checkable against the source.

### Business identifiers are not unique, and cannot be made so

`EligibilityCriterion.identifier` is the printed number, and the printed number is scoped
by a heading USDM does not carry. In MO29112 the same value appears on up to five
criteria. `StudyCohort.criterionIds` recovers the grouping from the other direction.
Document it; do not paper over it.

### Structural conformance does not cover dropped keys

Unmapped or misplaced JSON keys yield no triple (JSON-LD 1.1, no `@vocab`), so closed
shapes never see them and `conforms=True` is truthful about the graph while the JSON
carries invented attributes. The context check is the only detector.

Specimen: `StudyArm` has no `previousId`/`nextId` in v4.0.0. Both hand-built shells assert
them; the generator does not.

### Terminology

`USDM_CT.xlsx` sheet 2 binds each coded attribute to a codelist; the permitted terms live
in NCI EVS. Where the two disagree, `USDM_CT.xlsx` is the source of truth
(usdm-rdf `docs/shacl-design.md`). Known divergence: `StudyTitle.type` — EVS lists
`C207646` (Study Acronym), `USDM_CT.xlsx` lists `C94108` (Study Protocol Version Acronym).
Non-extensible, so either choice is a hard Violation against one source. This is the
CDISC Pilot's one CT Violation in the corpus audit, and it is already reported upstream as
DDF-RA issue #700.

### PDF extraction is not on the critical path

KFAH renders 56 of 161 pages with a space between every glyph; `pypdf` and `pdfplumber`
both produce it. It cost nothing, because the manifest is hand-authored and nothing
downstream parses the PDF. Bad extraction costs human reading time only.

This changes if manifest authoring is ever automated — at which point extraction quality
becomes load-bearing and this decision has to be revisited.

---

## 8. What to do next

Rough order. The first three are small and unblock the fourth.

1. **Fix the population-vs-cohort criteria defect** (§5) and document the three judgement
   rules as decisions.
2. **Add `epochAxis` to the manifest schema** — names which consolidated column property
   carries the epoch axis, plus a value-to-epoch map. Covers 19 of 24 protocols. The
   remaining 5 need explicit per-column assignment with a flagged judgement.
   ```yaml
   epochAxis:
     property: prop-002          # typed 'period' in the extraction
     map:
       Screening: SCREENING
       "Inpatient Period 1": TREATMENT_1
   ```
   Open question worth deciding deliberately: should Layer 1–3 mark the epoch axis in
   `soa-tables-consolidated.schema.json` instead? Marking it at extraction is more correct
   and benefits anything reading the consolidated table; resolving it in USDM Instantiation is
   cheaper and does not disturb a working pipeline.
3. **id-allocation convention** (§7) plus a pre-lift uniqueness check.
4. **The SoA profile.** Strictened `minCount` on the attributes that carry SoA meaning but
   are optional in the base shapes — `activityIds`, `encounterId`, `epochId`, `childIds`,
   `previousId`/`nextId` on `Activity` and `Encounter`, `windowLower`/`windowUpper` —
   plus a closure check that every `ScheduledInstance.epochId` resolves to a declared
   epoch. That closure check is what makes shell and SoA one document rather than two that
   happen to validate.

   A shell profile is worth considering alongside it: nothing currently checks that a
   generated shell contains what its manifest declared, or that every not-stated object
   carries its `not-stated-in-protocol` extension.
5. **The merge step** — shell + SoA into one document, with the usdm-rdf lifting as gate.
6. **Cohort-to-schedule extension namespace** — needs a URL and a resolution convention,
   since USDM has no edge (§3).
7. **Round-trip** (`usdm2soa` and a diff back to the consolidated table). The gaps are
   known in advance (§6), which arguably makes the diff less interesting than it looks:
   it will consist of exactly those and nothing else. Worth doing only if the output is
   meant to be a report on the gaps.

8. **Populate `StudyDesign.characteristics`.** Both MO29112 and J1P-MC-KFAH state adaptive
   designs, and `C207416` carries C98704 "Adaptive Design" and C207613 "Extension Study
   Design". Neither the generator nor the manifest schema has a slot for it. Add
   `design.characteristicsCt: [<keys>]` to the manifest and emit it; then correct the two
   affected manifests.
9. **A synthetic protocol.** An invented study, a manifest written for it, a shell
   generated from it. Would demonstrate the generator end to end with no confidential
   content, make §5's evidence checkable by someone outside this work, and supply the
   committable test input the usdm-rdf checker is missing. Only worth doing if any of
   this is ever meant to be public.

`cosmos-rdf` becomes the supplier for three of the nine seam edges
(`Activity.biomedicalConceptIds` and siblings) whenever BC binding happens. That dates
after the `w3id.org/cdisc/cosmos/` registration, since until then those IRIs do not
dereference.

---

## 9. Files

### In this repo

| Path | What |
|---|---|
| `shellgen.py` | The generator. 264 lines, no protocol-specific branches. |
| `schemas/usdm-manifest.schema.json` | Manifest schema. All three worked manifests validate. |
| `notebooks/70_soa_to_usdm.ipynb` | Consolidated table → USDM (CDISC Pilot). |
| `notebooks/80_shell_from_protocol.ipynb` | Shell for H2Q-MC-LZZT(c) from the protocol PDF. |
| `notebooks/85_shell_repeatability_test.ipynb` | Shell for MO29112 — the second-protocol test. |
| `notebooks/90_shell_floor.ipynb` | Floor variants and the ablation. |
| `notebooks/95_track_soa_test.ipynb` | Track-structured SoA test on NCT02291289. |

Notebooks 80 and 85 predate `shellgen.py` — they contain the hand-written builders those
shells were first produced with, and are kept as the evidence behind tests 1 and 2. New
shells should use `shellgen.py` and a manifest.

### Protocol-derived data

Manifests, generated shells and decisions logs are protocol-derived. **None of it is
published.** All three worked protocols draw on documents that are confidential (Roche
MO29112), CCI-redacted (Lilly J1P-MC-KFAH) or still under copyright (Lilly H2Q-MC-LZZT,
2006), and the criterion labels in the manifests are lifted text even though
`EligibilityCriterionItem.text` carries only a source pointer.

Layout used in this package, and the layout to use if any of it ever becomes publishable:

```
<PROTOCOL>/Shell/
├── <PROTOCOL>_manifest.yaml            # hand-authored
├── <PROTOCOL>_shell.json               # generated
├── <PROTOCOL>_shell_decisions.json     # generated
├── <PROTOCOL>_floor.json               # optional, Level 1
├── <PROTOCOL>_soa_usdm.json            # SoA lifted to USDM
└── <PROTOCOL>_soa_usdm_decisions.json
```

### What could be published, if that is ever wanted

Free of protocol content, verified by scan:

| File | |
|---|---|
| `shellgen.py` | no product, indication or criterion text |
| `schemas/usdm-manifest.schema.json` | " |
| `documents/usdm-instantiation.md` | " |
| `notebooks/70_soa_to_usdm.ipynb` | reads the consolidated JSON only |
| `notebooks/95_track_soa_test.ipynb` | " |

Not publishable as they stand — the hand-written builders are inline and carry protocol
facts as literals:

| File | content |
|---|---|
| `notebooks/80_shell_from_protocol.ipynb` | 26 criterion descriptors, 19 regimen mentions, 12 section references |
| `notebooks/85_shell_repeatability_test.ipynb` | 15 regimen mentions, 21 section references, cohort regimen text |
| `notebooks/90_shell_floor.ipynb` | study title and regimen |

Note the cost: 80 and 85 are the evidence behind tests 1 and 2, so without them the
scaffolding ratio, the regeneration result and the third-protocol result in §5 are claims
a reader cannot check. See §8 item 8 for the way out.

---

## 10. Corrections carried forward

Four things were wrong earlier in this work and are corrected above. Recorded so they are
not rediscovered:

- **`StudyArm` has no `previousId`/`nextId`** in USDM v4.0.0. Both hand-built shells
  assert them. Structural SHACL cannot catch this; only the context check sees it.
- **Adding `@base` to the published context would not work** — JSON-LD 1.1 ignores it in a
  remote context. Superseded by usdm-rdf decision D7.
- **The generator's criteria all land on the population** instead of splitting to cohorts
  (§5, known defect).
- **"Adaptive design is not expressible" was wrong.** `StudyDesign.characteristics` binds
  to `C207416`, which contains C98704 "Adaptive Design". Withdrawn in §6; the real defect
  is that this package never populates `characteristics` (§8 item 8).

All four are the same failure mode: assuming that an absence in the place you looked means
an absence in the model. It is the reason the manifest schema was tested against a third
protocol rather than two, and the reason §6 was re-verified before anything was written up
for CDISC.

---

## 11. Decisions recorded

Three open points from the first minimal build (NCT03637764, 2026-09-05), recorded as
decisions rather than fixed. Codes verified against SDTM CT 2026-03-27.

- **`InterventionalStudyDesign.model` is written as C82639 (Parallel Study), flagged not
  stated.** The attribute is mandatory (1) and the SoA does not state the design model, so
  some code must be written. C82639 is a member of C99076, so the document conforms — but
  it is not a reading of the protocol, and the not-stated flag on the design object is what
  says so. A reader must not take it as the study's model. An enriched build would take the
  model from the protocol; `usdm_manifest.py` reserves the `notstated_model` term today, so
  that needs a code change when it is wanted.
- **`StudyArm.type` C174266 (Investigational Arm) is checked against Protocol
  Terminology.** Its codelist, C174222, is not in SDTM CT; it is published in the NCI EVS
  CDISC Protocol Terminology package, where C174266 is a member (submission value
  "Experimental Arm", NCI preferred term "Investigational Arm"). The arm itself is flagged
  not stated.
- **Codes on the 20 codelists USDM borrows are checked by the gate (step B), not by hand.**
  usdm-rdf leaves these bindings `sh:deactivated` because their members are published in
  NCI EVS packages, not in the DDF deliverables. soa2usdm keeps its own extract of exactly
  those codelists, `ct/usdm-borrowed-codelists.tsv` (1,542 members), built by
  `tools/build_ct_extract.py` from SDTM CT 2026-03-27 and Protocol Terminology 2025-09-26;
  the extract's header names both files with their SHA-256. A non-member fails the gate on a
  non-extensible codelist and is reported on an extensible one. Eight of the 20 codelists
  are published in both packages; they are identical in these releases, and the build stops
  if they ever differ. `study.ctVersion` remains a single date per document and is written
  to every `Code.codeSystemVersion`, so C174266 carries the SDTM date although it comes from
  Protocol Terminology — known, left as is.
