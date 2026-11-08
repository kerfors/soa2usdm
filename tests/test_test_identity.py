"""
Test identity (step 6a) — test code + facets + specialization level, records only.

The reading and level cases run on a small stub of the lookups (Stub below), so they need no
cdisc-for-ai checkout. They are cases met on the four collections on 2026-11-08: a specimen in the
label outside the test ('Serum creatinine'), the component restated in a parenthesis ('Erythrocyte
count (RBC)'), the longest codelist phrase ('MUGA scan', not 'scan'), conditions ('WOCBP only',
'selected sites only'), fasting words, the exact specimen term (SERUM does not select SERUM OR PLASMA),
a shared observable key, a scale left unstated, two sources in conflict, and ECG components (a Folded_Facets
head, a short form with no EG hit, QTc). Rules 1.1.0: a phrase matching several variables ('blood': SPECTYPE and
LOC) is recorded for each, flagged, and does not narrow; free text is read only for Kind set and not open.

The guard runs on the real cdisc-for-ai lookups and is skipped without them: the not-generally-used
statements name the generics read from them (CV-A2 names --FAST only), Kind and Position come only from
Variable_Meaning, and every lookup sheet comes with its published Provenance (none hashed here). Published test identity
files validate against the schema.
"""
import json
from collections import defaultdict
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import config
from soa2usdm import test_identity as ti

SCHEMAS = Path(__file__).parent.parent / "schemas"

LB_VARS = [
    {"variable": "LBSPEC", "generic": "--SPEC", "kind": "observable", "position": "system",
     "meaning_status": "accepted", "codelists": ["SPECTYPE"]},
    {"variable": "LBMETHOD", "generic": "--METHOD", "kind": "observable", "position": "method",
     "meaning_status": "accepted", "codelists": ["METHOD"]},
    {"variable": "LBFAST", "generic": "--FAST", "kind": "practice", "position": "open",
     "meaning_status": "accepted", "codelists": ["NY"]},
]


class Grain:
    """The two grain lookups test identity uses: test strings and test_hit."""

    def __init__(self, test):
        self.test = test

    def test_hit(self, text):
        hits = self.test.get(ti.normalise(text), [])
        return ("whole", hits) if hits else (None, [])


class Stub(ti.TestIdentityLookups):
    def __init__(self):
        ph = defaultdict(lambda: defaultdict(set))
        for cl, phrase, sv, cid in [("SPECTYPE", "serum", "SERUM", "C13325"), ("SPECTYPE", "urine", "URINE", "C13283"),
                                    ("SPECTYPE", "plasma", "PLASMA", "C13356"), ("SPECTYPE", "blood", "BLOOD", "C12434"),
                                    ("SPECTYPE", "rbc", "ERYTHROCYTES", "C12521"),
                                    ("METHOD", "muga scan", "MUGA", "C38073"), ("METHOD", "muga", "MUGA", "C38073"),
                                    ("METHOD", "scan", "SCINTIGRAPHY", "C62667"),
                                    ("POSITION", "supine", "SUPINE", "C62167")]:
            ph[cl][phrase].add((sv, cid))
        self.phrases = ph
        self.facet_variables = {"LB": LB_VARS}
        self.facet_generics = ["--FAST", "--METHOD", "--POS", "--SPEC"]
        self.codelist_by_generic = defaultdict(set, {"--SPEC": {"SPECTYPE"}, "--METHOD": {"METHOD"},
                                                     "--POS": {"POSITION"}, "--FAST": {"NY"}})
        self.grain = Grain({
            "rbc": [{"code": "C51946", "submission_value": "RBC", "domains": "CP; LB"}],
            "pr": [{"code": "C74774", "submission_value": "PROGESTR", "domains": "LB; MI"}],
            "qtc": [{"code": "C100391", "submission_value": "QTCUNS", "domains": "EG"}],
        })
        spec = lambda ds, s, sn, sc="UNITS", key=None: {"ds_id": ds, "observable_key": key or f"X|Y|{sn}|{sc}|UNPINNED",
                                                      "spec": s, "spec_ncit": sn, "method": None,
                                                      "method_ncit": None, "scale": sc}
        self.specializations = {
            ("LB", "CREAT", "C64547"): [spec("CREATSERPL", "SERUM OR PLASMA", "C105706"),
                                        spec("CREATURIN", "URINE", "C13283")],
            ("LB", "GLUC", "C105585"): [spec("GLUCSER", "SERUM", "C13325", key="K1"),
                                        spec("GLUCSERPL", "SERUM", "C13325", key="K1"),
                                        spec("GLUCPL", "PLASMA", "C13356"), spec("GLUCBLD", "BLOOD", "C12434")],
            ("LB", "ALB", "C64431"): [spec("ALBURIN", "URINE", "C13283"),
                                      spec("ALBURINPRES", "URINE", "C13283", "NO_UNITS")],
            ("LB", "HGB", "C64848"): [spec("HGBBLD", "BLOOD", "C12434")],
        }
        head = lambda tc, tail: {"TESTCD": tc, "Head": "PR Interval", "Tail": tail, "Evidence": "CT naming"}
        self.folded_by_testcd = {"PRAG": head("PRAG", "Aggregate"), "PRSB": head("PRSB", "Single Beat")}
        self.folded_by_head = {"pr interval": [head("PRAG", "Aggregate"), head("PRSB", "Single Beat")]}
        self.collisions = {}
        self.not_generally_used = {}


