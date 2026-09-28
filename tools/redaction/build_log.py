"""One-off: writes REDACTIONS.json. Kept beside the log so the entries' provenance is readable."""
import json

PROMPT = "prompts/PDF_TO_JSON_PROMPT.md"
TAX = "documents/soa_table_type_definitions.md"

E = []


def add(id_, tier, file, find, replace, why):
    E.append({"id": id_, "tier": tier, "file": file, "find": find, "replace": replace, "why": why})


add("P1", "A", PROMPT,
    "On NCT04677179, 20 of 30 SoA pages are like this and only one page has a vector\ntable.",
    "In one protocol of an earlier run, most SoA pages were like this and only one page had a vector\ntable.",
    "names study; gives its raster page count")
add("P2", "A", PROMPT,
    "on NCT03637764 it caught 4 merged-span errors the Excel-verified extraction had missed",
    "in an earlier run it caught merged-span errors that an Excel-verified extraction had missed",
    "names study; gives its merged-span error count")
add("P3", "A", PROMPT,
    "on NCT04677179 this nearly dropped a CCI row that carries three marks",
    "in an earlier run this nearly dropped a row with a redacted cell that carries marks",
    "names study; gives a row and its mark count")
add("P4", "A", PROMPT,
    "on NCT04677179 the whole first body page of Table 4 was missed, taking 14 activities and\n  26 marks with it,",
    "in an earlier run a whole body page of one table was missed, taking its activities and\n  marks with it,",
    "names study/table; gives the restoration counts (a checklist invariant)")
add("P5a", "A", PROMPT,
    "(e.g. V10–V19 in one spread, V20–V29 in a \"(continued)\" spread)",
    "(e.g. the first block of visits in one spread, the next block in a \"(continued)\" spread)",
    "NCT04677179's actual tiling visit ranges")
add("P5b", "A", PROMPT,
    "(e.g. an explicit \"Not applicable during V10–V19\" note)",
    "(e.g. an explicit note that the row does not apply to that tile's visits)",
    "NCT04677179's actual visit range")
add("P6", "A", PROMPT,
    "(e.g. the Main Study table)",
    "(e.g. the primary schedule table)",
    "'Main Study' is NCT01847274's table title; points at its undefined-marker answer")
add("P7", "A", PROMPT,
    "on NCT04677179 T1 the serum-pregnancy and urine-pregnancy notes are a genuine pair, printed that way on doc pp.20 and 21",
    "in an earlier run two notes for related tests were a genuine pair, printed that way on consecutive pages",
    "names study/table; gives the containment verdict the gate re-asks")
add("P8", "B", PROMPT,
    "e.g. \"Prediabetes\", \"Cohort 1\", \"Continued Access\", \"Extension (nonresponders)\", \"Early Termination / Unscheduled / Post-Treatment\"",
    "e.g. \"Cohort <n>\", \"Part <X>\", \"<sub-population>\", \"<phase> (<population>)\"",
    "4 of 5 are verbatim accepted track_labels (NCT04184622, NCT02291289, NCT04557384, NCT04677179)")
add("P9", "B", PROMPT,
    "(e.g. \"Patients who have PD …\" spanning only some columns)",
    "(e.g. \"Participants who meet <criterion> …\" spanning only some columns)",
    "verbatim condition band of NCT02291289 T1")
add("P10", "B", PROMPT,
    "a Protocol Reference column, a Procedure Category column, or the narrow column carrying the header rows' own labels (\"VISIT\", \"WEEK\")",
    "a cross-reference column, a category column, or the narrow column carrying the header rows' own labels",
    "the label-column answers for NCT02107703 (L=3) and CDISC_Pilot (L=2)")
add("P11", "B", PROMPT,
    "\"X (Cycle 5 only)\", \"X (Day 3-5)\"",
    "\"X (Cycle n only)\", \"X (Day n–m)\"",
    "verbatim qualified marks of NCT04730349 T2")
