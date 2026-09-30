"""
Review page — the extraction against its rendered source pages.

PDF-free tests run on the banked NCT04677179 fixture; the tests that need the
collection's PDF (page geometry, column mapping, the full build) skip when the
usdm_data collection is not checked out beside the code, as test_page_geometry
does. The one fact pinned against the corpus is the tiled-table column map:
NCT04677179 Table 2 prints V10-V19 on its first page and V20-V29 on a later
one, so page column c is NOT column_position c+1 — the map must be read from
the header row, and the mark check that ignored this reported 63 false rows.
"""
import json
import shutil
from pathlib import Path

import pytest

from soa2usdm import config
from soa2usdm.review_page import (_across_tables, _column_map, _markers, build_review_model,
                                  render_review_html)

FIXTURE = Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179" / "SoA2USDM"
SOA_PDF = config.find_soa_pdf("NCT04677179", "usdm_data") if "usdm_data" in config.COLLECTIONS else None
SOA_PAGES = SOA_PDF.parent / "NCT04677179_soa_pages" if SOA_PDF else None
needs_pdf = pytest.mark.skipif(
    not (shutil.which("pdftoppm") and SOA_PDF), reason="needs poppler and the usdm_data PDFs")
needs_pages = pytest.mark.skipif(
    not (SOA_PAGES and (SOA_PAGES / "pages.json").exists()),
    reason="needs the pre-rendered NCT04677179_soa_pages (tools/page_map.py --render)")


def test_markers_are_split_from_the_comma_separated_string():
    assert _markers("n3") == ["n3"]
    assert _markers("a, b ,c") == ["a", "b", "c"]
    assert _markers(None) == [] and _markers("") == []


def test_across_tables_reads_folds_from_the_consolidated_golden():
    cons = json.loads((FIXTURE / "consolidated" / "NCT04677179_consolidated.json").read_text())
    across = _across_tables(cons)
    multi = [ua for ua in cons["unified_activities"] if len(ua["source_refs"]) > 1]
    assert len(across["folds"]) == len(multi)
    fold = next(f for f in across["folds"] if f["name"] == "Concomitant medications")
    assert [s["table"] for s in fold["sources"]] == [1, 2, 3, 4]
    assert fold["status"] == "exact"
    assert across["review_queue"] == cons["review_queue"]
    assert _across_tables(None) == {"folds": [], "review_queue": [], "stats": {}}


@needs_pdf
def test_column_map_is_read_from_the_header_row_on_a_tiled_table():
    from soa2usdm.page_grid import page_grid, page_words
    ext = json.loads((FIXTURE / "extracted" / "NCT04677179_Table_02_extraction.json").read_text())
    props = {p["row_position"]: p for p in ext["schedule_properties"]}
    grid = {}
    for g in ext["schedule_grid"]:
        grid.setdefault(g["row_position"], {})[g["column_position"]] = g["cell_value"]
    # PDF page 8 = document page 24 (first page of Table 2), page 12 = its V20-V29 tile.
    first = _column_map(page_grid(SOA_PDF, 8), page_words(SOA_PDF, 8), props, grid)
    later = _column_map(page_grid(SOA_PDF, 12), page_words(SOA_PDF, 12), props, grid)
    assert first[2] == "header" and later[2] == "header"
    assert first[1][1:11] == list(range(2, 12))     # V10..V19 -> column positions 2..11
    assert later[1][1:11] == list(range(12, 22))    # V20..V29 -> column positions 12..21
    assert first[1][11] is None                     # the Comment column carries no visit
    assert 1 in first[0].values()                   # the visit-number band was found


def test_unreadable_pages_carry_the_audit_reason_first_reason_wins():
    from soa2usdm.review_page import _unreadable_pages
    audit = {"pages_with_rotated_text": [1, 2], "pages_without_text_layer": [2, 3],
             "pages_without_grid": [3, 9]}
    out = _unreadable_pages(audit)
    assert sorted(out) == [1, 2, 3, 9]
    assert out[1].startswith("table printed rotated") and out[2].startswith("table printed rotated")
    assert out[3].startswith("no text layer") and out[9].startswith("no rule-line grid")
    assert _unreadable_pages({}) == {}


