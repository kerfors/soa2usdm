"""
SoA2USDM Activity Grain (per-study sidecar to the activity inventory)

Tags the grain of every activity of a study, as a first step towards matching
activities to CDISC:

    named test / panel / procedure / instrument / sample collection / other / unsure

plus structural roles that take a row out of the grain count:

    section header / specimen of parent / redacted

and, for a named test, the kind of finding:

    specimen / immunogenicity / measurement / instrument / pc / genomics / unsure

Rules, each one cited on the row: the rule that fired, the lookup hit (file,
sheet, field, code) and source = rule. Rule K1 gives the kind of a rule-hit
named test from the hit's domains through Domain_Coverage. AI proposals and
review decisions come from a hand-kept decisions file (source ai_proposed /
reviewed). Design and rule table: documents/activity-grain.md.

Lookups: public cdisc-for-ai files only (SDTM_Test_Identity,
SDTM_Instrument_Identity, Codelist_Phrases, Domain_Coverage), read with
keep_default_na=False. cdisc-for-ai is found as a sibling checkout
(../cdisc-for-ai), or through the SOA2USDM_CDISC_FOR_AI environment variable.

Name normalisation is the rule of the Codelist_Phrases ReadMe, so labels and
lookups normalise the same way: lower-case, split on every character that is
not a letter A-Z / a-z or a digit 0-9, parts joined by one space; a string
with no letter or digit keeps its own characters, lower-cased, without
whitespace. No plural or stemming. Rules run once per distinct phrase of a study.

Input: the study's rows as the activity inventory builds them
(activity_inventory.collect_rows), and the study's consolidated.json for
parents (parent_xact_id) and annotation ids.

Output: SoA2USDM/grain/<id>_activity_grain.json (schema_name
soa2usdm-activity-grain, schema_version 1.2). The inventory is not changed.

Decisions: SoA2USDM/grain/<id>_activity_grain_decisions.json (read only here;
schema soa2usdm-activity-grain-decisions 1.2), keyed by phrase within the
study. The rule result is kept on the label beside the decision. ai_proposed
decisions are made by prompts/ACTIVITY_GRAIN_DECISIONS_PROMPT.md from the
study's grain inputs file (soa2usdm.activity_grain_inputs), and only for the
phrases that file lists; the generator checks that the inputs file is current.
"""

import hashlib
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config

SCHEMA_NAME = "soa2usdm-activity-grain"
SCHEMA_VERSION = "1.3"
SCHEMA_VERSIONS = ("1.0", "1.1", "1.2", "1.3")
RULES_VERSION = "1.0.0"
WORD_LISTS_DATE = "2026-11-01"

CDISC_FOR_AI = Path(os.environ.get(
    "SOA2USDM_CDISC_FOR_AI",
    Path(__file__).resolve().parent.parent.parent / "cdisc-for-ai"))

LOOKUP_FILES = {
    "SDTM_Test_Identity": ("sdtm-test-codes/machine_actionable/SDTM_Test_Identity.xlsx", "Test Codes"),
    "SDTM_Instrument_Identity": ("sdtm-test-codes/machine_actionable/SDTM_Instrument_Identity.xlsx", "Instruments"),
    "Codelist_Phrases": ("sdtm-findings-graph/machine_actionable/Codelist_Phrases.xlsx", "Phrases"),
    "Domain_Coverage": ("sdtm-findings-graph/machine_actionable/Domain_Coverage.xlsx", "Domain_Coverage"),
}
# Codelists of Codelist_Phrases used here, and the grain a whole-label hit gives.
PHRASE_CODELIST_GRAIN = {"QSCAT": "instrument", "METHOD": "procedure", "SPECTYPE": "sample collection"}

GRAINS = ("named test", "panel", "procedure", "instrument", "sample collection", "other", "unsure")
ROLES = ("section header", "specimen of parent", "redacted")
FINDING_KINDS = ("specimen", "immunogenicity", "measurement", "instrument", "pc", "genomics", "unsure")
# K1: kind of a named test from its domains. A domain here is taken before the
# Consumer column of Domain_Coverage (PC sits in the Specimen_Findings scope,
# GF has no Consumer); the other domains by their Consumer.
DOMAIN_KIND = {"PC": "pc", "GF": "genomics"}
CONSUMER_KIND = {"Specimen_Findings": "specimen", "Immunogenicity_Findings": "immunogenicity",
                 "Measurement_Findings": "measurement", "Instrument_Findings": "instrument"}

# ---------------------------------------------------------------------------
# Dated word lists (WORD_LISTS_DATE). Matched on whole normalised tokens of the
# label text outside parentheses; no stemming, so 'tests' is not 'test'.
# ---------------------------------------------------------------------------
PANEL_WORDS = {
    "panel", "panels", "parameters", "profile", "chemistry", "chemistries",
    "hematology", "haematology", "coagulation", "serology", "serologies",
    "urinalysis", "tests", "markers", "assays", "assessments", "lfts", "cbc",
}
SAMPLE_WORDS = {"sample", "samples", "sampling", "specimen", "specimens", "biospecimen", "banked", "spare"}
# 'collection' fires only when the label also contains a SPECTYPE phrase
# ('Lymphoma tissue collection'), not for 'Collection of e-diary device'.
SAMPLE_WORDS_GATED = {"collection"}
PROCEDURE_WORDS = {
    "biopsy", "aspirate", "aspiration", "ultrasound", "mri", "ct", "pet", "x ray", "xray",
    "scan", "echo", "echocardiogram", "muga", "ecg", "electrocardiogram", "fibroscan",
    "endoscopy", "colonoscopy", "dxa", "dexa", "imaging",
}
ADMINISTRATIVE_WORDS = {
    "consent", "eligibility", "inclusion", "exclusion", "criteria", "randomization",
    "randomisation", "enrollment", "enrolment", "registration", "diary", "diaries", "ediary",
    "phone", "telephone", "call", "contact", "discharge", "dispensing", "dispense",
    "accountability", "compliance", "order", "administration", "administer", "infusion",
    "dosing", "dose", "imp", "ip", "reminder",
}
RECORD_WORDS = {
    "adverse", "ae", "aes", "concomitant", "history", "demographics", "demography",
    "medication", "medications",
}
WORD_CLASSES = (
    ("W1", "sample collection", SAMPLE_WORDS),
    ("W2", "procedure", PROCEDURE_WORDS),
    ("W3", "other", ADMINISTRATIVE_WORDS),
    ("W4", "other", RECORD_WORDS),
)
# A parenthesis that starts with one of these is a qualifier (condition,
# population, arm, lab site), never a member list.
QUALIFIER_CUES = ("if ", "for ", "at ", "only", "cohort", "part ", "parts ", "arm",
                  "central", "local", "include", "in ", "as ", "when ", "per ")
