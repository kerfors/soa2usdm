"""
Activity routing — the rules and statuses of soa2usdm.activity_routing, the
public-only guard, and the published routing files.

The rule cases run on a small stub of the lookups (Stub below), so they need no
cdisc-for-ai checkout. They are the cases met on cell_gene_therapy (2026-11-03
to 2026-11-05): an antibody test (routed IS: IS-OV, IS-A1, IS-A2, IS-A3, no
condition), IFN-gamma ELISpot (open IS/LB, not LB), flow
cytometry, an Ag/Ab combination test setting the antibody rule aside, a match
only in a footnote (weak), a match only in the parent label (open), and no
match (not routed, PP left out of the fallback). Test identity (schema 1.1): a
strong hit with one domain routes, with several domains opens, a weak hit gives
hints only, and a rule ranks above it (PK (Glucagon)).

The guard runs on the real cdisc-for-ai lookups and is skipped without them:
every statement a rule cites is a routing statement of the public
SDTMIG_Statements file.
"""
import json
import re
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import activity_routing as ar
from soa2usdm import config

SCHEMAS = Path(__file__).parent.parent / "schemas"


class Stub(ar.RoutingLookups):
    """RoutingLookups without files: cited statements by ID, kind -> domains as Domain_Coverage gives them."""

    def __init__(self):
        self.cited = {sid: {"text_sha256": "0" * 64} for r in ar.RULES for s in r["statements"]
                      for sid in [s["statement_id"]]}
        self.kind_domains = {"specimen": ["BS", "CP", "LB", "MB", "MI", "MS"], "immunogenicity": ["IS"],
                             "measurement": ["CV", "EG", "MK", "RE", "VS"], "pc": ["PC"], "genomics": ["GF"]}
        self.fallback_excluded = []


LK = Stub()


def _route(label, parent=None, annotations=(), kinds=("specimen",), ti=None):
    sources = [{"where": "label", "xannot_id": None, "text": label}]
    if parent:
        sources.append({"where": "parent_label", "xannot_id": None, "text": parent})
    for i, t in enumerate(annotations):
        sources.append({"where": "annotation", "xannot_id": f"xannot-{i:03d}", "text": t})
    return ar.route(ar.match_rules(sources), list(kinds), LK, ti)


def _label(phrase, strength, *hits, reasons=()):
    """A grain label entry with SDTM_Test_Identity hits (code, testcd, domains) and one non-test hit."""
    return {"phrase": phrase, "hit_strength": strength, "weak_reasons": list(reasons),
            "hits": [{"file": "SDTM_Test_Identity", "field": "TESTCD", "code": c, "submission_value": t, "domains": d}
                     for c, t, d in hits]
                    + [{"file": "Codelist_Phrases", "field": "submission value", "code": "C0", "submission_value": "X"}]}


def test_antibody_routed_is():
    for label in ("Anti-Drug Antibody/ADA (CL)", "Neutralizing antibodies to AAV5", "hFVIII TAb",
                  "ALLO-501A donor-specific anti-HLA antibodies(serum)"):
        r = _route(label, kinds=("immunogenicity",))
        assert (r["status"], r["domain"], r["question"]) == ("routed", "IS", None), label
        assert [s["statement_id"] for s in r["basis"][0]["statements"]] == ["IS-OV", "IS-A1", "IS-A2", "IS-A3"]


def test_factor_inhibitor_only():
    assert _route("Factor IX inhibitors (Bethesda assay)")["basis"][0]["rule_id"] == "RT-1"
    assert _route("Protease inhibitor use")["status"] == "not routed"


def test_elispot_not_routed_to_lb():
    r = _route("IFNg ELISpot", kinds=("immunogenicity",))
    assert (r["status"], r["candidates"]) == ("open", ["IS", "LB"])
    assert "IS-A4" in r["question"]


def test_flow_cytometry_routed_cp():
    r = _route("Immunophenotyping by flow cytometry")
    assert (r["status"], r["domain"]) == ("routed", "CP")


def test_ag_ab_sets_antibody_rule_aside():
    r = _route("HIV-1/2 Ag/Ab combination antibody test")
    assert (r["status"], r["domain"]) == ("routed", "MB")
    assert r["dropped"] == {"RT-1": {"by_rule": "RT-8", "statement_id": "IS-A5"}}


def test_annotation_only_is_weak():
    r = _route("Factor IX Recovery", annotations=["Test for factor IX inhibitor if recovery is low."],
               kinds=("specimen",))
    assert (r["status"], r["hints"], r["candidates"]) == ("weak", ["IS"], LK.kind_domains["specimen"])
    assert r["question"].startswith("matched only in annotation (xannot-000)")


