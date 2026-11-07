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
| grain `panel` whose label lists members (grain rules 1.2.0) | one row per named-test member (schema 1.3); the panel row is not reached, "panel, split from label", with its members |
| grain `panel` named only, linked to the study's protocol context (1.5) | one row per named-test member from the linked context panels; the panel row is not reached, "panel, members from protocol context", with its members |
| grain `panel` named only, otherwise | not reached, "panel, not split": the members need the protocol's lab appendix |
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
| weak, one code in one domain (NCIt synonym only, qualifier dropped, peeled …) | routed, `route_source` "test identity, weak hit" (rules 1.3.0; e.g. "Pregnancy test" → HCG → LB) |
| weak, several codes or several domains | not routed: the domains are hints; the candidates come from the grain kind |

A rule always ranks above the test identity. Where a rule fired, the hits are recorded and change nothing: "PK (Glucagon)"
is routed to PC by RT-9, although GLUCAGON is an LB test code. A weak hit routes only with one code in one domain: the
domain is then not in doubt, even where the test is ("Pregnancy test" reaches HCG only through an NCIt synonym; "Calcium
(cCa)" reaches CA only by dropping the qualifier, and cCa is corrected calcium). The route source keeps the weakness
visible. "eGFR (CKD-EPI)" hits GFRE and EGFR (LB, MI) and is not routed. A strong hit routes also to a domain the
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
├── {NCTID}_activity_routing.json   # generated (schema soa2usdm-activity-routing 1.5; earlier files stay valid)
└── {NCTID}_activity_routing.html   # page, rendered with the collection index
{NCTID}/SoA2USDM/panels/
└── {NCTID}_panel_context_members.json   # only where protocol context exists (schema soa2usdm-panel-context-members 1.0)
```

`<id>_activity_routing.json` holds:
- `inputs`: the sha256 of the study's grain file and of `consolidated.json`, and the cdisc-for-ai provenance (commit,
  file sha256, sheet content sha256) of `SDTMIG_Statements` and `Domain_Coverage`;
- `fallback_excluded`: PP, with PP-OV and PP-A1;
- `statements`: each cited statement once, verbatim, with source, section, page and text sha256;
- `counts`: rows, not reached, one count per status, and the routed rows routed by test identity (strong, and 1.2 weak);
- `rows[]`: one per routed named test, with the grain kind, status, domain or candidates, hints, the basis (rule, statements,
  matched phrases with where they matched), the rules set aside, the fallback, the question, `route_source` (rule, test
  identity, or test identity, weak hit) and `test_identity` (the label's SDTM_Test_Identity hits: strength, domains, codes);
- `not_reached[]`: panels and named-test parents, with the reason; a split panel with its members (1.3).

**Member rows (1.3).** A member row has the panel's `xact_id`, the `member_id` from the grain file, the member text as
`activity_name` and the panel label as `panel_name`. The member text is its label and routes on its own; the panel's parent
label supports or opens, as for any row; its test identity is the member's own hits. Rules that match the panel label
("Hematology" → RT-10, LB) are recorded as `panel_label_support` and never route, open or block the test identity.
`counts.rows_from_panel_members` counts the member rows.

**Panel annotations (1.4, rules 1.5.0).** The SoA annotations of the panel row or its parent describe the panel, not the
single member. For a member row they only support, as the panel label does: rules that match them are recorded as
`panel_annotation_support` (rule, annotation and phrase, domains) and never route, open or block the test identity. So a
member row is never weak. Case: NCT03283098 "Hematology, PT, aPTT", where the footnote's "hematology" (RT-10) made PT and
aPTT weak; now they route by their own test identity. Annotations that name the member itself are not looked at separately
yet.

## Panel members from protocol context

A grain `panel` row whose label lists no members ("Hematology", "Urinalysis", "Laboratory Safety Panels (Hematology and
Clinical Chemistry) (CL)") has its members only in the protocol: the lab appendix, a safety laboratory table, an SoA note.
Where a study has protocol context (`context/<id>_protocol_context.json`, `panels[]`: panel name, analytes, specimen, lab,
evidence), `soa2usdm.panel_context_members` takes the members from there, into a per-study sidecar of its own,
`panels/<id>_panel_context_members.json`. The grain file stays label-only; a collection that gets protocol context later
only gets these sidecars. Only cell_gene_therapy has protocol context so far; the other collections get nothing (no generic
panel list).

**Link by name (name rule 1.0.0, no AI).** Parentheses that hold only lab codes, "(CL)", "(LL)", are dropped. The whole
label, without its trailing parentheses, is tried first; when no context panel has that name, the label is split into panel
names at ",", "and", "&" outside parentheses (not at "/": "CBC w/differential"), and a trailing parenthesis that is not a
qualifier gives names too ("Laboratory Safety Panels (Lipid Panel)"). A context panel name loses its trailing parentheses
(source notes such as "(SoA note)", "(Table 2. Safety Laboratory Tests)"). Both sides are normalised as in the grain,
"haematology" is read as "hematology", trailing generic words are dropped (parameters, tests, test, assessments,
assessment), and spaces are ignored in the comparison ("auto-antibodies" = "autoantibodies"). A name links every context
panel with the same key. There is no containment, no plural and no stemming, so near misses stay unlinked ("CBC
w/differential" and "CBC Hematology", "serum immunoglobulins" and "Serum Immunoglobulin", "Coagulation" and "Coagulation
Screen"). A row is `linked`, `linked partly` (some of its names have no context panel) or `not linked`.

**Members.** The analytes of the linked context panels are split and looked up with the rules of the label members (grain
rules 1.2.0): a list analyte gives its members ("Serum electrolytes (sodium, potassium)"), any other analyte one member.
Where several context panels share one name (NCT05714345 "Coagulation (Table 2…)" and "Coagulation (SoA note)"), the members
are the union by phrase, each with every context panel and analyte it comes from; the phrases found in only one of them are
listed as `differences`, not resolved. Most such differences are spellings of the same test ("PTT" and "partial
thromboplastin time (PTT)"), and both stay as members. Member ids are c01, c02 … per SoA row. The specimen and lab of each
source context panel are recorded on the member as stated facets, with the context panel and its evidence pages; they are
not used for routing.

**Routing (1.5, rules 1.6.0).** The named-test members are routed as label members: the member text routes on its own; the
SoA panel label, the context panel names and the annotations of the panel row or its parent only support
(`panel_label_support`, `context_panel_support`, `panel_annotation_support`). The row is marked
`members_from: "protocol context"` and carries `context_sources` (context panel, pages) and `stated_facets`. No new rule, no
weaker status. `counts.rows_from_context_members` counts these rows; `inputs.panel_context_members` records the sidecar's
sha256, and routing stops when the sidecar is missing or stale where the study has protocol context.

Grain `panel` rows that are not lab panels (sample collections such as "Lymphoma tissue collection", "BM aspirate";
specimen-and-assay rows such as "TBNK (blood)", "Anti-ALLO-501A ADA") have no context panel and stay not reached; the
sidecar lists them as `not linked`, for a later grain pass.

## Running it

```
pip install -e '.[grain]'
python -m soa2usdm.activity_routing --collection cell_gene_therapy                # every study with a grain file
python -m soa2usdm.activity_routing --collection cell_gene_therapy --protocol NCT03489291
```

Where a study has protocol context, run `python -m soa2usdm.panel_context_members --collection <name>` after the grain and
before routing. The step reads the grain file through `activity_grain.load_current_grain`, so it stops on a stale grain file. It stops as well
when the grain was made at another cdisc-for-ai commit than the one checked out. Run it after the grain, before the
collection pages are built. The collection index renders a page per study, `SoA2USDM/routing/<id>_activity_routing.html`
(`soa2usdm.activity_routing_page`), and the shared navigation adds "activity routing" to the strip of every protocol page.
The page lists open and weak rows first, then routed and not routed, then the rows not reached and the cited statements.
Before any page is rendered, the index checks each routing file against the grain file and `consolidated.json`, and
**stops on a stale file** with the command to rerun.

## Status

Status on 2026-11-07, with cdisc-for-ai `a7d5821` (rules 1.6.0 for cell_gene_therapy, 1.5.0 for the others, which have no
protocol context; grain rules 1.2.0; routed by test identity in brackets, strong and weak; named tests include the panel
members, for cell_gene_therapy 158 of them from protocol context; not reached in brackets: split from label, members from
protocol context):

| Collection | Studies | Named tests (members) | routed | open | weak | not routed | not reached (split) |
|---|---|---|---|---|---|---|---|
| cell_gene_therapy | 5 | 244 (184) | 179 (90, weak 74) | 22 | 1 | 42 | 58 (11, 18) |
| usdm_data | 22 | 137 (44) | 107 (49, weak 57) | 20 | 0 | 10 | 83 (27) |
| cpmp | 13 | 40 (0) | 36 (20, weak 16) | 4 | 0 | 0 | 52 (0) |
| misc_studies | 2 | 43 (26) | 36 (18, weak 18) | 4 | 1 | 2 | 14 (6) |

Outside cell_gene_therapy the named tests are mostly routine laboratory tests and vital signs (HbA1c, height, weight, blood
pressure, pregnancy test, drug screen). No rule names them; the test identity routes almost all of them, a weak hit with
one code in one domain included. Weight and pulse stay open (CV or VS); not routed are the rows whose weak hit has several
codes or domains (temperature, PaO2/FiO2, eGFR). In cell_gene_therapy the antibody tests route to IS (RT-1); what stays open
is IFN-gamma ELISpot (RT-3, IS or LB), weight (CV or VS) and the ALLO-501A / ALLO-647 rows (CP or PC, or matched only in the
parent label or a footnote).

In the rules-only collections many rows are still `unsure` in the grain (usdm_data 314 of 811, cpmp 94 of 303, misc_studies
24 of 82), so they do not reach routing yet.