LIST_SEPARATORS = r",|\band\b|&|/"

TEST_FIELDS = (("TESTCD", "TESTCD", "CT"), ("TEST", "TEST", "CT"),
               ("NCIt_Preferred_Term", "NCIt_Preferred_Term", "CT"),
               ("NCIt_Synonyms", "NCIt_Synonyms", "NCIt"))
INSTRUMENT_FIELDS = (("Codelist_TESTCD", "Codelist_TESTCD", "CT"),
                     ("Instrument_Label", "Instrument_Label", "CT"),
                     ("Instrument_NCIt_Preferred_Term", "Instrument_NCIt_Preferred_Term", "NCIt"),
                     ("Instrument_NCIt_Synonyms", "Instrument_NCIt_Synonyms", "NCIt"))


def normalise(text: str) -> str:
    """Codelist_Phrases NORMALISATION rule."""
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", text.lower()) if p]
    return " ".join(parts) if parts else "".join(text.lower().split())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
class Lookups:
    """Phrase indexes over the public cdisc-for-ai files."""

    def __init__(self, root: Path = CDISC_FOR_AI):
        if not root.is_dir():
            raise FileNotFoundError(f"cdisc-for-ai checkout not found at {root} "
                                    f"(set SOA2USDM_CDISC_FOR_AI)")
        self.root = root
        self.provenance = self._provenance()
        self.test = defaultdict(list)
        self.test_compact = defaultdict(list)
        self.instrument = defaultdict(list)
        self.phrase = defaultdict(list)
        self.spectype_phrases = set()
        self.consumer = {}
        self.domain_rows = {}
        self.test_by_code = {}
        self.instrument_by_code = {}
        self.phrase_codes = set()
        self._load_tests()
        self._load_instruments()
        self._load_phrases()
        self._load_domain_coverage()

    def _read(self, key):
        import pandas as pd  # lookups only: the pages read grain files without pandas
        rel, sheet = LOOKUP_FILES[key]
        return pd.read_excel(self.root / rel, sheet_name=sheet, keep_default_na=False, dtype=str)

    def _provenance(self) -> dict:
        import pandas as pd
        commit = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        rels = [rel for rel, _ in LOOKUP_FILES.values()]
        dirty = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain", "--", *rels],
                               capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            raise RuntimeError(f"cdisc-for-ai lookup files have uncommitted changes:\n{dirty}")
        files = []
        for key, (rel, sheet) in LOOKUP_FILES.items():
            prov = pd.read_excel(self.root / rel, sheet_name="Provenance", keep_default_na=False, dtype=str)
            pv = dict(zip(prov["Key"], prov["Value"]))
            files.append({
                "file": key, "path": rel, "sheet": sheet,
                "file_sha256": _sha256(self.root / rel),
                "sheet_content_sha256": pv[f"{sheet}.Content_SHA256"],
                "generated": pv["Generated"],
                "sdtm_ct": pv["SDTM_CT"], "ncit": pv["NCIt"],
            })
        versions = json.loads((self.root / "Reference_Versions.json").read_text(encoding="utf-8"))
        return {"commit": commit, "reference_versions": versions, "files": files}

    def _load_tests(self):
        for r in self._read("SDTM_Test_Identity").to_dict("records"):
            self.test_by_code[r["NCIt_Code"]] = {"testcd": r["TESTCD"], "test": r["TEST"],
                                                 "domains": r["SDTM_Domains"]}
            for col, field, source in TEST_FIELDS:
                values = r[col].split("|") if col == "NCIt_Synonyms" else [r[col]]
                for v in values:
                    if not v.strip():
                        continue
                    hit = {"file": "SDTM_Test_Identity", "sheet": "Test Codes", "field": field,
                           "source": source, "as_published": v.strip(), "code": r["NCIt_Code"],
                           "submission_value": r["TESTCD"], "domains": r["SDTM_Domains"]}
                    phrase = normalise(v)
                    self.test[phrase].append(hit)
                    self.test_compact[phrase.replace(" ", "")].append(hit)

    def _load_instruments(self):
        for r in self._read("SDTM_Instrument_Identity").to_dict("records"):
            self.instrument_by_code[r["Codelist_NCIt_Code"]] = {"testcd": r["Codelist_TESTCD"],
                                                                "test": r["Instrument_Label"],
                                                                "domains": r["Domain"]}
            for col, field, source in INSTRUMENT_FIELDS:
                values = r[col].split("|") if col == "Instrument_NCIt_Synonyms" else [r[col]]
                for v in values:
                    if not v.strip():
                        continue
                    self.instrument[normalise(v)].append({
                        "file": "SDTM_Instrument_Identity", "sheet": "Instruments", "field": field,
                        "source": source, "as_published": v.strip(), "code": r["Codelist_NCIt_Code"],
                        "submission_value": r["Codelist_TESTCD"], "domains": r["Domain"]})

    def _load_phrases(self):
        for r in self._read("Codelist_Phrases").to_dict("records"):
            if r["codelist_submission_value"] not in PHRASE_CODELIST_GRAIN:
                continue
            self.phrase_codes.add((r["codelist_submission_value"], r["term_concept_id"]))
            self.phrase[r["phrase"]].append({
                "file": "Codelist_Phrases", "sheet": "Phrases", "field": r["field"],
                "source": r["source"], "as_published": r["as_published"], "code": r["term_concept_id"],
                "submission_value": r["term_submission_value"],
                "codelist": r["codelist_submission_value"],
                "terms_in_codelist": int(r["terms_in_codelist"])})
            if r["codelist_submission_value"] == "SPECTYPE":
                self.spectype_phrases.add(r["phrase"])

    def _load_domain_coverage(self):
        for r in self._read("Domain_Coverage").to_dict("records"):
            self.consumer[r["Domain"]] = r["Consumer"]
            self.domain_rows[r["Domain"]] = {"domain": r["Domain"], "domain_name": r["Domain_Name"],
                                             "observation_class": r["Observation_Class"],
                                             "consumer": r["Consumer"]}

    def whole(self, phrase: str):
        """All whole-phrase hits, keyed by the grain they give, in rule order."""
        out = []
        if phrase in self.test:
            out.append(("L1", "named test", self.test[phrase]))
        inst = list(self.instrument.get(phrase, []))
        inst += [h for h in self.phrase.get(phrase, []) if h["codelist"] == "QSCAT"]
        if inst:
            out.append(("L2", "instrument", inst))
        for rule, codelist in (("L3", "METHOD"), ("L4", "SPECTYPE")):
            hits = [h for h in self.phrase.get(phrase, []) if h["codelist"] == codelist]
            if hits:
                out.append((rule, PHRASE_CODELIST_GRAIN[codelist], hits))
        return out

    def test_hit(self, text: str):
        """Test lookup for a list member: whole phrase, then compact, then
        outside a trailing parenthesis. Returns (attempt, hits) or (None, [])."""
        phrase = normalise(text)
        if phrase in self.test:
            return "whole", self.test[phrase]
        if phrase.replace(" ", "") in self.test_compact:
            return "compact", self.test_compact[phrase.replace(" ", "")]
        outer, quals = split_trailing_parens(text)
        if quals and normalise(outer) in self.test:
            return "qualifier dropped", self.test[normalise(outer)]
        return None, []


