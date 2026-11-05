# Activity routing

`soa2usdm.activity_routing` gives each named test of a study a target SDTMIG v3.4 domain, or the candidate domains and the
question that stays open. It is the step after the [activity grain](activity-grain.md): the grain selects the rows that name a
test, routing says where such a test belongs. Each result cites the rule that fired, where it matched, and the SDTMIG v3.4
statements it rests on, or, where no rule fires, the SDTM test code of the activity label.

The step is a per-study sidecar. It does not change the grain file, the activity inventory or any layer of the pipeline.

## Rows

| Rows | Treatment |
|---|---|
| grain `named test`, not a parent | routed (one result per row) |
| grain `panel` | not reached: panels are not split yet |
| grain `named test` that is a parent | not reached: the children carry the tests |
| every other grain, and rows with a role | not part of the step |

## Sources and status

A rule is matched against three sources: the activity label, the parent activity label, and the SoA annotations (footnotes)
that reference the row or its parent. Only the activity label can route a row on its own. Parent label and annotations can
support a label match or add candidates, but a result resting on them alone stays open or weak. A footnote often names other
tests than the row's own, so it never decides alone.

| Status | Meaning |
|---|---|
| routed | one domain; matched in the activity label; no condition; no question |
| open | candidate domains, and the question the protocol (or CDISC) must settle |
| weak | matched only in SoA annotations: the rule domains are kept as hints; the candidates come from the grain kind |
| not routed | no rule fired: the candidates come from the grain kind through `Domain_Coverage` |

A condition on a statement is our reading of what the protocol must settle before the statement applies. Code never decides
a condition: a condition makes the result open, with the condition as the question.

## Test identity

Where no rule fires, the SDTM test codes the grain found for the activity label are a second source: the grain's
`SDTM_Test_Identity` hits (TESTCD, TEST, NCIt preferred term or synonym), with the domains the test code is published for.
Only the row's own label is used, as for the rules.

| Test identity hit | Result |
|---|---|
| strong, one domain | routed, `route_source` "test identity" (e.g. "HbA1c" → HBA1C → LB) |
| strong, several domains | open: those domains are the candidates; the question names the test code (e.g. "Weight" → WEIGHT → CV, VS) |
| weak (NCIt synonym only, qualifier dropped, several codes …) | not routed: the domains are hints; the candidates come from the grain kind |

A rule always ranks above the test identity. Where a rule fired, the hits are recorded and change nothing: "PK (Glucagon)"
is routed to PC by RT-9, although GLUCAGON is an LB test code. A weak hit never routes: "Pregnancy test" reaches HCG only
through an NCIt synonym, and "eGFR (CKD-EPI)" also hits EGFR, an MI test code. A strong hit routes also to a domain the
grain kind has no fallback for (RP "Childbearing potential", SS "Survival Status"): the domain is where the test code is
published.

The hits come from the grain file, which is an input of the routing file (sha256) and is made at the same cdisc-for-ai
commit, so no other lookup is read.

The fallback (weak, not routed) maps the grain kind back to domains through the public `Domain_Coverage` file (the reverse of
grain rule K1). PP is left out: PP holds parameters derived from PC data (PP-OV) and is a derived dataset (PP-A1).

## Rules

The rules are ours: the patterns and the reading. The statements are CDISC's, from the public cdisc-for-ai file
`sdtm-domain-reference/machine_actionable/SDTMIG_Statements.xlsx` (rows selected as `routing`), cited by Statement_ID and the
sha256 of their text. The routing file quotes each cited statement once, so the page and a reader need no other file.

| Rule | Name | Patterns (case-insensitive) | Statements → domain | Condition |
|---|---|---|---|---|
| RT-1 | antibody test | antibody, nAb, TAb, BAb, ADA, factor IX / VIII inhibitor | IS-OV, IS-A1, IS-A2, IS-A3 → IS | — |
| RT-3 | cytokine, chemokine, complement | cytokine, chemokine, complement, interferon, IFN, IL-*n* | IS-A6 → LB; IS-A4 → IS | (IS-A4) a cellular immune response measured by a non-flow-cytometry technique |
| RT-7 | flow cytometry | flow cytometry, FACS, (immuno)phenotyping | IS-A4, CP-OV, CP-A1, CP-A2 → CP | — |
| RT-8 | microbial Ag/Ab combination | Ag/Ab | IS-A5 → MB (sets RT-1 aside, as IS-A5 states the exception) | — |
| RT-9 | therapeutic drug level | pharmacokinetics, PK, drug level | PC-OV → PC | — |
| RT-10 | routine laboratory test | hematology, clinical chemistry, urinalysis | LB-OV → LB | — |

Notes on the rules:
- RT-1 routes to IS without a condition. Each kind of induced antibody falls under one of the cited assumptions: induced by
  a therapy (IS-A1: anti-drug antibodies, antibodies to a vector capsid or a transgene product, factor IX inhibitors), to an
  allergen, a microorganism or a self-antigen (IS-A2), any other induced humoral response such as anti-HLA (IS-A3). All
  give IS, so which kind a row is does not change the domain; it belongs to the target (binding agent), a later step.
  (Until cdisc-for-ai `a7d5821` only IS-A2 was in `SDTMIG_Statements`, and RT-1 stayed open.)
