# Activity grain

`soa2usdm.activity_grain` tags every SoA activity of a study with its **grain**: how many tests the row names, or what else it is. For a named
test it also gives the **kind of finding**. It is the first step towards linking activities to CDISC terms: it selects the rows that name a
test or an instrument, which later steps take further. Most SoA rows are neither and stop here.

The step is a per-study sidecar. It does not change the activity inventory (`activities.json`) or any layer of the pipeline.

## Values

| Field | Values | Set on |
|---|---|---|
| `grain` | named test · panel · instrument list · procedure · instrument · sample collection · other · unsure | every row without a role (instrument list: schema 1.5) |
| `role` | section header · specimen of parent · redacted | structural rows; a row with a role has no grain |
| `finding_kind` | specimen · immunogenicity · measurement · instrument · pc · genomics · unsure | named tests only; `null` otherwise |
| `kind_candidates` | two or more of the kinds above | with `finding_kind` unsure, when the domains or the input narrow the row to those kinds; empty otherwise |

`unsure` means **not resolved yet**. It does not mean "not a finding". In a study graded by rules only, most unsure rows are still open.

### Kinds of finding

The kind names the Findings file of [cdisc-for-ai](https://github.com/kerfors/cdisc-for-ai) that the rule hit points to. It is a coarse pointer:
the domain is decided in a later step, from cited SDTMIG statements, and the kind is used there only where no statement applies. Each kind
rests on a public row of `sdtm-findings-graph/machine_actionable/Domain_Coverage.xlsx`:

| Kind | Domain_Coverage basis |
|---|---|
| specimen | Consumer `Specimen_Findings` (LB, MB, MI, CP, BS, MS, PP) |
| immunogenicity | Consumer `Immunogenicity_Findings` (IS) |
| measurement | Consumer `Measurement_Findings` (VS, EG, MK, CV, RE) |
| instrument | Consumer `Instrument_Findings` (QS, FT, RS) |
| pc | domain PC: in the Specimen_Findings scope, but with no test codes, because the analyte is sponsor-defined |
| genomics | domain GF: excluded from Specimen_Findings, so it has no Consumer |

PC and GF are their own kinds because Domain_Coverage gives PC no test codes and GF no Consumer.

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
| L1p | named test | as L1q, but the parenthesis is the test's own abbreviation: it hits the same code, so nothing is dropped and the hit is not weak for that | NCT05051579 "Luteinizing hormone (LH)" |
| W1, W1g | sample collection | sample words in the head of the label (before "for"); "collection" only together with a SPECTYPE phrase | NCT03489291 "Blood & semen sampling" |
| W2 | procedure | procedure words (biopsy, ECG, MRI …) | NCT03861273 "Electrocardiogram" |
| W3, W4 | other | administrative and record words (consent, dosing, diary; adverse events, history) | NCT03489291 "Informed consent" |
| W-conflict | unsure | word lists that give different grains | NCT03402841 "Archival or fresh tumour biopsy sample …" |
| P1 | panel | panel words (panel, chemistry, serology, markers …) | NCT03489291 "Inflammatory markers IL-1β, IL-2, IL-6, IFNγ, MCP-1" |
| P2 | panel | a list in the label (rules 1.2.0, see "Lists" below): two members with evidence (a test, an instrument or a member that names a panel), or one test hit that is neither peeled nor by short code only; not a history label, not a mixed row | NCT04184622 "Pancreatic amylase, lipase"; NCT03489291 "Vital signs (blood pressure, pulse, body temperature)" |
| P2i | instrument list | a list with two instrument hits and no test (1.2.0) | NCT01847274 "FOSI, EQ-5D-5L, neuropathy questionnaire" |
| L1x | named test, always weak | peel-off, only where no rule above fired: brackets, specimen (SPECTYPE phrases), method (METHOD phrases), lab, condition and activity words are peeled off, and the rest is looked up as a test (see below) | NCT03548935 "Fasting plasma glucose" → GLUC |
| none | unsure | no rule fired | |
| K1 | finding_kind | for L1, L1q, L1a, L1p, L1x: the hit's `SDTM_Domains` through the table above | "Weight" (CV; VS) → measurement |

K1 gives `unsure`, with a flag naming the domains, when the domains point to more than one kind or to a domain with no Consumer. Examples:
"Temperature" (BS, DO, VS) and "Neurological assessment" (NV). When the domains give two or more kinds, those kinds are the row's
`kind_candidates`; the domain step takes them as candidates.

**Short codes.** A test hit made only through a string of three characters or fewer is not taken (L1, L1q, L1a). It stays on the label as
the flag "short code only, not taken: …", and the next rule is tried. Short codes collide with protocol abbreviations: "PK" (pharmacokinetics)
is the code of pyruvate kinase, and "PGI" (Patient Global Impression) that of pepsinogen I. Once the test hit is set aside, "PGI" resolves as an
instrument (L2). The cost is true short codes, such as "TSH", "FSH" and "HIV", which stay unsure until a decision resolves them.

**Peel-off (L1x).** Ordinary tests are often named inside activity wording or qualifiers: "Fasting serum insulin", "Ethanol testing",
"Urine drug screen". L1x tries, in order, the text after "for", the text before "for" (the text after it is then a qualifier, kept as
`after_for`) and the whole text outside brackets. It peels off SPECTYPE and METHOD phrases and the dated lab, condition and activity word
lists, and looks up the rest as a test. What it peeled is kept on the label (`peeled`), so a stated specimen, method or lab stays with
the row. Two guards: an activity word that is part of a test name is kept ("Pregnancy Test", "Drug Screen" and "Neurological Assessment"
hold "test", "screen" and "assessment"); a rest that is a generic word ("clinical", "concentration", "diagnosis" …, `PEEL_GENERIC_REST`)
or a hit only through a short code ("Serum PK") is not taken. An L1x hit is always weak ("peeled"): the rest is not the label.

**Lists (rules 1.2.0).** A label that lists several tests is split into members, recorded on the label (`members`, schema 1.5).
The split is made at commas, "and", "&" and "/" outside parentheses only. A trailing parenthesis that is not a list qualifies the whole
label ("INR, aPTT (select patients)"); a list in a member's parenthesis is a group under that member ("Electrolytes (K, Na, Cl, CO2)": K,
Na, Cl and CO2 have `in_group` the id of "Electrolytes"), also after "includes"; other parentheses of a member are its `qualifiers` ("AFP
(for HCC)", "AST (SGOT)"). A slash whose neighbouring words join to a test is part of the test name and not split ("Urinary
albumin/creatinine" → ALBCREAT, flagged). Each member has an id (`member_id` m01, m02 … in label order, depth-first; with the row's xact_id
it names the member, e.g. xact-013.m05) and a `member_grain`: named test (test lookup on the member, or peel-off, always weak), instrument
(L2), panel (the member names a panel: panel words, or "vital signs", "electrolytes"), or none. A short code is taken as a member, weak
("short code only"): inside a list of tests "K", "Cl" or "CO2" are credible. Named-test members carry their kind (K1). Guards: a list in a
history label ("use": "Substance use (alcohol, caffeine, tobacco use)") is not taken, with a flag; a member without a hit that holds
"exam", "examination" or "check" makes a mixed row ("Physical Exam, Weight, and Vital Signs", "Pregnancy test and contraception check"),
not a panel; one member hit by short code only is not enough ("CT/MRI", "PK, IG …"), nor one peeled hit. P1 keeps the listed members of
a label that names a panel ("Fasting lipid panel (triglycerides, …)"). Members are kept only where P1, P2 or P2i takes the list. A
member without a hit stays on the label, so the gap is visible. Panels named only ("Hematology", "Chemistry") have no members: they
need the protocol's lab appendix.

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

