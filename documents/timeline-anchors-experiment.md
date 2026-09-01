# Timeline anchors from consolidated SoA data — first experiment

**Status: experiment note, 2026-08-25. Nothing implemented. Input: `usdm_data/CDISC_Pilot` consolidated output only; the d4k `CDISC_Pilot_Study.json` was deliberately not opened, so a blind comparison against it is still available as the next step.**

Question: starting from `CDISC_Pilot_consolidated.json` (30 activities, 15 columns, 139 marks, 8 annotations), can the semantic layer identify the USDM timeline anchor — the `Timing` of type *Fixed Reference* (C201358) — for the main timeline, and can it see sub-timelines that need an anchor of their own? Method: read the consolidated data first and write down every claim with its evidence; only then grep the protocol narrative (`CDISC_Pilot.md`) to see which claims the SoA alone could not have made.

## 1. Main timeline — the anchor is found, and the SoA says what it is

Two independent signals in the consolidated data point at the same column, `xcol-003` (VISIT 3 / WEEK 0):

| Signal | Evidence in the consolidated file |
|---|---|
| A zero on a signed relative-time scale | `property_hierarchy` prop-002 `WEEK` (level 2) carries `-2, -.3, 0, 2, 4, 6, 8, 12, 16, 20, 24, 26`. Negative values before, positive after, exactly one zero. A header row with that shape *is* an offset scale, and the zero is its fixed reference. |
| A milestone activity whose only mark sits in the zero column | `xact-010 Patient randomized` has one mark in the whole matrix, at `xcol-003`. |

Signal 1 locates the anchor instance; signal 2 names the anchoring event. This is worth stating because of the open question in Tamer Chowdhury's thread — *what does the model assert about the anchoring event itself?* USDM asserts nothing: the Fixed Reference `Timing` hangs on a `ScheduledActivityInstance`, and the instance is just a container of `activityIds`. The SoA, by contrast, carries the assertion explicitly, as co-location of the zero and the milestone row. So the semantic layer should emit both: the `Timing` on the VISIT 3 instance, and a provenance statement that the anchor was derived from the pair (prop-002 zero, xact-010). Without the second statement the fact "the anchor is randomization" is only recoverable by a reader who knows to look inside `activityIds`.

Two other rows also have a single mark at WEEK 0: `xact-013 Ambulatory ECG removed` and, if read as a milestone, the first mark of `xact-022 Study drug record` (VISIT 3 through 13 and ET). Neither displaces randomization: "removed" is the closing half of a placed/removed pair (section 3), and the drug record is a recurring row, not a single-mark row. But it shows the heuristic needs the activity name, not just the mark geometry — a single mark in the zero column is necessary, not sufficient.

Narrative check: "Visits 1 through 13 should be scheduled relative to Visit 3 (Week 0 - randomization)" (protocol p. 9) and "Upon enrollment at Visit 3, and on the morning of each subsequent day of therapy, xanomeline or placebo will be administered" (p. 25). Both confirm the SoA reading and add one fact the SoA does not state: first dose is on the randomization day, so Week 0 is also Day 1 of treatment.

### What the main-timeline Timings look like, from the SoA alone

All offsets in the WEEK row are measured from the zero, so the faithful reading is anchor-relative, not chained:

| Column | Timing type | value | relativeFrom → relativeTo | relativeToFrom |
|---|---|---|---|---|
| xcol-003 (V3, wk 0) | Fixed Reference | 0 | — | — |
| xcol-001 (V1, wk -2) | Before | 2 weeks | V1 → V3 | Start to Start |
| xcol-002 (V2, wk -.3) | Before | *see below* | V2 → V3 | Start to Start |
| xcol-004 … xcol-013 (V4 wk 2 … V13 wk 26) | After | 2, 4, 6, 8, 12, 16, 20, 24, 26 weeks | Vn → V3 | Start to Start |

