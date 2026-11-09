"""
SoA2USDM Test identity (per-study sidecar after the routing) — step 6a

Test identity = test code + facets + specialization level. The facet definition is cdisc-for-ai
docs/Observables_Direction.md, "Facets and their kind (2026-11-08)": a facet is a value, beyond the test
code, that describes the planned observation. Kind (observable / practice / record / open) and identity
(Position) are properties of a facet; both are our position (Variable_Meaning), never the IG's.

Records only (6a): nothing here routes, opens or changes a routing row. Every row of the study's routing
file gets one record:

component       the routing row's test identity: its codes in the row's domain (all codes where the domain
                is not settled), and the part of the label that hit (the peeled rest, or the text outside a
                dropped parenthesis). A phrase of the rest that is an SDTM_Test_Identity string of the
                component's own code is the component restated ('Erythrocyte count (RBC)'), not a facet.
                Where the part that hit is a string of Test_String_Collisions, its rows are cited and the hit's
                codes are compared with its concepts; case never decides.
components      activity-level rows (ECG, RT-13): each component the study's protocol context measurements
                entry lists for the activity, matched to EG tests only: the SDTM_Test_Identity hit, else the
                head of a Folded_Facets test (normalised, equal). No words are added ("QT" is not "QT
                Interval"); a component without a hit stays open. A head with tails (Aggregate, Single Beat)
                gives the test family and the tails not stated (EG-A5; Folded_Facets).
facets          values beyond the test code, of every kind, read from: the label outside the test phrase,
                the member qualifiers, the specimen stated on the context panel, the lab_and_purpose entry of
                the activity (for a member, of its panel), and for activity-level rows the measurements entry
                (position_or_condition: --POS; method: --METHOD, --LEAD, --EVAL). A value is matched to a
                CDISC term only through a Codelist_Phrases phrase of the variable's IG codelist, longest match
                first, never overlapping; otherwise it is kept as printed. Rules 1.1.0 (decisions 2026-11-08):
                free text (label, member qualifiers) is read only for variables whose Kind is set and not open
                (where the domain is not settled: the generic's Kind in some domain); typed context fields are
                read for their own variable whatever its Kind. A phrase that matches the codelists of several
                variables gives one facet per variable, each with ambiguous_with the others; none is chosen and
                none narrows the specialization. Rules 1.4.0 (2026-11-09): a typed context field whose value
                names more than one thing next to the phrase ("plasma and PBMCs", "ECHO or MUGA scan": "and" /
                "or" in the phrase's clause, CLAUSE_BOUNDARIES) takes no term; the terms its phrases reach are
                kept in terms and the facet is list_value. Fasting is read from the words
                "fasting" / "non-fasting" (our word list, FASTING_WORDS). Each facet carries the variable, Kind
                and Position from Variable_Meaning, or Kind "not set" where the domain has no row
                (Domain_Variables only).
group_head      rules 1.2.0 (step 6b, 2026-11-08): a member of a group (in_group, label or context members) gets
                its group head. A head that is, as a whole, a phrase of the --METHOD or --SPEC codelist of the
                row's domain (Codelist_Phrases: submission value, preferred term, CDISC or NCIt synonym) is a
                facet of the member (where "group head"). Any other head ('dipstick', 'microscopic examination')
                is recorded as text, not read: it is not a CDISC term.
practice_text   EG, VS, CV: a --FAST or --SPEC value that the domain's statement lists among the qualifiers
                that would not generally be used (EG-A11 and VS-A4: both; CV-A2: --FAST only, read from the
                statement text) is kept as text with the statement, not as a facet.
conditions      whether the observation happens (reflex, population, site, visit): our dated word list
                (CONDITION_PATTERNS); not facets (Observables_Direction).
unread          label words outside the test phrase, the facets and the conditions.
specialization  the level over identity facets only (Position system, method, scale), from COSMoS
                Measurement_Specs for the component's code in the row's domain. A stated identity facet
                narrows the specializations by its exact CDISC term (SERUM does not select SERUM OR PLASMA);
                an identity facet not stated stays open and is never filled.

component_parts rules 1.3.0 (2026-11-09): in IS the analyte is split across ISTEST and ISBDAGNT (and ISMSCBCE):
                "the combination of ISTEST and ISBDAGNT [ISMSCBCE] should describe the entity or the analyte being
                measured" (ISBDAGNT-Notes, ISMSCBCE-Notes). Variable_Meaning gives both Position component, which
                the facet filter drops; a component carried in a variable other than --TESTCD is not the component
                restated. So for rows whose domain is IS these two variables are read as component parts, from the
                same free text as the facets (label, member qualifiers), by the same rule: a Codelist_Phrases phrase
                of the variable's codelists (ISBDAGNT: MICROORG, ISBDAGT; IS-A7), otherwise not read. ISMSCBCE has
                no codelist, so nothing is read for it until a typed context field exists. A part whose term is
                reached only through NCIt synonyms is weak ("NCIt synonym only", as grain rule L1q). Component
                parts are records only: they never narrow the specialization. Only ISBDAGNT and ISMSCBCE
                (COMPONENT_PART_VARIABLES); the other component variables (LBBDAGNT, --TSTDTL) are not read.

Levels: no component; component open (several codes); domain open; no specialization (COSMoS has none);
one specialization; selected by stated facets; facet not stated; stated facet matches no specialization;
stated facets conflict (two sources state different terms for one identity position: neither narrows);
and for ECG components: test code, test family (beat not stated), no component.

Folded_Facets is read from Codelist_Phrases.xlsx (cdisc-for-ai d688fd6; until then domain-behaviour/interim) and
Variable_Meaning from SDTM_Domain_Metadata.xlsx, both with their published Provenance (3cec261). A lookup file without
a Provenance sheet would have its sheet hash computed here (sheet_hash_computed_here); none has today.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .activity_grain import (CDISC_FOR_AI, Lookups, context_path, grain_path, normalise, peel_label,
                             split_trailing_parens)
from .activity_routing import load_current_routing, routing_path
from .panel_context_members import load_current_panel_members, panels_path

SCHEMA_NAME = "soa2usdm-test-identity"
SCHEMA_VERSION = "1.4"
SCHEMA_VERSIONS = ("1.0", "1.1", "1.2", "1.3", "1.4")
RULES_VERSION = "1.4.0"
WORD_LISTS_DATE = "2026-11-09"

FG = "sdtm-findings-graph/machine_actionable/"
FINDINGS_FILES = ("Specimen_Findings", "Measurement_Findings", "Immunogenicity_Findings")
# key -> (path, sheet, has a Provenance sheet with <sheet>.Content_SHA256)
LOOKUP_FILES = {
    "Variable_Meaning": ("sdtm-domain-reference/machine_actionable/SDTM_Domain_Metadata.xlsx", "Variable_Meaning", True),
    "SDTMIG_Statements": ("sdtm-domain-reference/machine_actionable/SDTMIG_Statements.xlsx", "Statements", True),
    "Codelist_Phrases": (FG + "Codelist_Phrases.xlsx", "Phrases", True),
    "Test_String_Collisions": (FG + "Codelist_Phrases.xlsx", "Test_String_Collisions", True),
    "Folded_Facets": (FG + "Codelist_Phrases.xlsx", "Folded_Facets", True),
}
for _f in FINDINGS_FILES:
    for _s in ("Domain_Variables", "Codelists", "Measurement_Specs"):
        LOOKUP_FILES[f"{_f}.{_s}"] = (FG + f"{_f}.xlsx", _s, True)

# A calculation method is a facet (Observables_Direction); --ANMETH has no Variable_Meaning row.
EXTRA_FACET_GENERICS = ("--ANMETH",)
# Identity positions used for the specialization level (Variable_Meaning Position).
IDENTITY_POSITIONS = ("system", "method", "scale")
# EG, VS, CV: the IG lists --FAST and --SPEC among the qualifiers that would not generally be used.
NOT_GENERALLY_USED = {"EG": "EG-A11", "VS": "VS-A4", "CV": "CV-A2"}
NOT_GENERALLY_USED_GENERICS = ("--FAST", "--SPEC")
# Activity-level context fields and the facet generics read from them.
MEASUREMENT_FIELDS = {"position_or_condition": ("--POS",), "method": ("--METHOD", "--LEAD", "--EVAL")}
LAB_AND_PURPOSE_FIELDS = {"specimen": "--SPEC", "method": "--METHOD"}
# Rules 1.2.0: a group head is read as a facet only as a whole phrase of these generics' codelists.
GROUP_HEAD_GENERICS = ("--METHOD", "--SPEC")
MIN_PHRASE_CHARS = 3
# Rules 1.3.0: component variables other than --TESTCD read as component parts, each with its CDISC basis.
COMPONENT_PART_VARIABLES = {"ISBDAGNT": "ISBDAGNT-Notes", "ISMSCBCE": "ISMSCBCE-Notes"}

# ---------------------------------------------------------------------------
# Dated word lists (WORD_LISTS_DATE): our pattern code, not CDISC sources.
# ---------------------------------------------------------------------------
FASTING_WORDS = (  # first match wins; reading None = fasting named, state not given
    (r"\bfasting not required\b", None),
    (r"\bnon[- ]?fasting\b", "N"),
    (r"\bfasting\b", "Y"),
)
CONDITION_PATTERNS = (  # whether the observation happens: reflex, population, site, visit
    ("reflex", r"\bif positive\b[^,;)]*"),
    ("reflex", r"\breflex\b[^,;)]*"),
    ("reflex", r"\bif (?:appropriate|indicated|clinically indicated|needed|required)\b"),
    ("site", r"\bif the test is available\b[^,;)]*"),
    ("site", r"\b(?:at )?selected sites(?: only)?\b"),
    ("population", r"\bhigh[- ]risk patients\b"),
    ("population", r"\bwomen of (?:child[- ]?bearing|reproductive) potential(?: only)?\b"),
    ("population", r"\bwocbp(?: only)?\b"),
    ("visit", r"\bonly (?:at|on|in|during) [^,;)]+"),
)
# Rules 1.4.0: a typed context field names more than one thing when a coordinator stands in the clause of a
# matched phrase. The clause runs from the phrase to a boundary word, a ';' or the end of the value, inside the
# phrase's own parenthesis; other parentheses are skipped. Commas and slashes are not coordinators ("Formalin
# fixed, paraffin-embedded"; "LC-MS/MS").
COORDINATORS = ("and", "or")
CLAUSE_BOUNDARIES = ("after", "at", "before", "by", "during", "except", "for", "from", "if", "in", "instead", "of",
                     "on", "prior", "to", "unless", "when", "whenever", "with", "within")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_identity_path(protocol_id: str, collection: str) -> Path:
    return config.get_soa2usdm_folder(protocol_id, collection) / "test_identity" / f"{protocol_id}_test_identity.json"


def generic(variable: str) -> str:
    return "--" + variable[2:]


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
class TestIdentityLookups:
    """Facet variables, codelist phrases, COSMoS specializations, Folded_Facets, string collisions and
    the not-generally-used statements, from the public cdisc-for-ai files; test hits from the grain lookups."""

    def __init__(self, root: Path = CDISC_FOR_AI, grain_lookups: Lookups | None = None):
        if not root.is_dir():
            raise FileNotFoundError(f"cdisc-for-ai checkout not found at {root} (set SOA2USDM_CDISC_FOR_AI)")
        self.root = root
        self.sheets = {k: self._read(k) for k in LOOKUP_FILES}
        self.provenance = self._provenance()
        self.grain = grain_lookups or Lookups(root)
        if self.grain.provenance["commit"] != self.provenance["commit"]:
            raise RuntimeError("grain lookups and test identity lookups read different cdisc-for-ai commits")
        self._load_facet_variables()
        self._load_phrases()
        self._load_specializations()
        self._load_folded()
        self._load_collisions()
        self._load_not_generally_used()
        self._load_component_part_basis()

    def _read(self, key):
        import pandas as pd
        rel, sheet, _ = LOOKUP_FILES[key]
        return pd.read_excel(self.root / rel, sheet_name=sheet, keep_default_na=False, dtype=str)

    def _provenance(self) -> dict:
        import pandas as pd
        commit = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        rels = sorted({rel for rel, _, _ in LOOKUP_FILES.values()})
        dirty = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain", "--", *rels],
                               capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            raise RuntimeError(f"cdisc-for-ai lookup files have uncommitted changes:\n{dirty}")
        files = []
        for key, (rel, sheet, has_prov) in LOOKUP_FILES.items():
            entry = {"file": key, "path": rel, "sheet": sheet,
                     "file_sha256": _sha256_bytes((self.root / rel).read_bytes())}
            if has_prov:
                prov = pd.read_excel(self.root / rel, sheet_name="Provenance", keep_default_na=False, dtype=str)
                pv = dict(zip(prov["Key"], prov["Value"]))
                entry |= {"sheet_content_sha256": pv[f"{sheet}.Content_SHA256"], "generated": pv["Generated"],
                          "sheet_hash_computed_here": False}
            else:
                csv = self.sheets[key].to_csv(index=False).encode("utf-8")
                entry |= {"sheet_content_sha256": _sha256_bytes(csv), "generated": None,
                          "sheet_hash_computed_here": True}
            files.append(entry)
        return {"commit": commit, "files": files}

    def _load_facet_variables(self):
        """domain -> [{variable, generic, kind, position, meaning_status, codelists}]"""
        meaning = {(r["Domain"], r["Key"]): r for r in self.sheets["Variable_Meaning"].to_dict("records")
                   if r["Domain"]}
        generics = {generic(k) for (d, k), r in meaning.items()
                    if r["Kind"] != "record" and r["Position"] != "component"}
        generics |= set(EXTRA_FACET_GENERICS)
        self.facet_generics = sorted(generics)
        self.facet_variables = defaultdict(list)
        self.codelist_by_generic = defaultdict(set)
        self.generic_kinds = defaultdict(set)
        self.component_part_variables = defaultdict(list)
        seen = set()
        for f in FINDINGS_FILES:
            cl = {r["codelist_concept_id"]: r["codelist_submission_value"]
                  for r in self.sheets[f"{f}.Codelists"].to_dict("records")}
            for r in self.sheets[f"{f}.Domain_Variables"].to_dict("records"):
                var, dom = r["Variable Name"], r["Dataset Name"]
                part = var in COMPONENT_PART_VARIABLES
                if (r["Generic_Variable"] not in generics and not part) or (dom, var) in seen:
                    continue
                seen.add((dom, var))
                codes = [c.strip() for c in r["CDISC CT Codelist Code(s)"].split(";") if c.strip()]
                m = meaning.get((dom, var))
                entry = {"variable": var, "generic": r["Generic_Variable"],
                         "kind": m["Kind"] if m else None, "position": m["Position"] if m else None,
                         "meaning_status": m["Status"] if m else None,
                         "codelists": sorted(cl.get(c, c) for c in codes)}
                if part:
                    if entry["position"] != "component":
                        raise ValueError(f"{var}: Variable_Meaning Position {entry['position']!r}, expected component")
                    self.component_part_variables[dom].append(entry)
                    continue
                self.facet_variables[dom].append(entry)
                self.codelist_by_generic[entry["generic"]].update(entry["codelists"])
                self.generic_kinds[entry["generic"]].add(entry["kind"])

    def _load_phrases(self):
        """codelist -> phrase -> [(submission_value, concept_id)]"""
        self.phrases = defaultdict(lambda: defaultdict(set))
        self.phrase_fields = defaultdict(set)
        for r in self.sheets["Codelist_Phrases"].to_dict("records"):
            self.phrases[r["codelist_submission_value"]][r["phrase"]].add(
                (r["term_submission_value"], r["term_concept_id"]))
            self.phrase_fields[(r["codelist_submission_value"], r["phrase"], r["term_concept_id"])].add(r["field"])

    def _load_specializations(self):
        """(domain, TESTCD, NCIt) -> [specialization]"""
        self.specializations = defaultdict(list)
        for f in FINDINGS_FILES:
            for r in self.sheets[f"{f}.Measurement_Specs"].to_dict("records"):
                key = r.get("Observable_Key") or ""
                parts = key.split("|") if key else []
                self.specializations[(r["domain"], r["TESTCD"], r["TESTCD_NCIt"])].append({
                    "ds_id": r["ds_id"], "observable_key": key or None,
                    "spec": r.get("SPEC_value") or None, "spec_ncit": r.get("SPEC_ncit") or None,
                    "method": r.get("METHOD_value") or None, "method_ncit": r.get("METHOD_ncit") or None,
                    "scale": parts[3] if len(parts) > 3 else None})

    def _load_folded(self):
        rows = [r for r in self.sheets["Folded_Facets"].to_dict("records") if r["Domain"] == "EG"]
        self.folded_by_testcd = {r["TESTCD"]: r for r in rows}
        self.folded_by_head = defaultdict(list)
        for r in rows:
            self.folded_by_head[normalise(r["Head"])].append(r)

    def _load_collisions(self):
        self.collisions = defaultdict(list)
        for r in self.sheets["Test_String_Collisions"].to_dict("records"):
            self.collisions[normalise(r["String"])].append(r)

    def _load_not_generally_used(self):
        st = {r["Statement_ID"]: r for r in self.sheets["SDTMIG_Statements"].to_dict("records")}
        self.not_generally_used = {}
        for dom, sid in NOT_GENERALLY_USED.items():
            if sid not in st:
                raise ValueError(f"{sid} not in SDTMIG_Statements")
            named = set(re.findall(r"--[A-Z]+", st[sid]["Text"].replace("‑", "-")))
            gens = [g for g in NOT_GENERALLY_USED_GENERICS if g in named]
            if not gens:
                raise ValueError(f"{sid} names none of {list(NOT_GENERALLY_USED_GENERICS)}")
            self.not_generally_used[dom] = {"statement_id": sid, "generics": gens,
                                            "text_sha256": _sha256_bytes(st[sid]["Text"].encode("utf-8"))}

    def _load_component_part_basis(self):
        st = {r["Statement_ID"]: r for r in self.sheets["SDTMIG_Statements"].to_dict("records")}
        self.component_part_basis = {}
        for var, sid in COMPONENT_PART_VARIABLES.items():
            if sid not in st:
                raise ValueError(f"{sid} not in SDTMIG_Statements")
            self.component_part_basis[var] = {"statement_id": sid,
                                              "text_sha256": _sha256_bytes(st[sid]["Text"].encode("utf-8"))}

    def variables_for(self, domain: str | None, generics: tuple | None = None) -> list:
        """Facet variables of a domain (or generic ones where the domain is not settled)."""
        if domain:
            out = self.facet_variables.get(domain, [])
        else:
            out = [{"variable": g, "generic": g, "kind": None, "position": None, "meaning_status": None,
                    "codelists": sorted(self.codelist_by_generic[g])} for g in self.facet_generics]
        return [v for v in out if generics is None or v["generic"] in generics]

    def text_variables(self, domain: str | None) -> list:
        """Facet variables read from free text (rules 1.1.0): Kind set and not open; where the domain is not
        settled, generics with such a Kind in some domain."""
        if domain:
            return [v for v in self.variables_for(domain) if v["kind"] not in (None, "open")]
        return [v for v in self.variables_for(None) if self.generic_kinds[v["generic"]] - {None, "open"}]


# ---------------------------------------------------------------------------
# Reading text
# ---------------------------------------------------------------------------
def scan_phrases(tokens: list, variables: list, phrases) -> list:
    """Longest-first, non-overlapping matches of codelist phrases in a token list. A phrase that matches
    the codelists of several variables gives one entry per variable. Returns
    [(start, end, variable_entry, phrase, terms, other_variables)]."""
    taken, out = set(), []
    for n in range(min(8, len(tokens)), 0, -1):
        for i in range(len(tokens) - n + 1):
            span = set(range(i, i + n))
            if span & taken:
                continue
            g = " ".join(tokens[i:i + n])
            if len(g) < MIN_PHRASE_CHARS:
                continue
            matched = []
            for v in variables:
                terms = set()
                for c in v["codelists"]:
                    terms |= phrases.get(c, {}).get(g, set())
                if terms:
                    matched.append((v, sorted(terms)))
            for v, terms in matched:
                others = [w["variable"] for w, _ in matched if w is not v]
                out.append((i, i + n, v, g, terms, others))
            if matched:
                taken |= span
    return sorted(out, key=lambda x: x[0])


def remove_phrase(tokens: list, phrase: str | None) -> list:
    """Tokens with the first occurrence of each word of the test phrase removed."""
    rest = list(tokens)
    for w in (phrase or "").split():
        if w in rest:
            rest.remove(w)
    return rest


def match_conditions(text: str) -> list:
    out = []
    for cls, pat in CONDITION_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            if not any(m.group(0).lower() in c["phrase"].lower() for c in out):
                out.append({"class": cls, "phrase": m.group(0).strip()})
    return out


def match_fasting(text: str) -> dict | None:
    for pat, reading in FASTING_WORDS:
        m = re.search(pat, text, re.I)
        if m:
            return {"phrase": m.group(0), "reading": reading}
    return None


def component_part(f: dict, lk: TestIdentityLookups) -> dict:
    """A facet read for a component-part variable, as a component part: its basis statement, and weak where
    every phrase that reached the term is an NCIt synonym (rules 1.3.0)."""
    weak = []
    if f["term"]:
        fields = lk.phrase_fields[(f["term"]["codelist"], f["value"], f["term"]["concept_id"])]
        if fields == {"NCIt synonym"}:
            weak.append("NCIt synonym only")
    return f | {"basis": lk.component_part_basis[f["variable"]]["statement_id"],
                "hit_strength": "weak" if weak else "strong", "weak_reasons": weak}


def _facet(v: dict, value: str, terms: list, where: str, via: str, **extra) -> dict:
    """The term is set by the caller (_term_codelist): exactly one CDISC term, or none."""
    return {"variable": v["variable"], "generic": v["generic"], "kind": v["kind"], "position": v["position"],
            "meaning_status": v["meaning_status"], "value": value, "term": None,
            "terms": [{"submission_value": s, "concept_id": c} for s, c in terms] if len(terms) > 1 else [],
            "where": where, "via": via} | extra


def _term_codelist(v: dict, terms: list, phrases) -> dict | None:
    if len(terms) != 1:
        return None
    for c in v["codelists"]:
        for ts in phrases.get(c, {}).values():
            if terms[0] in ts:
                return {"codelist": c, "submission_value": terms[0][0], "concept_id": terms[0][1]}
    return None


def restated(tokens: list, codes: list, lk: TestIdentityLookups) -> tuple[list, set]:
    """Phrases in the tokens that are SDTM_Test_Identity strings of one of the component's own codes
    ('Erythrocyte count (RBC)': RBC is the TESTCD of the hit). Longest first, not overlapping."""
    own = {c["code"] for c in codes}
    out, used = [], set()
    if not own:
        return out, used
    for n in range(min(8, len(tokens)), 0, -1):
        for i in range(len(tokens) - n + 1):
            span = set(range(i, i + n))
            g = " ".join(tokens[i:i + n])
            if span & used or g not in lk.grain.test:
                continue
            if own & {h["code"] for h in lk.grain.test[g]}:
                out.append(g)
                used |= span
    return out, used


def read_text(text: str, where: str, variables: list, lk: TestIdentityLookups, exclude: str | None = None,
              codes: list | None = None, **extra) -> tuple[list, list, list, list]:
    """Facets, conditions, the component restated and the unread words of one text. `exclude`: the part
    of the text that hit the test; `codes`: the component's codes (for restatements)."""
    conditions = [c | {"where": where} for c in match_conditions(text)]
    masked = text
    for c in conditions:
        masked = re.sub(re.escape(c["phrase"]), " ", masked, flags=re.I)
    fast = match_fasting(masked)
    facets = []
    if fast:
        fv = next((v for v in variables if v["generic"] == "--FAST"), None) or \
            {"variable": "--FAST", "generic": "--FAST", "kind": None, "position": None, "meaning_status": None,
             "codelists": ["NY"]}
        facets.append({"variable": fv["variable"], "generic": "--FAST", "kind": fv["kind"],
                       "position": fv["position"], "meaning_status": fv["meaning_status"],
                       "value": fast["phrase"], "term": None, "terms": [], "reading": fast["reading"],
                       "where": where, "via": "word list"} | extra)
        masked = re.sub(re.escape(fast["phrase"]), " ", masked, flags=re.I)
    tokens = remove_phrase(normalise(masked).split(), exclude)
    again, used = restated(tokens, codes or [], lk)
    rest_tokens = [t if k not in used else "\x00" for k, t in enumerate(tokens)]
    scan_vars = [v for v in variables if v["generic"] != "--FAST"]
    hits = [h for h in scan_phrases(rest_tokens, scan_vars, lk.phrases) if "\x00" not in h[3]]
    for i, j, v, g, terms, others in hits:
        f = _facet(v, g, terms, where, "codelist phrase", **extra)
        f["term"] = _term_codelist(v, terms, lk.phrases)
        if others:
            f["ambiguous_with"] = others
        facets.append(f)
        used |= set(range(i, j))
    unread = [t for k, t in enumerate(tokens) if k not in used]
    return facets, conditions, again, unread