# ---------------------------------------------------------------------------
# Hit strength — facts about the hit, used for review flags and the measures
# ---------------------------------------------------------------------------
def hit_strength(hits: list, attempt: str = "whole") -> tuple[str, list]:
    """('strong' | 'weak', reasons). Strong: one code, matched on a CT-published
    field, on the whole phrase, not only through a short submission value."""
    reasons = []
    codes = {h["code"] for h in hits}
    if len(codes) > 1:
        reasons.append("several codes")
    if not any(h["source"] == "CT" for h in hits):
        reasons.append("NCIt synonym only")
    if attempt != "whole":
        reasons.append(attempt)
    if all(len(h["as_published"]) <= 3 for h in hits):
        reasons.append("short code only")
    if any(h.get("terms_in_codelist", 1) > 1 for h in hits):
        reasons.append("phrase names several terms in codelist")
    return ("weak" if reasons else "strong"), reasons


def _cite(hits: list) -> list:
    """Distinct hits, compact, for the sidecar."""
    seen, out = set(), []
    for h in hits:
        key = (h["file"], h["code"], h["field"], h.get("codelist"))
        if key in seen:
            continue
        seen.add(key)
        out.append({k: h[k] for k in ("file", "sheet", "field", "source", "code",
                                      "submission_value", "as_published")
                    if k in h} | ({"codelist": h["codelist"]} if "codelist" in h else {})
                   | ({"domains": h["domains"]} if "domains" in h else {}))
    return out


def finding_kind(hits: list, lk: Lookups) -> dict:
    """K1: kind of a named test from the domains of its hits (SDTM_Domains,
    '; '-separated), through DOMAIN_KIND, then the Domain_Coverage Consumer.
    One kind for all domains, or 'unsure' with a flag; when the domains give
    two or more kinds, those kinds are the kind_candidates."""
    domains = sorted({d.strip() for h in hits for d in h["domains"].split(";") if d.strip()})
    kinds = {}
    for d in domains:
        if d not in lk.consumer:
            raise ValueError(f"domain {d!r} of a test hit is not in Domain_Coverage")
        kinds[d] = DOMAIN_KIND.get(d) or CONSUMER_KIND.get(lk.consumer[d])
    out = {"finding_kind": "unsure", "kind_rule": "K1", "kind_domains": domains, "kind_candidates": [],
           "flags": []}
    distinct = set(kinds.values())
    if len(distinct) == 1 and None not in distinct:
        out["finding_kind"] = distinct.pop()
    else:
        if len(distinct - {None}) >= 2:
            out["kind_candidates"] = sorted(distinct - {None})
        out["flags"].append("kind: " + (", ".join(f"{d} {kinds[d] or 'no Consumer'}" for d in domains)
                                       if domains else "hit has no domain"))
    return out


def domain_kind(domain: str, lk: Lookups) -> str | None:
    """The kind one domain gives (the K1 step for a single domain); None when
    the domain has no kind. Fails on a domain not in Domain_Coverage."""
    if domain not in lk.consumer:
        raise ValueError(f"domain {domain!r} is not in Domain_Coverage")
    return DOMAIN_KIND.get(domain) or CONSUMER_KIND.get(lk.consumer[domain])