The chained form in the LinkedIn figure ("P28D chained to Visit 4, wherever it landed") is a modelling choice that this SoA does not support: the header prints absolute offsets from the zero, and chaining them would be an interpretation, not a transcription. Start to Start is the default reading for visit-to-visit offsets; the SoA gives no basis for anything else.

Three things the SoA cannot supply, all confirmed missing rather than overlooked:

- **Windows.** No `windowLower`/`windowUpper` anywhere in the header or footnotes. The narrative has them (V4, 5, 7, 8, 13 within 3 days; V9–12 within 4 days; p. 9) — they exist only as prose.
- **The value of WEEK -.3.** Printed as `-.3` (transcribed as printed, no leading zero). 0.3 week is 2.1 days; the narrative says the Ambulatory ECG placed at V2 is a 24-hour recording removed at V3, which is consistent with "about two days before" but does not pin the number. A Timing value of `-.3 weeks` is what the evidence supports; converting to `P2D` would be an assumption and must be flagged as one.
- **Epochs.** No epoch header row. Screening activities cluster in the negative-week columns and the drug record starts at zero, so a screening/treatment split is *suggested*, but boundaries are not printed and `StudyEpoch` should not be emitted from this table without a stated rule.

## 2. Columns that are off the clock

Three columns carry no WEEK value, and the empty header cell is itself a signal: "not on the fixed scale".

- **xcol-014 ET (Early Termination).** No offset, by nature. In USDM this is a `ScheduledActivityInstance` reached through a decision/exit path, not through a `Timing` to the anchor. The SoA gives the activity set for it (Physical examination, Vital signs, ECG, Con-meds, labs, Plasma specimen, drug record, TTS survey, the four scales, AEs) but not the trigger.
- **xcol-015 RT (Retrieval).** SoA-only: same status as ET. Narrative (3.10.1.1): "retrieved on the date which would have represented Visit 12 (Week 24)" — so RT is in fact anchored, *After 24 weeks* from V3, but conditional on prior early termination. This is the one case here where the narrative changes the timing type of a column, not just its window.
- **xcol-006 (position 8, blank).** Retained by the extraction as a rule-bounded empty column; the printed VISIT sequence skips 6 and the narrative never mentions a Visit 6 (0 hits). The 2-weekly pattern for the first 8 weeks (0, 2, 4, 6, 8 = V3, 4, 5, 7, 8) is complete without it. Semantic layer rule: a column with no property values and no marks produces no instance.

## 3. Sub-timeline candidates

Tamer's second point — a sub-timeline is a whole timeline with its own anchor and its own clock — is where the SoA becomes thin. Five candidates, ordered by how much of them the SoA actually shows:

| Candidate | What the SoA shows | Own anchor | Own clock | Visible in SoA? |
|---|---|---|---|---|
| **A. Ambulatory ECG** | `xact-012 …placed` at V2, `xact-013 …removed` at V3 — a placed/removed pair spanning two main-timeline columns | placement | 24 h (narrative only) | partly — the interval, not its length |
| **B. NPI-X telephone follow-up** | footnote `b` on 4 cells: NPI-X at V8, V9, V10, V11 (`xannot-003`: "Performed at this visit and via telephone interview 2 weeks following this visit") | the clinic visit the mark sits in | +2 weeks | yes, fully |
| **C. PK plasma sampling** | `xact-020 Plasma Specimen (Xanomeline)` at V3, 4, 5, 7, 9, 11 — one plain `X` per visit | daily patch application (narrative) | time-of-day windows (narrative) | no |
| **D. Daily dosing** | `xact-022 Study drug record` at V3–V13 and ET | each morning's patch application | daily | no |
| **E. Placebo TTS test** | `xact-015` single mark at V1 | — | — | no; narrative says it is worn during the screening visit, no interval |

