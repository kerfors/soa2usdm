# The Annotation Model — a foundational problem

> Status: **for discussion, nothing decided.** Written 2026-07-30 after a run of annotation defects
> that turned out to share one root cause. Companion to `soa2usdm-schema-architecture.md`, which
> describes the three layers as designed; this note describes where the annotation entity does not
> hold up in practice.

## The problem in one sentence

**The model records where a footnote marker was printed, and then uses that as what the note
governs.** Position is *evidence* of scope. It is not scope. Almost every annotation defect found so
far is a consequence of treating the two as the same fact.

## Why this surfaced now

Six defects in three weeks, each fixed as if it were its own bug:

| # | Symptom | What it actually was |
|---|---|---|
| 1 | One note cell split into fragments duplicated across rows (NCT04677179: 111 raw → 77 fragmented) | Note text bounded by row proximity instead of by its cell |
| 2 | Two adjacent notes concatenated into one, bound to the first row (12 cases) | The same bounding problem, opposite direction |
| 3 | Corrected bindings never reached the consolidated output | Two representations of the binding; `resolve` believes `annotation_markers`, not `marker_locations` |
| 4 | A vital-signs note bound to *Endoscopy* | The row it belonged to was missing from that table — the note landed on whatever remained |
| 5 | A pharmacogenetics note bound to *Flow cytometry panel* in three tables | Same: the *Genetics sample* row was absent |
| 6 | 52 annotations across 10 protocols bound to unrelated activities | A `schedule_property` location resolved through a row-number lookup into the activity sharing that row |

Numbers 1 and 2 are geometry. Numbers 3 through 6 are the model. They kept arriving separately
because each had a plausible local fix, and each local fix left the root cause in place.

## What the corpus actually contains

Measured across 22 protocols, 731 raw annotations, 638 unified:

| | count |
|---|---|
| `annotation_type` = footnote / source_note / abbreviation / legend | 590 / 128 / 10 / 3 |
| `marker_locations` by type: activity_name / schedule_cell / schedule_property | 718 / 293 / 82 |
| Annotations spanning more than one location type | 9 |
| Unified annotations referencing activities only | 519 of 638 |
| Unified annotations with any column reference | 60 |
| Unified annotations with no reference at all (orphans) | 12 |
| Annotations bound to an activity purely by the row-number collision (defect 6) | **52** |

Two things stand out. Activity binding dominates — 519 of 638 unified annotations reference activities
and nothing else — which is *suspicious* rather than reassuring, because 82 source locations are
property-scoped and the consolidated model has no property reference at all. And 52 of the activity
bindings, one in ten, are known to be false.

## Three structural faults

### 1. The downstream vocabulary is narrower than the upstream one

Extraction can say a marker appears on a `schedule_property`, an `activity_name`, or a
`schedule_cell`. The consolidated `unified_annotation` can reference `referenced_xacts`,
`referenced_xcols`, `cell_references`. **Property has no target.** One third of the source vocabulary
has nowhere to land.

It did not fail loudly. A fallback in `consolidate._process_annotation` maps a location's
`row_position` to whatever activity holds that row, without checking `location_type` — so a property
note at row 1 attaches to the activity at row 1, a different one in every table. That is defect 6.

The general lesson is worth keeping: wherever a downstream layer's target vocabulary is narrower than
the upstream layer's, a bridge gets built, and the bridge is always a guess.

### 2. The same fact is stored twice, in two shapes

A binding lives both as `annotation_markers` (a comma-separated string on the row) and as
`marker_locations` (a list on the annotation). `resolve` derives `referenced_elements` from the first
and only consults the second when the first yields nothing.

Redundant state that can disagree eventually will. It cost an entire revision in which every raw file
read correctly and the consolidated output still pointed at the old activities, with no error
anywhere. One of these is derivable from the other; both being writable is the fault.

### 3. There is no way to say "no single target", or "I inferred this"

