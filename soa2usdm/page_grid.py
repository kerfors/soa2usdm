"""
Page Grid — rule-line cell geometry for SoA table pages

Recovers a table's cell rectangles from the rendered page rather than from the
PDF's vector layer, so that vector pages and full-page raster images (scanned
or image-only SoA pages, which carry no `rects`/`lines`/`curves`) go through
ONE code path. The text layer, when present, is then assigned to cells by
position: a word belongs to the cell whose rectangle contains its centre.

Method (prompts/PDF_TO_JSON_PROMPT.md §1d):
    1. Render the page to greyscale at 200 dpi (pdftoppm); ink = grey < 128.
    2. Vertical rules  = pixel columns holding a long unbroken run of ink.
    3. Horizontal rules = within each column band, pixel rows whose ink run
       covers the band's width.
    4. A row rule is kept when at least two column bands agree on it.
       This is what makes a solid fill (a redaction bar in the activity-name
       column) harmless: the bar reads as ink in ONE column only, so it can
       neither create a rule nor delete a row. Anchoring row geometry on a
       single column loses the rows a fill covers.
    5. Bands are the gaps between consecutive rules; px / (dpi / 72) = points.

Rules a column does NOT see are recorded as merged cells for that column: a
comment cell spanning three activity rows is one cell, and a note bounded by
it is one annotation, not three fragments.

Requires: poppler (pdftoppm, pdftotext) on PATH, and numpy.
"""

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


# =============================================================================
# Constants — the calibrated detector
# =============================================================================

RENDER_DPI = 200                # §1d render resolution
INK_MAX_GREY = 128              # grey below this is ink
MIN_RULE_LENGTH_IN = 0.5        # a rule is at least this long (inches)
VRULE_MAX_THICKNESS_PX = 12     # thicker than this is a filled area, not a rule
HRULE_MAX_THICKNESS_PX = 8
COLUMN_INSET_PX = 4             # ignore the column's own vertical rules
HRULE_MIN_COVERAGE = 0.9        # a row rule spans (almost) the whole column
MIN_COLUMN_WIDTH_PX = 6
MIN_BAND_HEIGHT_PX = 6
RULE_CLUSTER_TOL_PX = 3         # rules this close are the same rule
SUPERSCRIPT_HEIGHT = 0.85       # a marker glyph is set smaller than its line
SUPERSCRIPT_RISE = 0.15         # ... and raised above the line's baseline
MIN_RULE_COLUMNS = 2            # column bands that must agree on a row rule

XHTML = "{http://www.w3.org/1999/xhtml}"
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


# =============================================================================
# Data
# =============================================================================