def token_groups(value: str) -> list:
    """The normalised tokens of a value, each with its segment (';' starts one) and its parenthesis group
    (0 outside; each parenthesis or bracket its own group)."""
    out, seg, stack, n = [], 0, [0], 0
    for m in re.finditer(r"[A-Za-z0-9]+|[()\[\];]", value):
        t = m.group(0)
        if t == ";":
            seg, stack = seg + 1, [0]
        elif t in "([":
            n += 1
            stack.append(n)
        elif t in ")]":
            if len(stack) > 1:
                stack.pop()
        else:
            out.append((t.lower(), seg, stack[-1]))
    return out


def names_more(value: str, hits: list) -> bool:
    """Rules 1.4.0: True where a coordinator stands in the clause of a matched phrase (COORDINATORS,
    CLAUSE_BOUNDARIES)."""
    tg = token_groups(value)
    if [t for t, _, _ in tg] != normalise(value).split():
        raise ValueError(f"token groups do not follow the normalisation rule: {value!r}")
    for i, j, *_ in hits:
        seg, grp = tg[i][1], tg[i][2]
        for side in (range(i - 1, -1, -1), range(j, len(tg))):
            for k in side:
                t, s, g = tg[k]
                if s != seg or (grp and g != grp):
                    break
                if g != grp:
                    continue
                if t in CLAUSE_BOUNDARIES:
                    break
                if t in COORDINATORS:
                    return True
    return False


