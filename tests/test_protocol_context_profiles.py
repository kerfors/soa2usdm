"""
Protocol context profiles — the general profile (soa2usdm-protocol-context-general 1.1) beside the cell and
gene therapy profile: its schema, the checker per profile (quotes on the cited page, a wrong quote fails),
the page sections per profile, and the grain inputs study categories per profile (grain inputs 1.4).
Runs on a small hand-made file and pages text; no protocol PDF needed.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import activity_grain_inputs as agi
from soa2usdm import protocol_context_page as pcp

ROOT = Path(__file__).parent.parent
SCHEMAS = ROOT / "schemas"
spec = importlib.util.spec_from_file_location("check_protocol_context", ROOT / "tools" / "check_protocol_context.py")
cpc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpc)

PAGES = ("===== PAGE 1 =====\nProtocol ABC-123 Amendment 2\n"
         "===== PAGE 7 =====\nC-SSRS Columbia Suicide Severity Rating Scale\n"
         "The C-SSRS will be completed by the investigator at each visit.\n"
         "Vital signs include systolic and diastolic blood pressure, pulse rate and body temperature, "
         "measured after 5 minutes rest in a seated position.\n"
         "Hematology: hemoglobin, hematocrit, platelet count\n"
         "===== PAGE 9 =====\nA E a d verse e ve nt\n")


def _doc(pages_sha, quote="The C-SSRS will be completed by the investigator at each visit."):
    ev = lambda q: [{"page": 7, "quote": q}]
    return {
        "schema_name": "soa2usdm-protocol-context-general", "schema_version": "1.1", "nct_id": "NCT00000000",
        "document": "Protocol ABC-123 Amendment 2", "pages_covered": "1-7", "page_numbers": "1-7",
        "provenance": {"prompt_version": "1.0.0", "model": "test", "extracted_at": "2026-11-07",
                       "pdf_sha256": "0" * 64, "pages_file_sha256": pages_sha},
        "cross_references": [],
        "abbreviations": [{"term": "C-SSRS", "definition": "Columbia Suicide Severity Rating Scale", "page": 7}],
        "panels": [{"panel_name": "Hematology", "analytes": ["hemoglobin", "hematocrit", "platelet count"],
                    "specimen": None, "lab": None, "evidence": ev("Hematology: hemoglobin, hematocrit, platelet count")}],
        "lab_and_purpose": [],
        "instruments": [{"name": "Columbia Suicide Severity Rating Scale", "kind": "instrument", "abbreviation": "C-SSRS", "version": None,
                         "type": None, "respondent_or_rater": "investigator", "recall_period": None, "mode": None,
                         "scoring_or_range": None, "purpose": None, "soa_activities": ["C-SSRS"], "evidence": ev(quote)}],
        "measurements": [{"name": "Vital signs", "components": ["systolic and diastolic blood pressure", "pulse rate",
                                                                 "body temperature"],
                          "position_or_condition": "after 5 minutes rest in a seated position", "method": None, "units": None,
                          "soa_activities": ["Vital signs"],
                          "evidence": ev("measured after 5 minutes rest in a seated position.")}],
        "notes": "",
    }


@pytest.fixture
def files(tmp_path):
    pages = tmp_path / "NCT00000000_pages.txt"
    pages.write_text(PAGES, encoding="utf-8")
    sha = hashlib.sha256(pages.read_bytes()).hexdigest()
    return tmp_path, pages, sha


def _write(tmp_path, doc):
    f = tmp_path / "NCT00000000_protocol_context.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    return f


def test_general_profile_validates_and_checks(files):
    tmp_path, pages, sha = files
    doc = _doc(sha)
    jsonschema.validate(doc, json.loads((SCHEMAS / "soa2usdm-protocol-context-general.schema.json").read_text()))
    fails, visual = cpc.check(_write(tmp_path, doc), pages)
    assert (fails, visual) == ([], [])


def test_general_profile_wrong_quote_fails(files):
    tmp_path, pages, sha = files
    fails, _ = cpc.check(_write(tmp_path, _doc(sha, quote="The C-SSRS will be completed by the participant.")), pages)
    assert [(f[0], f[1], f[2]) for f in fails] == [("instruments", 0, 7)]


def test_general_profile_null_nct_id_validates(files):
    tmp_path, pages, sha = files
    fails, _ = cpc.check(_write(tmp_path, _doc(sha) | {"nct_id": None}), pages)
    assert fails == []


def test_instrument_kind_is_required(files):
    tmp_path, pages, sha = files
    doc = _doc(sha)
    del doc["instruments"][0]["kind"]
    fails, _ = cpc.check(_write(tmp_path, doc), pages)
    assert any(f[0] == "schema" for f in fails)


def test_letter_spaced_abbreviation_matches_without_whitespace(files):
    tmp_path, pages, sha = files
    doc = _doc(sha)
    doc["abbreviations"].append({"term": "AE", "definition": "adverse event", "page": 9})
    fails, _ = cpc.check(_write(tmp_path, doc), pages)
    assert fails == []
    doc["abbreviations"][-1]["definition"] = "adverse events"
    fails, _ = cpc.check(_write(tmp_path, doc), pages)
    assert [(f[0], f[1], f[2]) for f in fails] == [("abbreviations", 1, 9)]


def test_general_profile_has_no_cgt_categories(files):
    tmp_path, pages, sha = files
    fails, _ = cpc.check(_write(tmp_path, _doc(sha) | {"product": []}), pages)
    assert any(f[0] == "schema" for f in fails)


def test_shared_categories_have_the_cgt_shapes():
    cgt = json.loads((SCHEMAS / "soa2usdm-protocol-context-cgt.schema.json").read_text())["properties"]
    gen = json.loads((SCHEMAS / "soa2usdm-protocol-context-general.schema.json").read_text())["properties"]
    for k in ("cross_references", "abbreviations", "panels", "lab_and_purpose", "provenance"):
        assert gen[k] == cgt[k], k


def test_page_sections_and_grain_inputs_categories_per_profile():
    assert set(pcp.PROFILES) == set(agi.STUDY_CATEGORIES) == set(cpc.EVIDENCE_CATS)
    assert agi.STUDY_CATEGORIES["soa2usdm-protocol-context-general"] == ("instruments", "measurements")
    assert {k for k, _, _ in pcp.PROFILES["soa2usdm-protocol-context-general"]} == \
        set(cpc.EVIDENCE_CATS["soa2usdm-protocol-context-general"])
    inputs_schema = json.loads((SCHEMAS / "soa2usdm-activity-grain-inputs.schema.json").read_text())
    study = inputs_schema["properties"]["study"]
    jsonschema.validate({"instruments": [], "measurements": []}, study)
    jsonschema.validate({"product": [], "immunogenicity": [], "endpoint_assays": [], "genetic_testing": []}, study)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"instruments": [], "product": []}, study)
