# Timeline anchors across the corpus — survey

**Status: evidence note, 2026-09-29. Read-only; nothing implemented.** Input: the consolidated
output of all 24 protocols (22 in `usdm_data`, 2 in `misc_studies`). Every number below is
printed by `tools/anchor_survey.py`; rerun it to check or refresh them.

This runs rules 1 and 2 of [`timeline-anchors-experiment.md`](timeline-anchors-experiment.md)
across the corpus — the third of that note's next steps. The question is the one the SoA
patterns will have to answer: what does a printed SoA say about the clock its schedule is
measured on, and about the event that starts it?

## Method

For each protocol, the survey takes the main-segment header rows typed `study_day` or `week`
(the two types that carry relative time; `cycle`, `timepoint` and `other` mix labels and text).
Each printed value is read into a number where it can be — `D1`, `Day 3 (± 1 day)`,
`D-28 to D-1`, `(D-42 to -2)` — and kept verbatim next to it. A value it cannot read is reported
unread, not guessed. Three kinds are kept apart from numbers: values measured from something
other than the anchor (`after last dose`, `Post TxP`), pre-anchor values printed without a sign
(`≤28`), and hour or minute counts in a `timepoint` row.

- **Rule 1 (anchor column):** the first column whose relative-time value is 0; on a day row
  without a 0, the first column whose value is 1.
- **Rule 2 (anchoring event):** a row with a single mark in the whole matrix, placed in the
  anchor column, whose name is randomisation or first dose. The per-protocol table names the
  row that decided each call.

## Results

| Protocol | Clock row | Conv. | Anchor column (printed) | 0 printed | Restarts | Anchoring event | Second clock |
|---|---|---|---|---|---|---|---|
| NCT01797120 | none (epoch, timepoint) | | | | | |  |
| NCT05051579 | week: Week Relative to Randomization | zero | xcol-003 `0` | yes |  | randomisation (Randomization) | 2 Wks Post End of TXP |
| CDISC_Pilot | week: WEEK | zero | xcol-003 `0` | yes |  | randomisation (Patient randomized) |  |
| NCT01847274 | study_day: Day | day1 | xcol-002 `1` | no, skips −1→1 | 1 | randomisation elsewhere (Randomization at xcol-001, xcol-010) |  |
| NCT02107703 | study_day: Relative day within a cycle | day1 | xcol-003 `1` | no | 1 | not named |  |
| NCT02291289 | none (condition, epoch, other) | | | | | | (≤ 30 days after last dose of study treatment) |
| NCT03283098 | study_day: Study Day | day1 | xcol-003 `1 (HD)` | no |  | not named |  |
| NCT03402841 | study_day: Day | day1 | xcol-003 `1` | no, skips −1→1 |  | not named | Follow up 30 days after last dose of study medicat |
| NCT03421379 | study_day: Study Day | day1 | xcol-003 `Day 1` | no, skips −1→1 | 1 | randomisation (Randomization) | Within 28±2 days after last study treatment |
| NCT03548935 | week: Timing of Visit (Weeks) | zero | xcol-002 `0` | yes |  | randomisation (Randomisation criteria and randomisation) |  |
| NCT03548987 | week: Timing of Visit (Weeks) | zero | xcol-002 `0` | yes |  | randomisation elsewhere (Randomisation criteria and randomisation at xcol-012) |  |
| NCT03637764 | study_day: Study Day / Visit Timing | day1 | xcol-003 `D1 (±1)` | no, skips −1→1 | 1 | not named | 30 (±7) days after last IMP admin; 30 (±7) days after last IMPs admin; 60 (±7) days after last IMP admin; At 60 (±7) days after last IMPs admin; At 90 (±7) days after last IMPs admin; Every 90 days (±7) after last safety follow-up |
| NCT03693430 | week: Timing of Visit (Weeks) | zero | xcol-002 `0` | yes |  | randomisation (Randomisation criteria and randomisation) |  |
| NCT03817853 | study_day: Day | day1 | xcol-003 `D1` | no, skips −1→1 | 1 | not named |  |
| NCT04004988 | study_day: Study Day | day1 | xcol-003 `D1` | no, skips −1→1 |  | first dose (Tirzepatide Dosing) |  |
| NCT04184622 | week: Week of Treatment | zero | xcol-003 `0` | yes |  | randomisation (Randomization) | 17 wks Post TxP; 4 wks Post TxP |
| NCT04320615 | study_day: Study Day | day1 | xcol-002 `1` | in a range |  | randomisation (Randomization) | 15 min After end of infusion (+1 hr) |
| NCT04557384 | study_day: Day | day1 | xcol-003 `D1` | no | 2 | not named |  |
| NCT04573309 | study_day: Days | day1 | xcol-007 `1` | no, skips −1→1 |  | not named |  |
| NCT04677179 | study_day: Study day | day1 | xcol-002 `1` | no |  | randomisation (Randomization) | 58 or ETV + 8 weeks after last dose; 66 or ETV + 16 weeks after last dose |
| NCT04730349 | study_day: Day | day1 | xcol-002 `Day 1` | no | 1 | not named |  |
| NCT05176314 | study_day: Study Day | day1 | xcol-003 `1` | no, skips −1→1 |  | not named |  |
| NCT05259917 | none (modality, visit) | | | | | |  |
| NCT05324124 | study_day: Study day | day1 | xcol-003 `1` | no, skips −1→1 |  | not named | within 7 to 10 days after last dose |