**A** is an interval, and the semantic layer has a choice: two activities on the main timeline with a Timing between them (removal *After* placement, End to Start or Start to Start, value unknown from the SoA), or an `Activity` with a `timelineId` to a sub-timeline anchored at placement with a 24-hour exit. The SoA supports the first; the second needs the narrative's "24-hour". Recommendation: emit the pair on the main timeline with the Timing value left empty and flagged, since the duration is not in the evidence.

**B** is the cleanest case and the one worth prototyping first. Everything needed is in the consolidated file: the four cells, the relation ("2 weeks following this visit"), and the contact mode (telephone). Two USDM renderings are defensible:

- Four extra `ScheduledActivityInstance`s on the main timeline, each with an `Encounter` of contact mode telephone and a Timing *After 2 weeks* whose `relativeTo` is the clinic-visit instance (V8, V9, V10, V11) — chained to the visit, not to the study anchor. Resolves to weeks 10, 14, 18, 22, which fills the 4-week gaps so NPI-X is 2-weekly throughout; the narrative says exactly that ("at 2-week intervals either at clinic visits or via a telephone interview", 3.9.1.1).
- One sub-timeline "NPI-X telephone" with its own anchor = the clinic visit, entered four times.

The first is simpler and keeps one clock. The second is what Tamer's framing would produce. The choice is not decidable from the SoA; it is a modelling policy, and the note should record which one was chosen and why. A footnote of the form "*and via <contact mode> <n> <unit> following this visit*" is a reusable pattern (`After`, value n, relativeTo = the marked column's instance, encounter contact mode from the text).

**C** is the most interesting failure. The row name says PK, but a plain `X` per visit gives no hint of an inner clock. The narrative (3.9.2) describes a sparse-sampling design: one sample per visit, each visit assigned to one of five intervals (early AM before the new patch; 9–11; 11–13; 13–15; 15–17), order varying per patient. Its anchor is that morning's patch application, which is not a scheduled instance in the SoA at all (candidate D is invisible too), and its "offsets" are clock-time windows, not durations. USDM `Timing` has `windowLower`/`windowUpper` but no time-of-day semantics, and the per-patient permutation is a design rule, not a timing. This is the OGTT composition problem from the thread in a harder form: the sub-timeline exists, its anchor exists, but neither is in the SoA and the model has no obvious slot for the window rule. Record it as a known gap, not a modelling task.

## 4. Detection rules the semantic layer can implement

Derived from this one protocol, so provisional; each names its CDISC_Pilot instance.

1. **Anchor column** = the column whose relative-time property value is 0, on a property row that has both negative and positive values. (prop-002, xcol-003.) If several relative-time rows exist (DAY and WEEK), they must agree.
2. **Anchoring event** = a single-mark activity in the anchor column whose name is a milestone (randomized, enrolled, first dose, dosed). (xact-010.) Emit as provenance, not as a USDM attribute — USDM has no slot for it.
3. **Main-timeline Timings** = one per column with a relative-time value: sign gives Before/After, value copied as printed with its unit from the property name; `relativeTo` = anchor instance; Start to Start. (12 of the 15 columns; the anchor column is one of them, with value 0.)
4. **Off-clock columns** = columns with a visit identifier but no relative-time value: instances without a Timing to the anchor, to be connected by decision/exit logic. (ET, RT.) Columns with neither identifier nor marks produce nothing. (xcol-006.)
5. **Paired interval activities** = two activities whose names differ only by placed/removed, start/stop, applied/removed, with single marks in different columns. (xact-012/013.) Emit the pair and an inter-activity Timing with empty value, flagged.
6. **Footnote-carried sub-timing** = a footnote on marked cells containing *following/after/prior to this visit* plus a duration. (xannot-003.) Emit chained Timings from the marked cells.
7. **Rows whose name suggests an inner clock** (PK, plasma concentration, OGTT, glucose, 6MWT) but whose marks are plain: flag "possible sub-timeline, not derivable from SoA" for the reviewer. (xact-020.)

Rules 1–4 and 6 are fully evidenced here. Rule 5 needs the duration from outside the table. Rule 7 produces a flag, never an instance.