@dataclass(frozen=True)
class Word:
    """One text-layer word, in PDF points, origin top-left (as rendered)."""
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class PageGrid:
    """Cell geometry of one page, in PDF points.

    columns / rows are (start, end) band pairs in reading order.
    merged_cells[(row_index, column_index)] gives the row-index span of the
    cell occupying that position when it covers more than one row band.
    filled_cells holds positions whose column shows a solid fill instead of
    text (a redaction bar) — the row exists, its content does not.
    """
    page: int
    dpi: int
    width_pt: float
    height_pt: float
    columns: list[tuple[float, float]]
    rows: list[tuple[float, float]]
    merged_cells: dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)
    filled_cells: set[tuple[int, int]] = field(default_factory=set)

    def cell(self, row: int, column: int) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1) of one cell, widened over the rows it merges."""
        first, last = self.merged_cells.get((row, column), (row, row))
        x0, x1 = self.columns[column]
        return x0, self.rows[first][0], x1, self.rows[last][1]


# =============================================================================
# Rendering and text
# =============================================================================

def _require(tool: str) -> None:
    if shutil.which(tool) is None:
        raise RuntimeError(
            f"{tool} not found on PATH. Page geometry needs poppler-utils "
            f"(pdftoppm, pdftotext); install it or run this step where poppler is available."
        )


def _numpy():
    try:
        import numpy
    except ImportError:
        raise RuntimeError(
            "numpy is required for page geometry. Install the extra: pip install 'soa2usdm[bands]'"
        )
    return numpy


def render_page(pdf_path: Path, page: int, dpi: int = RENDER_DPI):
    """Render one page to a greyscale numpy array (rows = y, columns = x)."""
    _require("pdftoppm")
    np = _numpy()
    raw = subprocess.run(
        ["pdftoppm", "-gray", "-r", str(dpi), "-f", str(page), "-l", str(page),
         "-singlefile", str(pdf_path)],
        capture_output=True, check=True).stdout
    if raw[:2] != b"P5":
        raise RuntimeError(f"pdftoppm did not return a PGM for {pdf_path} page {page}")
    offset = 2
    header = []
    while len(header) < 3:
        while raw[offset:offset + 1].isspace():
            offset += 1
        if raw[offset:offset + 1] == b"#":
            while raw[offset:offset + 1] != b"\n":
                offset += 1
            continue
        start = offset
        while not raw[offset:offset + 1].isspace():
            offset += 1
        header.append(int(raw[start:offset]))
    offset += 1
    width, height, _maxval = header
    return np.frombuffer(raw[offset:offset + width * height], dtype="uint8").reshape(height, width)


def page_count(pdf_path: Path) -> int:
    """Number of pages in a PDF."""
    _require("pdfinfo")
    out = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, check=True,
                         text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1])
    raise RuntimeError(f"pdfinfo reported no page count for {pdf_path}")


def page_words(pdf_path: Path, page: int) -> list[Word]:
    """Text-layer words of one page, in points, origin top-left.

    Empty for a page with no text layer (an image-only scan) — the caller
    decides what that means; this function does not guess at pixels.
    """
    _require("pdftotext")
    raw = subprocess.run(
        ["pdftotext", "-bbox", "-f", str(page), "-l", str(page), str(pdf_path), "-"],
        capture_output=True, check=True).stdout.decode("utf-8", "replace")
    root = ET.fromstring(CONTROL_CHARS.sub("", raw))
    element = root.find(f".//{XHTML}page")
    return [Word(float(w.get("xMin")), float(w.get("yMin")),
                 float(w.get("xMax")), float(w.get("yMax")), w.text or "")
            for w in element.iter(f"{XHTML}word")]


# =============================================================================
# Rule detection — pure functions over the rendered page
# =============================================================================

def longest_runs(mask, axis: int):
    """Longest unbroken run of True per column (axis=0) or per row (axis=1)."""
    np = _numpy()
    scan = mask if axis == 0 else mask.T
    run = np.zeros(scan.shape[1], dtype="int32")
    best = np.zeros(scan.shape[1], dtype="int32")
    for line in scan:
        run = (run + 1) * line
        np.maximum(best, run, out=best)
    return best


def group_positions(positions, gap: int = 2) -> list[tuple[int, int]]:
    """Consecutive positions (within gap) collapsed to (first, last) runs."""
    groups: list[list[int]] = []
    for position in positions:
        if groups and position - groups[-1][-1] <= gap:
            groups[-1].append(int(position))
        else:
            groups.append([int(position)])
    return [(g[0], g[-1]) for g in groups]


def vertical_rules(ink, dpi: int = RENDER_DPI) -> list[tuple[int, int]]:
    """Column-rule positions in pixels.

    Length, not ink fraction: a table covering the top third of the page has
    rules as real as a full-page one.
    """
    np = _numpy()
    minimum = int(MIN_RULE_LENGTH_IN * dpi)
    candidates = np.where(longest_runs(ink, axis=0) >= minimum)[0]
    return [r for r in group_positions(candidates) if r[1] - r[0] <= VRULE_MAX_THICKNESS_PX]


def column_bands(rules: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """The gaps between consecutive vertical rules."""
    return [(a[1], b[0]) for a, b in zip(rules, rules[1:])
            if b[0] - a[1] >= MIN_COLUMN_WIDTH_PX]


def column_row_rules(ink, x0: int, x1: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(row rules, solid fills) inside one column band, in pixels.

    A run of ink covering the column's width is a rule; the same run too thick
    to be a rule is a filled cell — a redaction bar reads as ink across every
    one of its rows.
    """
    np = _numpy()
    inner = ink[:, x0 + COLUMN_INSET_PX:x1 - COLUMN_INSET_PX]
    if inner.shape[1] <= 0:
        return [], []
    needed = max(4, int(HRULE_MIN_COVERAGE * inner.shape[1]))
    runs = group_positions(np.where(longest_runs(inner, axis=1) >= needed)[0])
    rules = [r for r in runs if r[1] - r[0] <= HRULE_MAX_THICKNESS_PX]
    fills = [r for r in runs if r[1] - r[0] > HRULE_MAX_THICKNESS_PX]
    return rules, fills


