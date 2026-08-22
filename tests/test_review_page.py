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
needs_pdf = pytest.mark.skipif(
    not (shutil.which("pdftoppm") and SOA_PDF), reason="needs poppler and the usdm_data PDFs")


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


@needs_pdf
def test_full_build_places_every_page_and_renders(tmp_path):
    model = build_review_model("NCT04677179", "usdm_data", image_dir=tmp_path / "NCT04677179_review_pages")
    assert [t["number"] for t in model["tables"]] == [1, 2, 3, 4]
    for t in model["tables"]:
        assert t["pages"], f"table {t['number']} has no pages"
        assert all(p["col_method"] == "header" for p in t["pages"])
        assert t["checks"]["on_page_not_extracted"] == []
    # The one remaining mark difference is a detector artefact, not an extraction error:
    # on document page 36 a redacted (CCI) row's two marks land in the neighbouring
    # header band. Pinned so that a change in either direction is noticed.
    diffs = [(t["number"], d["row"], d["col"]) for t in model["tables"] for d in t["checks"]["mark_disagreements"]]
    assert diffs == [(3, 38, 4), (3, 38, 8)]
    html = render_review_html(model)
    assert "NCT04677179 — review of the SoA extraction" in html
    # Page images are files beside the HTML, referenced relatively, one per PDF page.
    assert model["image_dir"] == "NCT04677179_review_pages"
    for t in model["tables"]:
        for p in t["pages"]:
            assert p["img"] == f"NCT04677179_review_pages/p{p['pdf_page']:02d}.png"
            assert (tmp_path / p["img"]).exists()
    assert "</script>" in html and "<\\/" not in html.split("<script>")[0]