def _cdisc_basis_kinds(b: dict, lk: Lookups, where: str) -> set:
    """Check one cdisc basis entry against the lookups; return the kinds it
    supports (empty for a Codelist_Phrases entry)."""
    f = b.get("file")
    if f not in CDISC_BASIS_KEYS or set(b) != {"type", "file"} | CDISC_BASIS_KEYS[f]:
        raise ValueError(f"{where}: cdisc basis entry not understood: {b}")
    if f == "Domain_Coverage":
        if b["domain"] not in lk.domain_rows:
            raise ValueError(f"{where}: domain {b['domain']!r} is not in Domain_Coverage")
        return {domain_kind(b["domain"], lk)} - {None}
    if f == "Codelist_Phrases":
        if (b["codelist"], b["code"]) not in lk.phrase_codes:
            raise ValueError(f"{where}: {b['code']!r} is not a {b['codelist']} term in Codelist_Phrases")
        return set()
    index = lk.test_by_code if f == "SDTM_Test_Identity" else lk.instrument_by_code
    if b["code"] not in index:
        raise ValueError(f"{where}: {b['code']!r} is not in {f}")
    if index[b["code"]]["testcd"] != b["testcd"]:
        raise ValueError(f"{where}: {b['code']} is {index[b['code']]['testcd']!r} in {f}, not {b['testcd']!r}")
    domains = [d.strip() for d in index[b["code"]]["domains"].split(";") if d.strip()]
    return {domain_kind(d, lk) for d in domains} - {None}


# ---------------------------------------------------------------------------
# Label text
# ---------------------------------------------------------------------------
def split_trailing_parens(text: str) -> tuple[str, list]:
    """Split off parenthesised groups at the end of a label."""
    quals = []
    s = text.strip()
    while True:
        m = re.search(r"\(([^()]*)\)\s*[:.]?\s*$", s)
        if not m:
            return s, quals
        quals.insert(0, m.group(1).strip())
        s = s[:m.start()].strip()


def _is_member_list(content: str) -> bool:
    return (re.search(LIST_SEPARATORS, content) is not None
            and not content.strip().lower().startswith(QUALIFIER_CUES))


def _split_members(text: str) -> list:
    return [m.strip(" .:;-") for m in re.split(LIST_SEPARATORS, text) if m.strip(" .:;-")]


def _tokens(text: str) -> set:
    phrase = normalise(text)
    toks = set(phrase.split())
    words = phrase.split()
    toks |= {" ".join(words[i:i + 2]) for i in range(len(words) - 1)}
    return toks


def _contains_spectype(phrase: str, spectype: set) -> list:
    words = phrase.split()
    found = []
    for n in range(len(words), 0, -1):
        for i in range(len(words) - n + 1):
            g = " ".join(words[i:i + n])
            if g in spectype:
                found.append(g)
    return found


def _drop_short_code_tests(whole: list, flags: list) -> list:
    """A test hit only through a string of three characters or fewer is no hit
    ('PK' is pyruvate kinase, 'PGI' pepsinogen I); it is kept as a flag."""
    out = []
    for rule, grain, hits in whole:
        if rule == "L1" and "short code only" in hit_strength(hits)[1]:
            flags.append("short code only, not taken: " + ", ".join(sorted(
                {f"{h['submission_value']} ({h['domains']})" for h in hits})))
            continue
        out.append((rule, grain, hits))
    return out


