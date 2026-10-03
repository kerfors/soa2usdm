"""
document_references — what an annotation text points at in the protocol, stated
as data (inventory item 3, first part). The pointer only: nothing is looked up.

The texts below are annotation texts of published protocols, quoted as extracted.
The resolve test runs on the two banked fixtures; the extracted-table link needs
the published NCT04677179 resolved files (usdm_data) and is skipped without them.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import config
from soa2usdm.consolidate import consolidate_tables
from soa2usdm.references import find_document_references

SCHEMAS = Path(__file__).parent.parent / "schemas"
PROTOCOLS = Path(__file__).parent / "fixtures" / "protocols"


def _refs(*pairs):
    return [{"kind": kind, "target": target} for kind, target in pairs]


def test_one_entry_per_numbered_target_as_printed():
    assert find_document_references("See Section 6.1.") == _refs(("section", "6.1"))                      # NCT03693430
    assert find_document_references("see Appendix C") == _refs(("appendix", "C"))                         # NCT01797120
    assert find_document_references("See Pharmacokinetic Sampling Schedule (Attachment 7).") == _refs(("attachment", "7"))   # NCT02107703
    assert find_document_references("For procedures at an ETV, see ETV in Table 4.") == _refs(("table", "4"))               # NCT04677179
    assert find_document_references("See Section 10.3 Table 12") == _refs(("section", "10.3"), ("table", "12"))             # NCT03637764
    assert find_document_references("See Figure 5.1-1, Figure 5.1-2 and Figure 5.1-3.") == _refs(
        ("figure", "5.1-1"), ("figure", "5.1-2"), ("figure", "5.1-3"))                                    # NCT04730349
    # Printed without a space in the source cell
    assert find_document_references("See Appendix10.2, Clinical Laboratory Tests, for details.") == _refs(("appendix", "10.2"))   # NCT05324124


def test_a_text_without_a_numbered_target_has_none():
    assert find_document_references("See Pharmacokinetics and immunogenicity Flow Chart") == []           # NCT03637764
    assert find_document_references("A cycle is 21 days") == []                                           # NCT03637764


def test_a_reviewer_note_has_none():
    """A note written during review names tables and sections of its own; it is
    not protocol text (NCT01847274 Table 3, annot-004)."""
    text = ("Footnote not printed in the source (Table 9 prints only footnotes 1-3); no confident "
            "Table 7 (Main Study) equivalent for this Vital signs cell")
    assert find_document_references(text) == []
    assert find_document_references("Reviewer note, not source content: this row prints with no marks "
                                    "at the top of page 15. Table 2 (page 17)") == []


def _resolved(protocol):
    return sorted((PROTOCOLS / protocol / "SoA2USDM" / "resolved").glob("*_resolved.json"))


def test_resolved_fixture_carries_the_references_and_validates():
    schema = json.loads((SCHEMAS / "soa-table-resolved.schema.json").read_text())
    for protocol in ("NCT03637764", "NCT04677179"):
        for f in _resolved(protocol):
            table = json.loads(f.read_text())
            assert table["schema_version"] == "1.2"
            jsonschema.validate(table, schema)
            for annot in table["annotations"]:
                assert annot.get("document_references", []) == find_document_references(annot["annotation_text"])
                assert annot.get("document_references") != []          # absent, never empty
    table1 = json.loads(_resolved("NCT03637764")[0].read_text())
    by_text = {a["annotation_text"]: a for a in table1["annotations"]}
    assert by_text["See Section 10.3 Table 12"]["document_references"] == _refs(("section", "10.3"), ("table", "12"))
    assert "document_references" not in by_text["See Biomarker Flow Chart"]


def _published(protocol_id: str):
    if "usdm_data" not in config.COLLECTIONS:
        return []
    return config.find_resolved_files(protocol_id, "usdm_data")


@pytest.mark.skipif(not _published("NCT04677179"),
                    reason="needs the published NCT04677179 resolved files (usdm_data)")
def test_a_table_reference_to_an_extracted_table_carries_its_number():
    """NCT04677179: 'For procedures at an ETV, see ETV in Table 4.' — Table 4 is one
    of the protocol's extracted tables (its title starts 'Table 4.'), so the unified
    annotation's reference names it. NCT03637764 'Table 12' is a table of the
    protocol body; no extracted table prints that number."""
    out = consolidate_tables("NCT04677179", _published("NCT04677179"))
    assert out["schema_version"] == "1.5"
    by_text = {a["annotation_text"]: a for a in out["unified_annotations"]}
    assert by_text["For procedures at an ETV, see ETV in Table 4."]["document_references"] == [
        {"kind": "table", "target": "4", "table_num": 4}]
    jsonschema.validate(out, json.loads((SCHEMAS / "soa-tables-consolidated.schema.json").read_text()))
    other = consolidate_tables("NCT03637764", _resolved("NCT03637764"))
    body = {a["annotation_text"]: a for a in other["unified_annotations"]}["See Section 10.3 Table 12"]
    assert body["document_references"] == _refs(("section", "10.3"), ("table", "12"))
