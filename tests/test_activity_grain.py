"""
Activity grain — the label rules, rule K1 (kind of finding), the decisions
checks and the stale check of soa2usdm.activity_grain.

The rule cases run on a small stub of the lookups (Stub below), so they need no
cdisc-for-ai checkout; each stub entry has the shape of a real hit. The cases
are the traps met on cell_gene_therapy (2026-11-01): short codes in
parentheses, a word-list word after 'for', a dropped qualifier, the panel list
gate. One case runs on the real cdisc-for-ai lookups and is skipped without it.

The decisions tests are negative controls: one valid file, then one fault per
check, each of which must stop the generator. They include the 1.1 checks: the
grain inputs file (phrase listed, sha256 current), prompt_version, the cdisc
basis entries (domain, code + TESTCD, codelist term) and the kind rule.
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

    def __init__(self, tests=(), instruments=(), consumer=None, phrase_codes=()):
        self.test, self.test_compact = {}, {}
        self.instrument, self.phrase, self.spectype_phrases = {}, {}, set()
        self.test_by_code, self.instrument_by_code = {}, {}
        for h in tests:
            p = ag.normalise(h["as_published"])
            self.test.setdefault(p, []).append(h)
            self.test_compact.setdefault(p.replace(" ", ""), []).append(h)
            self.test_by_code[h["code"]] = {"testcd": h["submission_value"], "test": h["as_published"],
                                            "domains": h["domains"]}
        for h in instruments:
            self.instrument.setdefault(ag.normalise(h["as_published"]), []).append(h)
            self.instrument_by_code[h["code"]] = {"testcd": h["submission_value"], "test": h["as_published"],
                                                  "domains": h["domains"]}
        self.consumer = consumer or {"LB": "Specimen_Findings", "IS": "Immunogenicity_Findings",
                                     "VS": "Measurement_Findings", "CV": "Measurement_Findings",
                                     "QS": "Instrument_Findings", "PC": "Specimen_Findings",
                                     "GF": "", "SC": ""}
        self.domain_rows = {d: {"domain": d, "domain_name": d, "observation_class": "Findings", "consumer": c}
                            for d, c in self.consumer.items()}
        self.phrase_codes = set(phrase_codes)


CL = _test("CL", "C64495", "CL", "LB", field="TESTCD")
CHLORIDE = _test("Chloride", "C64495", "CL", "LB")
BILI = _test("Bilirubin", "C38037", "BILI", "LB")
SODIUM = _test("Sodium", "C64809", "SODIUM", "LB")
POTASSIUM = _test("Potassium", "C64853", "K", "LB")
PHQ9 = {"file": "SDTM_Instrument_Identity", "sheet": "Instruments", "field": "Instrument_Label",
        "source": "CT", "as_published": "PHQ-9", "code": "C103534", "submission_value": "PHQ01",
        "domains": "QS"}
CYKSCCL = _test("Cytokine-secreting Cells", "C181400", "CYKSCCL", "IS")
LK = Stub(tests=[CL, CHLORIDE, BILI, SODIUM, POTASSIUM, CYKSCCL], instruments=[PHQ9],
          phrase_codes=[("SPECTYPE", "C13325")])


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
    lk = Stub(tests=[_test("PK", "C156470", "PYK", "LB", field="NCIt_Synonyms", source="NCIt"),
                     _test("Pyruvate Kinase", "C156470", "PYK", "LB")])
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


FSH = _test("Follicle Stimulating Hormone", "C74783", "FSH", "LB")
FSH_CODE = _test("FSH", "C74783", "FSH", "LB", field="TESTCD")
GLUC = _test("Glucose", "C105585", "GLUC", "LB")
DRUGSCR = _test("Drug Screen", "C78139", "DRUGSCR", "LB")
HCG = _test("Pregnancy Test", "C64851", "HCG", "LB", field="NCIt_Synonyms", source="NCIt")
CLINRESP = _test("Clinical", "C123619", "CLINRESP", "RS", field="NCIt_Synonyms", source="NCIt")
PYK = _test("PK", "C156470", "PYK", "LB", field="NCIt_Synonyms", source="NCIt")


class PeelStub(Stub):
    """Stub with SPECTYPE phrases for the peel-off cases."""

    def __init__(self):
        super().__init__(tests=[FSH, FSH_CODE, GLUC, DRUGSCR, HCG, CLINRESP, PYK, BILI])
        self.spectype_phrases = {"plasma", "serum", "urine"}


PK = PeelStub()


def test_parenthesis_that_is_the_own_abbreviation_confirms():
    # 'Follicle-stimulating hormone (FSH)': the parenthesis hits the same code, so nothing is dropped
    rec = ag.label_grain("Follicle Stimulating Hormone (FSH)", PK)
    assert rec["rule_id"] == "L1p" and rec["grain"] == "named test"
    assert "qualifier dropped" not in rec["weak_reasons"]
    # Control: a real qualifier is still dropped and weak
    rec = ag.label_grain("Bilirubin (direct)", PK)
    assert rec["rule_id"] == "L1q" and rec["hit_strength"] == "weak"


def test_peel_off_finds_the_test_and_keeps_the_parts():
    rec = ag.label_grain("Fasting plasma glucose", PK)
    assert rec["rule_id"] == "L1x" and rec["grain"] == "named test"
    assert rec["hit_strength"] == "weak" and "peeled" in rec["weak_reasons"]
    assert rec["peeled"]["rest"] == "glucose"
    assert rec["peeled"]["specimen"] == ["plasma"] and rec["peeled"]["condition"] == ["fasting"]


def test_peel_off_keeps_an_activity_word_inside_a_test_name():
    # trap 2: 'test' and 'screen' are part of 'Pregnancy Test' and 'Drug Screen'
    rec = ag.label_grain("Serum pregnancy test", PK)
    assert rec["rule_id"] == "L1x" and rec["peeled"]["rest"] == "pregnancy test"
    assert rec["peeled"]["kept_in_test_name"] == ["pregnancy test"]
    rec = ag.label_grain("Urine drug screen", PK)
    assert rec["peeled"]["rest"] == "drug screen"


def test_peel_off_reads_the_part_before_for():
    rec = ag.label_grain("Pregnancy test for women of childbearing potential", PK)
    assert rec["rule_id"] == "L1x" and rec["peeled"]["candidate"] == "before for"
    assert rec["peeled"]["after_for"] == ["women of childbearing potential"]


def test_peel_off_takes_no_generic_rest_and_no_short_code():
    # trap 1: 'Clinical Laboratory Testing' is not CLINRESP
    rec = ag.label_grain("Clinical Laboratory Testing", PK)
    assert rec["rule_id"] == "none" and "peeled" not in rec
    # 'Serum PK' is not pyruvate kinase
    rec = ag.label_grain("Serum PK", PK)
    assert rec["rule_id"] == "none" and "peeled" not in rec


def test_peel_off_needs_something_peeled():
    # Control: a label with nothing to peel and no hit stays unsure
    rec = ag.label_grain("Glucagon xyz", PK)
    assert rec["rule_id"] == "none"


GAD7 = {"file": "SDTM_Instrument_Identity", "sheet": "Instruments", "field": "Instrument_Label",
        "source": "CT", "as_published": "GAD-7", "code": "C103518", "submission_value": "GAD01",
        "domains": "QS"}
ALBCREAT = _test("Albumin/Creatinine", "C74761", "ALBCREAT", "LB")
LISTS = Stub(tests=[CL, CHLORIDE, BILI, SODIUM, POTASSIUM, ALBCREAT], instruments=[PHQ9, GAD7])


def test_panel_list_two_member_hits():
    rec = ag.label_grain("Sodium, potassium", LISTS)
    assert rec["grain"] == "panel" and rec["rule_id"] == "P2"
    assert [(m["member_id"], m["phrase"], m["member_grain"]) for m in rec["members"]] == \
        [("m01", "sodium", "named test"), ("m02", "potassium", "named test")]
    assert rec["members"][0]["finding_kind"] == "specimen"


def test_panel_list_one_hit_neither_peeled_nor_short_code():
    # rules 1.2.0: one good hit is enough ('Pancreatic amylase, lipase'); the member without a hit is kept
    rec = ag.label_grain("Factor xyz, sodium", LISTS)
    assert rec["grain"] == "panel" and rec["rule_id"] == "P2"
    assert [m["member_grain"] for m in rec["members"]] == [None, "named test"]
    # control: one hit by short code only is not enough ('CT/MRI', 'PK, IG ...')
    rec = ag.label_grain("Factor xyz, CL", LISTS)
    assert rec["grain"] == "unsure" and rec["members"] == []


def test_list_is_split_outside_parentheses_only():
    rec = ag.label_grain("Vital signs (includes sodium, potassium and chloride), bilirubin", LISTS)
    assert rec["grain"] == "panel" and rec["rule_id"] == "P2"
    assert [(m["member_id"], m["text"], m["from"], m["in_group"], m["member_grain"]) for m in rec["members"]] == [
        ("m01", "Vital signs", "label", None, "panel"),
        ("m02", "sodium", "parenthesis", "m01", "named test"),
        ("m03", "potassium", "parenthesis", "m01", "named test"),
        ("m04", "chloride", "parenthesis", "m01", "named test"),
        ("m05", "bilirubin", "label", None, "named test")]


def test_trailing_parenthesis_qualifies_the_label_and_inner_one_the_member():
    rec = ag.label_grain("Sodium (at baseline only) / potassium (select patients)", LISTS)
    assert rec["grain"] == "panel" and rec["qualifiers"] == ["select patients"]
    assert [(m["text"], m["qualifiers"]) for m in rec["members"]] == \
        [("Sodium (at baseline only)", ["at baseline only"]), ("potassium", [])]


def test_slash_that_is_part_of_a_test_name_is_no_separator():
    rec = ag.label_grain("Urinary albumin/creatinine", LISTS)
    assert rec["members"] == [] and rec["grain"] != "panel"
    assert "slash is part of a test name: albumin/creatinine (ALBCREAT)" in rec["flags"]


def test_history_label_is_not_a_list():
    rec = ag.label_grain("Substance use (sodium, potassium)", LISTS)
    assert rec["grain"] != "panel" and rec["members"] == []
    assert "list members not taken: history word ('use')" in rec["flags"]


def test_mixed_row_is_not_a_list():
    rec = ag.label_grain("Sodium and contraception check", LISTS)
    assert rec["grain"] != "panel" and rec["members"] == []


def test_one_peeled_hit_is_not_enough():
    rec = ag.label_grain("Serum glucose, xyz", PK)
    assert rec["grain"] != "panel" and rec["members"] == []


def test_panel_word_label_keeps_its_listed_members():
    rec = ag.label_grain("Chemistry (sodium, potassium)", LISTS)
    assert rec["grain"] == "panel" and rec["rule_id"] == "P1"
    assert [(m["text"], m["in_group"], m["member_grain"]) for m in rec["members"]] == \
        [("Chemistry", None, "panel"), ("sodium", "m01", "named test"), ("potassium", "m01", "named test")]


def test_instrument_list_needs_two_instruments():
    rec = ag.label_grain("PHQ-9, GAD-7", LISTS)
    assert rec["grain"] == "instrument list" and rec["rule_id"] == "P2i"
    assert [m["member_grain"] for m in rec["members"]] == ["instrument", "instrument"]
    rec = ag.label_grain("PHQ-9, neuropathy questionnaire", LISTS)
    assert rec["grain"] != "instrument list" and rec["members"] == []


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


INPUTS = {"sha256": "e" * 64, "content_sha256": "d" * 64, "phrases": {"anti aav5 antibodies"}}
IS_ROW = {"type": "cdisc", "file": "Domain_Coverage", "domain": "IS"}


def _labels():
    return {"anti aav5 antibodies": {"grain": "unsure"}, "eligibility check": {"grain": "other"}}


def _decision(**kw):
    d = {"phrase": "anti aav5 antibodies", "grain": "named test", "finding_kind": "immunogenicity",
         "source": "ai_proposed", "rationale": "One assay.",
         "basis": [{"type": "label"}, {"type": "context", "pointer": "/immunogenicity/0"},
                   {"type": "annotation", "xannot_id": "xannot-001"}, {"type": "page", "page": 7}, IS_ROW],
         "proposed_by": "test", "proposed_at": "2026-11-02",
         "prompt_version": "1.0.0", "inputs_sha256": INPUTS["sha256"]}
    d.update(kw)
    return {k: v for k, v in d.items() if v is not None}


def _load(labels=None, context=CONTEXT, inputs=INPUTS, placeholders=frozenset()):
    return ag._load_decisions("NCT0", "c", labels or _labels(), context, ANNOTATIONS, LK, inputs, placeholders)


def _write(tmp_path, monkeypatch, decisions, context=CONTEXT, version="1.2"):
    doc = {"schema_name": "soa2usdm-activity-grain-decisions", "schema_version": version,
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
    out, sha = _load(labels)
    assert list(out) == ["anti aav5 antibodies"] and len(sha) == 64
    assert labels["anti aav5 antibodies"]["decision"]["finding_kind"] == "immunogenicity"
    assert labels["anti aav5 antibodies"]["decision"]["inputs_sha256"] == INPUTS["sha256"]


@pytest.mark.parametrize("basis", [
    [{"type": "label"}, {"type": "cdisc", "file": "SDTM_Test_Identity", "code": "C181400", "testcd": "CYKSCCL"}],
    [{"type": "label"}, IS_ROW, {"type": "cdisc", "file": "Codelist_Phrases", "codelist": "SPECTYPE",
                                 "code": "C13325"}],
])
def test_kind_from_a_cdisc_row_passes(tmp_path, monkeypatch, basis):
    _write(tmp_path, monkeypatch, [_decision(basis=basis)])
    _load()


def test_kind_candidates_from_cited_rows_pass(tmp_path, monkeypatch):
    lb = {"type": "cdisc", "file": "Domain_Coverage", "domain": "LB"}
    doc = _write(tmp_path, monkeypatch, [_decision(finding_kind="unsure", kind_candidates=["immunogenicity", "specimen"],
                                                   basis=[{"type": "label"}, IS_ROW, lb])])
    jsonschema.validate(doc, _schema("soa2usdm-activity-grain-decisions.schema.json"))
    labels = _labels()
    _load(labels)
    assert labels["anti aav5 antibodies"]["decision"]["kind_candidates"] == ["immunogenicity", "specimen"]


def test_k1_gives_candidates_for_several_kinds():
    k = ag.finding_kind([_test("Temperature", "C1", "TEMP", "LB; VS")], LK)
    assert (k["finding_kind"], k["kind_candidates"]) == ("unsure", ["measurement", "specimen"])
    k = ag.finding_kind([_test("Thing", "C2", "THING", "LB; SC")], LK)
    assert (k["finding_kind"], k["kind_candidates"]) == ("unsure", [])


def test_kind_unsure_needs_no_cdisc_row(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision(finding_kind="unsure", basis=[{"type": "label"}])])
    _load()


def test_reviewed_decision_in_a_1_0_file_passes(tmp_path, monkeypatch):
    d = _decision(phrase="eligibility check", grain="other", finding_kind=None, source="reviewed",
                  basis=[{"type": "label"}], prompt_version=None, inputs_sha256=None)
    doc = _write(tmp_path, monkeypatch, [d], version="1.0")
    jsonschema.validate(doc, _schema("soa2usdm-activity-grain-decisions.schema.json"))
    _load(inputs=None)


@pytest.mark.parametrize("decisions, message", [
    ([_decision(phrase="not in the study")], "stale decision"),
    ([_decision(phrase="eligibility check", grain="other", finding_kind=None)], "does not list"),
    ([_decision(prompt_version=None)], "without prompt_version"),
    ([_decision(inputs_sha256="f" * 64)], "another grain inputs file"),
    ([_decision(basis=[{"type": "label"}])], "rests on no cdisc basis entry"),
    ([_decision(finding_kind="specimen")], "rests on no cdisc basis entry"),
    ([_decision(basis=[{"type": "cdisc", "file": "Domain_Coverage", "domain": "XX"}])], "not in Domain_Coverage"),
    ([_decision(basis=[{"type": "cdisc", "file": "SDTM_Test_Identity", "code": "C999", "testcd": "X"}])],
     "not in SDTM_Test_Identity"),
    ([_decision(basis=[{"type": "cdisc", "file": "SDTM_Test_Identity", "code": "C181400", "testcd": "CYKSC"}])],
     "not 'CYKSC'"),
    ([_decision(basis=[IS_ROW, {"type": "cdisc", "file": "Codelist_Phrases", "codelist": "METHOD",
                                "code": "C13325"}])], "not a METHOD term"),
    ([_decision(basis=[{"type": "cdisc", "file": "Domain_Coverage", "code": "C1"}])], "cdisc basis entry not understood"),
    ([_decision(basis=[{"type": "cdisc", "file": "Findings", "domain": "IS"}])], "cdisc basis entry not understood"),
    ([_decision(kind_candidates=["immunogenicity", "specimen"])], "only with finding_kind unsure"),
    ([_decision(finding_kind="unsure", kind_candidates=["immunogenicity"])], "two or more distinct kinds"),
    ([_decision(finding_kind="unsure", kind_candidates=["immunogenicity", "immunogenicity"])], "two or more distinct kinds"),
    ([_decision(finding_kind="unsure", kind_candidates=["immunogenicity", "unsure"])], "two or more distinct kinds"),
    ([_decision(finding_kind="unsure", kind_candidates=["immunogenicity", "specimen"])], "rest on no cdisc"),
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
        _load()


def test_a_basis_citing_a_placeholder_annotation_stops(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision()])
    with pytest.raises(ValueError, match="'xannot-001' is a placeholder annotation"):
        _load(placeholders={"xannot-001"})


def test_content_fingerprint_in_a_1_3_file_passes(tmp_path, monkeypatch):
    doc = _write(tmp_path, monkeypatch, [_decision(inputs_content_sha256=INPUTS["content_sha256"])], version="1.3")
    jsonschema.validate(doc, _schema("soa2usdm-activity-grain-decisions.schema.json"))
    labels = _labels()
    _load(labels)
    assert labels["anti aav5 antibodies"]["decision"]["inputs_content_sha256"] == INPUTS["content_sha256"]


def test_content_fingerprint_replaces_the_whole_file_check(tmp_path, monkeypatch):
    # inputs_sha256 stays as a record from the earlier file; with the content fingerprint it is not checked
    _write(tmp_path, monkeypatch, [_decision(inputs_sha256="f" * 64, inputs_content_sha256=INPUTS["content_sha256"])],
           version="1.3")
    _load()


@pytest.mark.parametrize("decisions, version, message", [
    ([_decision(inputs_content_sha256="f" * 64)], "1.3", "inputs_content_sha256 differs"),
    ([_decision()], "1.3", "without inputs_content_sha256 in a 1.3 file"),
    ([_decision(inputs_content_sha256=INPUTS["content_sha256"])], "1.2", "needs schema 1.3"),
    ([_decision(inputs_sha256=None)], "1.2", "without inputs_sha256 or inputs_content_sha256"),
])
def test_faulty_content_fingerprint_stops(tmp_path, monkeypatch, decisions, version, message):
    _write(tmp_path, monkeypatch, decisions, version=version)
    with pytest.raises(ValueError, match=message):
        _load()


def test_carried_decision_in_a_1_4_file_passes(tmp_path, monkeypatch):
    doc = _write(tmp_path, monkeypatch, [_decision(inputs_content_sha256=INPUTS["content_sha256"],
                                                   carried_over_from="a" * 64)], version="1.4")
    jsonschema.validate(doc, _schema("soa2usdm-activity-grain-decisions.schema.json"))
    labels = _labels()
    _load(labels)
    assert labels["anti aav5 antibodies"]["decision"]["carried_over_from"] == "a" * 64


def test_carried_decision_in_a_1_5_file_passes(tmp_path, monkeypatch):
    """1.5 (a carry-over that released changed items) reads like 1.4."""
    doc = _write(tmp_path, monkeypatch, [_decision(inputs_content_sha256=INPUTS["content_sha256"],
                                                   carried_over_from="a" * 64)], version="1.5")
    jsonschema.validate(doc, _schema("soa2usdm-activity-grain-decisions.schema.json"))
    labels = _labels()
    _load(labels)
    assert labels["anti aav5 antibodies"]["decision"]["carried_over_from"] == "a" * 64


@pytest.mark.parametrize("decisions, version, message", [
    ([_decision(inputs_content_sha256=INPUTS["content_sha256"], carried_over_from="a" * 64)], "1.3",
     "carried_over_from needs schema 1.4"),
    ([_decision(inputs_content_sha256=INPUTS["content_sha256"], carried_over_from=INPUTS["content_sha256"])],
     "1.4", "carried_over_from needs schema 1.4 and other inputs"),
    ([_decision()], "1.4", "without inputs_content_sha256 in a 1.4 file"),
    ([_decision(phrase="eligibility check", grain="other", finding_kind=None, source="reviewed",
                basis=[{"type": "label"}], prompt_version=None, inputs_sha256=None,
                carried_over_from="a" * 64)], "1.4", "carried_over_from on a decision that is not ai_proposed"),
])
def test_faulty_carry_over_stops(tmp_path, monkeypatch, decisions, version, message):
    _write(tmp_path, monkeypatch, decisions, version=version)
    with pytest.raises(ValueError, match=message):
        _load()


def test_ai_proposed_without_inputs_file_stops(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision()])
    with pytest.raises(ValueError, match="no grain inputs file"):
        _load(inputs=None)


def test_kind_candidates_in_a_1_1_file_stop(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision(finding_kind="unsure", kind_candidates=["immunogenicity", "specimen"])],
           version="1.1")
    with pytest.raises(ValueError, match="need schema 1.2"):
        _load()


def test_ai_proposed_in_a_1_0_file_stops(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision(prompt_version=None, inputs_sha256=None)], version="1.0")
    with pytest.raises(ValueError, match="in a 1.0 file"):
        _load()


def test_cdisc_basis_in_a_1_0_file_stops(tmp_path, monkeypatch):
    d = _decision(source="reviewed", basis=[IS_ROW], prompt_version=None, inputs_sha256=None)
    _write(tmp_path, monkeypatch, [d], version="1.0")
    with pytest.raises(ValueError, match="basis entry not understood"):
        _load()


def test_changed_context_stops(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision()])
    changed = CONTEXT | {"sha256": "d" * 64}
    with pytest.raises(ValueError, match="protocol context changed"):
        _load(context=changed)


def test_page_basis_without_context_stops(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, [_decision(basis=[{"type": "page", "page": 3}, IS_ROW])], context=None)
    with pytest.raises(ValueError, match="without a protocol context file"):
        _load(context=None)


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
                   "protocol_context": None, "decisions": None, "grain_inputs": None}}))
    monkeypatch.setattr(ag, "grain_path", lambda pid, c: grain)
    monkeypatch.setattr(ag, "context_path", lambda pid, c: tmp_path / "none.json")
    monkeypatch.setattr(ag, "decisions_path", lambda pid, c: tmp_path / "none2.json")
    monkeypatch.setattr(ag, "inputs_path", lambda pid, c: tmp_path / "none3.json")
    monkeypatch.setattr(config, "find_consolidated_file", lambda pid, c: cons)
    assert ag.load_current_grain("c", "NCT0", rows) is not None
    renamed = [rows[0] | {"activity_name": "Chloride (serum)"}]
    with pytest.raises(RuntimeError, match="inventory rows changed"):
        ag.load_current_grain("c", "NCT0", renamed)
    (tmp_path / "none3.json").write_text("{}")
    with pytest.raises(RuntimeError, match="grain inputs changed"):
        ag.load_current_grain("c", "NCT0", rows)
    (tmp_path / "none3.json").unlink()
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
