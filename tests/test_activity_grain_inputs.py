"""
Activity grain inputs — what soa2usdm.activity_grain_inputs gathers for the
grain decisions prompt, and the generator's check that the file is current.

Item selection runs on hand-made labels. The cases on real data need the
cell_gene_therapy collection (with protocol context) and a cdisc-for-ai
checkout, and are skipped without them: the inputs are the same on a rebuild,
validate against their schema, list exactly the labels left to decide, and a
changed inputs file stops the generator (with its own message when only the
recorded versions changed). content_sha256 covers the content, not the
version records. Published inputs files validate.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import activity_grain as ag
from soa2usdm import activity_grain_inputs as gi
from soa2usdm import config

SCHEMA = json.loads((Path(__file__).parent.parent / "schemas"
                     / "soa2usdm-activity-grain-inputs.schema.json").read_text())


@pytest.mark.parametrize("label, item_type", [
    ({"grain": "unsure", "finding_kind": None}, "grain unsure"),
    ({"grain": "named test", "finding_kind": "unsure"}, "kind unsure"),
    ({"grain": "sample collection", "finding_kind": None}, "sample collection"),
    ({"grain": "procedure", "finding_kind": None, "rule_id": "W2", "hit_strength": None}, "procedure by word list"),
    ({"grain": "procedure", "finding_kind": None, "rule_id": "L3", "hit_strength": "weak"}, "procedure by word list"),
    ({"grain": "procedure", "finding_kind": None, "rule_id": "L3q", "hit_strength": "weak"}, "procedure by word list"),
    ({"grain": "procedure", "finding_kind": None, "rule_id": "L3", "hit_strength": "strong"}, None),
    ({"grain": "named test", "finding_kind": "specimen", "rule_id": "L1x", "hit_strength": "weak"}, "peeled test"),
    ({"grain": "named test", "finding_kind": "unsure", "rule_id": "L1x", "hit_strength": "weak"}, "peeled test"),
    ({"grain": "named test", "finding_kind": "specimen"}, None),
    ({"grain": "panel", "finding_kind": None}, None),
    ({"grain": "other", "finding_kind": None}, None),
])
def test_item_type(label, item_type):
    assert gi.item_type(label) == item_type


COLLECTION = "cell_gene_therapy"
STUDY = "NCT05020015"
needs_study = pytest.mark.skipif(
    not ag.CDISC_FOR_AI.is_dir() or not ag.context_path(STUDY, COLLECTION).exists(),
    reason=f"needs cdisc-for-ai and {COLLECTION}/{STUDY} with protocol context")


@pytest.fixture(scope="module")
def built():
    lk = ag.Lookups()
    from soa2usdm.activity_inventory import collect_rows
    rows = collect_rows(COLLECTION)
    return lk, rows, gi.build_grain_inputs(COLLECTION, STUDY, lk, rows)


@needs_study
def test_inputs_are_stable_and_validate(built):
    lk, rows, payload = built
    jsonschema.validate(payload, SCHEMA)
    assert gi.build_grain_inputs(COLLECTION, STUDY, lk, rows) == payload


@needs_study
def test_items_are_exactly_the_labels_left_to_decide(built):
    lk, rows, payload = built
    g = ag.generate_study_grain(COLLECTION, STUDY, lk, rows, use_decisions=False)
    with_rows = {r["phrase"] for r in g["activities"] if r["role"] is None}
    expected = {l["phrase"]: gi.item_type(l) for l in g["labels"]
                if gi.item_type(l) and l["phrase"] in with_rows}
    assert {i["phrase"]: i["item_type"] for i in payload["items"]} == expected
    assert [i["phrase"] for i in payload["items"]] == sorted(expected)


@needs_study
def test_every_pointer_resolves(built):
    _, _, payload = built
    ctx = json.loads(ag.context_path(STUDY, COLLECTION).read_text())
    entries = [e for i in payload["items"] for e in i["lab_and_purpose"] + i["abbreviations"]]
    entries += [e for c in payload["study"].values() for e in c]
    for e in entries:
        assert ag.resolve_pointer(ctx, e["pointer"]) == e["entry"]


@needs_study
def test_content_sha256_covers_content_not_sources(built):
    _, _, payload = built
    assert payload["content_sha256"] == gi.content_sha256(payload)
    moved = payload | {"sources": payload["sources"] | {"rules_version": "0.0.0"}, "schema_version": "1.1"}
    assert gi.content_sha256(moved) == payload["content_sha256"]
    assert gi.content_sha256(payload | {"items": payload["items"][1:]}) != payload["content_sha256"]


@needs_study
def test_changed_versions_only_stop_with_their_own_message(built, tmp_path, monkeypatch):
    lk, rows, payload = built
    path = tmp_path / f"{STUDY}_grain_inputs.json"
    monkeypatch.setattr(ag, "inputs_path", lambda pid, c: path)
    cdisc = payload["sources"]["cdisc_for_ai"] | {"commit": "0" * 40}
    path.write_text(json.dumps(payload | {"sources": payload["sources"] | {"cdisc_for_ai": cdisc}}))
    with pytest.raises(RuntimeError, match="only the recorded versions changed"):
        ag._current_inputs(COLLECTION, STUDY, lk, rows)


@needs_study
def test_changed_inputs_file_stops_the_generator(built, tmp_path, monkeypatch):
    lk, rows, payload = built
    path = tmp_path / f"{STUDY}_grain_inputs.json"
    monkeypatch.setattr(ag, "inputs_path", lambda pid, c: path)
    path.write_text(json.dumps(payload))
    current = ag._current_inputs(COLLECTION, STUDY, lk, rows)
    assert current["phrases"] == {i["phrase"] for i in payload["items"]}
    assert current["content_sha256"] == payload["content_sha256"]
    path.write_text(json.dumps(payload | {"items": payload["items"][1:]}))
    with pytest.raises(RuntimeError, match="stale, its inputs changed"):
        ag._current_inputs(COLLECTION, STUDY, lk, rows)


INPUT_FILES = sorted(config.COLLECTIONS_ROOT.glob("*/protocols/*/SoA2USDM/grain/*_grain_inputs.json"))


@pytest.mark.parametrize("path", INPUT_FILES, ids=lambda p: p.name)
def test_inputs_file_validates(path):
    jsonschema.validate(json.loads(path.read_text()), SCHEMA)
