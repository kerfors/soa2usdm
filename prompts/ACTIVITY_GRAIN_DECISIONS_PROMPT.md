# Activity grain decisions — grain and kind for what the rules leave to decide

Prompt version: 1.4.0 · Input schema: `soa2usdm-activity-grain-inputs` 1.2 · Output schema: `soa2usdm-activity-grain-decisions` 1.3

You decide the grain of SoA activities of ONE study and, for a named test, the kind of finding. The grain rules of
`soa2usdm.activity_grain` have already run; you decide only the labels they left to decide. Every decision cites what it rests on, and
the generator checks every citation. Background: `documents/activity-grain.md`.

## Input

ONE file: `SoA2USDM/grain/{NCTID}_grain_inputs.json`, gathered by code (`python -m soa2usdm.activity_grain_inputs`). Use this file and
nothing else: not the protocol PDF, not other files of the repositories, not CDISC material from memory or from the web.

- `items[]` — the labels to decide, one per `phrase`:
  - `item_type`: `grain unsure` (the rules give no grain), `kind unsure` (the rules give a named test but no single kind),
    `sample collection` (the rules give sample collection; a finding may be named in it), `procedure by word list` (the rules give
    procedure from a word such as biopsy, aspirate or ECG, or from a weak hit; a measure may be named in it);
  - `spellings`, `rows` (xact_id, parent, whether the parent is a section header);
  - `rule`: the rule result (rule_id, lookup hits, qualifiers, list members, flags, kind domains);
  - `annotations`: SoA footnotes bound to the rows (`via: row`) or to their parent (`via: parent`), with `xannot_id`;
  - `lab_and_purpose`, `abbreviations`: protocol context entries for this label, each with its `pointer`.
- `study`: protocol context entries with no link to an SoA row (product, immunogenicity, endpoint_assays, genetic_testing), each with its
  `pointer`. An entry applies to an item only when its own wording matches the item (same analyte, assay, target or specimen); say which
  words match in the rationale.
- `cdisc.domains[]`: every Domain_Coverage row with the `kind` it gives (`null` = no kind). `cdisc.tests[]`: test rows the rules hit.

## Grain values

| Grain | The row … |
|---|---|
| named test | names one test or assay result (one analyte, one measure, one assay readout), whatever the specimen or method |
| panel | names several tests under one label (a lab panel, a list of analytes, "vital signs") |
| procedure | names a procedure or examination whose results are not one named test (biopsy, imaging, ECG, physical examination) |
| instrument | names a questionnaire, rating scale or other instrument |
| sample collection | names a specimen taken or stored without naming what is measured in it (spare plasma, banked serum, PBMC collection) |
| other | is not an assessment: consent, eligibility, dosing, dispensing, contact, adverse events, medications, history |
| unsure | cannot be decided from the input; the rationale says what is open |

## Kinds of finding (named test only)

`specimen` · `immunogenicity` · `measurement` · `instrument` · `pc` · `genomics` · `unsure`. A kind is the `kind` of a Domain_Coverage row
in `cdisc.domains`. Decide the kind from the domains of the cited test row or Domain_Coverage row. Where the input leaves the domain to an
SDTMIG statement or a protocol fact, the kind is `unsure` with `kind_candidates`. Example: a drug concentration → PC (kind pc).

## Rules

1. **One decision per item, nothing else.** Every `phrase` in `items[]` gets exactly one decision; no decision for any other phrase.
2. **Per item type.**
   - `grain unsure`: decide the grain; give a kind if it is a named test.
   - `sample collection`: keep `sample collection` unless the label, a footnote or a cited context entry names what is measured. Then decide
     `named test` (one test) or `panel` (several), and say in the rationale which words name it.
   - `kind unsure`: decide the kind from the domains in `rule.kind_domains` and the cited facts, or keep `unsure`.
   - `procedure by word list`: keep `procedure` unless the label, a footnote or a cited context entry names what is measured in the
     material or images the procedure yields ("ALLO-501A in BM aspirate": the measure is ALLO-501A, the aspirate is where it is measured).
     Then decide `named test` (one measure) or `panel` (several), and say in the rationale which words name it.
3. **Kind rule.** A named test with a kind other than `unsure` cites at least one cdisc entry whose domain gives that kind: the
   Domain_Coverage row (`{"type": "cdisc", "file": "Domain_Coverage", "domain": "IS"}`), or a test row from `cdisc.tests`
   (`{"type": "cdisc", "file": "SDTM_Test_Identity", "code": "…", "testcd": "…"}`, copied exactly). Give one kind only when the input
   settles one domain. If it narrows the row to two or more kinds, the kind is `unsure` and `kind_candidates` lists those kinds, each
   given by a cited cdisc entry (for example IS and LB → `["immunogenicity", "specimen"]`). If it does not narrow the kind at all, the
   kind is `unsure` without `kind_candidates`.
4. **Unsure stays unsure.** Where the input does not settle the grain or the kind, the value is `unsure`, and the rationale names what is open
   (for example: "PC or MB: vector DNA by PCR, the input does not say which").
5. **Basis.** Every decision cites `{"type": "label"}` and every other entry it rests on: `{"type": "annotation", "xannot_id": "…"}`,
   `{"type": "context", "pointer": "…"}` (pointers exactly as given in the input), cdisc entries as in rule 3. No `page` entries.
6. **Rationale.** One or two sentences of facts from the input. No test codes or terms that are not in the cited cdisc entries. Do not
   name a TESTCD for the row: test identity is a later step.
7. **Abbreviations.** Read a short form only with the meaning its `abbreviations` entry gives (cite it). A short form without an entry is not
   expanded.
8. **Parentheses** are qualifiers (specimen, method, lab, arm, population) unless they list members of a panel; "(CL)" and "(LL)" are lab
   sites where an abbreviation entry says so.

## Output — one JSON file `SoA2USDM/grain/{NCTID}_activity_grain_decisions.json`

```json
{
  "schema_name": "soa2usdm-activity-grain-decisions",
  "schema_version": "1.3",
  "protocol_id": "{NCTID}",
  "protocol_context": {"sha256": "<sources.protocol_context.sha256>", "prompt_version": "<sources.protocol_context.prompt_version>"},
  "decisions": [
    {
      "phrase": "<items[].phrase, exactly>",
      "grain": "named test",
      "finding_kind": "immunogenicity",
      "source": "ai_proposed",
      "rationale": "…",
      "basis": [{"type": "label"}, {"type": "context", "pointer": "/immunogenicity/0"},
                {"type": "cdisc", "file": "Domain_Coverage", "domain": "IS"}],
      "proposed_by": "<model id>",
      "proposed_at": "YYYY-MM-DD",
      "prompt_version": "1.4.0",
      "inputs_content_sha256": "<content_sha256 of the inputs file, copied>"
    }
  ]
}
```

- `finding_kind` is present exactly when `grain` is `named test`.
- `kind_candidates` (two or more kinds, sorted) only together with `"finding_kind": "unsure"`, and only when the input narrows the kind.
- `decisions` sorted by `phrase`.
- `inputs_content_sha256` is the input's `content_sha256`, copied; `protocol_context` is copied from the input's `sources`.

## After writing

Run `python -m soa2usdm.activity_grain --collection <name> --protocol {NCTID}`. It stops on any decision that does not check out; fix the
decision, never the input. Report per study: decisions by grain, named tests by kind, and every `unsure` with its candidates and open question.