def read_field(value: str, gen: str, where: str, domain: str | None, lk: TestIdentityLookups, **extra) -> dict:
    """A context field typed for one facet (lab_and_purpose specimen / method): the value as printed,
    its CDISC term where exactly one phrase of the variable's codelists matches and the value names
    nothing more next to it (rules 1.4.0: otherwise list_value, no term, the reached terms in terms)."""
    v = next(iter(lk.variables_for(domain, (gen,))), None) or \
        {"variable": gen, "generic": gen, "kind": None, "position": None, "meaning_status": None,
         "codelists": sorted(lk.codelist_by_generic[gen])}
    hits = scan_phrases(normalise(value).split(), [v], lk.phrases)
    terms = sorted({t for h in hits for t in h[4]})
    f = _facet(v, value, terms, where, "context field", **extra)
    f["term"] = _term_codelist(v, terms, lk.phrases)
    if names_more(value, hits):
        f["term"] = None
        f["terms"] = [{"submission_value": s, "concept_id": c} for s, c in terms]
        f["list_value"] = True
    return f


def read_group_head(head: dict, domain: str | None, lk: TestIdentityLookups) -> tuple[dict, list]:
    """Rules 1.2.0: (group_head record, facets). A facet per --METHOD / --SPEC variable whose codelist has
    the whole head text as a phrase; otherwise the head is kept as text, read False."""
    variables = lk.variables_for(domain, GROUP_HEAD_GENERICS) or lk.variables_for(None, GROUP_HEAD_GENERICS)
    tokens = normalise(head["text"]).split()
    whole = [h for h in scan_phrases(tokens, variables, lk.phrases) if h[0] == 0 and h[1] == len(tokens)]
    facets = []
    for i, j, v, g, terms, others in whole:
        f = _facet(v, head["text"], terms, "group head", "codelist phrase, whole head",
                   group_head=head["member_id"])
        f["term"] = _term_codelist(v, terms, lk.phrases)
        if others:
            f["ambiguous_with"] = others
        facets.append(f)
    return {"member_id": head["member_id"], "text": head["text"], "read": bool(facets)}, facets