- Watch point: without a condition, any label with antibody, nAb, TAb, BAb or ADA routes to IS; only RT-8 (Ag/Ab, IS-A5)
  sets RT-1 aside. A test named after an antibody that SDTM places in another domain would be routed wrongly. In the
  collections so far RT-1 fires only on antibodies to a therapy, a vector capsid, a transgene product or HLA.
- RT-3 is open when it fires: IS-A6 sends cytokine measurements to LB, IS-A4 keeps cellular immune responses measured by
  non-flow techniques in IS (for example IFN-gamma ELISpot). Which one applies is a protocol question.
- "Inhibitor" only as factor IX / VIII inhibitor: SoA footnotes name other inhibitors (concomitant medication).
- ELISpot is not a trigger word, and "phenotype" alone does not fire RT-7 (RNA expression associated with a phenotype).
- Precedence only where the cited statement itself states the exception (RT-8 over RT-1, IS-A5).
- Rule IDs keep the numbering of the wider rule set; see below.

## Members-only material

CDISC also has material for its members that bears on routing, mainly the CDISC Controlled Terminology Rules. It has
statements on where some tests belong that SDTMIG v3.4 does not cover, for example total immunoglobulins, cytokines tested
as an antigen-stimulated immune response, vector shedding, replication-competent vectors and transgene integration. It is
useful here, but it is for CDISC members only, so it is not used in this repository. Every statement cited here is a public
SDTMIG v3.4 statement.

The gaps in the rule IDs (RT-2, RT-4, RT-5, RT-6) are rules that rest on members-only statements alone. Without them, those
rows fall back to the grain kind (status `not routed`).

## Files

```
{NCTID}/SoA2USDM/routing/
├── {NCTID}_activity_routing.json   # generated (schema soa2usdm-activity-routing 1.1; 1.0 files stay valid)
└── {NCTID}_activity_routing.html   # page, rendered with the collection index
```

`<id>_activity_routing.json` holds:
- `inputs`: the sha256 of the study's grain file and of `consolidated.json`, and the cdisc-for-ai provenance (commit,
  file sha256, sheet content sha256) of `SDTMIG_Statements` and `Domain_Coverage`;
- `fallback_excluded`: PP, with PP-OV and PP-A1;
- `statements`: each cited statement once, verbatim, with source, section, page and text sha256;
- `counts`: rows, not reached, one count per status, and the routed rows routed by test identity;
- `rows[]`: one per routed named test, with the grain kind, status, domain or candidates, hints, the basis (rule, statements,
  matched phrases with where they matched), the rules set aside, the fallback, the question, `route_source` (rule or test
  identity) and `test_identity` (the label's SDTM_Test_Identity hits: strength, domains, codes);
- `not_reached[]`: panels and named-test parents, with the reason.

## Running it

```
pip install -e '.[grain]'
python -m soa2usdm.activity_routing --collection cell_gene_therapy                # every study with a grain file
python -m soa2usdm.activity_routing --collection cell_gene_therapy --protocol NCT03489291
```

The step reads the grain file through `activity_grain.load_current_grain`, so it stops on a stale grain file. It stops as well
when the grain was made at another cdisc-for-ai commit than the one checked out. Run it after the grain, before the
collection pages are built. The collection index renders a page per study, `SoA2USDM/routing/<id>_activity_routing.html`
(`soa2usdm.activity_routing_page`), and the shared navigation adds "activity routing" to the strip of every protocol page.
The page lists open and weak rows first, then routed and not routed, then the rows not reached and the cited statements.
Before any page is rendered, the index checks each routing file against the grain file and `consolidated.json`, and
**stops on a stale file** with the command to rerun.

## Status

Status on 2026-11-05, with cdisc-for-ai `a7d5821` (rules 1.2.0; routed by test identity in brackets):

| Collection | Studies | Named tests | routed | open | weak | not routed | not reached |
|---|---|---|---|---|---|---|---|
| cell_gene_therapy | 5 | 59 | 17 (2) | 7 | 1 | 34 | 58 |
| usdm_data | 22 | 70 | 36 (35) | 10 | 0 | 24 | 73 |
| cpmp | 13 | 27 | 20 (20) | 4 | 0 | 3 | 52 |
| misc_studies | 2 | 16 | 10 (10) | 1 | 1 | 4 | 15 |

Outside cell_gene_therapy the named tests are mostly routine laboratory tests and vital signs (HbA1c, height, weight, blood
pressure). No rule names them; the test identity routes most of them. Weight and pulse stay open (CV or VS); the rows left
not routed have a weak test identity hit (pregnancy test, FSH, temperature …) or none. In cell_gene_therapy the antibody
tests route to IS (RT-1); what stays open is IFN-gamma ELISpot (RT-3, IS or LB), weight (CV or VS) and the ALLO-501A /
ALLO-647 rows (CP or PC, or matched only in the parent label or a footnote).

In the rules-only collections many rows are still `unsure` in the grain (usdm_data 337 of 811, cpmp 107 of 303, misc_studies
25 of 82), so they do not reach routing yet.