## 5. What the narrative added, in one list

For the record of what "SoA-only" costs on this protocol: visit windows (±3/±4 days); the RT column's Week-24 anchoring; the 24-hour length of the Ambulatory ECG; first dose = randomization day; the PK sampling design (C) and daily dosing (D) entirely; the screening/treatment phase names. Nothing the narrative said contradicted a claim made from the SoA.

## 6. Next steps

- Open `downloads/d4k/CDISC_Pilot_Study.json` (usdm-rdf) and compare: which instance carries the Fixed Reference Timing, whether V-to-V Timings are anchor-relative or chained, how ET/RT are connected, whether NPI-X telephone and the Ambulatory ECG appear as sub-timelines, instances, or not at all. This note is the blind prediction; the comparison is the experiment.
- Prototype rule 6 (NPI-X telephone) as the first emitted sub-timing, since it is the one case fully evidenced by the consolidated data.
- Run rules 1–2 across the other usdm_data protocols to see how often the anchor column is a zero on a DAY row versus a WEEK row, and how often the anchoring event is a single-mark milestone row versus absent (first dose folded into a "study drug administration" recurring row).

---

# 7. Comparison against the d4k USDM model (added 2026-08-25)

Source now opened: `usdm-rdf/downloads/d4k/CDISC_Pilot_Study.json` (the DDF-RA CDISC Pilot example, `systemName`/tag as pinned in usdm-rdf). Sections 1–6 above were written without it and are left unchanged; this section scores them.

The d4k design has **four** ScheduleTimelines, not one: `Main Timeline` (`mainTimeline: true`, 16 instances, 16 timings), plus three sub-timelines with `mainTimeline: false` — `Adverse Event`, `Early Termination`, and `Vital Sign Blood Pressure`. That shape already answers part of the question: USDM here uses separate whole timelines for the off-clock and inner-clock material, exactly the "its own anchor, its own clock" structure from Tamer's post — one Fixed Reference per timeline.

## Scorecard