# ---------------------------------------------------------------------------
# Component, collisions, specialization
# ---------------------------------------------------------------------------
def collisions_for(phrase: str | None, codes: list, lk: TestIdentityLookups) -> dict | None:
    rows = lk.collisions.get(normalise(phrase or ""), [])
    if not rows:
        return None
    theirs = sorted({r["NCIt_Code"] for r in rows})
    ours = sorted({c["code"] for c in codes})
    relation = ("equal" if set(ours) == set(theirs) else "ours fewer" if set(ours) < set(theirs)
                else "ours more" if set(ours) > set(theirs) else "different")
    return {"string": rows[0]["String"], "concepts": theirs, "ours": ours, "relation": relation,
            "rows": [{"NCIt_Code": r["NCIt_Code"], "TESTCD": r["TESTCD"], "TEST": r["TEST"],
                      "Codelists": r["Codelists"], "Shared_Via": r["Shared_Via"],
                      "Case_Differs": r["Case_Differs"] or None} for r in rows]}


def specialization(domain: str | None, codes: list, facets: list, lk: TestIdentityLookups) -> dict:
    if not codes:
        return {"level": "no component"}
    if len(codes) > 1:
        return {"level": "component open", "codes": [c["testcd"] for c in codes]}
    if not domain:
        return {"level": "domain open"}
    c = codes[0]
    specs = lk.specializations.get((domain, c["testcd"], c["code"]), [])
    if not specs:
        return {"level": "no specialization"}
    key = lambda s: s["observable_key"] or s["ds_id"]
    observables = {key(s) for s in specs}
    out = {"specializations": [s["ds_id"] for s in specs],
           "differ_by": [p for p, f in (("system", "spec_ncit"), ("method", "method_ncit"), ("scale", "scale"))
                         if len({s[f] for s in specs}) > 1]}
    if len(observables) == 1:
        return {"level": "one specialization"} | out
    stated = {}
    for f in facets:
        if f["position"] in IDENTITY_POSITIONS and f["term"] and not f.get("ambiguous_with"):
            stated.setdefault(f["position"], set()).add(f["term"]["concept_id"])
    conflicts = sorted(p for p, ids in stated.items() if len(ids) > 1)
    remaining = specs
    selected_by = []
    for pos, field in (("system", "spec_ncit"), ("method", "method_ncit")):
        ids = stated.get(pos)
        if ids and len(ids) == 1:
            cid = next(iter(ids))
            remaining = [s for s in remaining if s[field] == cid]
            selected_by.append({"position": pos, "concept_id": cid})
    out |= {"stated": selected_by, "conflicting_positions": conflicts}
    if conflicts:
        return {"level": "stated facets conflict"} | out
    if selected_by and not remaining:
        return {"level": "stated facet matches no specialization"} | out
    if len({key(s) for s in remaining}) == 1:
        return {"level": "selected by stated facets", "selected": [s["ds_id"] for s in remaining]} | out
    return {"level": "facet not stated", "remaining": [s["ds_id"] for s in remaining],
            "not_stated": [p for p, f in (("system", "spec_ncit"), ("method", "method_ncit"), ("scale", "scale"))
                           if len({s[f] for s in remaining}) > 1]} | out


