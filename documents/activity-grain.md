# Activity grain

`soa2usdm.activity_grain` tags every SoA activity of a study with its **grain**: how many tests the row names, or what else it is. For a named
test it also gives the **kind of finding**. This is the cheap first cut towards matching activities to CDISC. It decides which rows go to a
later, per-row mapping step and routes each one there. Most SoA rows are not findings and only need to be routed out.

The step is a per-study sidecar. It does not change the activity inventory (`activities.json`) or any layer of the pipeline.

## Values

| Field | Values | Set on |
|---|---|---|
| `grain` | named test · panel · procedure · instrument · sample collection · other · unsure | every row without a role |
| `role` | section header · specimen of parent · redacted | structural rows; a row with a role has no grain |
| `finding_kind` | specimen · immunogenicity · measurement · instrument · pc · genomics · unsure | named tests only; `null` otherwise |

`unsure` means **not resolved yet**. It does not mean "not a finding". In a study graded by rules only, most unsure rows are still open.

### Kinds of finding

The kind picks the Findings file of [cdisc-for-ai](https://github.com/kerfors/cdisc-for-ai) that a later step reads candidate tests from. Each kind
rests on a public row of `sdtm-findings-graph/machine_actionable/Domain_Coverage.xlsx`:

| Kind | Domain_Coverage basis |
|---|---|
| specimen | Consumer `Specimen_Findings` (LB, MB, MI, CP, BS, MS, PP) |
| immunogenicity | Consumer `Immunogenicity_Findings` (IS) |
| measurement | Consumer `Measurement_Findings` (VS, EG, MK, CV, RE) |
| instrument | Consumer `Instrument_Findings` (QS, FT, RS) |
| pc | domain PC: in the Specimen_Findings scope, but with no test codes, because the analyte is sponsor-defined |
| genomics | domain GF: excluded from Specimen_Findings, so it has no Consumer |

PC and GF are their own kinds because what a later step needs for them differs from the rest of Specimen.

## Rules

The rules are the same for every study. They run once per distinct label of the study (the normalised phrase), in this order; the first that
fires wins. Every row cites the rule that fired and every lookup hit it used. Examples are real rows from the collections.

| Rule | Gives | What fires it | Example |
|---|---|---|---|
| S1 | role redacted | `is_redacted` in the inventory | NCT03489291 "CCI" |
| S2 | role section header | `is_section_header` | NCT03489291 "Local Laboratory" |
| S3 | role specimen of parent | the parent row (consolidated `parent_xact_id`) is a sample collection, and the row is a SPECTYPE phrase | NCT03489291 "Blood" under "Sampling for vector genome detection:" |
| L1 | named test | whole label = a test in SDTM_Test_Identity (TESTCD, TEST, NCIt preferred term or synonym); not when the hit is only through a code of three characters or fewer (see below) | NCT03489291 "Height" |
| L2 | instrument | whole label = an instrument in SDTM_Instrument_Identity, or a QSCAT phrase | NCT04323098 "EQ-5D-5L" |
| L3 | procedure | whole label = a METHOD phrase (Codelist_Phrases) | NCT03489291 "Physical examination" |
| L4 | sample collection | whole label = a SPECTYPE phrase | NCT01847274 "Tumor sample" |
| L4F | sample collection | a SPECTYPE phrase followed by "for" | NCT04323098 "Serum for exploratory biomarkers" |
| L1q–L4q | as L1–L4, always weak | the same, with trailing parentheses removed | NCT05714345 "Gene expression profile (blood RNA)" |
| L1a, L2a | named test, instrument | a one-item parenthesis alone; not through a short code only, such as "(CL)" for central laboratory | NCT04677179 "Inflammatory Bowel Disease Questionnaire (IBDQ)" |
| W1, W1g | sample collection | sample words in the head of the label (before "for"); "collection" only together with a SPECTYPE phrase | NCT03489291 "Blood & semen sampling" |
| W2 | procedure | procedure words (biopsy, ECG, MRI …) | NCT03861273 "Electrocardiogram" |
| W3, W4 | other | administrative and record words (consent, dosing, diary; adverse events, history) | NCT03489291 "Informed consent" |
| W-conflict | unsure | word lists that give different grains | NCT03402841 "Archival or fresh tumour biopsy sample …" |
| P1 | panel | panel words (panel, chemistry, serology, markers …) | NCT03489291 "Inflammatory markers IL-1β, IL-2, IL-6, IFNγ, MCP-1" |
| P2 | panel | a list in the label or in a parenthesis with at least two members that hit a test | NCT03489291 "Vital signs (blood pressure, pulse, body temperature)" |
| none | unsure | no rule fired | |
| K1 | finding_kind | for L1, L1q, L1a: the hit's `SDTM_Domains` through the table above | "Weight" (CV; VS) → measurement |

K1 gives `unsure`, with a flag naming the domains, when the domains point to more than one kind or to a domain with no Consumer. Examples:
"Temperature" (BS, DO, VS) and "Neurological assessment" (NV).

**Short codes.** A test hit made only through a string of three characters or fewer is not taken (L1, L1q, L1a). It stays on the label as
the flag "short code only, not taken: …", and the next rule is tried. Short codes collide with protocol abbreviations: "PK" (pharmacokinetics)
is the code of pyruvate kinase, and "PGI" (Patient Global Impression) that of pepsinogen I. Once the test hit is set aside, "PGI" resolves as an
instrument (L2). The cost is true short codes, such as "TSH", "FSH" and "HIV", which stay unsure until a decision resolves them.

The word lists are dated (`word_lists_date`) and kept small. The step does not tune them further: named tests that are specific to a product
or an assay are not in CT, and no word list finds them.

**Hit strength.** A hit is *strong* when all of these hold: one code; matched on a CT-published field; on the whole phrase; not only through a
string of three characters or fewer. Otherwise it is *weak*, and `weak_reasons` says why ("qualifier dropped", "NCIt synonym only",
"several codes", "short code only", "phrase names several terms in codelist"). Dropping a qualifier can change the test: "Bilirubin (direct)"
reaches BILI only by dropping "direct", so the hit is weak.

**Normalisation** is the Codelist_Phrases rule: lower case, split on anything that is not a letter or a digit, parts joined by one space. No
plural forms or stemming.

## Lookups and provenance

The lookups are public cdisc-for-ai files only: SDTM_Test_Identity, SDTM_Instrument_Identity, Codelist_Phrases (QSCAT, METHOD, SPECTYPE)
and Domain_Coverage. cdisc-for-ai is found as a sibling checkout, or through `SOA2USDM_CDISC_FOR_AI`. The run stops when the lookup files
have uncommitted changes. The output records the cdisc-for-ai commit, `Reference_Versions.json`, and per file its sha256, sheet content hash
and source versions.

## Decisions (AI proposals and reviews)

Labels the rules leave unsure can be decided in a hand-kept file per study, `SoA2USDM/grain/<id>_activity_grain_decisions.json` (schema
`soa2usdm-activity-grain-decisions` 1.0). The generator reads this file and never writes it.

- `source: ai_proposed` is allowed only on a label the rules left unsure. `source: reviewed` is allowed on any label, and can set the kind of a
  rule-hit named test.
- `finding_kind` is present exactly when the decided grain is named test.
- `basis` lists what the decision rests on:
  - `{"type": "label"}` — the label text;
  - `{"type": "annotation", "xannot_id": …}` — a footnote or other SoA annotation in the study's `consolidated.json`;
  - `{"type": "context", "pointer": "/immunogenicity/3"}` — an entry of the study's protocol context file (JSON Pointer);
  - `{"type": "page", "page": n}` — a protocol page, used only when no context entry holds the fact.
- The rule result stays on the label beside the decision.

**The generator stops** on any of these:
- a phrase that is no longer in the study;
- `ai_proposed` on a label the rules resolved;
- two decisions for one phrase;
- a missing or misplaced `finding_kind`;
- an empty basis, or a basis entry of unknown shape;
- an `xannot_id` that is not in `consolidated.json`;
- a pointer that does not resolve;
- a page outside the context file's `pages_covered`;
- a context or page basis without a context file;
- a `protocol_context` record (sha256, prompt version) that differs from the current context file. After the context is extracted again, check
  the decisions against it, then update the record.

**What the checks prove:** that a cited entry, annotation or page exists. They do not prove that it supports the decision. A person reviews that.

AI proposals rest on public material only: the label, the SoA annotations, the published protocol context, and the public cdisc-for-ai
files. Where that material does not settle the kind, the kind stays `unsure`, and the rationale says what is open (for example, vector-DNA
shedding by PCR: PC, MB or GF).

## Files

```
{NCTID}/SoA2USDM/grain/
├── {NCTID}_activity_grain.json             # generated (schema soa2usdm-activity-grain 1.0)
└── {NCTID}_activity_grain_decisions.json   # hand-kept, where decisions exist
```

`<id>_activity_grain.json` holds:
- `inputs`: the sha256 of the study's inventory rows (canonical JSON), of `consolidated.json`, of the protocol context file and of the
  decisions file, plus the cdisc-for-ai provenance;
- `counts`: by grain, by kind and by role, each with and without decisions;
- `labels[]`: one per distinct phrase, with the rule result, hits, flags and any decision;
- `activities[]`: one per inventory row, with grain, kind, role, rule, source, the section header it sits under, and its parent.

## Running it

```
pip install -e '.[grain]'
python -m soa2usdm.activity_grain --collection cell_gene_therapy                # every study
python -m soa2usdm.activity_grain --collection cell_gene_therapy --protocol NCT03489291
```

The step reads the study's rows as the inventory builds them (`activity_inventory.collect_rows`), so it runs after consolidation, before the
collection pages are built. The collection index renders a page per study, `SoA2USDM/grain/<id>_activity_grain.html`
(`soa2usdm.activity_grain_page`). The page shows counts, then every activity with its grain, kind, rule and evidence, and each decision with
its basis resolved. It carries the shared navigation: "activity grain" in the strip of every protocol page, and the breadcrumb back to the
study's row on the index. The index column "Activity grain" links the page, the JSON, and the study on the Activities page. On the Activities
page, the Grain and Kind columns link each row to its row on the grain page. Before any page is rendered, the index and the Activities page
check each grain file against its inputs, and **stop on a stale file** with the command to rerun. Notebook: `notebooks/02_activity_grain.ipynb`.

## Status

Status on 2026-11-02, with cdisc-for-ai `75ef8dd` (SDTM CT 2026-09-25):

| Collection | Studies | Rows with a grain | named test | unsure | Decisions |
|---|---|---|---|---|---|
| cell_gene_therapy | 5 | 229 | 50 | 11 | AI proposals (89, not reviewed) |
| usdm_data | 22 | 811 | 70 | 337 | rules only |
| cpmp | 13 | 303 | 27 | 107 | rules only |
| misc_studies | 2 | 82 | 16 | 25 | rules only |

AI proposals for the rules-only collections wait for their protocol context.