| # | Blind prediction (§1–4) | d4k model | Verdict |
|---|---|---|---|
| Anchor column | VISIT 3 / WEEK 0 is the Fixed Reference | `Timing_3` type **Fixed Reference** (C201358) sits on `ScheduledActivityInstance_11`, whose encounter `E3` is named **Baseline** = Visit 3 | **Correct** |
| Anchor expressed as | Week 0 is also Day 1 of treatment | the Fixed Reference `value` is **P1D "1 Day"**, not a week — d4k anchors as Day 1 | **Correct**, and sharper than the SoA: they chose the day form |
| Anchoring event | randomization; emit as provenance because USDM has no slot | `SAI_11.activityIds` contains **"Patient randomised"** — but the Timing asserts nothing; it is recoverable only by reading the instance's activity list | **Correct**, including the reason: the "what the anchor is" fact lives inside `activityIds`, unstated by the Timing |
| Timing direction | anchor-relative, not chained; Before/After to V3; Start to Start | every main-visit Timing is **Before/After, relativeTo `SAI_11`, Start to Start** (C201355) | **Correct** |
| Offsets | V4=2w After … V13=26w After, from the WEEK row | P2W, P4W, P6W, P8W, P12W, P16W, P20W, P24W, P26W After — value-for-value the WEEK row | **Correct** |
| WEEK −.3 | ambiguous; P2D would be an assumption to flag | d4k encoded **P2D "2 days"** on V2, plus a within-day window **PT4H..PT0H ("-4..0 hours")** | **Correct call on the ambiguity** — d4k made exactly the conversion I flagged as an assumption, and added an hours window the SoA has no field for |
| Windows | absent from SoA, prose only | windowLower/Upper populated: **±3 days** (V4,5,7,8,13), **±4 days** (V9,10,11,12) — the narrative values | **Correct**: not derivable from the SoA; d4k pulled them from the text |
| NPI-X telephone (candidate B / rule 6) | four extra SAIs on the main timeline, each **After 2 weeks, relativeTo the clinic-visit instance** (V8–V11), chained to the visit not the anchor | `SAI_16,18,20,22`, each **After P2W** relative to `SAI_15/17/19/21` (= V8,V9,V10,V11) — chained to the visit | **Correct, structurally exact** — including the choice of "extra SAIs chained to the visit" over "a separate sub-timeline" |
| NPI-X — encounter detail | separate telephone `Encounter` with contact mode telephone | d4k **reuses the clinic encounter** (E8 serves both SAI_15 and SAI_16) and adds **"Telephone Call"** to that encounter's `contactModes` alongside "In Person" | **Partly wrong**: right that telephone is captured, wrong about where — modality on the shared encounter, not a new encounter |
| ET | off the anchor clock, reached by decision/exit | modelled as its **own sub-timeline** (`ScheduleTimeline_2`, one SAI, 15 activities, own Fixed Reference) | **Correct in substance** (off the main clock, own anchor), **wrong on mechanism** (separate timeline, not a `ScheduledDecisionInstance` on main) |
| RT (Retrieval) | anchored After 24 weeks, conditional on early termination | **absent** — no Retrieval timeline, no retrieval activity, nowhere in the JSON | **Divergence, in the SoA's favour**: the SoA carries the RT column; d4k's model drops it |
| Blank position-8 column | produces no instance | no Visit-6 instance exists | **Correct** |
| Ambulatory ECG (candidate A / rule 5) | placed/removed pair; emit on main, interval Timing value left empty | `Activity_14 placed` on `SAI_10` (V2), `Activity_15 removed` on `SAI_11` (V3); **no interval Timing between them** | **Correct**: d4k also does not encode the 24-hour duration — the pair sits on two main SAIs with no inter-activity timing |
| PK plasma sampling (candidate C / rule 7) | sub-timeline anchored on patch application, time-of-day windows, no model slot; invisible in SoA | **no PK sub-timeline**; `Plasma Specimen` is a plain activity on the visit SAIs | **Correct**: the sampling design is unmodelled in d4k too — the gap is real, not just an SoA limitation |
| Daily dosing (candidate D) | invisible in SoA | `Study drug` is a plain activity on the visit SAIs; no daily sub-timeline | **Correct** |
| Epochs | do **not** emit from the SoA without a stated rule | d4k emits **5 epochs**: Screening (V1–V2), Treatment 1 (V3–V4), Treatment 2 (V5–V11), Treatment 3 (V12), Follow-Up (V13) | **Correct caution**: those boundaries — especially the Treatment 1/2/3 split and V13 as Follow-Up — are **not** derivable from the SoA table; d4k used external structure |

## What d4k has that my rules would have missed

Two sub-timelines exist that the SoA-only rules do not reach:

- **Vital Sign Blood Pressure Timeline** (`ScheduleTimeline_3`) — six instances on a **minutes** clock: Fixed Reference at PT0M, then After PT5M, PT0M, PT1M, PT0M, PT2M, cycling Supine → Vital Signs Supine → Stand → Vital Signs Standing. This is a real inner-clock sub-timeline, and rule 7 would **not** have flagged it: the SoA row is "Vital signs/Temperature", whose name gives no hint of a supine/standing BP profile. The inner clock came from biomedical-concept / procedure knowledge, not from the table. This is the honest miss — my heuristic keys on suggestive row names (PK, OGTT, 6MWT), and a bare "vital signs" row defeats it.
- **Adverse Event Timeline** (`ScheduleTimeline_1`) — its own Fixed Reference, one SAI. AEs are a continuous every-visit row in the SoA (`xact-030`, marks in every column), and d4k lifts them onto a dedicated timeline. Not an inner-clock case, but another instance of "one SoA row → its own timeline" that mark geometry alone would not predict.

Neither is derivable from the consolidated SoA, which is the point: they mark the ceiling of what the semantic layer can do from the table, and they are the same class of fact (composition and inner clocks) that the LinkedIn thread identified as living below the timeline.