def label_grain(text: str, lk: Lookups) -> dict:
    """Grain of one distinct label. Rules in order; the first that fires wins."""
    phrase = normalise(text)
    rec = {"phrase": phrase, "grain": "unsure", "rule_id": None, "hits": [], "hit_strength": None,
           "weak_reasons": [], "qualifiers": [], "members": [], "flags": [],
           "finding_kind": None, "kind_rule": None, "kind_domains": [], "kind_candidates": []}
    if re.search(r"[^\x00-\x7f]", text):
        rec["flags"].append("non-ASCII characters split by normalisation")

    def take(rule, grain, hits, attempt="whole"):
        rec.update(grain=grain, rule_id=rule, hits=_cite(hits))
        rec["hit_strength"], rec["weak_reasons"] = hit_strength(hits, attempt)
        if grain == "named test":
            k = finding_kind(hits, lk)
            rec["flags"] += k.pop("flags")
            rec.update(k)
        return rec

    # L1-L4: whole-label lookups
    whole = _drop_short_code_tests(lk.whole(phrase), rec["flags"])
    if whole:
        rule, grain, hits = whole[0]
        if len(whole) > 1:
            rec["flags"].append("hits in several lookups: " + ", ".join(r for r, _, _ in whole))
        return take(rule, grain, hits)

    # L4F: a SPECTYPE phrase followed by 'for' ('Plasma for ctDNA')
    m = re.match(r"^(.*?)\s+for\s+", phrase)
    if m and m.group(1) in lk.spectype_phrases:
        return take("L4F", "sample collection",
                    [h for h in lk.phrase[m.group(1)] if h["codelist"] == "SPECTYPE"])

    outer, quals = split_trailing_parens(text)
    rec["qualifiers"] = quals
    spec_q = [h for q in quals for h in lk.phrase.get(normalise(q), []) if h["codelist"] == "SPECTYPE"]
    if spec_q:
        rec["specimen_qualifier_hits"] = _cite(spec_q)
    # L1q-L4q: lookups with the trailing parentheses removed (always weak)
    if quals:
        whole = _drop_short_code_tests(lk.whole(normalise(outer)), rec["flags"])
        if whole:
            rule, grain, hits = whole[0]
            return take(rule + "q", grain, hits, "qualifier dropped")
        # L1a-L2a: one-item parenthesis alone ('PHQ-9'). Test and instrument
        # hits only: a specimen or method in parentheses qualifies the label
        # ('TBNK (blood)'); a hit only through a short code is no hit ('(CL)').
        for q in quals:
            if not re.search(LIST_SEPARATORS, q):
                for rule, grain, hits in lk.whole(normalise(q)):
                    if rule in ("L1", "L2") and "short code only" not in hit_strength(hits)[1]:
                        return take(rule + "a", grain, hits, "parenthesis content")

    # W1-W4: dated word lists on the head of the label: the text outside
    # parentheses, before ' for ' ('X for eligibility check' is not administrative)
    outside = re.sub(r"\([^()]*\)", " ", text)
    toks = _tokens(outside)
    head_toks = _tokens(re.split(r"\bfor\b", outside, maxsplit=1, flags=re.I)[0])
    fired = []
    for rule, grain, words in WORD_CLASSES:
        w = sorted(head_toks & words)
        if w:
            fired.append((rule, grain, w))
    if head_toks & SAMPLE_WORDS_GATED:
        st = _contains_spectype(normalise(text), lk.spectype_phrases)
        if st:
            fired.append(("W1g", "sample collection", sorted(head_toks & SAMPLE_WORDS_GATED) + [f"SPECTYPE '{st[0]}'"]))
    if fired:
        grains = {g for _, g, _ in fired}
        rec["words"] = {r: w for r, _, w in fired}
        if len(grains) == 1:
            rec.update(grain=fired[0][1], rule_id="+".join(r for r, _, _ in fired))
        else:
            rec.update(grain="unsure", rule_id="W-conflict")
            rec["flags"].append("word lists disagree: " + ", ".join(f"{r} {g}" for r, g, _ in fired))
        return rec

    # Lists: inside a parenthesis (not mid-label, not a qualifier) and outside.
    # A list counts when at least two of its members hit a test.
    lists = []
    for q in quals:
        if _is_member_list(q):
            lists.append(("parenthesis", _split_members(q)))
    outer_members = _split_members(outer)
    if len(outer_members) > 1:
        lists.append(("label", outer_members))
    members = []
    for where, ms in lists:
        looked = []
        for mtext in ms:
            attempt, hits = lk.test_hit(mtext)
            entry = {"text": mtext, "phrase": normalise(mtext), "from": where}
            if hits:
                strength, reasons = hit_strength(hits, attempt)
                entry |= {"hits": _cite(hits), "hit_strength": strength, "weak_reasons": reasons}
            looked.append(entry)
        if sum(1 for e in looked if "hits" in e) >= 2:
            members += looked
    rec["members"] = members

    panel_words = sorted(toks & PANEL_WORDS)
    if panel_words:
        rec.update(grain="panel", rule_id="P1")
        rec["words"] = {"P1": panel_words}
        return rec
    if members:
        rec.update(grain="panel", rule_id="P2")
        return rec
    rec["rule_id"] = "none"
    return rec


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------
DECISIONS_SCHEMA = "soa2usdm-activity-grain-decisions"
DECISION_SOURCES = ("ai_proposed", "reviewed")
DECISIONS_SCHEMA_VERSIONS = ("1.0", "1.1", "1.2", "1.3")
# Basis entry type → its keys besides 'type'.
BASIS_TYPES = {"label": set(), "annotation": {"xannot_id"}, "context": {"pointer"}, "page": {"page"}}
# cdisc basis (decisions 1.1): file → its keys besides 'type' and 'file'.
CDISC_BASIS_KEYS = {"Domain_Coverage": {"domain"}, "SDTM_Test_Identity": {"code", "testcd"},
                    "SDTM_Instrument_Identity": {"code", "testcd"}, "Codelist_Phrases": {"codelist", "code"}}


def grain_dir(protocol_id: str, collection: str) -> Path:
    return config.get_soa2usdm_folder(protocol_id, collection) / "grain"


def grain_path(protocol_id: str, collection: str) -> Path:
    return grain_dir(protocol_id, collection) / f"{protocol_id}_activity_grain.json"


def decisions_path(protocol_id: str, collection: str) -> Path:
    return grain_dir(protocol_id, collection) / f"{protocol_id}_activity_grain_decisions.json"


def inputs_path(protocol_id: str, collection: str) -> Path:
    return grain_dir(protocol_id, collection) / f"{protocol_id}_grain_inputs.json"


def context_path(protocol_id: str, collection: str) -> Path:
    return (config.get_soa2usdm_folder(protocol_id, collection) / "context"
            / f"{protocol_id}_protocol_context.json")


def rows_sha256(rows: list) -> str:
    """SHA-256 of a study's inventory rows as canonical JSON (sorted keys, compact)."""
    text = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def study_rows(collection: str, protocol_id: str, all_rows: list | None = None) -> list:
    """The study's rows as the activity inventory builds them (collect_rows)."""
    if all_rows is None:
        from .activity_inventory import collect_rows
        all_rows = collect_rows(collection)
    rows = [r for r in all_rows if r["protocol_id"] == protocol_id]
    if not rows:
        raise ValueError(f"{collection}/{protocol_id}: no activities in the inventory")
    return rows


def pages_covered(text: str) -> set:
    """Protocol context pages_covered ('1-113', '268-423', '1-5, 7') as a set
    of page numbers. Fails on any other form."""
    pages = set()
    for part in text.split(","):
        m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", part)
        if not m:
            raise ValueError(f"pages_covered not understood: {text!r}")
        lo = int(m.group(1))
        hi = int(m.group(2) or lo)
        pages |= set(range(lo, hi + 1))
    return pages


def resolve_pointer(doc, pointer: str):
    """JSON Pointer (RFC 6901) into doc. Fails when it does not resolve or
    names the whole document."""
    if not pointer.startswith("/") or pointer == "/":
        raise ValueError(f"pointer must name an entry: {pointer!r}")
    node = doc
    for raw in pointer[1:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list) and key.isdigit() and int(key) < len(node):
            node = node[int(key)]
        elif isinstance(node, dict) and key in node:
            node = node[key]
        else:
            raise ValueError(f"pointer does not resolve: {pointer!r}")
    return node


