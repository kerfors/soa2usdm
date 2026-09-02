"""
Page geometry and the row-completeness audit.

The geometry tests run on real measurements banked from NCT04677179 PDF page
27 (doc page 43) — the page whose activity-name column carries a solid
redaction bar. The bar is the reason row geometry is taken from column
agreement instead of from one anchor column, so it is also the negative
control: fed only that column's rules, the same code loses the row, exactly as
the first version of this method did.

The audit tests run on what those pages actually print (banked verbatim from
read_page) against a real historical extraction — NCT04677179 Table 2 before
the missing 'Genetics sample' row was restored. A completeness check that has
never seen an incomplete extraction proves nothing.

Tests needing the PDFs themselves are skipped when the collection is not
checked out, like the rest of the suite; the banked fixtures keep the logic
under test on a bare clone.
"""
import json
import shutil

import pytest

from soa2usdm import config
from soa2usdm.page_grid import consensus_rules, row_bands
from soa2usdm.row_audit import (PageRead, PageRow, assign_pages, audit_table, best_matches,
                                caption_table, extraction_labels, keyed, label_columns,
                                match_score, normalise)

PAGES_DIR = config.FIXTURES_ROOT / "pages"
NEGATIVE_DIR = config.FIXTURES_ROOT / "negative"
RULES_FIXTURE = json.loads((PAGES_DIR / "NCT04677179_page27_rules.json").read_text(encoding="utf-8"))
LABELS_FIXTURE = json.loads(
    (PAGES_DIR / "NCT04677179_table02_page_labels.json").read_text(encoding="utf-8"))
TABLE4_FIXTURE = json.loads(
    (PAGES_DIR / "NCT04677179_table04_page_labels.json").read_text(encoding="utf-8"))
PRE_GENETICS = json.loads(
    (NEGATIVE_DIR / "NCT04677179_Table_02_pre_genetics_extraction.json").read_text(encoding="utf-8"))
PRE_PAGE43 = json.loads(
    (NEGATIVE_DIR / "NCT04677179_Table_04_pre_page43_extraction.json").read_text(encoding="utf-8"))

# The redaction bar on page 27 covers pixels 1199-1240; the row it hides runs
# between the rules at 1200 and 1239.
REDACTED_ROW = (1200, 1239)

POPPLER = all(shutil.which(tool) for tool in ("pdftoppm", "pdftotext", "pdfinfo"))
try:
    import numpy  # noqa: F401
    NUMPY = True
except ImportError:
    NUMPY = False
SOA_PDF = config.find_soa_pdf("NCT04677179", config.DEFAULT_COLLECTION)
needs_pdf = pytest.mark.skipif(
    not (POPPLER and NUMPY and SOA_PDF),
    reason="needs poppler, numpy and the collection's PDFs")


def banked_column_rules():
    return [[tuple(rule) for rule in column] for column in RULES_FIXTURE["column_row_rules_px"]]


def banked_reads(fixture=None):
    """The banked page labels as the audit's own objects."""
    reads = {}
    for page in (fixture or LABELS_FIXTURE)["pages"]:
        rows = [PageRow(page=page["page"], row=row["row"], y0=row["y0"], y1=row["y1"],
                        texts=row["texts"]) for row in page["rows"]]
        reads[page["page"]] = PageRead(page=page["page"], rows=rows, caption=page["caption"],
                                       has_grid=page["has_grid"], has_text=page["has_text"],
                                       mark_columns=page["mark_columns"], rotated=page["rotated"])
    return reads


# =============================================================================
# Row geometry
# =============================================================================

def test_columns_agree_on_the_row_rules():
    bands = row_bands([position for position, _columns in consensus_rules(banked_column_rules())])
    assert len(bands) == 22
    assert REDACTED_ROW in bands


def test_single_column_geometry_loses_the_redacted_row():
    """Negative control: the black-bar failure, on the page it happened on.

    Column 0's own rules are swallowed by the fill, so a method anchored on
    the activity-name column reads the redacted row and its neighbour as one
    band — the row disappears, marks and all.
    """
    name_column = banked_column_rules()[0]
    bands = row_bands([position for position, _columns in
                       consensus_rules([name_column], min_columns=1)])
    assert REDACTED_ROW not in bands
    assert len(bands) < 22
    swallowed = [band for band in bands if band[0] <= REDACTED_ROW[0] and band[1] >= REDACTED_ROW[1]]
    assert len(swallowed) == 1