LK = Stub()
CREAT = [{"code": "C64547", "testcd": "CREAT", "domains": ["LB"]}]
GLUC = [{"code": "C105585", "testcd": "GLUC", "domains": ["LB"]}]
RBC = [{"code": "C51946", "testcd": "RBC", "domains": ["CP", "LB"]}]


def _f(variable, concept, position="system"):
    return {"variable": variable, "position": position, "term": {"concept_id": concept}}


def test_specimen_in_the_label_outside_the_test():
    facets, conds, again, unread = ti.read_text("Serum creatinine", "label", LB_VARS, LK, exclude="creatinine",
                                                codes=CREAT)
    assert [(f["variable"], f["term"]["submission_value"]) for f in facets] == [("LBSPEC", "SERUM")]
    assert not conds and not again and not unread


def test_component_restated_is_not_a_specimen():
    facets, _, again, unread = ti.read_text("Erythrocyte count (RBC)", "label", LB_VARS, LK,
                                            exclude="erythrocyte count", codes=RBC)
    assert facets == [] and again == ["rbc"] and unread == []


def test_longest_codelist_phrase_wins():
    v = [{"variable": "CVMETHOD", "generic": "--METHOD", "kind": None, "position": None, "meaning_status": None,
          "codelists": ["METHOD"]}]
    facets, _, _, unread = ti.read_text("LVEF (MUGA scan)", "label", v, LK, exclude="lvef")
    assert [(f["value"], f["term"]["submission_value"]) for f in facets] == [("muga scan", "MUGA")]
    assert facets[0]["kind"] is None and unread == []


def test_conditions_are_not_facets():
    assert [c["class"] for c in ti.match_conditions("Pregnancy test (WOCBP only)")] == ["population"]
    assert [c["class"] for c in ti.match_conditions("Triplicate ECGs (selected sites only)")] == ["site"]
    assert [(c["class"], c["phrase"]) for c in ti.match_conditions("cell count (Reflex Testing) if positive")] \
        == [("reflex", "if positive"), ("reflex", "Reflex Testing")]
    assert ti.match_conditions("Serum creatinine") == []


def test_fasting_words():
    assert ti.match_fasting("glucose (non-fasting)")["reading"] == "N"
    assert ti.match_fasting("Fasting Glucose")["reading"] == "Y"
    assert ti.match_fasting("Blood Chemistry (fasting not required)")["reading"] is None
    facets, *_ = ti.read_text("Fasting plasma glucose", "label", LB_VARS, LK, exclude="glucose", codes=GLUC)
    assert {(f["variable"], f["via"]) for f in facets} == {("LBFAST", "word list"), ("LBSPEC", "codelist phrase")}


def test_exact_specimen_term_only():
    s = ti.specialization("LB", CREAT, [_f("LBSPEC", "C13325")], LK)          # SERUM vs SERUM OR PLASMA
    assert s["level"] == "stated facet matches no specialization"
    s = ti.specialization("LB", CREAT, [_f("LBSPEC", "C13283")], LK)          # URINE
    assert s["level"] == "selected by stated facets" and s["selected"] == ["CREATURIN"]


def test_shared_key_is_one_observable():
    s = ti.specialization("LB", GLUC, [_f("LBSPEC", "C13325")], LK)
    assert s["level"] == "selected by stated facets" and s["selected"] == ["GLUCSER", "GLUCSERPL"]


def test_unstated_identity_facet_stays_open():
    alb = [{"code": "C64431", "testcd": "ALB", "domains": ["LB"]}]
    s = ti.specialization("LB", alb, [_f("LBSPEC", "C13283")], LK)
    assert s["level"] == "facet not stated" and s["not_stated"] == ["scale"]
    assert ti.specialization("LB", [{"code": "C64848", "testcd": "HGB", "domains": ["LB"]}], [], LK)["level"] \
        == "one specialization"
    assert ti.specialization("LB", GLUC, [], LK)["level"] == "facet not stated"


def test_conflicting_sources_do_not_narrow():
    s = ti.specialization("LB", GLUC, [_f("LBSPEC", "C13356"), _f("LBSPEC", "C12434")], LK)
    assert s["level"] == "stated facets conflict" and s["conflicting_positions"] == ["system"]


def test_practice_facets_do_not_narrow():
    s = ti.specialization("LB", GLUC, [{"variable": "LBFAST", "position": "open", "term": {"concept_id": "Y"}}], LK)
    assert s["level"] == "facet not stated"


