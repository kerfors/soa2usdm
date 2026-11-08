"""
Panel members from protocol context — the name rule (D1), the members and their union (D2, D3),
the stated facets (D5), and the published panel context members files.

The rule cases use the labels and context panel names met on cell_gene_therapy (2026-11-07) and
the stub lookups of test_activity_grain, so they need no cdisc-for-ai checkout.
"""
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import config
from soa2usdm import panel_context_members as pcm
from soa2usdm.activity_grain import context_path, grain_path
from test_activity_grain import LK

SCHEMAS = Path(__file__).parent.parent / "schemas"


# ---------------------------------------------------------------------------
# Name rule (D1)
# ---------------------------------------------------------------------------
def test_name_key_spelling_generic_words_and_spaces():
    assert pcm.name_key("Haematology parameters") == pcm.name_key("Hematology")
    assert pcm.name_key("Serum chemistry parameters") == pcm.name_key("Serum Chemistry")
    assert pcm.name_key("Reflex autoantibodies") == pcm.name_key("Reflex auto-antibodies")
    assert pcm.name_key("Urine Tests") == pcm.name_key("Urine")
    # no plural, no containment
    assert pcm.name_key("serum immunoglobulins") != pcm.name_key("Serum Immunoglobulin")
    assert pcm.name_key("Coagulation") != pcm.name_key("Coagulation Screen")


def test_lab_code_parentheses_dropped():
    assert pcm.drop_lab_codes("FIX Activity, LFT (CL, LL) and FIX Antigen (CL)") == "FIX Activity, LFT and FIX Antigen"
    assert pcm.drop_lab_codes("TBNK (blood)") == "TBNK (blood)"


def test_soa_panel_names():
    assert pcm.soa_panel_names("Laboratory Safety Panels (Hematology and Clinical Chemistry) (CL)") == \
        ["Laboratory Safety Panels", "Hematology", "Clinical Chemistry"]
    assert pcm.soa_panel_names("Laboratory Safety Panels (Lipid Panel) (CL)") == ["Laboratory Safety Panels", "Lipid Panel"]
    assert pcm.soa_panel_names("Hematology, serum chemistry, coagulation, serum immunoglobulins") == \
        ["Hematology", "serum chemistry", "coagulation", "serum immunoglobulins"]
    # not split at '/'; a qualifier parenthesis gives no name
    assert pcm.soa_panel_names("CBC w/differential") == ["CBC w/differential"]
    assert pcm.soa_panel_names("Quantitative serum immunoglobulins (local)") == ["Quantitative serum immunoglobulins"]


def test_whole_label_first_and_context_source_note_dropped():
    cps = [{"panel_name": "Hepatitis B and Hepatitis C"}, {"panel_name": "Coagulation (SoA note)"},
           {"panel_name": "Coagulation (Table 2. Safety Laboratory Tests)"}]
    assert pcm.link_names("Hepatitis B and Hepatitis C (CL)", cps) == [("Hepatitis B and Hepatitis C", [0])]
    assert pcm.link_names("Coagulation", cps) == [("Coagulation", [1, 2])]
    assert pcm.link_names("Hematology and coagulation parameters", cps) == \
        [("Hematology", []), ("coagulation parameters", [1, 2])]


# ---------------------------------------------------------------------------
# Members (D2, D3, D5)
# ---------------------------------------------------------------------------
CPS = [{"panel_name": "Chemistry (Table 2)", "analytes": ["Sodium", "Bilirubin", "Electrolytes (Chloride, Potassium)"],
        "specimen": "Serum", "lab": None, "evidence": [{"page": 5, "quote": "q"}]},
       {"panel_name": "Chemistry (SoA note)", "analytes": ["Sodium", "Chloride", "xyz"],
        "specimen": None, "lab": "Local Laboratory", "evidence": [{"page": 9, "quote": "q"}, {"page": 8, "quote": "q"}]}]


def test_members_union_by_phrase_with_sources_differences_and_facets():
    r = pcm.panel_row({"xact_id": "xact-001", "activity_name": "Chemistry (CL)"}, CPS, LK)
    assert r["link"] == "linked" and r["names"] == [{"name": "Chemistry", "key": "chemistry",
                                                     "context_panels": ["/panels/0", "/panels/1"]}]
    ms = {m["phrase"]: m for m in r["members"]}
    assert [m["member_id"] for m in r["members"]] == ["c01", "c02", "c03", "c04", "c05", "c06"]
    assert ms["sodium"]["sources"] == [{"context_panel": "/panels/0", "analyte": "Sodium"},
                                       {"context_panel": "/panels/1", "analyte": "Sodium"}]
    assert ms["sodium"]["from"] == "analyte" and ms["sodium"]["member_grain"] == "named test"
    # a list analyte: its members, grouped under the first one, as for label members
    assert (ms["electrolytes"]["from"], ms["chloride"]["from"], ms["chloride"]["in_group"]) == \
        ("analyte list", "analyte parenthesis", ms["electrolytes"]["member_id"])
    assert ms["chloride"]["sources"] == [{"context_panel": "/panels/0", "analyte": "Electrolytes (Chloride, Potassium)"},
                                         {"context_panel": "/panels/1", "analyte": "Chloride"}]
    assert ms["xyz"]["member_grain"] is None
    assert r["differences"] == [{"name": "Chemistry", "context_panels": ["/panels/0", "/panels/1"], "common": 2,
                                 "only_in": [{"context_panel": "/panels/0",
                                              "phrases": ["bilirubin", "electrolytes", "potassium"]},
                                             {"context_panel": "/panels/1", "phrases": ["xyz"]}]}]
    assert ms["sodium"]["stated_facets"] == [
        {"facet": "specimen", "value": "Serum", "context_panel": "/panels/0", "pages": [5]},
        {"facet": "lab", "value": "Local Laboratory", "context_panel": "/panels/1", "pages": [8, 9]}]


