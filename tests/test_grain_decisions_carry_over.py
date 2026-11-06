"""
tools/grain_decisions_carry_over.py — carries ai_proposed grain decisions to new
grain inputs when their items are unchanged (decisions schema 1.4), drops and
records a decision whose phrase is no longer an item, and leaves reviewed
decisions alone. Negative controls: a decision not made from the inputs on disk,
a changed item, a changed study block and a new cdisc test row stop it without
writing anything.
"""
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import activity_grain as ag
from soa2usdm import activity_grain_inputs as gi

TOOL = Path(__file__).parent.parent / "tools" / "grain_decisions_carry_over.py"
spec = importlib.util.spec_from_file_location("grain_decisions_carry_over", TOOL)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
SCHEMA = json.loads((Path(__file__).parent.parent / "schemas"
                     / "soa2usdm-activity-grain-decisions.schema.json").read_text())

ITEM_A = {"phrase": "anti aav5 antibodies", "spellings": ["Anti-AAV5 antibodies"], "rule": {"grain": "unsure"}}
ITEM_B = {"phrase": "ebv and adenovirus monitoring", "spellings": ["EBV and adenovirus monitoring"],
          "rule": {"grain": "unsure"}}
OLD = {"schema_name": "soa2usdm-activity-grain-inputs", "schema_version": "1.3", "collection": "c",
       "protocol_id": "NCT0", "sources": {"rules_version": "1.1.0"}, "items": [ITEM_A, ITEM_B],
       "study": {"product": []}, "cdisc": {"domains": [{"domain": "IS"}], "tests": [{"code": "C1"}, {"code": "C2"}]}}


def _new(**kw):
    """The inputs as gathered with the new rules: ITEM_B is no longer an item, one cdisc row less."""
    d = json.loads(json.dumps(OLD)) | {"sources": {"rules_version": "1.2.0"}, "items": [ITEM_A],
                                       "cdisc": {"domains": [{"domain": "IS"}], "tests": [{"code": "C1"}]}}
    d.update(kw)
    return d


def _ai(phrase, sha):
    return {"phrase": phrase, "grain": "panel", "source": "ai_proposed", "rationale": "Several tests.",
            "basis": [{"type": "label"}], "proposed_by": "test", "proposed_at": "2026-11-06",
            "prompt_version": "1.5.0", "inputs_content_sha256": sha}


def _setup(tmp_path, monkeypatch, new, made_from=None):
    ipath, dpath = tmp_path / "NCT0_grain_inputs.json", tmp_path / "NCT0_activity_grain_decisions.json"
    ipath.write_text(json.dumps(OLD, indent=1))
    old_sha = gi.content_sha256(OLD)
    rv = {"phrase": "eligibility check", "grain": "other", "source": "reviewed", "rationale": "Admin.",
          "basis": [{"type": "label"}], "proposed_by": "Kerstin Forsberg", "proposed_at": "2026-11-02"}
    doc = {"schema_name": "soa2usdm-activity-grain-decisions", "schema_version": "1.3", "protocol_id": "NCT0",
           "protocol_context": None,
           "decisions": [_ai(ITEM_A["phrase"], made_from or old_sha), _ai(ITEM_B["phrase"], old_sha), rv]}
    dpath.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    written = []
    monkeypatch.setattr(ag, "inputs_path", lambda pid, c: ipath)
    monkeypatch.setattr(ag, "decisions_path", lambda pid, c: dpath)
    monkeypatch.setattr(tool, "build_grain_inputs", lambda c, pid, lk, rows: new)
    monkeypatch.setattr(tool, "write_grain_inputs", lambda c, pid, lk, rows: written.append(pid))
    monkeypatch.setattr(ag, "label_grain", lambda text, lk: {"grain": "panel", "rule_id": "P2"})
    return dpath, doc, old_sha, written


def test_unchanged_items_are_carried_and_the_rest_recorded(tmp_path, monkeypatch):
    new = _new()
    dpath, before, old_sha, written = _setup(tmp_path, monkeypatch, new)
    tool.carry_over("c", "NCT0", None, [])
    after = json.loads(dpath.read_text())
    jsonschema.validate(after, SCHEMA)
    assert after["schema_version"] == "1.4" and written == ["NCT0"]
    a, rv = after["decisions"]
    new_sha = gi.content_sha256(new)
    assert a == before["decisions"][0] | {"inputs_content_sha256": new_sha, "carried_over_from": old_sha}
    assert rv == before["decisions"][2]
    assert after["carry_overs"] == [{
        "from_inputs_content_sha256": old_sha, "to_inputs_content_sha256": new_sha,
        "grain_rules_version": ag.RULES_VERSION, "carried_on": after["carry_overs"][0]["carried_on"], "carried": 1,
        "dropped": [{"phrase": ITEM_B["phrase"], "grain": "panel", "rule_result": "panel/P2"}]}]


def test_unchanged_content_needs_no_carry_over(tmp_path, monkeypatch):
    dpath, _, _, written = _setup(tmp_path, monkeypatch, json.loads(json.dumps(OLD)))
    text = dpath.read_text()
    assert "nothing to carry" in tool.carry_over("c", "NCT0", None, [])
    assert dpath.read_text() == text and written == []


@pytest.mark.parametrize("new, made_from, message", [
    (_new(), "f" * 64, "not made from the current"),
    (_new(items=[ITEM_A | {"rule": {"grain": "procedure"}}]), None, "item\\(s\\) changed"),
    (_new(study={"product": [{"name": "x"}]}), None, "'study' of the grain inputs changed"),
    (_new(cdisc={"domains": [{"domain": "IS"}], "tests": [{"code": "C1"}, {"code": "C3"}]}), None,
     "new cdisc test row"),
])
def test_carry_over_stops_without_writing(tmp_path, monkeypatch, new, made_from, message):
    dpath, _, _, written = _setup(tmp_path, monkeypatch, new, made_from)
    text = dpath.read_text()
    with pytest.raises(ValueError, match=message):
        tool.carry_over("c", "NCT0", None, [])
    assert dpath.read_text() == text and written == []