def _load_decisions(protocol_id: str, collection: str, labels: dict, context: dict | None,
                    annotation_ids: set, lk: Lookups, inputs: dict | None) -> tuple[dict, str | None]:
    """Read the study's decisions file (never written here), if present.
    Keyed by phrase. Returns (decisions by phrase, sha256 of the file or None).

    inputs: the study's current grain inputs file as {"sha256", "content_sha256",
    "phrases"}, or None when it has none.

    Fails fast on: a phrase not in the study (stale); an unknown grain, kind or
    source; ai_proposed on a phrase the grain inputs file does not list, in a
    1.0 file, without prompt_version, without inputs_content_sha256 in a 1.3
    file, without inputs_sha256 or inputs_content_sha256 in a 1.1 / 1.2 file,
    with an inputs_content_sha256 outside a 1.3 file, with an
    inputs_content_sha256 that is not the current inputs file's content_sha256,
    or (without inputs_content_sha256) with an inputs_sha256 that is not the
    current inputs file's sha256; a named test with a kind other than
    unsure decided by ai_proposed without a cdisc basis entry giving that kind;
    a cdisc basis entry whose domain, code, TESTCD or codelist term is not as
    published; kind_candidates outside a 1.2 file, without finding_kind unsure,
    with fewer than two kinds, or with a kind no cited cdisc entry gives; two
    decisions for one phrase; finding_kind missing on a named
    test or present on another grain; an empty basis or a basis entry of unknown shape; an xannot_id not in the
    study's consolidated.json; a context pointer that does not resolve; a page
    outside the context's pages_covered; a context or page basis without a
    protocol context file; a protocol_context record that differs from the
    current context file (sha256, prompt_version).
    The decision is recorded on the label; the rule result stays beside it."""
    path = decisions_path(protocol_id, collection)
    if not path.exists():
        return {}, None
    raw = path.read_bytes()
    doc = json.loads(raw)
    if doc["schema_name"] != DECISIONS_SCHEMA or doc["schema_version"] not in DECISIONS_SCHEMA_VERSIONS:
        raise ValueError(f"{path}: expected {DECISIONS_SCHEMA} {' or '.join(DECISIONS_SCHEMA_VERSIONS)}")
    if doc["protocol_id"] != protocol_id:
        raise ValueError(f"{path}: protocol_id {doc['protocol_id']!r}, expected {protocol_id!r}")
    rec = doc["protocol_context"]
    if context is None:
        if rec is not None:
            raise ValueError(f"{path}: records a protocol context, but {protocol_id} has no context file")
        pages = set()
    else:
        now = {"sha256": context["sha256"], "prompt_version": context["prompt_version"]}
        if rec != now:
            raise ValueError(f"{path}: stale, the protocol context changed (recorded {rec}, now {now}); "
                             f"check the decisions against it, then update protocol_context")
        pages = pages_covered(context["doc"]["pages_covered"])
    out = {}
    for d in doc["decisions"]:
        p = d["phrase"]
        where = f"{path}: decision for {p!r}"
        if p not in labels:
            raise ValueError(f"{path}: stale decision, phrase not in the study: {p!r}")
        if d["grain"] not in GRAINS or d["source"] not in DECISION_SOURCES:
            raise ValueError(f"{where}: unknown grain or source")
        if d["source"] == "ai_proposed":
            if doc["schema_version"] == "1.0":
                raise ValueError(f"{where}: ai_proposed in a 1.0 file; ai_proposed decisions come from the "
                                 f"prompt and need schema 1.1 (prompt_version, inputs_sha256)")
            if "prompt_version" not in d:
                raise ValueError(f"{where}: ai_proposed without prompt_version")
            if "inputs_content_sha256" in d and doc["schema_version"] != "1.3":
                raise ValueError(f"{where}: inputs_content_sha256 needs schema 1.3")
            if doc["schema_version"] == "1.3" and "inputs_content_sha256" not in d:
                raise ValueError(f"{where}: ai_proposed without inputs_content_sha256 in a 1.3 file")
            if "inputs_content_sha256" not in d and "inputs_sha256" not in d:
                raise ValueError(f"{where}: ai_proposed without inputs_sha256 or inputs_content_sha256")
            if inputs is None:
                raise ValueError(f"{where}: ai_proposed, but the study has no grain inputs file")
            if p not in inputs["phrases"]:
                raise ValueError(f"{where}: ai_proposed on a phrase the grain inputs file does not list")
            if "inputs_content_sha256" in d:
                if d["inputs_content_sha256"] != inputs["content_sha256"]:
                    raise ValueError(f"{where}: made from other grain inputs (inputs_content_sha256 differs)")
            elif d["inputs_sha256"] != inputs["sha256"]:
                raise ValueError(f"{where}: made from another grain inputs file (inputs_sha256 differs)")
        if p in out:
            raise ValueError(f"{where}: two decisions")
        if (d["grain"] == "named test") != ("finding_kind" in d):
            raise ValueError(f"{where}: finding_kind is required for a named test, and only there")
        if "finding_kind" in d and d["finding_kind"] not in FINDING_KINDS:
            raise ValueError(f"{where}: unknown finding_kind {d['finding_kind']!r}")
        if not d["basis"]:
            raise ValueError(f"{where}: empty basis")
        kinds_cited = set()
        for b in d["basis"]:
            t = b.get("type") if isinstance(b, dict) else None
            if t == "cdisc" and doc["schema_version"] != "1.0":
                kinds_cited |= _cdisc_basis_kinds(b, lk, where)
                continue
            if t not in BASIS_TYPES or set(b) != {"type"} | BASIS_TYPES[t]:
                raise ValueError(f"{where}: basis entry not understood: {b}")
            if t == "annotation" and b["xannot_id"] not in annotation_ids:
                raise ValueError(f"{where}: {b['xannot_id']!r} is not in the consolidated annotations")
            if t in ("context", "page") and context is None:
                raise ValueError(f"{where}: {t} basis without a protocol context file to check it against")
            if t == "context":
                try:
                    resolve_pointer(context["doc"], b["pointer"])
                except ValueError as e:
                    raise ValueError(f"{where}: {e}") from None
            if t == "page" and b["page"] not in pages:
                raise ValueError(f"{where}: page {b['page']} is outside pages_covered "
                                 f"{context['doc']['pages_covered']!r}")
        if (d["source"] == "ai_proposed" and d["grain"] == "named test" and d["finding_kind"] != "unsure"
                and d["finding_kind"] not in kinds_cited):
            raise ValueError(f"{where}: kind {d['finding_kind']!r} rests on no cdisc basis entry giving it "
                             f"(cited: {sorted(kinds_cited) or 'none'})")
        if "kind_candidates" in d:
            cands = d["kind_candidates"]
            if doc["schema_version"] in ("1.0", "1.1"):
                raise ValueError(f"{where}: kind_candidates need schema 1.2")
            if d.get("finding_kind") != "unsure":
                raise ValueError(f"{where}: kind_candidates only with finding_kind unsure")
            if len(cands) < 2 or len(set(cands)) != len(cands) or not set(cands) <= set(FINDING_KINDS) - {"unsure"}:
                raise ValueError(f"{where}: kind_candidates must be two or more distinct kinds: {cands}")
            if not set(cands) <= kinds_cited:
                raise ValueError(f"{where}: kind_candidates {sorted(set(cands) - kinds_cited)} rest on no cdisc "
                                 f"basis entry giving them (cited: {sorted(kinds_cited) or 'none'})")
        out[p] = d
        labels[p]["decision"] = {k: d[k] for k in ("grain", "finding_kind", "kind_candidates", "source",
                                                   "rationale", "basis", "proposed_by", "proposed_at",
                                                   "prompt_version", "inputs_sha256", "inputs_content_sha256")
                                     if k in d}
    return out, hashlib.sha256(raw).hexdigest()