What the rules leave to decide is decided in a file per study, `SoA2USDM/grain/<id>_activity_grain_decisions.json` (schema
`soa2usdm-activity-grain-decisions` 1.3; earlier files stay valid, 1.0 for reviewed decisions only). The generator reads this file and never writes it.

AI proposals are made in three steps per study:

1. **Gather (code).** `python -m soa2usdm.activity_grain_inputs --collection <name> [--protocol <NCTID>]` writes
   `SoA2USDM/grain/<id>_grain_inputs.json` (schema `soa2usdm-activity-grain-inputs` 1.3) from public files only. Its items are the labels
   whose rule result leaves something to decide and that have a row without a role: **grain unsure** (no grain), **kind unsure** (a named
   test without a single kind from K1), **sample collection** (a finding may be named in it) and **procedure by word list** (procedure from
   W2 or a weak hit, not from a strong L3 METHOD phrase; a measure may be named in it, as in "ALLO-501A in BM aspirate") and **peeled
   test** (1.3: a named test from L1x only; a footnote or the protocol may show a panel or another test). Per item:
   spellings, rows and parents, the rule result, the SoA annotations bound to its rows or their parents, the protocol context
   `lab_and_purpose` entries for the label, and the abbreviations in the label. Per study: the context categories with no link to an SoA row
   (product, immunogenicity, endpoint assays, genetic testing). CDISC: every Domain_Coverage row with the kind it gives, and the test rows
   the rules hit. Every context entry carries its JSON Pointer. The file has no generation time: the same inputs give the same file. It
   needs the study's protocol context. `content_sha256` (1.2) is the sha256 of what the prompt decides from (collection, protocol_id,
   items, study, cdisc) as canonical JSON; it leaves out `sources`, the recorded versions.
