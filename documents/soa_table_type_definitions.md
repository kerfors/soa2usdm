# SoA Table Type Definitions (v4)

Classification scheme for Schedule of Activities tables in clinical trial protocols. Used for structure discovery before extraction and consolidation.

---

## Table Types

### main_soa
The primary Schedule of Activities table that serves as the anchor for the study timeline. Contains the core activity × timepoint grid showing what procedures are performed at which visits/days/cycles. Every protocol has at least one. When multiple independent schedules exist (e.g., Screening table and Treatment table with different column structures), each is classified as main_soa.

### continuation
A physical continuation of another table split across pages due to space constraints. Has identical column headers - the rows simply continue. Common in protocols with many activities. During consolidation, rows are appended to the parent table.

### domain
A table with the same column structure (timeline) as the main_soa but containing a different category of activities. Sponsors sometimes split assessments into separate tables by domain for readability - Non-laboratory assessments, Laboratory assessments, PK assessments, etc. During consolidation, activities merge into a unified list aligned to the shared timeline.

*Examples:*
- *Amgen protocol with Table 1a (Non-lab), Table 1b (Lab), Table 1c (PK) - all sharing 20 columns but grouping different assessment types.*
- *Responder/Non-responder schedules that share the same visit structure but show different activities or conditional assessments for each population.*

### subsidiary
A table with different (typically finer) column structure providing detailed timing for a subset of activities. Often used for intensive PK sampling where the main SoA shows "PK sampling" as a single activity, but a subsidiary table breaks this down by hour or minute. Links back to specific activities in the main timeline.

*Example: Alexion Table 2 showing hour-by-hour PK/PD sampling times (columns: -0.5h, 0h, 1h, 2h, 4h...) for specific study days referenced in Table 1.*

### track
A table representing a genuinely separate study timeline for a different population or study phase. Has different column structure because the schedule itself is different - different visits, different duration, different timing. Maps to a separate ScheduleTimeline in USDM.

*Examples:*
- *NCT04184622 Section 1.3.2 - an additional 2-year treatment schedule only for participants with prediabetes at randomization, with its own visit numbering (101-199) and timing.*
- *Continued Access schedules with distinct visit structures for participants continuing treatment after the main study period.*

### reference
A table containing non-activity content - sample specifications, timing parameters, notes, abbreviations, or explanatory text. Rows are not procedures performed on subjects. Not a timeline; provides metadata that may link to activities but doesn't represent scheduled assessments.

*Examples:* 
- *PK sampling tables where rows are "Sample 1, Sample 2..." with collection specifications*
- *"Additional Information" tables explaining activity details*
- *Abbreviation lists*

*Note: Reference tables often capture content that downstream processing may represent as annotations - footnotes, instructions, conditional logic, or explanatory text that applies to specific activities or timepoints in the main schedule.*

---

## Summary Table

| Type | Column Structure | Row Content | Consolidation Action |
|------|------------------|-------------|---------------------|
| **main_soa** | Primary grid | Activities | Anchor table |
| **continuation** | SAME as parent | Activities continue | Append rows |
| **domain** | SAME as parent | Different activity category | Merge activities |
| **subsidiary** | DIFFERENT (finer) | Activity subset, detailed timing | Link to parent activities |
| **track** | DIFFERENT | Different population/phase | Separate ScheduleTimeline |
| **reference** | N/A | Non-activities | Annotations/metadata |

---

## Decision Tree

```
Are the rows ACTIVITIES (procedures performed on subjects)?
│
├─ NO → reference
│
└─ YES → Does it share the SAME columns as another table?
         │
         ├─ YES → Is it a physical page split (rows continue)?
         │        │
         │        ├─ YES → continuation
         │        └─ NO  → domain
         │
         └─ NO → Is this the primary/anchor table?
                  │
                  ├─ YES → main_soa
                  └─ NO  → Does it provide finer timing granularity?
                           │
                           ├─ YES → subsidiary
                           └─ NO  → track
```