## Net read

Of the fourteen scored predictions, ten are correct outright, three are correct in substance with the mechanism or detail different (NPI-X encounter placement, ET as a separate timeline rather than a decision instance, epochs emitted from outside the SoA as I cautioned), and one is a genuine divergence where d4k dropped something the SoA carries (RT). The detection rules that were "fully evidenced" (1–4, 6) all reproduce what d4k did. The two things I called un-derivable — windows and the anchoring-event assertion — are exactly the two places d4k reached outside the table (narrative windows; randomization recoverable only inside `activityIds`). The interesting-failure call on PK holds: d4k did not model it either.

The clearest single confirmation of the thread's framing: the anchor is a relationship, not a field. d4k's Fixed Reference is a `Timing` (P1D) hanging on the Baseline instance and pointing at itself; nothing on that instance says "this is the origin because randomization happens here" — that has to be read out of its `activityIds`. Emitting the provenance statement (rule 2) is therefore not redundant with the USDM output; it records a fact the USDM output leaves implicit.

## Follow-ups this comparison opens

- The NPI-X encounter finding refines rule 6: a footnote-carried telephone follow-up should add the contact mode to the **existing** encounter and add a chained SAI, not mint a new encounter. Worth checking against a protocol where the telephone contact is at a visit that has no in-person component.
- RT dropped by d4k but present in the SoA is a concrete example for the SoA-patterns publication: the extraction preserves a scheduled column that a hand-built USDM model omitted. It is the kind of divergence the evidence layer (global-identifiers note) is meant to make citable.
- Epochs: since d4k's epoch boundaries are not in the table, the semantic layer should either leave epochs unset or take them from a stated source, never infer them from column clustering. Rule set unchanged; this is now confirmed rather than asserted.

---

# 8. Re-tag against Dave's SoA Patterns (interim v1.0, added 2026-08-25)

Source: d4k "SoA Patterns v1.0" training material (readme, **interim / unofficial**; reflects late-Feb-2026 material; Iberson-Hurst has signalled a more rigorous successor — "Foundation, Patterns and SoAs", 17 Jun 2026 — from 169 SoAs / 1,700+ footnotes → ~12 recognisable SoA shapes + 21 footnote kinds → a small set of USDM timeline patterns). The pattern names below are provisional and expected to be superseded.

**Structural alignment first.** d4k's CDISC_Pilot model from §7 — one Main Timeline + one Vital-Sign-BP subsidiary + two unscheduled timelines (Adverse Event, Early Termination) — is a direct instance of Dave's top-level taxonomy: one main timeline + zero-or-more subsidiary timelines (precise / reusable logic) + zero-or-more unscheduled-event timelines. The four-timeline shape I found in the JSON is not arbitrary; it is that taxonomy realised.

