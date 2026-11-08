# Test identity — test code, facets and specialization level (step 6a)

`python -m soa2usdm.test_identity --collection <name> [--protocol <NCTID>]` writes
`SoA2USDM/test_identity/<id>_test_identity.json` per study, one record per row of the study's routing file.
It runs after the routing and records only: nothing here routes, opens or changes a routing row. Rules
1.0.0, schema 1.0, word lists 2026-11-08. A review page follows in 6a-2; matching fixes that move the
routing (a restated component counting as corroboration, peeling, abbreviation expansion) follow in 6b.

## The frame

Test identity is the test code plus facets plus a specialization level. The facet definition is
cdisc-for-ai `docs/Observables_Direction.md`, "Facets and their kind (2026-11-08)":

- A facet is a value, beyond the test code, that describes the planned observation.
- Its **Kind** (observable, practice, record, open) and its identity (**Position**: component, system,
  method, scale; not part of the observable; open) are our position, from `Variable_Meaning` in
  `SDTM_Domain_Metadata.xlsx`, never the IG's.
- Recognition reads facets of every kind. The key and the specialization level use identity facets only.
  An identity facet the protocol does not state stays open and is never filled.
- Conditions (whether the observation happens) and analysis (averaging repetitions) are not facets.
- Two planned observations that differ only by a practice facet are the same observable planned two ways.

SDTMIG 4.1.9-3 states the general pattern (a generic test code with qualifier variables), LB-A8 names the
LB facets, EG-A5 puts the QT correction method into the ECG test name.

## What a record holds

| Field | Content | Source |
|---|---|---|
| `component` | the routing row's codes in its domain, the part of the label that hit (the peeled rest, or the text outside a dropped parenthesis), and the component restated | routing test identity; SDTM_Test_Identity |
| `component.collisions` | the Test_String_Collisions rows of the part that hit, our codes against its concepts (`equal`, `ours fewer`, `ours more`); case never decides | Codelist_Phrases / Test_String_Collisions |
| `components` | ECG activity rows: each component of the protocol context measurements entry, matched to EG tests only (SDTM_Test_Identity, else the head of a Folded_Facets test); no words are added | protocol context; Folded_Facets |
| `facets` | variable, Kind, Position, value as printed, CDISC term, where stated | Variable_Meaning, Domain_Variables, Codelist_Phrases |
| `practice_text` | EG, VS, CV: --FAST / --SPEC text the domain's statement lists as not generally used | EG-A11, VS-A4 (both), CV-A2 (--FAST only) |
| `conditions` | reflex, population, site, visit | our word list |
| `unread` | label words outside the part that hit, the facets and the conditions | — |
| `specialization` | the level, the COSMoS specializations and what separates them | Measurement_Specs |

### Facets

Facet variables of a domain are the `Domain_Variables` rows whose generic variable is a facet in
`Variable_Meaning` somewhere (Kind not record, Position not component), plus --ANMETH (a calculation method
is a facet). Kind and Position come from the domain's own `Variable_Meaning` row; where the domain has
none (CP, MB, PC, CV …), Kind is "not set" and the variable is never in a key.

Sources, in this order: the label outside the part that hit; member qualifiers; the specimen stated on the
context panel; the `lab_and_purpose` entry of the activity (for a member, of its panel: inheritance only
from what is stated); for ECG activity rows the measurements entry (`position_or_condition` → --POS;
`method` → --METHOD, --LEAD, --EVAL).

A value is matched to a CDISC term only through a `Codelist_Phrases` phrase of the variable's IG codelist,
longest match first, never overlapping ("MUGA scan" is MUGA, not also "scan"). A typed context field keeps
its value as printed and takes a term only when exactly one phrase matches. A phrase of the label that is an
SDTM_Test_Identity string of the component's own code is the component restated, not a facet: in
"Erythrocyte count (RBC)" the parenthesis is the test, not the specimen ERYTHROCYTES.

Fasting is read from the words "fasting", "non-fasting" and "fasting not required" (our word list); the
reading is Y, N or none.

### Specialization level

| Level | Meaning |
|---|---|
| no component | no test hit |
| component open | several codes |
| domain open | the routing has not settled the domain |
| no specialization | COSMoS has no specialization for the code in the domain |
| one specialization | one observable (specializations sharing an Observable_Key count as one) |
| selected by stated facets | stated identity facets leave one observable |
| facet not stated | several observables remain; `not_stated` lists the positions that still separate them |
| stated facet matches no specialization | a stated term equals none of the specializations' terms |
| stated facets conflict | two sources state different terms for one identity position; neither narrows |

A stated facet narrows by its exact CDISC term (decision 2026-11-08): SERUM does not select a SERUM OR
PLASMA specialization. Scale is never stated in a SoA and stays open where it separates specializations.

ECG components: `test code`, `test family, beat not stated` (the Folded_Facets head has Aggregate and
Single Beat tails; EG-A5), `component open`, or `no component`. Bare forms ("QT", "QRS", "RR", "QTcF")
have no CDISC form and stay open; "heart rate" hits HR in CV and VS, not EG, and is listed outside EG.

## Lookups and provenance

All from the public cdisc-for-ai checkout: `SDTM_Domain_Metadata.xlsx` (Variable_Meaning),
`SDTMIG_Statements.xlsx`, `Codelist_Phrases.xlsx` (Phrases, Test_String_Collisions), the Specimen,
Measurement and Immunogenicity Findings files (Domain_Variables, Codelists, Measurement_Specs), and
`domain-behaviour/interim/Domain_Behaviour.xlsx` (Folded_Facets), plus the grain lookups for test hits.
Variable_Meaning and Folded_Facets have no Provenance sheet; their sheet hashes are computed here
(`sheet_hash_computed_here`). The domain-behaviour track is read here by decision (2026-11-08), although
cdisc-for-ai describes it as read by nothing.

## Figures (all four collections, cdisc-for-ai 844384b)

982 rows (312 standalone, 627 panel members, 43 ECG activity rows with 124 components); 608 facets, 464
with a CDISC term; conditions on 4 rows; collisions cited on 14 rows (all `equal`).

| Level | Standalone | Members |
|---|---|---|
| no component | 130 | 1 |
| component open | 2 | 8 |
| domain open | 23 | 57 |
| no specialization | 54 | 75 |
| one specialization | 41 | 261 |
| selected by stated facets | 19 | 15 |
| facet not stated | 23 | 193 |
| stated facet matches no specialization | 14 | 17 |
| stated facets conflict | 6 | 0 |

ECG components: no component 109, test code 4, test family (beat not stated) 11.