def generate_study_grain(collection: str, protocol_id: str, lk: Lookups | None = None,
                         all_rows: list | None = None, use_decisions: bool = True) -> dict:
    """Build the <id>_activity_grain.json payload for one study.
    use_decisions=False gives the rules alone (the grain inputs file is built
    from that); the payload is then not meant to be written."""
    rows_in = study_rows(collection, protocol_id, all_rows)
    cons_path = config.find_consolidated_file(protocol_id, collection)
    if cons_path is None:
        raise FileNotFoundError(f"{collection}/{protocol_id}: no consolidated.json")
    cons_raw = cons_path.read_bytes()
    cons = json.loads(cons_raw)
    unified = {u["xact_id"]: u for u in cons["unified_activities"]}
    annotation_ids = {a["xannot_id"] for a in cons["unified_annotations"]}
    missing = [r["xact_id"] for r in rows_in if r["xact_id"] not in unified]
    if missing:
        raise ValueError(f"{cons_path}: inventory rows not in unified_activities: {missing}")
    ctx_file = context_path(protocol_id, collection)
    context = None
    if ctx_file.exists():
        ctx_raw = ctx_file.read_bytes()
        ctx_doc = json.loads(ctx_raw)
        context = {"sha256": hashlib.sha256(ctx_raw).hexdigest(),
                   "prompt_version": ctx_doc["provenance"]["prompt_version"], "doc": ctx_doc}
    lk = lk or Lookups()

    # Text rules once per distinct phrase of the study (first spelling met is the one evaluated)
    labels = {}
    for a in rows_in:
        if a["is_section_header"] or a["is_redacted"]:
            continue
        p = normalise(a["activity_name"])
        if p not in labels:
            labels[p] = label_grain(a["activity_name"], lk) | {"spellings": []}
        if a["activity_name"] not in labels[p]["spellings"]:
            labels[p]["spellings"].append(a["activity_name"])

    decisions, decisions_sha, inputs = {}, None, None
    if use_decisions:
        inputs = _current_inputs(collection, protocol_id, lk, all_rows)
        decisions, decisions_sha = _load_decisions(protocol_id, collection, labels, context, annotation_ids,
                                                   lk, inputs)

    rows = []
    for a in rows_in:
        phrase = normalise(a["activity_name"])
        row = {"protocol_id": protocol_id, "xact_id": a["xact_id"], "activity_name": a["activity_name"],
               "phrase": phrase, "hierarchy_level": a["hierarchy_level"], "parent_name": a["parent_name"],
               "role": None, "grain": None, "finding_kind": None, "kind_candidates": [], "rule_id": None,
               "context": [],
               "parent_xact_id": None, "source": "rule", "flags": []}
        if a["is_redacted"]:
            row.update(role="redacted", rule_id="S1")
            rows.append(row)
            continue
        if a["is_section_header"]:
            row.update(role="section header", rule_id="S2")
            rows.append(row)
            continue
        lab = labels[phrase]
        row.update(grain=lab["grain"], finding_kind=lab["finding_kind"], kind_candidates=lab["kind_candidates"],
                   rule_id=lab["rule_id"])
        if phrase in decisions:
            d = decisions[phrase]
            row.update(grain=d["grain"], finding_kind=d.get("finding_kind"),
                       kind_candidates=d.get("kind_candidates", []), source=d["source"])
        # Parent by id (consolidated parent_xact_id), not by name
        par_id = unified[a["xact_id"]]["parent_xact_id"]
        if a["parent_name"] and not par_id:
            row["flags"].append("parent named, no parent row")
        if par_id:
            if par_id not in unified:
                raise ValueError(f"{cons_path}: {a['xact_id']} has parent_xact_id {par_id!r}, not a row")
            par = unified[par_id]
            if par["is_section_header"]:
                row["context"].append(par["activity_name"])
            else:
                row["parent_xact_id"] = par_id
                row["flags"].append("child of a non-header parent")
                par_lab = labels.get(normalise(par["activity_name"]))
                spec = [h for h in lk.phrase.get(phrase, []) if h["codelist"] == "SPECTYPE"]
                if par_lab and par_lab["grain"] == "sample collection" and spec:
                    row.update(role="specimen of parent", grain=None, finding_kind=None, kind_candidates=[], rule_id="S3",
                               specimen_hits=_cite(spec))
        rows.append(row)

    counts = {
        "activities": len(rows),
        "by_role": dict(Counter(r["role"] for r in rows if r["role"])),
        "by_grain": {g: sum(1 for r in rows if r["grain"] == g) for g in GRAINS},
        "by_grain_rules_only": {g: sum(1 for r in rows if not r["role"] and labels[r["phrase"]]["grain"] == g)
                                for g in GRAINS},
        "by_finding_kind": {k: sum(1 for r in rows if r["finding_kind"] == k) for k in FINDING_KINDS},
        "by_finding_kind_rules_only": {k: sum(1 for r in rows if not r["role"]
                                              and labels[r["phrase"]]["finding_kind"] == k)
                                       for k in FINDING_KINDS},
        "by_rule": dict(sorted(Counter(r["rule_id"] for r in rows).items())),
        "by_source": dict(Counter(r["source"] for r in rows)),
        "distinct_labels": len(labels),
    }
    return {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
        "collection": collection, "protocol_id": protocol_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rules_version": RULES_VERSION, "word_lists_date": WORD_LISTS_DATE,
        "inputs": {
            "inventory_rows": {"rows": len(rows_in), "sha256": rows_sha256(rows_in)},
            "consolidated": {"sha256": hashlib.sha256(cons_raw).hexdigest()},
            "protocol_context": ({"sha256": context["sha256"], "prompt_version": context["prompt_version"]}
                                 if context else None),
            "decisions": {"sha256": decisions_sha} if decisions_sha else None,
            "grain_inputs": {"sha256": inputs["sha256"]} if inputs else None,
            "cdisc_for_ai": lk.provenance,
        },
        "counts": counts,
        "labels": [labels[p] | {"phrase": p} for p in sorted(labels)],
        "activities": rows,
    }