**Mapping** (our §1–4 finding → Dave's named pattern → what the pattern adds over my SoA-only rule):

| Our finding / rule | Dave's pattern | What it adds |
|---|---|---|
| Anchor column = zero on a signed row (rule 1) | **Anchor Point** — three named manifestations: Cycle 1 Day 1; Week 0 of treatment (prev weeks −1, −2); Days from randomization (Day 0 blank) | Generalises my single signal to three; CDISC_Pilot's WEEK row is Dave's "Week 0 baseline" manifestation exactly |
| Anchoring event = milestone row (rule 2) | Anchor Point (randomization is a named manifestation) | Names the event as a manifestation but confirms the USDM Timing carries no event slot — the provenance point stands |
| Anchor-relative Timings (rule 3) | **Fixed Timing from Anchor** | Confirms anchor-relative-with-windows as the canonical main pattern; notes fixed and relative may mix in one timeline |
| Windows absent from the SoA | Fixed Timing from Anchor (windows intrinsic to the pattern) | The pattern says a window *belongs* on each fixed point — reframes "narrative-only" as "value from narrative, slot from pattern" |
| NPI-X telephone +2w (rule 6) | **Relative Timing Between Points** + **Footnote Extraction** | Two patterns converge: "occurs a set time after the previous visit regardless of when it landed" is Dave's canonical relative-timing use, and it is footnote-carried |
| ET off-clock (my mechanism was wrong) | **Other Unscheduled Events** — right side of table, no week number, no window → unscheduled → mini-timeline with entry condition | Gives the mechanism d4k used and I missed: a separate mini-timeline, not a decision instance on main. The absence-of-window signal is his, and cleaner than my "off-clock column" |
| RT (dropped by d4k) | Other Unscheduled Events | Same pattern; would have caught what the hand-built model omitted |
| AE every-visit row (mark geometry wouldn't predict) | **Adverse Events** — a row of X across all visits → its own unscheduled timeline | Names exactly the lift d4k did; my rules had no handle on it |
| Vital Sign BP sub-timeline (my miss) | **Footnote Extraction** | The sub-timeline I could not see from the row name is the one Dave's pattern is built to recover — from footnotes / BC. His worked example is vitals → ECG → 30-min gap → blood/PK on one encounter; d4k's is the same class, a supine/stand BP profile |
| PK plasma sampling (rule 7 = flag only) | **Sub-Timeline for Precise Schedules** — PD profile, own anchor at dosing, precise pre/post intervals | Supplies the target shape and the anchor-location convention (dosing) I said had "no model slot" — but instantiating the intervals still needs the content |
| Ambulatory ECG placed/removed (rule 5) | nearest: Footnote Extraction / sub-timeline | Not a named Dave example; the interval-value gap is unchanged |
| Epochs (I cautioned: don't derive from columns) | Main Timeline (each timepoint → encounter + epoch) | Gives the epoch vocabulary (screening / treatment / follow-up) but not table-derived boundaries — the caution holds |
| (not in CDISC_Pilot) treat-until-progression | **Cycles** — bounded loop + decision/exit ("progression or death") | The thread's "cycle 8 is a traversal, not a column" as a named pattern; relevant to the oncology protocols in the collection |

**Net.** Of the four §7 rows where I was wrong-on-mechanism or missed the item — ET, AE, Vital-Sign BP, and the RT divergence — Dave's patterns name the correct answer in every case. The rules I called "fully evidenced" (1–4, 6) each land on a named pattern, and Dave's Anchor-Point and Unscheduled-Events patterns are *better detectors* than my ad-hoc versions.

**Where the claim is exactly right, and its limit.** The patterns are a recogniser + a target USDM shape + a rendering convention. Converting SoA *shapes* and *typed footnotes* into timeline structure is their whole job, and it closes most of what I logged as un-derivable in §1–5. The residual is delimited precisely by Dave's own examples: the Footnote-Extraction and Sub-Timeline patterns instantiate only where the footnote or an adjunct table carries the content (his ECG example works because the footnote says "triplicate, 30 min before PK"). CDISC_Pilot puts its PK sparse-sampling design in *body prose* (§3.9.2), not a footnote or a PD table, so even the correctly-named sub-timeline pattern cannot fill in the intervals from the SoA artifact alone. Pattern recognition raises the ceiling from "flag it" to "instantiate the shape"; it does not reach content the SoA artifact never carried.

**Forward hook.** The rigorous successor Dave signalled decomposes the corpus into ~12 SoA shapes and 21 footnote kinds. Those are exactly the two things this project's Layer-1 output already produces — the consolidated table shape and the typed annotations (legend / footnote / abbreviation). The extraction layer is the input substrate that pattern recognition consumes; the semantic layer is where a recognised (shape, footnote-kind) pair is emitted as its USDM timeline pattern. What the patterns still cannot supply — the PK intervals, the 24-hour Holter duration, the actual window values — is the same residual that lives in the narrative and the BC/Procedure layer, i.e. the "level below" left open in the thread.