def test_parent_label_only_is_open():
    r = _route("ALLO-501A", parent="Cellular kinetics/PK assessments", kinds=("pc",))
    assert (r["status"], r["candidates"]) == ("open", ["PC"])
    assert "no match in the activity label" in r["question"]


def test_no_rule_falls_back_to_grain_kind():
    r = _route("Hemoglobin A1C")
    assert (r["status"], r["candidates"], r["basis"]) == ("not routed", LK.kind_domains["specimen"], [])
    assert r["fallback"] == {"from": "grain kind -> Domain_Coverage", "kinds": ["specimen"]}


def test_routed_needs_label_match_and_no_condition():
    """Negative control on the status rule: a routed result always rests on a label match with no condition."""
    for label in ("Hematology", "PK sampling", "FACS"):
        r = _route(label)
        assert r["status"] == "routed"
        assert all(b["label_match"] for b in r["basis"])
        assert not any(s["condition"] for b in r["basis"] for s in b["statements"])


def test_test_identity_strong_one_domain_routes():
    ti = ar.test_identity(_label("hba1c", "strong", ("C64849", "HBA1C", "LB")))
    r = _route("HbA1c", ti=ti)
    assert (r["status"], r["domain"], r["route_source"], r["basis"], r["fallback"]) == \
        ("routed", "LB", "test identity", [], None)
    assert r["test_identity"]["codes"] == [{"code": "C64849", "testcd": "HBA1C", "domains": ["LB"]}]


def test_test_identity_strong_several_domains_open():
    ti = ar.test_identity(_label("weight", "strong", ("C25208", "WEIGHT", "CV; VS")))
    r = _route("Weight", kinds=("measurement",), ti=ti)
    assert (r["status"], r["candidates"], r["route_source"], r["fallback"]) == \
        ("open", ["CV", "VS"], "test identity", None)
    assert "WEIGHT" in r["question"] and "CV, VS" in r["question"]


def test_test_identity_weak_one_code_one_domain_routes():
    # 1.3.0: one code in one domain routes, marked as a weak hit
    ti = ar.test_identity(_label("pregnancy test", "weak", ("C64851", "HCG", "LB"), reasons=["NCIt synonym only"]))
    r = _route("Pregnancy test", ti=ti)
    assert (r["status"], r["domain"], r["route_source"], r["fallback"]) == \
        ("routed", "LB", "test identity, weak hit", None)


def test_test_identity_weak_several_codes_or_domains_gives_hints_only():
    ti = ar.test_identity(_label("temperature", "weak", ("C174446", "TEMP", "VS"), ("C25206", "TEMP", "BS; DO"),
                                 reasons=["several codes"]))
    r = _route("Temperature", ti=ti)
    assert (r["status"], r["hints"], r["route_source"]) == ("not routed", ["BS", "DO", "VS"], None)
    ti = ar.test_identity(_label("pao2 fio2", "weak", ("C119293", "PO2FIO2", "LB; RE"), reasons=["NCIt synonym only"]))
    r = _route("PaO2/FiO2", ti=ti)
    assert (r["status"], r["hints"], r["route_source"]) == ("not routed", ["LB", "RE"], None)


def test_rule_ranks_above_test_identity():
    ti = ar.test_identity(_label("pk glucagon", "weak", ("C74859", "GLUCAGON", "LB")))
    r = _route("PK (Glucagon)", ti=ti)
    assert (r["status"], r["domain"], r["route_source"]) == ("routed", "PC", "rule")
    assert r["test_identity"]["domains"] == ["LB"]
    strong = ar.test_identity(_label("anti drug antibody", "strong", ("C1", "X", "LB")))
    r = _route("Anti-Drug Antibody", kinds=("immunogenicity",), ti=strong)
    assert (r["status"], r["domain"], r["route_source"]) == ("routed", "IS", "rule")


def test_test_identity_reads_only_test_identity_hits():
    assert ar.test_identity(None) is None
    assert ar.test_identity({"phrase": "x", "hit_strength": "strong", "weak_reasons": [],
                             "hits": [{"file": "Codelist_Phrases", "field": "f", "code": "C1",
                                       "submission_value": "BLOOD"}]}) is None
    ti = ar.test_identity(_label("temperature", "weak", ("C174446", "TEMP", "VS"), ("C25206", "TEMP", "BS; DO")))
    assert ti["domains"] == ["BS", "DO", "VS"]