2. **Propose (prompt).** A Claude session runs [`prompts/ACTIVITY_GRAIN_DECISIONS_PROMPT.md`](../prompts/ACTIVITY_GRAIN_DECISIONS_PROMPT.md)
   on that one file and writes the decisions file: one decision per item, nothing else.
3. **Check (generator).** `python -m soa2usdm.activity_grain` checks the decisions (below) and writes the grain file.

A person then reviews the decisions per study.

- `source: ai_proposed` is allowed only on a phrase the study's current grain inputs file lists, and must carry `prompt_version` and
  `inputs_content_sha256` (1.3: the inputs file's `content_sha256`). Decisions in 1.1 / 1.2 files carry `inputs_sha256` (the sha256 of the
  whole inputs file) instead; it is checked when `inputs_content_sha256` is absent, and kept as a record when it is added
  (`tools/grain_decisions_record_content_sha.py`). A new cdisc-for-ai commit that changes nothing the prompt reads therefore needs a
  new gathering, not a new prompt run. `source: reviewed` is allowed on any label, and can set the kind of a rule-hit named test.
- **Carry-over (decisions 1.4).** A grain rules change can change the inputs content while most items stay as they were.
  `tools/grain_decisions_carry_over.py --collection <name> [--protocol <NCTID>]` keeps an ai_proposed decision whose item is unchanged:
  its `inputs_content_sha256` becomes the new one and `carried_over_from` keeps the one it was made from; the decision is not changed.
  A decision whose phrase is no longer an item (the rules now give the label a grain with nothing to decide) is removed and recorded in
  `carry_overs[].dropped` with the rule result. The tool stops and writes nothing when a decision was not made from the inputs file on
  disk, when an item changed, when the study block or the cdisc domains changed, or when the new inputs hold a cdisc test row the old did
  not: those need the prompt. It runs before the inputs are gathered again; it writes the decisions file and then the new inputs file.
  The grain page marks a carried decision "AI proposal (carried over)".
- `finding_kind` is present exactly when the decided grain is named test.
- `basis` lists what the decision rests on:
  - `{"type": "label"}` — the label text;
  - `{"type": "annotation", "xannot_id": …}` — a footnote or other SoA annotation in the study's `consolidated.json`;
  - `{"type": "context", "pointer": "/immunogenicity/3"}` — an entry of the study's protocol context file (JSON Pointer);
  - `{"type": "page", "page": n}` — a protocol page, used only when no context entry holds the fact;
  - `{"type": "cdisc", "file": …, …}` (1.1) — a row of a public cdisc-for-ai file at the commit the grain file records:
    `{"file": "Domain_Coverage", "domain": "IS"}`, `{"file": "SDTM_Test_Identity", "code": "C181400", "testcd": "CYKSCCL"}` (also
    `SDTM_Instrument_Identity`), `{"file": "Codelist_Phrases", "codelist": "SPECTYPE", "code": "C13325"}`.
- **Kind rule:** an `ai_proposed` named test with a kind other than `unsure` cites at least one `cdisc` entry whose domain gives that kind
  (rule K1 for one domain: PC → pc, GF → genomics, otherwise the Domain_Coverage Consumer).
- **Kind candidates (1.2):** when the input narrows a named test to two or more kinds without settling one, the kind is `unsure` and
  `kind_candidates` lists them; each candidate rests on a cited `cdisc` entry giving it. The FIX inhibitor rows are an example: IS or LB.
- The rule result stays on the label beside the decision.