def test_levels_without_one_settled_code():
    assert ti.specialization("LB", [], [], LK)["level"] == "no component"
    assert ti.specialization(None, CREAT, [], LK)["level"] == "domain open"
    assert ti.specialization("LB", CREAT + GLUC, [], LK)["level"] == "component open"


def test_ecg_components():
    c = ti.ecg_component("PR interval", "/measurements/0/components/0", LK)
    assert c["level"] == "test family, beat not stated" and c["via"] == "Folded_Facets head"
    assert c["family"]["testcds"] == ["PRAG", "PRSB"] and c["family"]["tails"] == ["Aggregate", "Single Beat"]
    c = ti.ecg_component("PR", "/measurements/0/components/1", LK)          # no words added; PROGESTR is not EG
    assert c["level"] == "no component" and c["outside_eg"] == [{"testcd": "PROGESTR", "domains": "LB; MI"}]
    c = ti.ecg_component("QTc", "/measurements/0/components/2", LK)
    assert c["level"] == "test code" and [x["testcd"] for x in c["codes"]] == ["QTCUNS"]


def test_ambiguous_phrase_gives_one_facet_per_variable():
    """1.1.0: 'blood' is a SPECTYPE and a LOC term; with the domain open both are recorded, none chosen."""
    v = [{"variable": "--LOC", "generic": "--LOC", "kind": None, "position": None, "meaning_status": None,
          "codelists": ["LOC"]},
         {"variable": "--SPEC", "generic": "--SPEC", "kind": None, "position": None, "meaning_status": None,
          "codelists": ["SPECTYPE"]}]
    LK.phrases["LOC"]["blood"].add(("BLOOD", "C12434"))
    try:
        facets, *_ = ti.read_text("Blood culture", "label", v, LK, exclude="culture")
    finally:
        del LK.phrases["LOC"]["blood"]
    assert [(f["variable"], f["ambiguous_with"]) for f in facets] == [("--LOC", ["--SPEC"]), ("--SPEC", ["--LOC"])]


def test_ambiguous_facet_does_not_narrow():
    f = _f("LBSPEC", "C13283") | {"ambiguous_with": ["LBLOC"]}
    assert ti.specialization("LB", CREAT, [f], LK)["level"] == "facet not stated"


def test_free_text_reads_kind_set_and_not_open():
    """1.1.0: --ORRESU (Kind open) and variables without a Kind are not read from labels."""
    lk = Stub()
    unit = {"variable": "LBORRESU", "generic": "--ORRESU", "kind": "open", "position": "open",
            "meaning_status": "proposed", "codelists": ["UNIT"]}
    lk.facet_variables = {"LB": LB_VARS + [unit]}
    lk.facet_generics = ["--FAST", "--METHOD", "--ORRESU", "--SPEC"]
    lk.codelist_by_generic["--ORRESU"] = {"UNIT"}
    lk.generic_kinds = defaultdict(set, {"--SPEC": {"observable"}, "--METHOD": {"observable"},
                                         "--FAST": {"practice"}, "--ORRESU": {"open"}})
    assert [v["variable"] for v in lk.text_variables("LB")] == ["LBSPEC", "LBMETHOD", "LBFAST"]
    assert [v["variable"] for v in lk.text_variables(None)] == ["--FAST", "--METHOD", "--SPEC"]


# ---------------------------------------------------------------------------
# Guard on the real cdisc-for-ai lookups
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real():
    if not ti.CDISC_FOR_AI.is_dir():
        pytest.skip("no cdisc-for-ai checkout")
    return ti.TestIdentityLookups()


def test_not_generally_used_read_from_the_statements(real):
    assert real.not_generally_used["EG"]["generics"] == ["--FAST", "--SPEC"]
    assert real.not_generally_used["VS"]["generics"] == ["--FAST", "--SPEC"]
    assert real.not_generally_used["CV"]["generics"] == ["--FAST"]


def test_kind_only_from_variable_meaning(real):
    meaning = {(r["Domain"], r["Key"]) for r in real.sheets["Variable_Meaning"].to_dict("records")}
    for dom, vs in real.facet_variables.items():
        for v in vs:
            assert (v["kind"] is None) == ((dom, v["variable"]) not in meaning), (dom, v["variable"])


def test_open_kind_not_read_from_free_text(real):
    assert "LBORRESU" not in [v["variable"] for v in real.text_variables("LB")]
    assert {"LBSPEC", "LBMETHOD", "LBFAST"} <= {v["variable"] for v in real.text_variables("LB")}


def test_every_lookup_sheet_has_published_provenance(real):
    assert not [f["file"] for f in real.provenance["files"] if f["sheet_hash_computed_here"]]


def _published():
    out = []
    for coll in [c for c in config.COLLECTIONS if c != "fixtures"]:
        out += sorted(config.COLLECTIONS[coll].glob("*/SoA2USDM/test_identity/*_test_identity.json"))
    return out


@pytest.mark.parametrize("path", _published(), ids=lambda p: p.stem)
def test_published_files_validate(path):
    schema = json.loads((SCHEMAS / "soa2usdm-test-identity.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), schema)