def ecg_component(text: str, pointer: str, lk: TestIdentityLookups) -> dict:
    attempt, hits = lk.grain.test_hit(text)
    dom = lambda h: [d.strip() for d in h["domains"].split(";")]
    eg = {h["code"]: h for h in hits if "EG" in dom(h)}
    outside = sorted({(h["submission_value"], h["domains"]) for h in hits if "EG" not in dom(h)})
    codes = [{"code": h["code"], "testcd": h["submission_value"], "domains": dom(h)} for h in eg.values()]
    via = "SDTM_Test_Identity" if codes else None
    family = None
    head_rows = lk.folded_by_head.get(normalise(text), [])
    if codes:
        r = lk.folded_by_testcd.get(codes[0]["testcd"]) if len(codes) == 1 else None
        head_rows = lk.folded_by_head.get(normalise(r["Head"]), []) if r else []
    elif head_rows:
        via = "Folded_Facets head"
    if head_rows:
        family = {"head": head_rows[0]["Head"], "testcds": sorted(r["TESTCD"] for r in head_rows),
                  "tails": sorted({r["Tail"] for r in head_rows}),
                  "evidence": sorted({r["Evidence"] for r in head_rows})}
    level = ("test family, beat not stated" if family and len(family["testcds"]) > 1
             else "component open" if len(codes) > 1 else "test code" if codes or family else "no component")
    return {"text": text, "pointer": pointer, "attempt": attempt if codes else None, "via": via,
            "codes": codes, "outside_eg": [{"testcd": t, "domains": d} for t, d in outside],
            "family": family, "level": level}


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------
def hit_part(text: str, ti: dict, lk: TestIdentityLookups) -> str | None:
    """The part of the label that hit the test, as the grain found it: the peeled rest (L1x), the text
    outside the trailing parenthesis (qualifier dropped), else the whole phrase."""
    if not ti:
        return None
    reasons = ti.get("weak_reasons") or []
    if "peeled" in reasons:
        peeled = peel_label(text, lk.grain)
        return peeled[0] if peeled else ti.get("phrase")
    if "qualifier dropped" in reasons:
        return normalise(split_trailing_parens(text)[0])
    if lk.grain.test_hit(text)[0] == "restated":
        # grain rules 1.4.0: the parenthesis restates the component; the head hit the test
        return normalise(split_trailing_parens(text)[0])
    return ti.get("phrase")


