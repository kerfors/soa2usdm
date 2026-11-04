"""
tools/grain_decisions_record_content_sha.py — the one-time carry-over of grain
decisions to schema 1.3: it adds inputs_content_sha256 only when every
ai_proposed decision was made from the current grain inputs file, and changes
nothing else. Negative controls: a decision from another inputs file, and a
file that is already 1.3, stop it without writing.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import activity_grain as ag
from soa2usdm import activity_grain_inputs as gi

TOOL = Path(__file__).parent.parent / "tools" / "grain_decisions_record_content_sha.py"
spec = importlib.util.spec_from_file_location("grain_decisions_record_content_sha", TOOL)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
SCHEMA = json.loads((Path(__file__).parent.parent / "schemas"
                     / "soa2usdm-activity-grain-decisions.schema.json").read_text())

INPUTS = {"schema_name": "soa2usdm-activity-grain-inputs", "schema_version": "1.1", "collection": "c",
          "protocol_id": "NCT0", "sources": {"rules_version": "1.0.0"},
          "items": [{"phrase": "anti aav5 antibodies"}], "study": {}, "cdisc": {"domains": [], "tests": []}}


def _setup(tmp_path, monkeypatch, inputs_sha=None, version="1.2"):
    ipath, dpath = tmp_path / "NCT0_grain_inputs.json", tmp_path / "NCT0_activity_grain_decisions.json"
    ipath.write_text(json.dumps(INPUTS, indent=1))
    whole = hashlib.sha256(ipath.read_bytes()).hexdigest()
    ai = {"phrase": "anti aav5 antibodies", "grain": "named test", "finding_kind": "immunogenicity",
          "source": "ai_proposed", "rationale": "One assay.", "basis": [{"type": "label"}],
          "proposed_by": "test", "proposed_at": "2026-11-02", "prompt_version": "1.2.0",
          "inputs_sha256": inputs_sha or whole}
    rv = {"phrase": "eligibility check", "grain": "other", "source": "reviewed", "rationale": "Admin.",
          "basis": [{"type": "label"}], "proposed_by": "Kerstin Forsberg", "proposed_at": "2026-11-02"}
    doc = {"schema_name": "soa2usdm-activity-grain-decisions", "schema_version": version, "protocol_id": "NCT0",
           "protocol_context": None, "decisions": [ai, rv]}
    dpath.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    monkeypatch.setattr(ag, "inputs_path", lambda pid, c: ipath)
    monkeypatch.setattr(ag, "decisions_path", lambda pid, c: dpath)
    return dpath, doc, whole


def test_record_adds_the_content_fingerprint_only(tmp_path, monkeypatch):
    dpath, before, whole = _setup(tmp_path, monkeypatch)
    tool.record("c", "NCT0")
    after = json.loads(dpath.read_text())
    jsonschema.validate(after, SCHEMA)
    assert after["schema_version"] == "1.3"
    ai, rv = after["decisions"]
    assert ai["inputs_content_sha256"] == gi.content_sha256(INPUTS)
    assert ai["inputs_sha256"] == whole
    assert {k: v for k, v in ai.items() if k != "inputs_content_sha256"} == before["decisions"][0]
    assert rv == before["decisions"][1]


@pytest.mark.parametrize("kw, message", [
    ({"inputs_sha256": "f" * 64}, "not made from the current"),
    ({"version": "1.3"}, "already schema 1.3"),
    ({"version": "1.0"}, "only 1.1 / 1.2 files"),
])
def test_record_stops_without_writing(tmp_path, monkeypatch, kw, message):
    dpath, _, _ = _setup(tmp_path, monkeypatch, inputs_sha=kw.get("inputs_sha256"), version=kw.get("version", "1.2"))
    text = dpath.read_text()
    with pytest.raises(ValueError, match=message):
        tool.record("c", "NCT0")
    assert dpath.read_text() == text