add("P12", "B", PROMPT,
    "\"Inclusion criteria (6.1)\", \"HbA1c (Appendix 2)\", \"Trial product compliance (7.1) (7.6)\"",
    "\"<activity> (x.y)\", \"<lab test> (Appendix n)\", \"<activity> (x.y) (x.z)\"",
    "verbatim inline-reference labels of the three Novo T1s")
add("P13", "B", PROMPT,
    "\"V2ᵃ\", \"ETVᵇ\", \"V997ᶜ\"",
    "\"V2ᵃ\", \"V5ᵇ\", \"V9ᶜ\"",
    "ETV and V997 occur only in NCT04677179")
add("P14a", "B", PROMPT,
    "e.g. \"See Section 8.2.2.\", \"See Appendix 8.\"",
    "e.g. \"See Section x.y.z.\", \"See Appendix n.\"",
    "verbatim annotations of NCT04677179/NCT03637764 and NCT02291289 (the gate 5a cases)")
add("P14b", "B", PROMPT,
    "(\"See Appendix 2 for details. Day 1 predose sample is for baseline only.\")",
    "(\"See Appendix n for details. <one sentence of instruction>.\")",
    "verbatim annotation of NCT04004988 T1")
add("T1", "A", TAX,
    "*Amgen protocol with Table 1a (Non-lab), Table 1b (Lab), Table 1c (PK) - all sharing 20 columns but grouping different assessment types.*",
    "*A protocol with separate Non-laboratory, Laboratory and PK tables - all sharing the same columns but grouping different assessment types.*",
    "sponsor identifies NCT03283098; gives its table types and column count")
add("T2", "A", TAX,
    "*Example: Alexion Table 2 showing hour-by-hour PK/PD sampling times (columns: -0.5h, 0h, 1h, 2h, 4h...) for specific study days referenced in Table 1.*",
    "*Example: a table showing hour-by-hour PK/PD sampling times (columns such as pre-dose, 0h, 1h, 2h...) for specific study days referenced in the main SoA.*",
    "sponsor identifies NCT04573309; gives its T2 classification")
add("T3", "A", TAX,
    "*NCT04184622 Section 1.3.2 - an additional 2-year treatment schedule only for participants with prediabetes at randomization, with its own visit numbering (101-199) and timing.*",
    "*An additional treatment schedule only for a sub-population identified at randomization, with its own visit numbering and timing.*",
    "names study; gives its track, population and visit numbering")
add("T4", "A", TAX,
    "*NCT04677179 Tables 2 and 3 - Maintenance (responders at Week 12) and Extension (non-responders at Week 12). Their visit labels, weeks and study days are numerically identical (V10-V29), but the two schedules apply to mutually exclusive populations, so each is its own track.*",
    "*Two tables whose visit labels, weeks and study days are numerically identical, but which schedule mutually exclusive populations (e.g. responders vs non-responders at an interim assessment), so each is its own track.*",
    "names study/tables; gives their classification and visit range")
add("T5", "B", TAX,
    "*Continued Access schedules with distinct",
    "*Post-study access schedules with distinct",
    "'Continued Access' is NCT04557384 T2's accepted track_label")

log = {"note": "Sweep 2 redaction log. Apply with apply_redactions.py after EVERY prompt/taxonomy edit. "
               "Must never enter the blind tree.",
       "prompt_version": "3.9.3", "taxonomy_version": "v8",
       "copied_unchanged": ["schemas/soa-table-extraction.schema.json"],
       "tier_c_kept": ["P = predose (§5)", "Fasting / Telephone-visit bands (§1b)", "Sample 1, Sample 2 (§2, taxonomy)",
                       "See instructions (§5)", "responders vs non-responders (prompt §2, taxonomy)"],
       "entries": E}
with open("REDACTIONS.json", "w", encoding="utf-8") as f:
    json.dump(log, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(len(E), "entries")