A legend, an abbreviation key, a footnote marker printed on the *Comment column header* — these govern
the table, not a row. The model has no table scope, so the extraction prompt instructs that such notes
be given a `schedule_property` location "for traceability". That invented location is then consumed by
the fallback as real scope. **The workaround manufactures the defect.**

Equally, a binding read confidently off a printed marker and one guessed from which row a note happened
to sit beside are stored identically. The distinction survives only as prose in the uncertainty report,
where no code can act on it.

## Underneath: annotations are not one kind of thing

`soa-table-extraction.schema.json` describes annotations as "the table's overflow mechanism — they
encode study logic that doesn't fit the 2D grid presentation." That is an accurate description of the
*source* and a poor foundation for a *model*, because what overflows is at least three unrelated kinds
of content:

- **Definitional** — "X = performed at this visit", "ETV = early termination visit". Has no target and
  never will. Currently forced to invent one.
- **Qualifying** — "Only for participants positive for anti-HBc at screening". Modifies exactly one
  grid element. The model serves this case well.
- **Study logic** — "Visits continue every 4 weeks until study treatment discontinuation", "A cycle is
  21 days". Not really a note: a timing or a condition, which USDM models as first-class entities.

Forcing all three through one entity with one binding is what makes "what should this link to"
unanswerable. For the definitional third, the honest answer is *nothing* — and the model cannot say it.

## Why it matters more from here

Inside the SoA layers a mis-bound footnote is close to cosmetic; the schedule matrix is unaffected and
a reader sees a note next to a slightly wrong row. Transformed to USDM it stops being cosmetic: a note
attached to an activity becomes a statement about that activity in the study definition. Defect 6 alone
would carry 52 false statements forward, and nothing downstream could tell them from the true ones.

The current model is adequate for the qualifying case, which is the majority. It is not adequate for
the other two, and it cannot currently express its own uncertainty.

## Candidate directions

Sketches, not proposals. Costs are the honest part.

### A — Patch the leak

Restrict the fallback to `activity_name` locations; add `referenced_props` to the consolidated schema
so property notes have somewhere true to point.

*Fixes:* defect 6. *Leaves:* duplicated binding state, no table scope, no way to record inference.
*Cost:* one schema field, one function, re-consolidation of ~10 protocols. Days.

### B — Separate evidence from scope

An annotation carries its text and type, a list of **anchors** (where the marker was printed — page,
row, column; evidence, never consumed as scope) and a list of **scopes** (what it governs: activity,
property, column, cell, table-wide, or explicitly unresolved), each recording how it was determined —
printed marker, geometric inference, or human judgement. `annotation_markers` becomes derived for
display and stops being writable.

*Fixes:* faults 1, 2 and 3 together. Unresolved becomes sayable, so today's silent wrong answers become
visible gaps. *Cost:* both schemas, `resolve` and `consolidate` rewritten, prompt rewritten,
re-extraction of every protocol. Weeks.

### C — Split by kind

B, plus separating definitional content out of annotations entirely — legends and abbreviation keys
become table metadata, and study-logic notes are marked as candidates for USDM timings and conditions
rather than notes.

*Fixes:* the heterogeneity, and makes the USDM transform deterministic where it is currently
heuristic. *Cost:* B, plus a taxonomy pass over 731 annotations. Weeks, and it changes what the
downstream transform consumes.

## Provenance: method, not confidence

*Added after the first reading, when the question came back as: should* every *interpreted field
across the whole schema carry how it was determined?*

Applied uniformly, that overcomplicates. `soa-table-extraction` has **73 leaf fields**, and the large
majority are transcription or mechanics — `table_number`, `row_position`, `column_position`,
`page_start`, `cell_text`, timestamps, filenames. Tagging those adds noise, invites cargo-cult filling
nobody reads, and competes for the extractor's attention with the content itself. There is a real risk
of degrading extraction quality in order to record metadata about extraction quality.

