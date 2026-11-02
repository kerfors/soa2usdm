"""
Activity grain — the label rules, rule K1 (kind of finding), the decisions
checks and the stale check of soa2usdm.activity_grain.

The rule cases run on a small stub of the lookups (Stub below), so they need no
cdisc-for-ai checkout; each stub entry has the shape of a real hit. The cases
are the traps met on cell_gene_therapy (2026-11-01): short codes in
parentheses, a word-list word after 'for', a dropped qualifier, the panel list
gate. One case runs on the real cdisc-for-ai lookups and is skipped without it.

The decisions tests are negative controls: one valid file, then one fault per
check, each of which must stop the generator.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import activity_grain as ag
from soa2usdm import config

SCHEMAS = Path(__file__).parent.parent / "schemas"


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


# ---------------------------------------------------------------------------
# Stub lookups
# ---------------------------------------------------------------------------
def _test(value, code, testcd, domains, field="TEST", source="CT"):
    return {"file": "SDTM_Test_Identity", "sheet": "Test Codes", "field": field, "source": source,
            "as_published": value, "code": code, "submission_value": testcd, "domains": domains}


class Stub(ag.Lookups):
    """Lookups with hand-made indexes; the methods are the real ones."""

    def __init__(self, tests=(), instruments=(), consumer=None):
        self.test, self.test_compact = {}, {}
        self.instrument, self.phrase, self.spectype_phrases = {}, {}, set()
        for h in tests:
            p = ag.normalise(h["as_published"])
            self.test.setdefault(p, []).append(h)
            self.test_compact.setdefault(p.replace(" ", ""), []).append(h)
        for h in instruments:
            self.instrument.setdefault(ag.normalise(h["as_published"]), []).append(h)
        self.consumer = consumer or {"LB": "Specimen_Findings", "IS": "Immunogenicity_Findings",
                                     "VS": "Measurement_Findings", "CV": "Measurement_Findings",
                                     "QS": "Instrument_Findings", "PC": "Specimen_Findings",
                                     "GF": "", "SC": ""}


CL = _test("CL", "C64495", "CL", "LB", field="TESTCD")
CHLORIDE = _test("Chloride", "C64495", "CL", "LB")
BILI = _test("Bilirubin", "C38037", "BILI", "LB")
SODIUM = _test("Sodium", "C64809", "SODIUM", "LB")
POTASSIUM = _test("Potassium", "C64853", "K", "LB")
PHQ9 = {"file": "SDTM_Instrument_Identity", "sheet": "Instruments", "field": "Instrument_Label",
        "source": "CT", "as_published": "PHQ-9", "code": "C103534", "submission_value": "PHQ01",
        "domains": "QS"}
LK = Stub(tests=[CL, CHLORIDE, BILI, SODIUM, POTASSIUM], instruments=[PHQ9])


# ---------------------------------------------------------------------------
# Label rules
# ---------------------------------------------------------------------------
def test_short_code_in_parentheses_is_no_hit():
    # '(CL)' = central laboratory, not chloride: a hit only through a short code is no hit
    rec = ag.label_grain("Factor IX inhibitor (CL)", LK)
    assert rec["grain"] == "unsure" and rec["rule_id"] == "none"
    assert rec["qualifiers"] == ["CL"]


def test_whole_label_short_code_is_no_hit():
    # 'PK' = pharmacokinetics, not pyruvate kinase; also with a qualifier ('PK (Day 1)')
    lk = Stub(tests=[_test("PK", "C111292", "PYK", "LB", field="NCIt_Synonyms", source="NCIt"),
                     _test("Pyruvate Kinase", "C111292", "PYK", "LB")])
    for label in ("PK", "PK (Day 1)"):
        rec = ag.label_grain(label, lk)
        assert rec["grain"] == "unsure" and rec["rule_id"] == "none", label
        assert any(f.startswith("short code only, not taken: PYK") for f in rec["flags"]), label
    # Control: the longer string still hits
    assert ag.label_grain("Pyruvate kinase", lk)["rule_id"] == "L1"


def test_parenthesis_alone_hits_on_a_longer_string():
    # Control for the guard: the same rule (L2a) fires on 'PHQ-9'
    rec = ag.label_grain("Depression questionnaire (PHQ-9)", LK)
    assert rec["grain"] == "instrument" and rec["rule_id"] == "L2a"


def test_word_list_reads_only_the_head_before_for():
    # 'eligibility' after 'for' does not make the row administrative; the panel word does
    rec = ag.label_grain("Hepatitis B serology for eligibility check", LK)
    assert rec["grain"] == "panel" and rec["rule_id"] == "P1"
    # Control: in the head, the same word fires W3
    rec = ag.label_grain("Eligibility check", LK)
    assert rec["grain"] == "other" and rec["rule_id"] == "W3"


def test_dropped_qualifier_is_a_weak_hit():
    # 'Bilirubin (direct)' reaches BILI only by dropping the qualifier, which can change the test
    rec = ag.label_grain("Bilirubin (direct)", LK)
    assert rec["rule_id"] == "L1q" and rec["grain"] == "named test"
    assert rec["hit_strength"] == "weak" and "qualifier dropped" in rec["weak_reasons"]
    assert [h["submission_value"] for h in rec["hits"]] == ["BILI"]


def test_panel_list_needs_two_member_hits():
    rec = ag.label_grain("Sodium, potassium", LK)
    assert rec["grain"] == "panel" and rec["rule_id"] == "P2"
    assert [m["phrase"] for m in rec["members"]] == ["sodium", "potassium"]
    rec = ag.label_grain("Sodium, factor xyz", LK)
    assert rec["grain"] == "unsure" and rec["members"] == []


# ---------------------------------------------------------------------------
# K1 — kind of finding
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("domains, kind", [
    ("LB", "specimen"), ("CV; VS", "measurement"), ("IS", "immunogenicity"),
    ("GF", "genomics"), ("PC", "pc"), ("QS", "instrument"),
])
def test_k1_one_kind(domains, kind):
    k = ag.finding_kind([_test("X", "C1", "X", domains)], LK)
    assert k["finding_kind"] == kind and k["kind_rule"] == "K1" and k["flags"] == []


@pytest.mark.parametrize("hits", [
    [_test("X", "C1", "X", "LB; IS")],                                # two kinds
    [_test("X", "C1", "X", "LB"), _test("X", "C2", "X", "VS")],       # two codes, two kinds
    [_test("X", "C1", "X", "SC")],                                    # no Consumer
])
def test_k1_unsure_with_flag(hits):
    k = ag.finding_kind(hits, LK)
    assert k["finding_kind"] == "unsure" and len(k["flags"]) == 1


def test_k1_domain_not_in_domain_coverage_fails():
    with pytest.raises(ValueError, match="not in Domain_Coverage"):
        ag.finding_kind([_test("X", "C1", "X", "ZZ")], LK)


def test_named_test_label_carries_its_kind():
    rec = ag.label_grain("Chloride", LK)
    assert (rec["grain"], rec["finding_kind"], rec["kind_domains"]) == ("named test", "specimen", ["LB"])
    rec = ag.label_grain("Eligibility check", LK)
    assert rec["finding_kind"] is None and rec["kind_rule"] is None


@pytest.mark.skipif(not ag.CDISC_FOR_AI.is_dir(), reason="needs a cdisc-for-ai checkout")
def test_real_lookups():
    lk = ag.Lookups()
    rec = ag.label_grain("Hemoglobin A1c", lk)
    assert (rec["grain"], rec["rule_id"], rec["finding_kind"]) == ("named test", "L1", "specimen")
    # TSH reaches its test only through the 3-character code: no hit, kept as a flag
    rec = ag.label_grain("TSH", lk)
    assert rec["grain"] == "unsure" and "short code only, not taken: TSH (LB)" in rec["flags"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def test_pages_covered():
    assert ag.pages_covered("268-270") == {268, 269, 270}
    assert ag.pages_covered("1-2, 7") == {1, 2, 7}
    with pytest.raises(ValueError):
        ag.pages_covered("p. 1 to 5")


def test_resolve_pointer():
    doc = {"immunogenicity": [{"measure": "a"}, {"measure": "b/c"}]}
    assert ag.resolve_pointer(doc, "/immunogenicity/1") == {"measure": "b/c"}
    for bad in ("/immunogenicity/2", "/panels/0", "/", "immunogenicity/0"):
        with pytest.raises(ValueError):
            ag.resolve_pointer(doc, bad)


# ---------------------------------------------------------------------------
# Decisions — negative controls
# ---------------------------------------------------------------------------
CONTEXT = {"sha256": "c" * 64, "prompt_version": "1.0.0",
           "doc": {"pages_covered": "1-10", "immunogenicity": [{"measure": "nAb to AAV5"}]}}
ANNOTATIONS = {"xannot-001"}


def _labels():
    return {"anti aav5 antibodies": {"grain": "unsure"}, "eligibility check": {"grain": "other"}}


def _decision(**kw):
    d = {"phrase": "anti aav5 antibodies", "grain": "named test", "finding_kind": "immunogenicity",
         "source": "ai_proposed", "rationale": "One assay.",
         "basis": [{"type": "label"}, {"type": "context", "pointer": "/immunogenicity/0"},
                   {"type": "annotation", "xannot_id": "xannot-001"}, {"type": "page", "page": 7}],
         "proposed_by": "test", "proposed_at": "2026-11-02"}
    d.update(kw)
    return {k: v for k, v in d.items() if v is not None}


def _write(tmp_path, monkeypatch, decisions, context=CONTEXT):
    doc = {"schema_name": "soa2usdm-activity-grain-decisions", "schema_version": "1.0",
           "protocol_id": "NCT0", "decisions": decisions,
           "protocol_context": ({"sha256": context["sha256"], "prompt_version": context["prompt_version"]}
                                if context else None)}
    path = tmp_path / "NCT0_activity_grain_decisions.json"
    path.write_text(json.dumps(doc))
    monkeypatch.setattr(ag, "decisions_path", lambda pid, c: path)
    return doc


def test_valid_decisions_pass_and_validate(tmp_path, monkeypatch):
    doc = _write(tmp_path, monkeypatch, [_decision()])
    jsonschema.validate(doc, _schema("soa2usdm-activity-grain-decisions.schema.json"))
    labels = _labels()
    out, sha = ag._load_decisions("NCT0", "c", labels, CONTEXT, ANNOTATIONS)
    assert list(out) == ["anti aav5 antibodies"] and len(sha) == 64
    assert labels["anti aav5 antibodies"]["decision"]["finding_kind"] == "immunogenicity"


@pytest.mark.parametrize("decisions, message", [
    ([_decision(phrase="not in the study")], "stale decision"),
    ([_decision(phrase="eligibility check", grain="other", finding_kind=None)], "rules resolved"),
    ([_decision(finding_kind=None)], "finding_kind is required"),
    ([_decision(grain="panel")], "finding_kind is required"),
    ([_decision(finding_kind="lab")], "unknown finding_kind"),
    ([_decision(basis=[])], "empty basis"),
    ([_decision(basis=["label text"])], "not understood"),
    ([_decision(basis=[{"type": "label", "page": 3}])], "not understood"),
    ([_decision(basis=[{"type": "annotation", "xannot_id": "xannot-999"}])], "consolidated annotations"),
    ([_decision(basis=[{"type": "context", "pointer": "/immunogenicity/5"}])], "does not resolve"),
    ([_decision(basis=[{"type": "page", "page": 11}])], "outside pages_covered"),
    ([_decision(), _decision()], "two decisions"),
])
def test_faulty_decision_stops(tmp_path, monkeypatch, decisions, message):
    _write(tmp_path, monkeypatch, decisions)
    with pytest.raises(ValueError, match=message):
        ag._load_decisions("NCT0", "c", _labels(), CONTEXT, ANNOTATIONS)


def test_changed_context_stops(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision()])
    changed = CONTEXT | {"sha256": "d" * 64}
    with pytest.raises(ValueError, match="protocol context changed"):
        ag._load_decisions("NCT0", "c", _labels(), changed, ANNOTATIONS)


def test_page_basis_without_context_stops(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision(basis=[{"type": "page", "page": 3}])], context=None)
    with pytest.raises(ValueError, match="without a protocol context file"):
        ag._load_decisions("NCT0", "c", _labels(), None, ANNOTATIONS)


# ---------------------------------------------------------------------------
# Stale check (the pages call it)
# ---------------------------------------------------------------------------
def test_stale_grain_file_stops(tmp_path, monkeypatch):
    rows = [{"protocol_id": "NCT0", "xact_id": "xact-001", "activity_name": "Chloride"}]
    cons = tmp_path / "NCT0_consolidated.json"
    cons.write_text("{}")
    grain = tmp_path / "NCT0_activity_grain.json"
    grain.write_text(json.dumps({
        "schema_name": ag.SCHEMA_NAME, "schema_version": ag.SCHEMA_VERSION,
        "inputs": {"inventory_rows": {"rows": 1, "sha256": ag.rows_sha256(rows)},
                   "consolidated": {"sha256": ag.hashlib.sha256(b"{}").hexdigest()},
                   "protocol_context": None, "decisions": None}}))
    monkeypatch.setattr(ag, "grain_path", lambda pid, c: grain)
    monkeypatch.setattr(ag, "context_path", lambda pid, c: tmp_path / "none.json")
    monkeypatch.setattr(ag, "decisions_path", lambda pid, c: tmp_path / "none2.json")
    monkeypatch.setattr(config, "find_consolidated_file", lambda pid, c: cons)
    assert ag.load_current_grain("c", "NCT0", rows) is not None
    renamed = [rows[0] | {"activity_name": "Chloride (serum)"}]
    with pytest.raises(RuntimeError, match="inventory rows changed"):
        ag.load_current_grain("c", "NCT0", renamed)
    cons.write_text('{"changed": 1}')
    with pytest.raises(RuntimeError, match="consolidated.json changed"):
        ag.load_current_grain("c", "NCT0", rows)


# ---------------------------------------------------------------------------
# Published files validate against their schemas
# ---------------------------------------------------------------------------
GRAIN_FILES = sorted(config.COLLECTIONS_ROOT.glob("*/protocols/*/SoA2USDM/grain/*_activity_grain.json"))
DECISION_FILES = sorted(config.COLLECTIONS_ROOT.glob("*/protocols/*/SoA2USDM/grain/*_activity_grain_decisions.json"))


@pytest.mark.parametrize("path", GRAIN_FILES, ids=lambda p: p.name)
def test_grain_file_validates(path):
    jsonschema.validate(json.loads(path.read_text()), _schema("soa2usdm-activity-grain.schema.json"))


@pytest.mark.parametrize("path", DECISION_FILES, ids=lambda p: p.name)
def test_decisions_file_validates(path):
    jsonschema.validate(json.loads(path.read_text()), _schema("soa2usdm-activity-grain-decisions.schema.json"))