`xcol` ids and printed values are from each protocol's `*_consolidated.json`; the review page
shows the source page for every column.

## What the corpus says

**1. Where the clock is.** 15 SoAs print a study-day row, 6 a week row, 3 neither — NCT01797120
(epoch, timepoint), NCT02291289 (condition, epoch, other), NCT05259917 (modality, visit). In those
three the schedule has no printed relative time at all.

**2. Day 1 for days, week 0 for weeks.** No day row prints Day 0 as a column. In 9 of the 15 the
header visibly jumps from −1 (or a range ending at −1) to 1; the only 0 on a day row is
NCT04320615's screening range `−2 to 0`, where Day 0 is the last screening day, not the anchor.
Every week-anchored SoA puts its anchor at week 0. NCT04677179, the one SoA printing both
rows, shows the two conventions side by side: the randomisation column is Day 1 with week `—`,
and Week 1 is Day 8.

**3. The anchoring event is often not in the table.** Of the 21 SoAs with a clock:

| Anchor column marks | SoAs |
|---|---|
| randomisation, as a single-mark row | 8 |
| nothing named — Day 1 is a column, with no milestone row | 10 |
| randomisation, printed elsewhere | 2 — NCT01847274 (randomised during screening; Day 1 is Cycle 1 Day 1), NCT03548987 (week 0 is the start of run-in; randomisation at week 20) |
| first dose, as a single-mark row | 1 — NCT04004988 |

So the August finding — the anchor is asserted by the SoA but not by USDM — holds only where a
milestone row exists. In ten SoAs the table does not assert it either, and in two the zero is
something other than randomisation. The event has to come from the protocol text.

**4. Clocks that restart.** Seven day rows restart along the column order: six at cycle boundaries
(NCT04557384 twice), one per crossover period (NCT03421379, Day −1 / Day 1 in each).
In NCT02107703 and NCT04557384 the only day scale is within-cycle, and screening is printed
unsigned — `≤28`, `≤14`, `≤7` — with the direction left to the reader. NCT04004988 instead prints
one set of columns labelled "Periods 1 and 2".

**5. More than one clock.** Eight SoAs print values measured from the end of treatment or the
last dose rather than the anchor — for example `2 Wks Post End of TXP`, `30 (±7) days after last
IMPs admin`, `58 or ETV + 8 weeks after last dose`. NCT03637764 chains a third clock onto that
one (`Every 90 days (±7) after last safety follow-up`). Two SoAs also count hours or minutes
inside a day: NCT04320615 (`0 Pre-dose (−4 hrs)`, `24 hrs (±4 hrs)`, `15 min After end of
infusion`) and NCT03637764 (`EOI +30 min`) — a clock with its own zero at dosing or at end of
infusion.

## What this means for the patterns

An anchor, as printed, is three separate things, and the corpus has all three varying
independently:

- **the unit and its origin** — Day 1 on day rows, week 0 on week rows, never Day 0;
- **the event** — named in 11 of 21 SoAs (randomisation 8 at the anchor, first dose 1, and 2
  where the named event is not the zero), absent in 10;
- **the number of clocks** — one study clock, restarted per cycle or period in 7, joined by an
  end-of-treatment clock in 8 and an hours clock in 2.

A pattern that states only "the anchor" will fit the eight single-clock, randomisation-anchored
SoAs and leave the rest to interpretation. Rules 1 and 2 of the August note are confirmed as
detectors for the first two items; the third needs rules for clocks that restart and for clocks
anchored on the end of treatment, which the August note did not have.

## Limits

- One extraction per protocol, read as printed. Where the extraction typed a header row
  differently (`timepoint` or `other` for a row a reader might call a day row), the survey
  follows the typing.
- The event call is name matching (`randomi[sz]`; dosing / study drug administration, excluding
  schema, training, observe and determine). The table prints the deciding row for every call.
- Unread values are listed by the script, not interpreted: `Cycle n, Day 1`, `FE 1`,
  `29/ET (HD)`, `Screening`, and the sentences some SoAs print in a day cell.