@pytest.mark.skipif(not ar.CDISC_FOR_AI.is_dir(), reason="needs a cdisc-for-ai checkout")
def test_rules_cite_public_routing_statements_only():
    lk = ar.RoutingLookups()
    for rule in ar.RULES:
        for s in rule["statements"]:
            row = lk.statements[s["statement_id"]]
            assert row["Selected_As"] == "routing"
            assert set(s["domains"]) <= {row["Domain"]} | {d for d in s["domains"] if d in row["Text"]}
    assert "PP" not in {d for ds in lk.kind_domains.values() for d in ds}


# ---------------------------------------------------------------------------
# Published files
# ---------------------------------------------------------------------------
ROUTING_FILES = sorted(config.COLLECTIONS_ROOT.glob("*/protocols/*/SoA2USDM/routing/*_activity_routing.json"))


@pytest.mark.parametrize("path", ROUTING_FILES, ids=lambda p: p.name)
def test_routing_file_validates(path):
    schema = json.loads((SCHEMAS / "soa2usdm-activity-routing.schema.json").read_text())
    jsonschema.validate(json.loads(path.read_text()), schema)


@pytest.mark.parametrize("path", ROUTING_FILES, ids=lambda p: p.name)
def test_routing_file_consistent(path):
    """Statement texts match their sha256; every cited statement is quoted; a matched phrase occurs in its
    source; an annotation match points to a footnote referencing the row or its parent."""
    d = json.loads(path.read_text())
    for sid, s in d["statements"].items():
        assert ar.sha256_text(s["text"]) == s["text_sha256"], sid
    cons = json.loads(config.find_consolidated_file(d["protocol_id"], d["collection"]).read_text())
    ann = {a["xannot_id"]: a for a in cons["unified_annotations"]}
    for r in d["rows"]:
        for b in r["basis"]:
            for s in b["statements"]:
                assert d["statements"][s["statement_id"]]["text_sha256"] == s["text_sha256"]
            for m in b["matched"]:
                if m["where"] == "label":
                    text = r["activity_name"]
                elif m["where"] == "parent_label":
                    text = r["parent_name"]
                else:
                    a = ann[m["xannot_id"]]
                    assert {r["xact_id"], r["parent_xact_id"]} & set(a["referenced_xacts"])
                    text = a["annotation_text"]
                assert m["phrase"].lower() in text.lower(), (r["xact_id"], m)
        assert d["counts"][r["status"]] >= 1
    assert d["counts"]["rows"] == len(d["rows"])
    assert not any(re.search(r"-R-\d+$", sid) for sid in d["statements"])


@pytest.mark.parametrize("path", ROUTING_FILES, ids=lambda p: p.name)
def test_routing_file_test_identity(path):
    """1.1 files: the test identity of a row is the one its grain file gives the label, and it routes or
    opens a row only where no rule fired, strong, as the status rule says."""
    d = json.loads(path.read_text())
    if d["schema_version"] == "1.0":
        pytest.skip("1.0 file: no test identity")
    grain = json.loads((path.parent.parent / "grain" / f"{d['protocol_id']}_activity_grain.json").read_text())
    labels = {lb["phrase"]: lb for lb in grain["labels"]}
    phrase = {a["xact_id"]: a["phrase"] for a in grain["activities"]}
    for r in d["rows"]:
        ti = r["test_identity"]
        assert ti == ar.test_identity(labels.get(phrase[r["xact_id"]])), r["xact_id"]
        if r["route_source"] == "test identity, weak hit":
            assert r["basis"] == [] and ti["hit_strength"] == "weak" and r["fallback"] is None
            assert r["status"] == "routed" and len(ti["codes"]) == 1 and ti["domains"] == [r["domain"]]
        elif r["route_source"] == "test identity":
            assert r["basis"] == [] and ti["hit_strength"] == "strong" and r["fallback"] is None
            if r["status"] == "routed":
                assert ti["domains"] == [r["domain"]]
            else:
                assert r["status"] == "open" and r["candidates"] == ti["domains"] and len(ti["domains"]) > 1
        elif r["status"] == "routed":
            assert r["route_source"] == "rule" and r["basis"]
        if not r["basis"] and ti and ti["hit_strength"] == "weak" and r["route_source"] is None:
            assert r["status"] == "not routed" and r["hints"] == ti["domains"]
            assert len(ti["codes"]) > 1 or len(ti["domains"]) > 1
    assert d["counts"]["routed_by_test_identity"] == sum(
        1 for r in d["rows"] if r["status"] == "routed" and r["route_source"] == "test identity")