def test_the_fill_is_reported_where_it_is():
    fills = RULES_FIXTURE["column_fills_px"]
    assert fills[0] == [[1199, 1240]]
    assert all(not column for column in fills[1:])


# =============================================================================
# Label matching
# =============================================================================

def test_match_score_accepts_equal_marked_and_clipped_labels():
    assert match_score("vitalsigns", "vitalsigns")[0] == 3
    assert match_score("demographicsi", "demographics")[0] == 2
    assert match_score("haematologyclinicaldchemistry", "haematologyclinicalchemistry")[0] == 2
    assert match_score("coloncopybiopsysamplecollec", "coloncopybiopsysamplecollection")[0] == 1


def test_match_score_refuses_a_substring():
    """'randomization' must not bind to 'weeks from randomization'."""
    assert match_score("randomization", "weeksfromrandomization")[0] == 0
    assert match_score("dosing", "nodosingatetv")[0] == 0


def test_best_matches_keeps_equally_good_labels():
    labels = keyed(["CCI", "CCI (redacted)", "Vital signs"])
    assert set(best_matches("CCI", labels)) == {"CCI", "CCI (redacted)"}
    assert best_matches("", labels) == []


# =============================================================================
# Page to table assignment
# =============================================================================

def test_captions_split_tables_that_share_their_activities():
    scores = [[5, 5], [5, 5], [5, 5], [5, 5]]
    assert assign_pages(scores, [None, None, 1, None]) == [0, 0, 1, 1]
    # Without a caption the same scores cannot separate the two tables, and
    # the earlier table takes the pages — visible afterwards as a page count
    # that disagrees with the extraction's own page range.
    assert assign_pages(scores, [None] * 4) == [0, 0, 0, 0]


def test_declared_page_windows_separate_lookalike_tables():
    """NCT04320615: three appendices (77-80, 81-83, 84-85) sharing most row
    labels. Label overlap alone gave Table 1 five pages and Table 3 none; the
    declared windows settle it; pages whose labels fit an excluded table
    better than any table inside their window are reported, not moved."""
    from soa2usdm.row_audit import constrain_to_windows
    pages = list(range(1, 10))
    doc_pages = {p: p + 76 for p in pages}
    windows = [(77, 80), (81, 83), (84, 85)]
    scores = [[20, 18, 3], [19, 17, 2], [0, 0, 0], [0, 0, 0], [17, 15, 4],
              [2, 2, 0], [16, 16, 2], [15, 15, 14], [0, 0, 0]]
    outside = constrain_to_windows(scores, pages, doc_pages, windows)
    assert scores == [[20, 0, 0], [19, 0, 0], [0, 0, 0], [0, 0, 0], [0, 15, 0],
                      [0, 2, 0], [0, 16, 0], [0, 0, 14], [0, 0, 0]]
    assert assign_pages(scores, [None] * 9) == [0, 0, None, None, 1, 1, 1, 2, None]
    assert [(o["page"], o["table_index"], o["best_inside_window"]) for o in outside] == [
        (5, 0, 15), (8, 0, 14), (8, 1, 14)]
    # A table without a declared window takes any page, and an excluded table
    # that merely ties the inside one is zeroed without a report.
    scores = [[5, 5], [5, 5]]
    assert constrain_to_windows(scores, [1, 2], {1: 10, 2: 11}, [(10, 10), (None, None)]) == []
    assert scores == [[5, 5], [0, 5]]


def test_a_caption_two_tables_share_anchors_nothing():
    titles = ["Study Schedule Protocol I8F-MC-GPGS", "Study Schedule Protocol I8F-MC-GPGS"]
    assert caption_table(normalise("Study Schedule Protocol I8F-MC-GPGS"), titles) is None
    concluded = ["Schedule of Events for Protocol H2Q-MC-LZZT(c)",
                 "Schedule of Events for Protocol H2Q-MC-LZZT(c) (concluded)"]
    assert caption_table(normalise("Schedule of Events for Protocol H2Q-MC-LZZT(c) (concluded) "
                                   "Visit 9 10 11"), concluded) == 1


