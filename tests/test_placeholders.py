"""
Placeholder annotations (Layer 1 hygiene, decided 2026-11-07).

A marker with no protocol text behind it becomes annotation_type 'placeholder'
with an empty annotation_text and a placeholder_reason; text that is not
protocol text moves to review_note. Both arrive through a corrections sidecar
(raw stays immutable). The schemas tie type, text and reason together;
consolidation never merges two placeholders on their (empty) text; grain
inputs leave placeholders out; pages show the reason in place of the text.
On the published collections: no annotation text that reads as a placeholder
or a borrowed equivalent is left untyped.
"""
import json
import re
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import config
from soa2usdm.consolidate import AnnotationConsolidator
from soa2usdm.corrections import apply_corrections
from soa2usdm.placeholders import display_text

SCHEMAS = Path(__file__).parent.parent / "schemas"


def _schema(name):
    return json.loads((SCHEMAS / name).read_text())


def _annotation_def(name, key):
    s = _schema(name)
    return {"$schema": s.get("$schema"), "definitions": s["definitions"], **s["definitions"][key]}


EXTRACTION = _annotation_def("soa-table-extraction.schema.json", "annotation")
LOC = [{"table_number": 1, "location_type": "activity_name", "row_position": 3}]
PH = {"annotation_marker": "d", "annotation_type": "placeholder", "annotation_text": "",
      "placeholder_reason": "redacted", "marker_locations": LOC}


def test_a_placeholder_validates_with_its_reason_and_a_review_note():
    jsonschema.validate(PH, EXTRACTION)
    jsonschema.validate(PH | {"placeholder_reason": "not_printed", "review_note": "Table 7 footnote 16."}, EXTRACTION)


@pytest.mark.parametrize("annot", [
    PH | {"annotation_text": "Definition not printed in the source."},     # text on a placeholder
    {k: v for k, v in PH.items() if k != "placeholder_reason"},             # no reason
    PH | {"placeholder_reason": "missing"},                                 # unknown reason
    PH | {"annotation_type": "footnote", "annotation_text": "x"},           # reason on a footnote
])
def test_type_text_and_reason_belong_together(annot):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(annot, EXTRACTION)


def test_a_sidecar_retypes_an_annotation_and_raw_is_untouched():
    raw = {"table_metadata": {"table_number": 1},
           "annotations": [{"annotation_marker": "d", "annotation_type": "footnote",
                            "annotation_text": "Definition not printed in the source: CCI.", "marker_locations": LOC}]}
    before = json.dumps(raw)
    corr = {"corrections": [{"id": "corr-001", "target": "annotations", "op": "set", "match": {"annotation_marker": "d"},
                             "set": {"annotation_type": "placeholder", "annotation_text": "",
                                     "placeholder_reason": "redacted"}}]}
    out = apply_corrections(raw, corr)
    assert out["annotations"][0] == PH
    assert json.dumps(raw) == before


def test_placeholders_are_never_merged_on_their_empty_text():
    c = AnnotationConsolidator()
    for marker in ("d", "f"):
        c._process_annotation({"annotation_id": f"annot-{marker}", "annotation_marker": marker,
                               "annotation_type": "placeholder", "annotation_text": "",
                               "placeholder_reason": "redacted", "referenced_elements": {}},
                              1, {}, {}, {}, {}, {})
    c._process_annotation({"annotation_id": "annot-x", "annotation_marker": "x", "annotation_type": "footnote",
                           "annotation_text": "", "referenced_elements": {}}, 1, {}, {}, {}, {}, {})
    out = [ua.to_dict() for ua in c.unified_annotations]
    assert [u["xannot_id"] for u in out] == ["xannot-001", "xannot-002", "xannot-003"]
    assert [u.get("placeholder_reason") for u in out] == ["redacted", "redacted", None]


def test_a_page_shows_the_reason_in_place_of_the_empty_text():
    assert display_text(PH) == "[redacted in source]"
    assert display_text(PH | {"placeholder_reason": "not_printed"}) == "[definition not printed in source]"
    assert display_text({"annotation_type": "footnote", "annotation_text": "Fasting."}) == "Fasting."


# What Layer 1 writes for a marker without protocol text (PDF_TO_JSON_PROMPT §6) and what
# a reviewer note starts with; typed placeholders carry none of it in annotation_text.
UNTYPED = re.compile(r"^(?:Definition |Footnote )?not printed in the (?:extracted )?source|^Reviewer note"
                     r"|Probable equivalent|not source content", re.I)
CONSOLIDATED = sorted(config.COLLECTIONS_ROOT.glob("*/protocols/*/SoA2USDM/consolidated/*_consolidated.json"))


@pytest.mark.skipif(not CONSOLIDATED, reason="needs the collections")
def test_no_untyped_placeholder_text_in_the_collections():
    found = []
    for path in CONSOLIDATED:
        for u in json.loads(path.read_text())["unified_annotations"]:
            if UNTYPED.search(u["annotation_text"]):
                found.append(f"{path.parts[-4]}:{u['xannot_id']}")
    assert found == []