Applied selectively it is worth doing, and the schema already contains the idiom. `activity_name` has
`activity_name_source` beside it; `property_name` has `property_name_source` — which already carries
`synthesized: boolean`. The pattern is not foreign to the design, it is under-applied. What follows is
an extension of an existing convention, not a new mechanism.

### The test: could this value have been arrived at more than one way?

`cell_value` for a plain X has one way — read it. A note's text has three. That question cuts 73
fields to roughly eight, and every one of the eight has produced a defect in the last three weeks:

| Field | Alternative methods | Defect it produced |
|---|---|---|
| `annotation.annotation_text` | vector rules / raster rules / proximity | fragmentation, then over-merge (defects 1, 2) |
| `annotation.marker_locations` (scope) | printed marker / nearest row / inferred | defects 4, 5, 6 |
| `activity.activity_name` | text layer / reconstructed from a glyph stream | "Addition alc. Difficile"; section-header bleed into names |
| `activity_name_source.indentation_level` | indentation / shading / bold — schema already calls this human judgement | hierarchy errors in the resolved layer |
| `activity_schedule_value.cell_value` in a merged span | glyph position / rule-line geometry | T2/T3 tile merge dropped 34 + 38 marks |
| `activity_schedule_value.source_range`, `schedule_grid_value.merged_cell_range` | same | merged-span errors caught on NCT03637764 |
| `schedule_property.property_type`, `hierarchical_level` | classification judgement | recurring low-confidence entries in uncertainty reports |
| `table_metadata.table_type` | taxonomy judgement (domain / track / subsidiary) | documented judgement call in this protocol's own report |

### Three design rules that keep it cheap

**Record method, not confidence.** A model self-reporting confidence is unreliable and systematically
optimistic — a number that feels informative and is not. Method is objective and re-derivable: *this
note was bounded by proximity* is a claim checkable against the PDF later, and it is exactly the claim
that would have flagged NCT04677179 on the day it was extracted. A confidence score would not have.

**Exception-based, not exhaustive.** Absent means the normal method — transcribed, read directly, rule
lines present. Record only the deviation. That inverts the burden from tagging everything to declaring
the guesses, keeps every existing extraction valid, and avoids the drift trap already paid for once
with `annotation_markers`: a field that can disagree with another eventually will.

**Only where something branches on it.** A validator that refuses to pass proximity-bounded notes. A
review queue ordered by method rather than by protocol. A viewer that greys inferred marks. Provenance
that nothing consumes is documentation with a schema tax.

### Where this sits against A, B and C

This is the core of **B** at closer to **A**'s cost. It does not require the anchors/scopes split, and
it does not require re-extraction to be *valid* — absent provenance is a legal state meaning "normal
method", so existing files stay conformant and gain the field as protocols are re-extracted anyway.
What it does deliver is the thing the whole note is about: the layer becomes able to say *I inferred
this*, in a form code can act on rather than prose in a report.

It does not, by itself, fix the property-has-no-target gap (defect 6) or give table-scope notes a home.
Those remain A and B respectively.

## What is not in question

- The 2D-presentation insight in `soa2usdm-schema-architecture.md` holds. This is not a challenge to
  the three-layer design.
- The mark layer is unaffected. Every defect here is in the annotation layer; `schedule_matrix` has
  been byte-stable throughout.
- The five detectors now in place (fragmentation, degenerate typing, partial marker binding,
  cross-table binding conflict, over-merge) stay useful under any of A, B or C. They are how these
  faults became visible.

## Questions to settle before choosing

1. Does the USDM transform need property- and table-scoped notes, or can it drop them? If it can drop
   them, A may be enough and the rest is tidiness.
2. Is re-extraction of the corpus acceptable? B and C require it. A does not.
3. Should the extraction record **how** each interpreted value was arrived at — for the eight fields
   where it could have been arrived at more than one way — and should "unresolved" be an allowed
   answer rather than a guess? See *Provenance: method, not confidence* above. That single answer
   decides most of the rest.
4. Is the definitional third worth modelling at all, or should legends and abbreviation keys simply
   stop becoming annotations?
