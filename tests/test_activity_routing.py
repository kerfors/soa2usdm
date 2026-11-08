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
        self.cited = {sid: {"text_sha256": "0" * 64}
                      for r in ar.RULES + ar.PANEL_RULES + ar.RESOLUTION_RULES + ar.ACTIVITY_RULES
                      for s in r["statements"]
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
def _member(mid, text, *hits, strength="strong", reasons=(), grain="named test", kind="specimen"):
    lab = _label(text.lower(), strength, *hits, reasons=reasons)
    return {"member_id": mid, "text": text, "phrase": text.lower(), "from": "label", "in_group": None,
            "qualifiers": [], "member_grain": grain, "hits": lab["hits"], "hit_strength": strength,
            "weak_reasons": list(reasons), "finding_kind": kind, "kind_candidates": []}


def _split(label, members):
    a = {"protocol_id": "NCT0", "xact_id": "xact-002", "activity_name": label, "parent_xact_id": "xact-001"}
    unified = {"xact-001": {"activity_name": "Laboratory Assessments", "is_section_header": False,
                            "parent_xact_id": None},
               "xact-002": {"activity_name": label, "is_section_header": False, "parent_xact_id": "xact-001"}}
    cons = {"unified_annotations": []}
    return ar._member_rows(a, members, unified, cons, LK)


def test_member_rows_route_on_the_member_and_its_own_test_identity():
    rows = _split("PT, aPTT", [_member("m01", "PT", ("C62656", "PT", "LB"), strength="weak",
                                       reasons=("short code only",)),
                               _member("m02", "aPTT", ("C38462", "APTT", "LB")),
                               _member("m03", "xyz", grain=None)])
    assert [(r["member_id"], r["status"], r["domain"], r["route_source"]) for r in rows] == \
        [("m01", "routed", "LB", "test identity, weak hit"), ("m02", "routed", "LB", "test identity")]
    assert rows[0]["activity_name"] == "PT" and rows[0]["panel_name"] == "PT, aPTT"
    assert rows[0]["parent_name"] == "Laboratory Assessments" and rows[0]["grain"]["source"] == "panel member"


def test_panel_label_only_supports():
    # 'Hematology' in the panel label fires RT-10 (LB); it is recorded and does not block the test identity
    rows = _split("Hematology, aPTT", [_member("m01", "Hematology", grain="panel"),
                                       _member("m02", "aPTT", ("C38462", "APTT", "LB"))])
    assert len(rows) == 1
    r = rows[0]
    assert (r["status"], r["domain"], r["route_source"], r["basis"]) == ("routed", "LB", "test identity", [])
    assert [s["rule_id"] for s in r["panel_label_support"]] == ["RT-10"]


def test_panel_annotations_only_support():
    # The footnote on the panel row (NCT03283098 xannot-012, text as extracted) names 'hematology'
    # (RT-10, LB) and describes the panel: support only, so the member routes by its own test
    # identity and is not weak (rules 1.5.0)
    a = {"protocol_id": "NCT03283098", "xact_id": "xact-016", "activity_name": "Hematology, PT, aPTT",
         "parent_xact_id": None}
    unified = {"xact-016": {"activity_name": a["activity_name"], "is_section_header": False, "parent_xact_id": None}}
    cons = {"unified_annotations": [{"xannot_id": "xannot-012", "referenced_xacts": ["xact-016"],
                                     "annotation_text": "Blood sample for PT and aPTT will be drawn prior to heparin "
                                                        "administration for dialysis. Day 1 hematology and coagulation "
                                                        "tests will be performed only if day 1 occurs more than 2 weeks "
                                                        "after the screening hematology and coagulation tests."}]}
    rows = ar._member_rows(a, [_member("m03", "aPTT", ("C38462", "APTT", "LB"))], unified, cons, LK)
    r = rows[0]
    assert (r["status"], r["domain"], r["route_source"], r["basis"]) == ("routed", "LB", "test identity", [])
    assert r["panel_annotation_support"] == [{"rule_id": "RT-10", "domains": ["LB"],
                                              "matched": [{"xannot_id": "xannot-012", "phrase": "hematology"}]}]


def test_context_members_marked_and_context_panel_only_supports():
    # NCT05714345 'CBC w/differential' style: members from a context panel named 'Hematology' (RT-10, LB):
    # the name supports only; the member routes by its own test identity, marked, with the stated facets
    m = _member("c01", "aPTT", ("C38462", "APTT", "LB")) | {
        "sources": [{"context_panel": "/panels/0", "analyte": "aPTT"}],
        "stated_facets": [{"facet": "lab", "value": "Local Laboratory", "context_panel": "/panels/0", "pages": [125]}]}
    cps = {"/panels/0": {"pointer": "/panels/0", "panel_name": "Hematology (SoA note)", "specimen": None,
                         "lab": "Local Laboratory", "evidence": [{"page": 125, "quote": "q"}, {"page": 121, "quote": "q"}]}}
    a = {"protocol_id": "NCT0", "xact_id": "xact-002", "activity_name": "Blood tests", "parent_xact_id": None}
    unified = {"xact-002": {"activity_name": "Blood tests", "is_section_header": False, "parent_xact_id": None}}
    r = ar._member_rows(a, [m], unified, {"unified_annotations": []}, LK, cps)[0]
    assert (r["status"], r["domain"], r["route_source"], r["basis"]) == ("routed", "LB", "test identity", [])
    assert r["members_from"] == "protocol context" and r["grain"]["source"] == "panel member, protocol context"
    assert r["context_sources"] == [{"context_panel": "/panels/0", "panel_name": "Hematology (SoA note)",
                                     "pages": [121, 125]}]
    assert [s["rule_id"] for s in r["context_panel_support"]] == ["RT-10"]
    assert r["stated_facets"] == m["stated_facets"]
    # label members carry no marker
    assert "members_from" not in _split("PT, aPTT", [_member("m02", "aPTT", ("C38462", "APTT", "LB"))])[0]


def test_vital_signs_panel_settles_vs_for_vs_ov_measurements_only():
    # Decision B: 'TEMP' (two codes: VS, BS/DO) and 'Weight' (CV; VS) in a vital-signs panel route VS by RT-11;
    # 'HR' (CV; VS, not named in VS-OV) keeps its test identity and stays open
    rows = _split("Vital Signs (BP, HR, RR, TEMP) and Weight", [
        _member("m01", "TEMP", ("C174446", "TEMP", "VS"), ("C25206", "TEMP", "BS; DO"), strength="weak",
                reasons=("several codes",)),
        _member("m02", "HR", ("C49677", "HR", "CV; VS"), kind="measurement"),
        _member("m03", "Weight", ("C25208", "WEIGHT", "CV; VS"), kind="measurement")])
    got = {r["activity_name"]: (r["status"], r["domain"], r["route_source"], [b["rule_id"] for b in r["basis"]])
           for r in rows}
    assert got == {"TEMP": ("routed", "VS", "rule", ["RT-11"]), "HR": ("open", None, "test identity", []),
                   "Weight": ("routed", "VS", "rule", ["RT-11"])}
    b = [r for r in rows if r["activity_name"] == "TEMP"][0]["basis"][0]
    assert {(m["where"], m["phrase"]) for m in b["matched"]} == {("label", "TEMP"), ("panel_label", "Vital Signs")}


def test_vs_measurement_outside_a_vital_signs_panel_not_settled():
    rows = _split("Weight, Height", [_member("m01", "Weight", ("C25208", "WEIGHT", "CV; VS"), kind="measurement")])
    assert (rows[0]["status"], rows[0]["basis"]) == ("open", [])
    assert ar.match_panel_rules("Weight", "Body measurements") == []
    assert ar.match_panel_rules("Pulse", "Vital signs") == []


# ---------------------------------------------------------------------------
# Rules 1.8.0 (step 5, 2026-11-08)
# ---------------------------------------------------------------------------
LYM = ("C51949", "LYM", "CP; LB; MI")


def test_haematology_panel_resolves_cp_lb_to_lb():
    # RT-12: a strong CP/LB(/MI) test code in a panel whose label names haematology routes LB (LB-OV, CP-OV)
    rows = _split("Haematology", [_member("m01", "Lymphocytes", LYM),
                                  _member("m02", "Platelets", ("C51951", "PLAT", "CP; LB"))])
    got = [(r["status"], r["domain"], r["route_source"], [b["rule_id"] for b in r["basis"]]) for r in rows]
    assert got == [("routed", "LB", "rule", ["RT-12"])] * 2
    b = rows[0]["basis"][0]
    assert b["matched"] == [{"where": "panel_label", "xannot_id": None, "phrase": "Haematology"}]
    assert [s["statement_id"] for s in b["statements"]] == ["LB-OV", "CP-OV"] and b["label_match"] is False
    assert rows[0]["test_identity"]["domains"] == ["CP", "LB", "MI"]
    # 'differentials' (CP-OV's word) names it too
    assert _split("CBC with differentials, Platelets", [_member("m01", "Lymphocytes", LYM)])[0]["domain"] == "LB"


def test_haematology_resolution_not_outside_its_conditions():
    # urinalysis panel; weak hit; a test code not in both CP and LB; flow cytometry named in the panel label
    assert _split("Urinalysis", [_member("m01", "Leukocytes", ("C51948", "WBC", "BS; CP; LB; MI"))])[0]["status"] == "open"
    r = _split("Hematology", [_member("m01", "T cells", ("C1", "TLYCE", "CP; LB"), strength="weak",
                                      reasons=("NCIt synonym only",))])[0]
    assert (r["status"], r["basis"]) == ("not routed", [])
    r = _split("Hematology", [_member("m01", "MCH", ("C1", "MCH", "LB; MB"))])[0]
    assert (r["status"], r["candidates"]) == ("open", ["LB", "MB"])
    r = _split("Hematology and flow cytometry", [_member("m01", "Lymphocytes", LYM)])[0]
    assert (r["status"], r["basis"]) == ("open", [])


def test_haematology_resolution_needs_the_context_panel_name_too():
    m = _member("c01", "Leukocytes", ("C51948", "WBC", "BS; CP; LB; MI")) | {
        "sources": [{"context_panel": "/panels/1", "analyte": "Leukocytes"}], "stated_facets": []}
    a = {"protocol_id": "NCT0", "xact_id": "xact-002", "activity_name": "Clinical Lab Tests (Hematology, Urinalysis)",
         "parent_xact_id": None}
    unified = {"xact-002": {"activity_name": a["activity_name"], "is_section_header": False, "parent_xact_id": None}}
    for name, status in (("Urinalysis", "open"), ("Hematology", "routed")):
        cps = {"/panels/1": {"pointer": "/panels/1", "panel_name": name, "evidence": [{"page": 9, "quote": "q"}]}}
        r = ar._member_rows(a, [m], unified, {"unified_annotations": []}, LK, cps)[0]
        assert r["status"] == status, name
    assert {(x["where"], x["phrase"]) for x in r["basis"][0]["matched"]} == \
        {("panel_label", "Hematology"), ("context_panel", "Hematology")}


def test_annotation_only_rule_gives_way_to_label_test_identity():
    # NCT01797120 'HBV DNA': the footnote's 'antibodies' (RT-1) made it weak; the label's HBDNA (MB) routes
    note = ("Patients on antiviral prophylaxis treatment or positive HBV antibodies should be tested for HBV-DNA "
            "≤ 7 days prior to the start of C1D1")
    ti = ar.test_identity(_label("hbv dna", "weak", ("C103404", "HBDNA", "MB"), reasons=["NCIt synonym only"]))
    r = _route("HBV DNA", annotations=[note], ti=ti)
    assert (r["status"], r["domain"], r["route_source"], r["basis"]) == ("routed", "MB", "test identity, weak hit", [])
    assert r["annotation_hints"] == [{"rule_id": "RT-1", "domains": ["IS"],
                                      "matched": [{"xannot_id": "xannot-000", "phrase": "antibodies"}]}]
    # no label test identity: still weak (Factor IX Recovery)
    r = _route("Factor IX Recovery", annotations=["Test for factor IX inhibitor if recovery is low."])
    assert r["status"] == "weak" and "annotation_hints" not in r


def test_weak_hit_does_not_route_when_grain_kind_unsure():
    # NCT05714345 'MRD assessment': MRDRESP (RS) through a supplied word; the AI left the kind unsure
    ti = ar.test_identity(_label("mrd assessment", "weak", ("C124433", "MRDRESP", "RS"),
                                 reasons=["NCIt synonym only", "peeled", "activity word supplied: result"]))
    r = ar.route([], [], LK, ti, kind_unsure=True)
    assert (r["status"], r["domain"], r["hints"], r["route_source"]) == ("not routed", None, ["RS"], None)
    assert r["question"].startswith("weak test code hit MRDRESP -> RS")
    # kind unsure but its candidates cover the domain, or a definite kind: routes as before
    assert ar.route([], ["specimen", "pc"], LK, ar.test_identity(_label("x", "weak", ("C1", "X", "LB"))),
                    kind_unsure=True)["status"] == "routed"
    assert ar.route([], [], LK, ti)["status"] == "routed"


def test_ecg_activity_rule_matches_label_and_sets_device_handling_aside():
    # RT-13: ECG / EKG / electrocardiogram on a grain panel or procedure; placed / removed set aside
    for label in ("12-lead ECG", "Triplicate ECGs (selected sites only)", "Electrocardiogram", "EKG"):
        fired, aside = ar.match_activity_rules(label, "procedure")
        assert [r["rule_id"] for r in fired] == ["RT-13"] and aside == [], label
    fired, aside = ar.match_activity_rules("Ambulatory ECG placed", "panel")
    assert fired == [] and [r["rule_id"] for r in aside] == ["RT-13"]
    assert ar.match_activity_rules("12-lead ECG", "named test") == ([], [])
    assert ar.match_activity_rules("Echocardiogram", "procedure") == ([], [])


def test_ecg_activity_row_routed_eg():
    a = {"protocol_id": "NCT0", "xact_id": "xact-003", "activity_name": "12-lead ECG", "phrase": "12 lead ecg",
         "parent_xact_id": None, "grain": "procedure", "finding_kind": None, "kind_candidates": [], "source": "ai_proposed"}
    unified = {"xact-003": {"activity_name": "12-lead ECG", "is_section_header": False, "parent_xact_id": None}}
    fired, _ = ar.match_activity_rules(a["activity_name"], a["grain"])
    r = ar._own_row(a, unified, {"unified_annotations": []}, {}, LK, fired)
    assert (r["status"], r["domain"], r["route_source"], r["activity_level"]) == ("routed", "EG", "rule", True)
    assert r["basis"][0]["rule_id"] == "RT-13" and r["basis"][0]["matched"][0]["phrase"] == "ECG"
    assert r["grain"]["grain"] == "procedure" and r["test_identity"] is None and r["annotation_support"] == []
    # a footnote naming PK (RT-9) only supports: the row stays routed EG (NCT05051579 xannot-004 style)
    cons = {"unified_annotations": [{"xannot_id": "xannot-004", "referenced_xacts": ["xact-003"],
                                     "annotation_text": "ECGs should be done before PK sampling."}]}
    r = ar._own_row(a, unified, cons, {}, LK, fired)
    assert (r["status"], r["domain"]) == ("routed", "EG")
    assert r["annotation_support"] == [{"rule_id": "RT-9", "domains": ["PC"],
                                        "matched": [{"xannot_id": "xannot-004", "phrase": "PK"}]}]


def test_rules_cite_public_routing_statements_only():
    lk = ar.RoutingLookups()
    for rule in ar.RULES + ar.PANEL_RULES + ar.RESOLUTION_RULES + ar.ACTIVITY_RULES:
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
def test_routing_file_counts_by_unit(path):
    """1.7: the standalone and member counts add up to the status counts and match the rows.
    1.9: with the activity-level rows as a third unit."""
    d = json.loads(path.read_text())
    bu = d["counts"]["by_unit"]
    for st in ar.STATUSES:
        assert bu["standalone"][st] + bu["member"][st] + bu.get("activity", {}).get(st, 0) == d["counts"][st]
    assert bu == {"standalone": ar.unit_counts([r for r in d["rows"] if "member_id" not in r
                                                and not r.get("activity_level")]),
                  "member": ar.unit_counts([r for r in d["rows"] if "member_id" in r])} | (
        {"activity": ar.unit_counts([r for r in d["rows"] if r.get("activity_level")])} if "activity" in bu else {})
    for r in d["rows"]:  # 1.9: only an activity-level row has another grain than named test
        assert (r["grain"]["grain"] != "named test") == bool(r.get("activity_level")), r["xact_id"]
        if r.get("activity_level"):
            assert "member_id" not in r and r["grain"]["grain"] in ("panel", "procedure")
            assert {b["rule_id"] for b in r["basis"]} & {ru["rule_id"] for ru in ar.ACTIVITY_RULES}
    assert sum(bu["member"][st] for st in ar.STATUSES) == d["counts"]["rows_from_panel_members"]


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
                elif m["where"] == "panel_label":  # 1.6: only in a panel rule's basis; 1.8: or a resolution rule's
                    assert b["rule_id"] in {pr["rule_id"] for pr in ar.PANEL_RULES + ar.RESOLUTION_RULES}, \
                        (r["xact_id"], b["rule_id"])
                    text = r["panel_name"]
                elif m["where"] == "context_panel":  # 1.8: only in a resolution rule's basis
                    assert b["rule_id"] in {pr["rule_id"] for pr in ar.RESOLUTION_RULES}, (r["xact_id"], b["rule_id"])
                    text = " | ".join(cs["panel_name"] for cs in r["context_sources"])
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
    pcm_file = path.parent.parent / "panels" / f"{d['protocol_id']}_panel_context_members.json"
    context = ({(r["xact_id"], m["member_id"]): m for r in json.loads(pcm_file.read_text())["rows"] for m in r["members"]}
               if pcm_file.exists() else {})
    for r in d["rows"]:
        ti = r["test_identity"]
        if r.get("members_from") == "protocol context":  # 1.5: the member from the panel context members file
            assert ti == ar.test_identity(context[(r["xact_id"], r["member_id"])]), (r["xact_id"], r["member_id"])
        elif "member_id" in r:  # 1.3: a member row's test identity is the member's own
            member = {m["member_id"]: m for m in labels[phrase[r["xact_id"]]]["members"]}[r["member_id"]]
            assert ti == ar.test_identity(member), (r["xact_id"], r["member_id"])
        else:
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
            # 1.8.0: one code in one domain gives a hint only where the grain kind is unsure and does not cover it
            assert len(ti["codes"]) > 1 or len(ti["domains"]) > 1 or (
                r["grain"]["finding_kind"] == "unsure" and ti["domains"][0] not in r["candidates"]
                and r["question"].startswith("weak test code hit")), r["xact_id"]
        if r.get("annotation_hints"):  # 1.8.0: annotation rules gave way to the label's test identity
            assert not r["basis"] and r["route_source"] in ("test identity", "test identity, weak hit")
            assert "member_id" not in r
    assert d["counts"]["routed_by_test_identity"] == sum(
        1 for r in d["rows"] if r["status"] == "routed" and r["route_source"] == "test identity")