# =============================================================================
# The audit, against a real incomplete extraction
# =============================================================================

def test_audit_finds_the_row_the_extraction_dropped():
    """Negative control: Table 2 as it stood before the Genetics sample fix.

    The row prints on PDF page 15 (doc page 31) and three of this protocol's
    four extractions did not have it. Nothing in the JSON could say so.
    """
    reads = banked_reads()
    result = audit_table(reads, sorted(reads), extraction_labels(PRE_GENETICS))
    missing = [finding["text"] for finding in result["on_page_not_extracted"]]
    assert any(normalise(text) == "geneticssample" for text in missing)
    assert result["label_columns"] == [0]


def test_audit_is_quiet_once_the_row_is_there():
    restored = json.loads(json.dumps(PRE_GENETICS))
    restored["activities"].append({"row_position": 999, "activity_name": "Genetics sample"})
    reads = banked_reads()
    result = audit_table(reads, sorted(reads), extraction_labels(restored))
    missing = [finding["text"] for finding in result["on_page_not_extracted"]]
    assert not any(normalise(text) == "geneticssample" for text in missing)


def test_audit_finds_the_page_the_extraction_never_covered():
    """Negative control: Table 4 as it stood before the rev3 re-extraction.

    Its activities began on PDF page 28; everything on PDF page 27 (doc page
    43) — 14 rows and their 26 marks — had never been extracted. The page is
    the unit that went missing, and only the pages can show that.
    """
    reads = banked_reads(TABLE4_FIXTURE)
    result = audit_table(reads, sorted(reads), extraction_labels(PRE_PAGE43))
    dropped = [finding for finding in result["on_page_not_extracted"] if finding["page"] == 27]
    assert len(dropped) == 14
    printed = {normalise(finding["text"]) for finding in dropped}
    assert "adverseevents" in printed
    assert "vitalsigns" in printed
    coverage = {page["page"]: page for page in result["page_coverage"]}
    assert coverage[27]["matched"] < coverage[28]["matched"]


def test_audit_reports_labels_no_page_prints():
    invented = json.loads(json.dumps(PRE_GENETICS))
    invented["activities"].append({"row_position": 998, "activity_name": "Bone marrow aspirate"})
    reads = banked_reads()
    result = audit_table(reads, sorted(reads), extraction_labels(invented))
    assert "Bone marrow aspirate" in result["extracted_not_on_page"]


def test_label_columns_ignore_columns_of_marks():
    reads = banked_reads()
    rows = [row for page in sorted(reads) for row in reads[page].rows]
    assert label_columns(rows, keyed(extraction_labels(PRE_GENETICS))) == [0]


# =============================================================================
# The pixel path, when the PDFs are there
# =============================================================================

@needs_pdf
def test_page_grid_reproduces_the_banked_rules():
    from soa2usdm.page_grid import (INK_MAX_GREY, column_bands, column_row_rules, render_page,
                                    vertical_rules)
    ink = render_page(SOA_PDF, RULES_FIXTURE["pdf_page"]) < INK_MAX_GREY
    columns = column_bands(vertical_rules(ink))
    assert [list(column) for column in columns] == RULES_FIXTURE["column_bands_px"]
    for index, (x0, x1) in enumerate(columns):
        rules, fills = column_row_rules(ink, x0, x1)
        assert [list(rule) for rule in rules] == RULES_FIXTURE["column_row_rules_px"][index]
        assert [list(fill) for fill in fills] == RULES_FIXTURE["column_fills_px"][index]


@needs_pdf
@pytest.mark.parametrize("fixture", [LABELS_FIXTURE, TABLE4_FIXTURE],
                         ids=["table02", "table04"])
def test_read_page_reproduces_the_banked_labels(fixture):
    from soa2usdm.row_audit import read_page
    for page in fixture["pages"]:
        read = read_page(SOA_PDF, page["page"])
        assert [row.texts for row in read.rows] == [row["texts"] for row in page["rows"]]
        assert read.mark_columns == page["mark_columns"]
        assert read.rotated == page["rotated"]
