# SoA Table Type Definitions (v5)

Classification scheme for Schedule of Activities tables in clinical trial protocols. Used for structure discovery before extraction and consolidation.

---

## Table Types

### main_soa
The primary Schedule of Activities table that serves as the anchor for the study timeline. Contains the core activity × timepoint grid showing what procedures are performed at which visits/days/cycles. Every protocol has at least one. When multiple independent schedules exist (e.g., Screening table and Treatment table with different column structures), each is classified as main_soa.

### continuation
A physical continuation of another table split across pages due to space constraints. Has identical column headers - the rows simply continue. Common in protocols with many activities. During consolidation, rows are appended to the parent table.

### domain
A table with the same column structure (timeline) as the main_soa, **applying to the same participants**, but containing a different category of activities. Sponsors sometimes split assessments into separate tables by domain for readability - Non-laboratory assessments, Laboratory assessments, PK assessments, etc. During consolidation, activities merge into a unified list aligned to the shared timeline.

*Examples:*
- *Amgen protocol with Table 1a (Non-lab), Table 1b (Lab), Table 1c (PK) - all sharing 20 columns but grouping different assessment types.*

*NOT domain:* two schedules that split the study population into **mutually exclusive groups** (responders vs non-responders, arm A vs arm B) are `track`, not `domain` - even when they share identical visit labels. See the discriminator below.

### subsidiary
A table with different (typically finer) column structure providing detailed timing for a subset of activities. Often used for intensive PK sampling where the main SoA shows "PK sampling" as a single activity, but a subsidiary table breaks this down by hour or minute. Links back to specific activities in the main timeline.

*Example: Alexion Table 2 showing hour-by-hour PK/PD sampling times (columns: -0.5h, 0h, 1h, 2h, 4h...) for specific study days referenced in Table 1.*

### track
A table representing a genuinely separate study timeline for a different population or study phase. Usually the column structure differs too - different visits, different duration, different timing - but **a different column structure is not required**: what makes a table a track is that it schedules a *different set of participants*, or the same participants in a *different study phase*. Maps to a separate ScheduleTimeline in USDM.

*Examples:*
- *NCT04184622 Section 1.3.2 - an additional 2-year treatment schedule only for participants with prediabetes at randomization, with its own visit numbering (101-199) and timing.*
- *Continued Access schedules with distinct visit structures for participants continuing treatment after the main study period.*
- *NCT04677179 Tables 2 and 3 - Maintenance (responders at Week 12) and Extension (non-responders at Week 12). Their visit labels, weeks and study days are numerically identical (V10-V29), but the two schedules apply to mutually exclusive populations, so each is its own track.*

### reference
A table containing non-activity content - sample specifications, timing parameters, notes, abbreviations, or explanatory text. Rows are not procedures performed on subjects. Not a timeline; provides metadata that may link to activities but doesn't represent scheduled assessments.

**A table is `reference` only if its rows key to nothing in the schedule.** Where each row names an activity, a visit or a timepoint that already appears in the SoA and the row's other cell explains it — an "Additional Information" or "Notes on assessments" table — that content is annotations, not a table. See the note below.

*Examples:* 
- *PK sampling tables where rows are "Sample 1, Sample 2..." with collection specifications*
- *Abbreviation lists*

*Note — where the conversion happens.* Content explaining specific activities or timepoints in the main schedule becomes **annotations at extraction time** (prompt §6). It does not become a `reference` table for something downstream to convert later: `resolve` binds an annotation to its element through that row's `annotation_markers`, so a note left as a table row binds to nothing, and the loss is silent — the table is schema-valid, no marker is partial, and only the annotation count on the parent table shows it.

---

## Summary Table

| Type | Column Structure | Row Content | Consolidation Action |
|------|------------------|-------------|---------------------|
| **main_soa** | Primary grid | Activities | Anchor table |
| **continuation** | SAME as parent | Activities continue | Append rows |
| **domain** | SAME as parent | Different activity category, SAME participants | Merge activities |
| **subsidiary** | DIFFERENT (finer) | Activity subset, detailed timing | Link to parent activities |
| **track** | DIFFERENT, or same | Different population/phase | Separate ScheduleTimeline |
| **reference** | N/A | Non-activities | Annotations/metadata |

---

## Decision Tree

```
Are the rows ACTIVITIES (procedures performed on subjects)?
│
├─ NO → Do the rows key to activities, visits or timepoints in another table?
│       │
│       ├─ YES → NOT a table — extract the content as annotations (prompt §6)
│       └─ NO  → reference
│
└─ YES → Does it share the SAME columns as another table?
         │
         ├─ YES → Is it a physical page split (rows continue)?
         │        │
         │        ├─ YES → continuation
         │        └─ NO  → Does it schedule the SAME participants as that table?
         │                 │
         │                 ├─ YES → domain
         │                 └─ NO  → track   (mutually exclusive populations)
         │
         └─ NO → Is this the primary/anchor table?
                  │
                  ├─ YES → main_soa
                  └─ NO  → Does it provide finer timing granularity?
                           │
                           ├─ YES → subsidiary
                           └─ NO  → track
```

**The population question is not optional.** Two schedules can carry byte-identical visit
labels, weeks and study days and still be separate tracks: identical columns mean the sponsor
reused a visit numbering scheme, not that the same people attend those visits. Getting this
wrong is silent - the consolidated `schedule_matrix` and column count are unaffected, but the
`population_track` of every column in the misclassified table goes null, and the branch
identity is gone with nothing failing anywhere.