**The generator stops** on any of these:
- a phrase that is no longer in the study;
- `ai_proposed` on a phrase the grain inputs file does not list, in a 1.0 file, without `prompt_version`, without
  `inputs_content_sha256` in a 1.3 file, with an `inputs_content_sha256` that is not the current `content_sha256`, or (without it) with an
  `inputs_sha256` that is not the current inputs file's;
- a grain inputs file whose content differs from the inputs rebuilt from the study's files now (rerun the gathering, then the prompt);
- a grain inputs file whose content is the same but whose recorded versions differ (rerun the gathering; the decisions stay valid);
- a `cdisc` entry whose domain, code, TESTCD or codelist term is not as published;
- an `ai_proposed` kind that no cited `cdisc` entry gives;
- `kind_candidates` outside a 1.2 file, without `finding_kind` unsure, with fewer than two kinds, or with a kind no cited `cdisc` entry gives;
- two decisions for one phrase;
- a missing or misplaced `finding_kind`;
- an empty basis, or a basis entry of unknown shape;
- an `xannot_id` that is not in `consolidated.json`;
- a pointer that does not resolve;
- a page outside the context file's `pages_covered`;
- a context or page basis without a context file;
- a `protocol_context` record (sha256, prompt version) that differs from the current context file. After the context is extracted again, check
  the decisions against it, then update the record.

**What the checks prove:** that a cited entry, annotation, page or cdisc row exists and is as published, and that a kind rests on a cited
domain. They do not prove that it supports the decision. A person reviews that.

AI proposals rest on public material only, and only on what the grain inputs file holds. Where that material does not settle the kind, the
kind stays `unsure`, and the rationale says what is open (for example, vector-DNA shedding by PCR: PC, MB or GF).

## After the grain

Activities and tests are linked as the protocol documents them: each named test or instrument gets the CDISC terms the protocol supports,
as specifically as the protocol states them, and no more. The steps after the grain are the domain (from cited SDTMIG v3.4 statements), the
test with its target and the facets the protocol states (specimen, method, condition), and an optional COSMoS pointer where exactly one BC
or DSS applies. The domain step is in this repository: [activity-routing.md](activity-routing.md). The others are not in
this repository yet. Panels whose label lists their members are split (rules 1.2.0, "Lists" above) and routed per member; panels
named only wait for the protocol's lab appendix.

## Files

```
{NCTID}/SoA2USDM/grain/
├── {NCTID}_activity_grain.json             # generated (schema soa2usdm-activity-grain 1.5)
├── {NCTID}_grain_inputs.json               # gathered for the decisions prompt (where AI proposals are made)
└── {NCTID}_activity_grain_decisions.json   # from the prompt and reviews, where decisions exist
```

`<id>_activity_grain.json` holds:
- `inputs`: the sha256 of the study's inventory rows (canonical JSON), of `consolidated.json`, of the protocol context file, of the
  decisions file and of the grain inputs file, plus the cdisc-for-ai provenance;
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
study's row on the index. The index column "Activity grain" links the page and the JSON, with the study's named tests and unsure rows
counted. On the Activities page, the Grain and Kind columns (for searching across studies) link each row to its row on the grain page. Before any page is rendered, the index and the Activities page
check each grain file against its inputs, and **stop on a stale file** with the command to rerun. Notebook: `notebooks/02_activity_grain.ipynb`.

## Status

Status on 2026-11-06, grain rules 1.2.0 (lists), with cdisc-for-ai `a7d5821` (SDTM CT 2026-09-25):

| Collection | Studies | Rows with a grain | named test | panel | instrument list | unsure | Decisions |
|---|---|---|---|---|---|---|---|
| cell_gene_therapy | 5 | 229 | 61 | 57 | 0 | 7 | AI proposals (143: 63 prompt 1.2.0, 80 prompt 1.5.0 for NCT04323098 and NCT05714345 since 2026-11-06; not reviewed; NCT05714345 carried over to rules 1.2.0, decisions schema 1.4, one decision dropped) |
| usdm_data | 22 | 811 | 93 | 83 | 2 | 302 | rules only |
| cpmp | 13 | 303 | 40 | 52 | 0 | 94 | rules only |
| misc_studies | 2 | 82 | 17 | 14 | 0 | 25 | rules only |

AI proposals for the rules-only collections wait for their protocol context.