def _current_inputs(collection: str, protocol_id: str, lk: Lookups, all_rows: list | None) -> dict | None:
    """The study's grain inputs file as {"sha256", "content_sha256", "phrases"},
    or None when it has none. Fails when the file differs from the inputs rebuilt
    now: in content (CONTENT_KEYS) — rerun the gathering, then the decisions
    prompt; or only in the version records and schema version — rerun the
    gathering; decisions made from the same content stay valid."""
    path = inputs_path(protocol_id, collection)
    if not path.exists():
        return None
    from .activity_grain_inputs import CONTENT_KEYS, build_grain_inputs, content_sha256
    raw = path.read_bytes()
    doc = json.loads(raw)
    now = build_grain_inputs(collection, protocol_id, lk, all_rows)
    if any(doc[k] != now[k] for k in CONTENT_KEYS):
        raise RuntimeError(f"{path}: stale, its inputs changed; rerun: python -m soa2usdm.activity_grain_inputs "
                           f"--collection {collection} --protocol {protocol_id}, then the decisions prompt")
    if doc != now:
        raise RuntimeError(f"{path}: only the recorded versions changed (content the same); rerun: python -m "
                           f"soa2usdm.activity_grain_inputs --collection {collection} --protocol {protocol_id}; "
                           f"decisions made from the same content stay valid")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "content_sha256": content_sha256(doc),
            "phrases": {i["phrase"] for i in doc["items"]}}


def load_current_grain(collection: str, protocol_id: str, all_rows: list | None = None) -> dict | None:
    """The study's grain file, checked against its inputs as they are now; None
    when the study has none. Fails when an input changed since the file was
    generated (inventory rows, consolidated.json, protocol context, decisions,
    grain inputs)."""
    path = grain_path(protocol_id, collection)
    if not path.exists():
        return None
    g = json.loads(path.read_text(encoding="utf-8"))
    if g["schema_name"] != SCHEMA_NAME or g["schema_version"] not in SCHEMA_VERSIONS:
        raise ValueError(f"{path}: expected {SCHEMA_NAME} {' or '.join(SCHEMA_VERSIONS)}")
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
    ins = g["inputs"]
    now = {"inventory rows": rows_sha256(study_rows(collection, protocol_id, all_rows)),
           "consolidated.json": sha(config.find_consolidated_file(protocol_id, collection)),
           "protocol context": sha(context_path(protocol_id, collection)),
           "decisions": sha(decisions_path(protocol_id, collection)),
           "grain inputs": sha(inputs_path(protocol_id, collection))}
    was = {"inventory rows": ins["inventory_rows"]["sha256"],
           "consolidated.json": ins["consolidated"]["sha256"],
           "protocol context": (ins["protocol_context"] or {}).get("sha256"),
           "decisions": (ins["decisions"] or {}).get("sha256"),
           # 1.0 files were made before grain inputs files existed
           "grain inputs": (None if g["schema_version"] == "1.0" else (ins["grain_inputs"] or {}).get("sha256"))}
    changed = [k for k in now if now[k] != was[k]]
    if changed:
        raise RuntimeError(f"{path}: stale ({', '.join(changed)} changed since it was generated); rerun: "
                           f"python -m soa2usdm.activity_grain --collection {collection} --protocol {protocol_id}")
    return g


def write_study_grain(collection: str, protocol_id: str, lk: Lookups | None = None,
                      all_rows: list | None = None) -> Path:
    payload = generate_study_grain(collection, protocol_id, lk, all_rows)
    out = grain_path(protocol_id, collection)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Tag the grain of each activity, per study.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", help="one study; default: every study of the collection")
    args = ap.parse_args()
    from .activity_inventory import collect_rows
    all_rows = collect_rows(args.collection)
    pids = [args.protocol] if args.protocol else sorted({r["protocol_id"] for r in all_rows})
    lk = Lookups()
    for pid in pids:
        print(write_study_grain(args.collection, pid, lk, all_rows))


if __name__ == "__main__":
    main()
