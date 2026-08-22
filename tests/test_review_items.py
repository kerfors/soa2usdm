"""
review_items — open judgement calls as data (backlog item 6).

An extraction may carry `review_items`, one per row of the uncertainty report's
Decisions-needed block. Resolution is DERIVED: an item is decided exactly when
a corrections-sidecar entry names it in `review_item` (op `confirm` keeps the
call; any other op is the alternative taken). Nothing records a decision in the
raw extraction, so raw stays immutable and the sidecar is the only write path.

The item used throughout is D2 of NCT05051579 (misc_studies), transcribed from
that protocol's uncertainty report of 2026-08-20 — the n12 scope call.
"""
import copy
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import config
from soa2usdm.corrections import apply_corrections, review_status
from soa2usdm.resolve import resolve_extraction
from soa2usdm.consolidate import consolidate_tables

FIXTURE = Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179" / "SoA2USDM" / "extracted"
RAW_T1 = FIXTURE / "NCT04677179_Table_01_extraction.json"

D2 = {
    "id": "D2",
    "severity": "high",
    "location": {"page": 16, "row_positions": [49, 50, 51], "annotation_marker": "n12"},
    "call_made": "Note 12 (menopausal status) applied to three rows: FSH, because the note sits "
                 "inside the FSH row's box, and LH and Estradiol because the note names all three analytes.",
    "alternative": "FSH only - the strict geometric reading.",
    "report_section": "6",
}


def _schema(name):
    return json.loads((config.SCHEMAS_DIR / name).read_text())


def _sidecar(*corrections):
    return {"schema_name": "soa-table-corrections", "schema_version": "1.0",
            "target_extraction": RAW_T1.name, "corrections": list(corrections)}


def _corr(cid, **kw):
    base = {"id": cid, "target": "annotations", "op": "confirm", "reason": "test",
            "by": "pytest", "at": "2026-08-22T12:00:00+02:00"}
    base.update(kw)
    return base


# ---------------------------------------------------------------- schemas

def test_review_item_validates_and_required_fields_are_enforced():
    raw = json.loads(RAW_T1.read_text())
    schema = _schema("soa-table-extraction.schema.json")
    raw["review_items"] = [D2]
    jsonschema.validate(raw, schema)
    for missing in ("severity", "location", "call_made", "alternative", "report_section"):
        broken = copy.deepcopy(D2)
        del broken[missing]
        raw["review_items"] = [broken]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(raw, schema)
    raw["review_items"] = [{**D2, "id": "2"}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(raw, schema)


def test_review_items_absent_is_legal_everywhere():
    """No backfill is forced: the whole banked fixture corpus validates without the key."""
    ext = _schema("soa-table-extraction.schema.json")
    for p in sorted(FIXTURE.glob("*_extraction.json")):
        doc = json.loads(p.read_text())
        assert "review_items" not in doc
        jsonschema.validate(doc, ext)


def test_corrections_schema_accepts_confirm_and_review_item():
    schema = _schema("soa-table-corrections.schema.json")
    jsonschema.validate(_sidecar(_corr("corr-001", review_item="D2")), schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_sidecar(_corr("corr-001", review_item="two")), schema)


# ---------------------------------------------------------------- apply_corrections

def test_confirm_changes_nothing_and_requires_review_item():
    raw = json.loads(RAW_T1.read_text())
    raw["review_items"] = [D2]
    out = apply_corrections(raw, _sidecar(_corr("corr-001", review_item="D2")))
    assert out == raw
    with pytest.raises(ValueError, match="requires 'review_item'"):
        apply_corrections(raw, _sidecar(_corr("corr-001")))


def test_review_item_reference_must_exist():
    raw = json.loads(RAW_T1.read_text())
    raw["review_items"] = [D2]
    with pytest.raises(ValueError, match="not in the extraction's review_items"):
        apply_corrections(raw, _sidecar(_corr("corr-001", review_item="D9")))


def test_sidecar_can_add_review_items_to_an_older_extraction():
    """Backfill route for pre-v3.8.0 extractions: raw untouched, items arrive via the sidecar."""
    raw = json.loads(RAW_T1.read_text())
    assert "review_items" not in raw
    out = apply_corrections(raw, _sidecar(
        _corr("corr-001", target="review_items", op="add", set=D2),
        _corr("corr-002", review_item="D2"),          # may reference the item just added
    ))
    assert out["review_items"] == [D2]
    assert "review_items" not in raw                 # the raw dict is not mutated


# ---------------------------------------------------------------- derived status

def test_review_status_is_derived_from_sidecar_references(tmp_path):
    raw = json.loads(RAW_T1.read_text())
    raw["review_items"] = [D2, {**D2, "id": "D3"}]
    (tmp_path / RAW_T1.name).write_text(json.dumps(raw))
    status = review_status(tmp_path)
    assert (status["total"], status["open"], status["decided"]) == (2, 2, 0)

    sidecar = tmp_path / RAW_T1.name.replace("_extraction.json", "_corrections.json")
    sidecar.write_text(json.dumps(_sidecar(_corr("corr-001", review_item="D3"))))
    status = review_status(tmp_path)
    assert (status["total"], status["open"], status["decided"]) == (2, 1, 1)
    by_id = {i["id"]: i for i in status["items"]}
    assert by_id["D3"]["correction_id"] == "corr-001" and by_id["D2"]["correction_id"] is None


# ---------------------------------------------------------------- pass-through

def test_resolve_carries_review_items_only_when_present():
    raw = json.loads(RAW_T1.read_text())
    assert "review_items" not in resolve_extraction(copy.deepcopy(raw), RAW_T1.name)
    raw["review_items"] = [D2]
    assert resolve_extraction(raw, RAW_T1.name)["review_items"] == [D2]


def test_consolidate_aggregates_review_items_with_table_number(tmp_path):
    raw = json.loads(RAW_T1.read_text())
    raw["review_items"] = [D2]
    resolved = resolve_extraction(raw, RAW_T1.name)
    f = tmp_path / "t1_resolved.json"
    f.write_text(json.dumps(resolved))
    out = consolidate_tables("NCT04677179", [f])
    assert out["review_items"] == [{"table_number": 1, **D2}]
    assert out["review_queue"] == []                  # consolidation's own queue is separate

    # ids must be unique across tables: the same id in a second table is a defect
    g = tmp_path / "t2_resolved.json"
    resolved2 = copy.deepcopy(resolved)
    resolved2["table_metadata"]["table_number"] = 2
    g.write_text(json.dumps(resolved2))
    with pytest.raises(ValueError, match="not unique"):
        consolidate_tables("NCT04677179", [f, g])

    jsonschema.validate(out, _schema("soa-tables-consolidated.schema.json"))
    jsonschema.validate(resolved, _schema("soa-table-resolved.schema.json"))