@needs_pdf
@needs_pages
def test_full_build_places_every_page_and_references_prerendered_images():
    model = build_review_model("NCT04677179", "usdm_data")
    assert [t["number"] for t in model["tables"]] == [1, 2, 3, 4]
    for t in model["tables"]:
        assert t["pages"], f"table {t['number']} has no pages"
        assert all(p["col_method"] == "header" for p in t["pages"])
        assert t["checks"]["rows_checked"] and t["checks"]["marks_checked"]
        assert t["checks"]["unreadable_pages"] == []
        assert t["checks"]["on_page_not_extracted"] == []
    # The one remaining mark difference is a detector artefact, not an extraction error:
    # on document page 36 a redacted (CCI) row's two marks land in the neighbouring
    # header band. Pinned so that a change in either direction is noticed.
    diffs = [(t["number"], d["row"], d["col"]) for t in model["tables"] for d in t["checks"]["mark_disagreements"]]
    assert diffs == [(3, 38, 4), (3, 38, 8)]
    html = render_review_html(model)
    assert "NCT04677179 — review of the SoA extraction" in html
    # Page images are the pre-rendered, stamped files beside the PDF, referenced
    # relative to the HTML in extracted/. page_frac maps the overlay onto the page
    # region only (the caption strip below it is synthetic).
    assert model["image_dir"] == "../../NCT04677179_soa_pages"
    for t in model["tables"]:
        for p in t["pages"]:
            assert p["img"] == f"../../NCT04677179_soa_pages/p{p['pdf_page']:02d}.png"
            assert (SOA_PAGES / f"p{p['pdf_page']:02d}.png").exists()
            assert 0.9 < p["page_frac"] < 1.0
    assert "</script>" in html and "<\\/" not in html.split("<script>")[0]


@needs_pdf
@needs_pages
def test_mark_check_catches_a_removed_and_an_added_mark(monkeypatch):
    """Negative control: the mark check must flag a mark the extraction lost and a mark it
    invented. NCT04677179 T1 'Informed consent' (row 6) is marked in column 2 only."""
    from soa2usdm import review_page
    real_load = review_page._load

    def tampered(path):
        doc = real_load(path)
        if "Table_01_extraction" in path.name:
            cells = doc["activity_schedule"]
            cells[:] = [c for c in cells if (c["row_position"], c["column_position"]) != (6, 2)]
            cells.append({"table_number": 1, "row_position": 6, "column_position": 3,
                          "cell_value": "X", "source_range": ""})
            # A span with nothing printed under it is a difference too.
            for col in (5, 6):
                cells.append({"table_number": 1, "row_position": 6, "column_position": col,
                              "cell_value": "X", "source_range": "5:6"})
        return doc

    monkeypatch.setattr(review_page, "_load", tampered)
    model = build_review_model("NCT04677179", "usdm_data")
    t1 = [t for t in model["tables"] if t["number"] == 1][0]
    diffs = {(d["row"], d["col"]): (d["extracted"], d["on_page"]) for d in t1["checks"]["mark_disagreements"]}
    assert diffs == {(6, 2): (False, True), (6, 3): (True, False), (6, 5): (True, False), (6, 6): (True, False)}


needs_nct01847274 = pytest.mark.skipif(
    not (shutil.which("pdftoppm") and "usdm_data" in config.COLLECTIONS
         and config.find_soa_pdf("NCT01847274", "usdm_data")),
    reason="needs poppler and the NCT01847274 SoA PDF")


@needs_nct01847274
def test_mark_check_compares_a_merged_mark_once_over_its_span():
    """'Bone marrow aspirate and biopsy' prints one X across a merged cell; the extraction
    repeats it over the covered columns with source_range. That agrees with the page."""
    model = build_review_model("NCT01847274", "usdm_data")
    assert [d for t in model["tables"] for d in t["checks"]["mark_disagreements"]] == []