def consensus_rules(per_column: list[list[tuple[int, int]]],
                    min_columns: int = MIN_RULE_COLUMNS) -> list[tuple[int, set[int]]]:
    """Row rules the columns agree on, as (position, columns that saw it).

    Agreement is the whole point: a rule seen in one column only is that
    column's own ink (the top or bottom edge of a fill), not a row boundary.
    """
    seen: dict[int, set[int]] = {}
    for index, rules in enumerate(per_column):
        for a, b in rules:
            seen.setdefault((a + b) // 2, set()).add(index)
    clusters: list[list[int]] = []
    for position in sorted(seen):
        if clusters and position - clusters[-1][-1] <= RULE_CLUSTER_TOL_PX:
            clusters[-1].append(position)
        else:
            clusters.append([position])
    needed = min(min_columns, len(per_column))
    kept = []
    for cluster in clusters:
        columns: set[int] = set()
        for position in cluster:
            columns |= seen[position]
        if len(columns) >= needed:
            kept.append((round(sum(cluster) / len(cluster)), columns))
    return kept


def row_bands(rule_positions: list[int]) -> list[tuple[int, int]]:
    """The gaps between consecutive row rules."""
    return [(a, b) for a, b in zip(rule_positions, rule_positions[1:])
            if b - a >= MIN_BAND_HEIGHT_PX]


# =============================================================================
# The grid
# =============================================================================

def page_grid(pdf_path: Path, page: int, dpi: int = RENDER_DPI) -> PageGrid:
    """Cell geometry of one page — the same path for vector and raster pages."""
    ink = render_page(pdf_path, page, dpi) < INK_MAX_GREY
    height_px, width_px = ink.shape
    scale = dpi / 72.0
    columns_px = column_bands(vertical_rules(ink, dpi))
    per_column, fills = [], []
    for x0, x1 in columns_px:
        rules, filled = column_row_rules(ink, x0, x1)
        per_column.append(rules)
        fills.append(filled)
    rules = consensus_rules(per_column)
    bands_px = row_bands([position for position, _columns in rules])
    grid = PageGrid(
        page=page, dpi=dpi,
        width_pt=width_px / scale, height_pt=height_px / scale,
        columns=[(x0 / scale, x1 / scale) for x0, x1 in columns_px],
        rows=[(y0 / scale, y1 / scale) for y0, y1 in bands_px],
    )
    _mark_merges(grid, bands_px, rules, fills)
    _mark_fills(grid, bands_px, fills)
    return grid


def _mark_merges(grid: PageGrid, bands_px, rules, fills) -> None:
    """Record, per column, the row bands a single cell covers.

    The rule between two bands is missing in a column exactly when that
    column's cell spans both — the geometric definition of a merged cell.
    A rule buried in a solid fill is obscured, not absent: a redaction bar
    does not merge the rows it covers.
    """
    support = {position: columns for position, columns in rules}
    for column, filled in enumerate(fills):
        start = 0
        for index in range(len(bands_px)):
            boundary = bands_px[index][1]
            obscured = any(a <= boundary <= b for a, b in filled)
            joins_next = (index + 1 < len(bands_px)
                          and bands_px[index + 1][0] == boundary
                          and column not in support.get(boundary, set())
                          and not obscured)
            if joins_next:
                continue
            if start != index:
                for member in range(start, index + 1):
                    grid.merged_cells[(member, column)] = (start, index)
            start = index + 1


def _mark_fills(grid: PageGrid, bands_px, fills) -> None:
    """Record cells whose column is solid ink over the band (a redaction bar)."""
    for column, filled in enumerate(fills):
        for a, b in filled:
            for index, (y0, y1) in enumerate(bands_px):
                if a <= (y0 + y1) // 2 <= b:
                    grid.filled_cells.add((index, column))


# =============================================================================
# Text by cell
# =============================================================================

def words_in(words: list[Word], x0: float, y0: float, x1: float, y1: float) -> list[Word]:
    """Words whose centre falls inside the rectangle."""
    return [w for w in words if x0 <= w.cx <= x1 and y0 <= w.cy <= y1]


def text_lines(words: list[Word]) -> list[list[Word]]:
    """Words grouped into printed lines, each line left to right.

    Grouping is by vertical overlap rather than by y coordinate, so a
    superscript footnote marker stays on the line it annotates instead of
    sorting ahead of it and turning 'Demographics ⁱ' into 'iDemographics'.
    """
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: w.cy):
        for line in lines:
            top = min(w.y0 for w in line)
            bottom = max(w.y1 for w in line)
            if top <= word.cy <= bottom:
                line.append(word)
                break
        else:
            lines.append([word])
    for line in lines:
        line.sort(key=lambda w: w.x0)
    return sorted(lines, key=lambda line: min(w.y0 for w in line))


def join_words(words: list[Word]) -> str:
    """Words in reading order, spaced only where the source leaves a real gap.

    Deliberately gap-driven: a de-glyphed text layer stores single characters,
    and joining those on a fixed separator would put a space inside every word.
    """
    parts: list[str] = []
    for line in text_lines(words):
        previous = None
        for word in line:
            if previous is not None and word.x0 - previous.x1 > 0.18 * max(1.0, previous.y1 - previous.y0):
                parts.append(" ")
            parts.append(word.text)
            previous = word
    return "".join(parts).strip()


def drop_superscripts(words: list[Word]) -> list[Word]:
    """Words minus the superscript glyphs printed on each line.

    A footnote marker is set smaller and raised: 'CBC¹²' is the row CBC, not a
    row called CBC12. Dropping markers geometrically beats stripping them
    textually, which cannot tell a marker from a label that ends in a digit.
    """
    kept: list[Word] = []
    for line in text_lines(words):
        heights = sorted(w.y1 - w.y0 for w in line)
        median = heights[len(heights) // 2]
        baseline = max(w.y1 for w in line)
        for word in line:
            raised = baseline - word.y1 >= SUPERSCRIPT_RISE * median
            small = (word.y1 - word.y0) <= SUPERSCRIPT_HEIGHT * median
            if not (raised and small):
                kept.append(word)
    return kept


def cell_text(grid: PageGrid, words: list[Word], row: int, column: int) -> str:
    """Text of one cell, over the full extent of a merged cell."""
    return join_words(words_in(words, *grid.cell(row, column)))


def column_texts(grid: PageGrid, words: list[Word], column: int = 0) -> list[str]:
    """Text of every row band in one column — the activity-label column by default."""
    return [cell_text(grid, words, row, column) for row in range(len(grid.rows))]