def _domain(row: dict) -> str | None:
    if row["domain"]:
        return row["domain"]
    c = row.get("candidates") or []
    return c[0] if len(c) == 1 else None


def _dedupe(facets: list) -> list:
    seen, out = set(), []
    for f in facets:
        k = (f["variable"], normalise(f["value"]), f["where"], f.get("pointer"))
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def study_record(row: dict, ctx: dict | None, members: dict, lk: TestIdentityLookups,
                 group_members: dict | None = None) -> dict:
    unit = "activity" if row.get("activity_level") else "member" if "member_id" in row else "standalone"
    domain = _domain(row)
    parts_vars = lk.component_part_variables.get(domain, []) if domain else []
    variables = lk.text_variables(domain) + parts_vars
    ti = row.get("test_identity") or {}
    codes = [c for c in ti.get("codes", []) if not domain or domain in c["domains"]]
    phrase = ti.get("phrase")
    part = hit_part(row["activity_name"], ti, lk)
    all_codes = ti.get("codes", [])
    facets, conditions, again, unread = read_text(row["activity_name"], "label", variables, lk, exclude=part,
                                                  codes=all_codes)
    if unit == "member":
        m = members.get((row["xact_id"], row["member_id"])) or {}
        for q in m.get("qualifiers", []):
            f, c, a, u = read_text(q, "member qualifier", variables, lk, codes=all_codes)
            facets += f
            conditions += c
            again += a
            unread += u
        for sf in row.get("stated_facets") or []:
            if sf["facet"] == "specimen":
                facets.append(read_field(sf["value"], "--SPEC", "context panel", domain, lk,
                                         pointer=sf["context_panel"], pages=sf["pages"]))
        gm = (group_members or {}).get((row["xact_id"], row["member_id"])) or {}
        head = (group_members or {}).get((row["xact_id"], gm.get("in_group"))) if gm.get("in_group") else None
        if head:
            group_head, hf = read_group_head(head, domain, lk)
            facets += hf
    lap = {e["soa_activity"]: (i, e) for i, e in enumerate((ctx or {}).get("lab_and_purpose", []))}
    hit = lap.get(row["activity_name"]) or (lap.get(row.get("panel_name")) if unit == "member" else None)
    if hit:
        i, e = hit
        for field, gen in LAB_AND_PURPOSE_FIELDS.items():
            if e.get(field):
                facets.append(read_field(e[field], gen, "lab_and_purpose", domain, lk,
                                         pointer=f"/lab_and_purpose/{i}"))
    components = None
    if unit == "activity":
        components = []
        for i, mm in enumerate((ctx or {}).get("measurements", [])):
            if row["activity_name"] not in (mm.get("soa_activities") or []):
                continue
            for field, gens in MEASUREMENT_FIELDS.items():
                if mm.get(field):
                    f, c, _, _ = read_text(mm[field], "measurements", lk.variables_for(domain, gens) or
                                        lk.variables_for(None, gens), lk, pointer=f"/measurements/{i}/{field}")
                    facets += f
                    conditions += [x | {"pointer": f"/measurements/{i}/{field}"} for x in c]
            for j, comp in enumerate(mm.get("components") or []):
                components.append(ecg_component(comp, f"/measurements/{i}/components/{j}", lk))
    practice_text = []
    ngu = lk.not_generally_used.get(domain or "")
    if ngu:
        keep = []
        for f in facets:
            if f["generic"] in ngu["generics"]:
                practice_text.append({"variable": f["variable"], "value": f["value"], "where": f["where"],
                                      "pointer": f.get("pointer"), "statement_id": ngu["statement_id"]})
            else:
                keep.append(f)
        facets = keep
    facets = _dedupe(facets)
    part_names = {v["variable"] for v in parts_vars}
    parts = [component_part(f, lk) for f in facets if f["variable"] in part_names]
    facets = [f for f in facets if f["variable"] not in part_names]
    rec = {"xact_id": row["xact_id"]}
    if unit == "member":
        rec |= {"member_id": row["member_id"], "panel_name": row["panel_name"]}
        if head:
            rec["group_head"] = group_head
    rec |= {"activity_name": row["activity_name"], "unit": unit, "routing_status": row["status"],
            "domain": domain,
            "component": ({"phrase": phrase, "hit_part": part, "hit_strength": ti.get("hit_strength"),
                           "weak_reasons": ti.get("weak_reasons", []), "codes": codes, "restated": again,
                           "collisions": collisions_for(part, all_codes, lk)} if ti else None)}
    if components is not None:
        rec["components"] = components
    if parts_vars:
        rec["component_parts"] = parts
    rec |= {"facets": facets, "practice_text": practice_text, "conditions": conditions, "unread": unread,
            "specialization": (specialization(domain, codes, facets, lk) if unit != "activity"
                               else {"level": "per component"})}
    return rec