def test_not_linked_and_linked_partly():
    assert pcm.panel_row({"xact_id": "x", "activity_name": "Vital Signs"}, CPS, LK)["link"] == "not linked"
    r = pcm.panel_row({"xact_id": "x", "activity_name": "Chemistry, Urinalysis"}, CPS, LK)
    assert r["link"] == "linked partly" and [n["context_panels"] for n in r["names"]] == [["/panels/0", "/panels/1"], []]


# ---------------------------------------------------------------------------
# Published files
# ---------------------------------------------------------------------------
PANEL_FILES = sorted(config.COLLECTIONS_ROOT.glob("*/protocols/*/SoA2USDM/panels/*_panel_context_members.json"))
STUDIES = sorted({(p.parent.name, p.parent.parent.parent.name) for p in
                  config.COLLECTIONS_ROOT.glob("*/protocols/*/SoA2USDM")})


@pytest.mark.parametrize("path", PANEL_FILES, ids=lambda p: p.name)
def test_panel_file_validates(path):
    schema = json.loads((SCHEMAS / "soa2usdm-panel-context-members.schema.json").read_text())
    jsonschema.validate(json.loads(path.read_text()), schema)


@pytest.mark.parametrize("path", PANEL_FILES, ids=lambda p: p.name)
def test_panel_file_consistent(path):
    """Inputs are the files as they are now; each context panel is the protocol context's own entry;
    every pointer resolves; the counts add up."""
    d = json.loads(path.read_text())
    pid, c = d["protocol_id"], d["collection"]
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    assert d["inputs"]["activity_grain"]["sha256"] == sha(grain_path(pid, c))
    assert d["inputs"]["protocol_context"]["sha256"] == sha(context_path(pid, c))
    ctx = json.loads(context_path(pid, c).read_text())
    for cp in d["context_panels"]:
        src = ctx["panels"][int(cp["pointer"].rsplit("/", 1)[1])]
        assert cp == {"pointer": cp["pointer"], "panel_name": src["panel_name"], "specimen": src.get("specimen"),
                      "lab": src.get("lab"), "evidence": src["evidence"]}
    ptrs = {cp["pointer"] for cp in d["context_panels"]}
    for r in d["rows"]:
        assert {p for n in r["names"] for p in n["context_panels"]} <= ptrs
        for m in r["members"]:
            assert {s["context_panel"] for s in m["sources"]} <= ptrs
            assert any(m["text"] in s["analyte"] for s in m["sources"]), (r["xact_id"], m["member_id"])
    assert d["counts"]["members"] == sum(len(r["members"]) for r in d["rows"])
    assert d["counts"]["panel_rows"] == len(d["rows"]) == sum(d["counts"]["by_link"].values())


@pytest.mark.parametrize("study", STUDIES, ids=lambda s: f"{s[1]}/{s[0]}")
def test_panel_file_only_where_protocol_context(study):
    pid, c = study
    has = pcm.panels_path(pid, c).exists()
    assert has == (context_path(pid, c).exists() and grain_path(pid, c).exists())


# ---------------------------------------------------------------------------
# Reading review of the members (step 3 4d), kept by hand
# ---------------------------------------------------------------------------
REVIEW_JSON = config.COLLECTIONS_ROOT / "panel_member_review.json"


@pytest.mark.skipif(not REVIEW_JSON.exists(), reason="collections/panel_member_review.json not present")
def test_review_file_validates_and_subjects_resolve():
    schema = json.loads((SCHEMAS / "soa2usdm-panel-member-review.schema.json").read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    review = json.loads(REVIEW_JSON.read_text())
    jsonschema.validate(review, schema)
    keys = [json.dumps(e["subject"], sort_keys=True) for e in review["reviews"]]
    assert len(keys) == len(set(keys)), "a subject is reviewed twice"
    for e in review["reviews"]:
        s = e["subject"]
        ctx = json.loads(context_path(s["protocol_id"], s["collection"]).read_text())
        cp = ctx["panels"][int(s["context_panel"].rsplit("/", 1)[1])]
        if s["kind"] == "analyte":
            assert s["analyte"] in cp["analytes"], s
            d = json.loads(pcm.panels_path(s["protocol_id"], s["collection"]).read_text())
            assert s["xact_id"] in {r["xact_id"] for r in d["rows"]}, s
