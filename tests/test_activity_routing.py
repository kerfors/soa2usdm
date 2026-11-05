"""
Activity routing — the rules and statuses of soa2usdm.activity_routing, the
public-only guard, and the published routing files.

The rule cases run on a small stub of the lookups (Stub below), so they need no
cdisc-for-ai checkout. They are the cases met on cell_gene_therapy (2026-11-03
to 2026-11-05): an antibody test (open while no public statement covers
antibodies induced by a therapy), IFN-gamma ELISpot (open IS/LB, not LB), flow
cytometry, an Ag/Ab combination test setting the antibody rule aside, a match
only in a footnote (weak), a match only in the parent label (open), and no
match (not routed, PP left out of the fallback).

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


def _route(label, parent=None, annotations=(), kinds=("specimen",)):
    sources = [{"where": "label", "xannot_id": None, "text": label}]
    if parent:
        sources.append({"where": "parent_label", "xannot_id": None, "text": parent})
    for i, t in enumerate(annotations):
        sources.append({"where": "annotation", "xannot_id": f"xannot-{i:03d}", "text": t})
    return ar.route(ar.match_rules(sources), list(kinds), LK)


def test_antibody_open_until_public_statement():
    r = _route("Anti-Drug Antibody/ADA (CL)", kinds=("immunogenicity",))
    assert (r["status"], r["domain"], r["candidates"]) == ("open", None, ["IS"])
    assert "RT-1 IS-A2" in r["question"]


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