def generate_study_test_identity(collection: str, protocol_id: str, lk: TestIdentityLookups | None = None) -> dict:
    lk = lk or TestIdentityLookups()
    r = load_current_routing(collection, protocol_id)
    if r is None:
        raise FileNotFoundError(f"{collection}/{protocol_id}: no routing file; run soa2usdm.activity_routing")
    if r["inputs"]["cdisc_for_ai"]["commit"] != lk.provenance["commit"]:
        raise RuntimeError(f"{collection}/{protocol_id}: routing made at cdisc-for-ai "
                           f"{r['inputs']['cdisc_for_ai']['commit'][:7]}, lookups at {lk.provenance['commit'][:7]}; "
                           f"rerun the grain, panel members and routing")
    cpath = context_path(protocol_id, collection)
    ctx = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else None
    pcm = load_current_panel_members(collection, protocol_id)
    members = {(pr["xact_id"], m["member_id"]): m for pr in (pcm["rows"] if pcm else []) for m in pr["members"]}
    # rules 1.2.0: label members (grain) and context members, for the group head of a member
    gpath = grain_path(protocol_id, collection)
    g = json.loads(gpath.read_text(encoding="utf-8"))
    labels = {lb["phrase"]: lb for lb in g["labels"]}
    group_members = dict(members)
    for a in g["activities"]:
        for m in (labels.get(a["phrase"]) or {}).get("members", []):
            group_members[(a["xact_id"], m["member_id"])] = m
    rows = [study_record(row, ctx, members, lk, group_members) for row in r["rows"]]
    by_unit = defaultdict(Counter)
    for x in rows:
        if x["unit"] == "activity":
            for c in x["components"]:
                by_unit["activity components"][c["level"]] += 1
        else:
            by_unit[x["unit"]][x["specialization"]["level"]] += 1
    sha = lambda p: _sha256_bytes(p.read_bytes()) if p.exists() else None
    return {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
        "collection": collection, "protocol_id": protocol_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rules_version": RULES_VERSION, "word_lists_date": WORD_LISTS_DATE,
        "inputs": {"activity_routing": {"schema_version": r["schema_version"],
                                        "sha256": sha(routing_path(protocol_id, collection))},
                   "activity_grain": {"schema_version": g["schema_version"], "sha256": sha(gpath)},
                   "panel_context_members": {"sha256": sha(panels_path(protocol_id, collection))} if pcm else None,
                   "protocol_context": {"sha256": sha(cpath)} if ctx else None,
                   "cdisc_for_ai": lk.provenance},
        "not_generally_used": lk.not_generally_used,
        "counts": {"rows": len(rows),
                   "levels": {u: dict(sorted(c.items())) for u, c in sorted(by_unit.items())},
                   "facets": dict(sorted(Counter(f["variable"] for x in rows for f in x["facets"]).items())),
                   "facets_with_term": sum(1 for x in rows for f in x["facets"] if f["term"]),
                   "component_parts": dict(sorted(Counter(f"{p['variable']} {p['hit_strength']}" for x in rows
                                                          for p in x.get("component_parts", [])).items())),
                   "practice_text": sum(len(x["practice_text"]) for x in rows),
                   "rows_with_conditions": sum(1 for x in rows if x["conditions"]),
                   "rows_with_unread": sum(1 for x in rows if x["unread"]),
                   "rows_with_collisions": sum(1 for x in rows if (x["component"] or {}).get("collisions")),
                   "group_heads": dict(sorted(Counter("read" if x["group_head"]["read"] else "not read"
                                                      for x in rows if x.get("group_head")).items()))},
        "rows": rows,
    }


def write_study_test_identity(collection: str, protocol_id: str, lk: TestIdentityLookups | None = None) -> Path:
    payload = generate_study_test_identity(collection, protocol_id, lk)
    out = test_identity_path(protocol_id, collection)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Test identity (test code + facets + specialization level), per study.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", help="one study; default: every study of the collection with a routing file")
    args = ap.parse_args()
    root = config.COLLECTIONS[args.collection]
    pids = [args.protocol] if args.protocol else sorted(
        p.name for p in root.iterdir()
        if (p / "SoA2USDM" / "routing" / f"{p.name}_activity_routing.json").exists())
    lk = TestIdentityLookups()
    for pid in pids:
        print(write_study_test_identity(args.collection, pid, lk))


if __name__ == "__main__":
    main()
