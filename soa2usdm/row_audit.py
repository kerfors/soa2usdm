"""
Row Completeness Audit (collection-scoped)

Compares the activity labels an extraction contains against the activity
labels its source pages actually print, using the rule-line cell geometry in
page_grid. This is the one completeness check that cannot be built from the
JSON alone: an extraction that silently omits a row — or a whole page — is
internally consistent, and every JSON-only metric (density, structural gaps,
row counts) is blind to it. Only the page knows what was there.

The method found the missing 'Genetics sample' row in NCT04677179 T2/T3/T4 and
the never-extracted first page of that protocol's Table 4.

Two directions are reported per table:
    on_page_not_extracted   a label the page prints and no extraction row
                            matches — a candidate dropped row.
    extracted_not_on_page   an extraction label no page band matches — a
                            candidate mislabelled or misplaced row.

Both are candidates for human review, not verdicts: a sponsor convention
(section headers never tabulated, redaction placeholders) reads exactly like a
dropped row here, and only the protocol's reviewer can tell them apart.

Two things are deliberately derived from the pages rather than assumed:

  * Which pages belong to which table — by the caption each page prints, then
    by label overlap under the constraint that tables do not interleave.
    Arithmetic on `table_metadata.page_start/page_end` does not survive the
    corpus (the SoA PDFs are page subsets whose offsets follow no single
    rule), and page metadata is itself extraction output — an audit must not
    lean on what it audits. The derived assignment is reported so it can be
    checked.

  * Which columns carry row labels — some tables print the procedure name in
    one column, others a category column plus a name column, and both carry
    auditable rows. A column counts as a label column when the extraction's
    labels explain most of what it prints.

Requires poppler and numpy (see page_grid).
"""

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .base import PipelineStepBase
from .page_grid import (cell_text, drop_superscripts, join_words, page_count,
                        page_grid, page_words)

# =============================================================================
# Constants
# =============================================================================

MARK_CHARS = 3                  # a schedule mark is 'X', 'X1', '—' — never prose
MARK_COLUMN_RATE = 0.5          # ... and a schedule column is mostly marks
MIN_MARK_COLUMNS = 2            # a schedule page has at least this many
PAGE_IN_TABLE_RATE = 0.5        # a page belongs to a table when it explains this much of it
ROTATED_WORD_RATE = 0.5         # this many sideways words means the table is printed rotated
ROTATED_ASPECT = 1.5            # ... a word being sideways when it is this much taller than wide
LABEL_COLUMN_LIMIT = 3          # leading columns that may carry row labels
LABEL_COLUMN_MATCH_RATE = 0.5   # ... and how much of one the labels must explain
LABEL_COLUMN_MIN_MATCHES = 2
CAPTION_BAND = 0.22             # top fraction of the page holding the table caption
CAPTION_MATCH_CHARS = 40        # caption prefix compared against the table title
CAPTION_ANCHOR_WEIGHT = 1000    # a caption outweighs any amount of label overlap
MARKER_CHARS = 4                # footnote-marker characters printed with a label
MIN_MARKED_CHARS = 6            # shortest label matched through marker characters
MIN_CLIPPED_CHARS = 12          # shortest prefix accepted as a clipped label
NOTE_BAND_CHARS = 150           # longer than any label in the corpus (max 117): a note block
NOISE = re.compile(r"[^a-z0-9]")
TRAILING_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")


# =============================================================================
# Label matching — pure
# =============================================================================

def normalise(text: str) -> str:
    """Comparison form: lowercase, letters and digits only.

    Whitespace is dropped, not normalised: a de-glyphed text layer prints
    'Sc he d ule of A ctivities', and any space-preserving comparison fails on
    exactly the pages that most need auditing.
    """
    return NOISE.sub("", (text or "").lower())


def label_keys(label: str) -> set[str]:
    """Comparison forms of an extraction label.

    A trailing parenthetical is often the extractor's own qualifier
    ('CCI (redacted)') rather than printed text, so it is also matched without.
    """
    return {normalise(label), normalise(TRAILING_PARENTHETICAL.sub("", label or ""))} - {""}


def contains_in_order(key: str, printed: str) -> bool:
    """Every character of key appears in printed, in order."""
    position = 0
    for character in key:
        position = printed.find(character, position) + 1
        if position == 0:
            return False
    return True


def match_score(printed: str, key: str) -> tuple[int, int]:
    """How well a printed band matches one label key: (kind, length).

    kind 3 equal, 2 the label with a few footnote-marker characters printed
    around or inside it, 1 one is a clipped prefix of the other, 0 no match.
    Strict on purpose — substring matching binds 'randomization' to 'weeks
    from randomization' and poisons everything after it.
    """
    if not printed or not key:
        return (0, 0)
    if printed == key:
        return (3, len(key))
    if (len(key) >= MIN_MARKED_CHARS and 0 < len(printed) - len(key) <= MARKER_CHARS
            and contains_in_order(key, printed)):
        return (2, len(key))
    if len(printed) >= MIN_CLIPPED_CHARS and (key.startswith(printed) or printed.startswith(key)):
        return (1, min(len(printed), len(key)))
    return (0, 0)


def best_matches(printed_text: str, keyed_labels: list[tuple[str, str]]) -> list[str]:
    """Every label tied at the best score for this text.

    Ties are kept rather than broken: a page printing 'CCI' beside six
    redacted rows matches all of them equally, and picking one would report
    the other five as missing.
    """
    printed = normalise(printed_text)
    if not printed:
        return []
    best: list[str] = []
    best_score = (0, 0)
    for key, label in keyed_labels:
        score = match_score(printed, key)
        if score > best_score:
            best, best_score = [label], score
        elif score == best_score and score[0] > 0 and label not in best:
            best.append(label)
    return best


def extraction_labels(extraction: dict) -> list[str]:
    """Every label an extraction claims a row for, activities and properties.

    Schedule-property rows (visit number, study day, fasting visit) print in
    the same column as activities and repeat on every continuation page; they
    are labels for matching, never findings.
    """
    labels = [a.get("activity_name", "") for a in extraction.get("activities", [])]
    labels += [p.get("property_name", "") for p in extraction.get("schedule_properties", [])]
    return [label for label in labels if label]


def keyed(labels: list[str]) -> list[tuple[str, str]]:
    """(comparison key, label) pairs for matching."""
    return [(key, label) for label in labels for key in label_keys(label)]


# =============================================================================
# Reading pages
# =============================================================================

@dataclass
class PageRow:
    """One row band of a page: what each candidate label column prints."""
    page: int
    row: int
    y0: float
    y1: float
    texts: list[str]


@dataclass
class PageRead:
    """Everything one page contributes to the audit, read once."""
    page: int
    rows: list[PageRow]
    caption: str
    has_grid: bool
    has_text: bool
    mark_columns: int = 0
    rotated: bool = False

    @property
    def is_schedule_page(self) -> bool:
        """Whether this page carries a schedule grid at all.

        A page can hold a rule-lined table of activity names and still not be
        part of the SoA — a glossary of visit definitions lists the same
        procedures in the same shape. What it lacks is columns of marks, and
        that is the difference this tests.
        """
        return self.mark_columns >= MIN_MARK_COLUMNS


def read_page(pdf_path: Path, page: int) -> PageRead:
    """Row bands and caption of one page.

    A page with no rule-line grid carries no table (a footnote page); a page
    with a grid but no text layer is an image-only scan. Neither yields rows,
    and the difference matters: the first is nothing to audit, the second is
    an audit that cannot be performed. Nothing is read from pixels.
    """
    grid = page_grid(pdf_path, page)
    words = page_words(pdf_path, page)
    caption = normalise(join_words([w for w in words if w.y1 <= grid.height_pt * CAPTION_BAND]))
    has_grid = bool(grid.columns and grid.rows)
    if not has_grid or not words:
        return PageRead(page=page, rows=[], caption=caption,
                        has_grid=has_grid, has_text=bool(words))
    labels = drop_superscripts(words)
    columns = min(LABEL_COLUMN_LIMIT, len(grid.columns))
    rows = [PageRow(page=page, row=index,
                    y0=round(grid.rows[index][0], 1), y1=round(grid.rows[index][1], 1),
                    texts=[cell_text(grid, labels, index, column) for column in range(columns)])
            for index in range(len(grid.rows))]
    multichar = [w for w in words if len(w.text) >= 3]
    sideways = sum(1 for w in multichar if (w.y1 - w.y0) > ROTATED_ASPECT * (w.x1 - w.x0))
    rotated = bool(multichar) and sideways / len(multichar) >= ROTATED_WORD_RATE
    marks = 0
    for column in range(len(grid.columns)):
        cells = [normalise(cell_text(grid, words, row, column)) for row in range(len(grid.rows))]
        filled = [cell for cell in cells if cell]
        if (filled and sum(1 for cell in filled if len(cell) <= MARK_CHARS) / len(filled)
                >= MARK_COLUMN_RATE):
            marks += 1
    return PageRead(page=page, rows=rows, caption=caption, has_grid=True, has_text=True,
                    mark_columns=marks, rotated=rotated)


def caption_table(caption: str, titles: list[str]) -> int | None:
    """Which table's title this page's caption prints, if any.

    Continuation pages repeat the caption, and it is the only signal that
    separates sibling tables: page geometry and label overlap cannot tell
    Table 2 from Table 3 when both schedule the same procedures.
    """
    matches = []
    for index, title in enumerate(titles):
        key = normalise(title)[:CAPTION_MATCH_CHARS]
        if len(key) >= MIN_CLIPPED_CHARS and key in caption:
            matches.append((len(key), index))
    if not matches:
        return None
    # Longest title wins: sibling tables share a prefix ('... (concluded)'),
    # and the shorter title matches the longer table's caption too. Tables
    # sharing one title anchor nothing — the caption cannot tell them apart.
    longest = max(length for length, _index in matches)
    tied = [index for length, index in matches if length == longest]
    return tied[0] if len(tied) == 1 else None


def label_columns(rows: list[PageRow], keyed_labels: list[tuple[str, str]]) -> list[int]:
    """Which candidate columns carry row labels for this table.

    Decided by what the extraction explains rather than by column width: a
    schedule column holds marks, which match nothing, while a category column
    and a procedure column both match and both hold auditable rows.
    """
    if not rows:
        return []
    chosen = []
    for column in range(max(len(row.texts) for row in rows)):
        texts = [row.texts[column] for row in rows
                 if column < len(row.texts) and row.texts[column].strip()]
        if not texts:
            continue
        matched = sum(1 for text in texts if best_matches(text, keyed_labels))
        if matched >= LABEL_COLUMN_MIN_MATCHES and matched / len(texts) >= LABEL_COLUMN_MATCH_RATE:
            chosen.append(column)
    return chosen


def page_score(rows: list[PageRow], keyed_labels: list[tuple[str, str]]) -> int:
    """How many of a page's row bands one table's labels explain."""
    return sum(1 for row in rows
               if any(best_matches(text, keyed_labels) for text in row.texts))


def assign_pages(scores: list[list[int]], anchors: list[int | None]) -> list[int | None]:
    """Assign each page to a table, or to none, maximising explained bands.

    Tables run in document order and do not interleave, so the assignment is
    an ordered partition. Pages whose caption names a table are anchored to
    it; the rest follow from that ordering and from how many of their bands
    each table's labels explain. Ties go to the earlier table.
    scores[page][table]; returns one table index (or None) per page.
    """
    pages = len(scores)
    tables = len(scores[0]) if pages else 0
    if not pages or not tables:
        return [None] * pages
    weight = [[score + (CAPTION_ANCHOR_WEIGHT if anchors[page] == table else 0)
               for table, score in enumerate(row)] for page, row in enumerate(scores)]
    best = [[0] * (tables + 1) for _ in range(pages + 1)]
    choice: list[list[tuple | None]] = [[None] * (tables + 1) for _ in range(pages + 1)]
    for table in range(1, tables + 1):
        for page in range(1, pages + 1):
            options = [("skip_table", best[page][table - 1], (page, table - 1))]
            if weight[page - 1][table - 1] > 0 and anchors[page - 1] in (None, table - 1):
                options.append(("take", best[page - 1][table] + weight[page - 1][table - 1],
                                (page - 1, table)))
            if anchors[page - 1] is None:
                options.append(("unassigned", best[page - 1][table], (page - 1, table)))
            kind, value, move = max(options, key=lambda option: option[1])
            best[page][table] = value
            choice[page][table] = (kind, move[0], move[1])
    assignment: list[int | None] = [None] * pages
    page, table = pages, tables
    while page > 0 and table > 0:
        move = choice[page][table]
        if move is None:
            break
        kind, page, table = move
        if kind == "take":
            assignment[page] = table - 1
    return assignment


# =============================================================================
# The audit
# =============================================================================

def audit_table(reads: dict[int, PageRead], pages: list[int], labels: list[str]) -> dict:
    """Compare one table's extraction labels against the pages assigned to it."""
    keyed_labels = keyed(labels)
    columns = label_columns([row for page in pages for row in reads[page].rows], keyed_labels)
    coverage = [{"page": page, "bands": len(reads[page].rows), "matched": 0} for page in pages]
    if not columns:
        # No column on these pages reads as a list of this table's labels —
        # a transposed table (activities across the top) or an assignment
        # that went wrong. Reporting every label as missing would be noise.
        return {"pages": pages, "label_columns": [], "page_coverage": coverage,
                "on_page_not_extracted": [], "extracted_not_on_page": [], "note_bands": [],
                "note": "no label column identified — transposed table, or wrong pages assigned"}
    seen: set[str] = set()
    unmatched: list[dict] = []
    notes: list[dict] = []
    coverage = []
    for page in pages:
        in_body = False
        matched_here = 0
        page_rows = reads[page].rows
        for row in page_rows:
            found = False
            for column in (c for c in columns if c < len(row.texts)):
                matches = best_matches(row.texts[column], keyed_labels)
                if matches:
                    seen.update(matches)
                    found = True
            if found:
                in_body = True
                matched_here += 1
                continue
            if not in_body:
                # Bands above the first matched row are the caption and the
                # table's instruction block, not rows.
                continue
            for column in (c for c in columns if c < len(row.texts)):
                text = row.texts[column]
                if not text.strip():
                    continue
                record = {"page": page, "row": row.row, "y": row.y0,
                          "column": column, "text": text}
                # A band longer than any label in the corpus is the table's
                # footnote or instruction block, not a row.
                (notes if len(normalise(text)) > NOTE_BAND_CHARS else unmatched).append(record)
        coverage.append({"page": page, "bands": len(page_rows), "matched": matched_here})
    return {
        "pages": pages,
        "label_columns": columns,
        "page_coverage": coverage,
        "on_page_not_extracted": unmatched,
        "extracted_not_on_page": sorted(set(labels) - seen),
        "note_bands": notes,
    }


def audit_protocol(protocol_id: str, collection: str) -> dict:
    """Row-completeness audit of every table of one protocol."""
    pdf_path = config.find_soa_pdf(protocol_id, collection)
    extraction_files = config.find_extraction_files(protocol_id, collection)
    result = {"protocol_id": protocol_id, "tables": [], "status": "ok",
              "pdf": pdf_path.name if pdf_path else None}
    if pdf_path is None:
        result["status"] = "no_pdf"
        return result
    if not extraction_files:
        result["status"] = "no_extraction"
        return result

    extractions = [json.loads(path.read_text(encoding="utf-8")) for path in extraction_files]
    labels_per_table = [extraction_labels(extraction) for extraction in extractions]
    keyed_per_table = [keyed(labels) for labels in labels_per_table]

    pages = list(range(1, page_count(pdf_path) + 1))
    reads = {page: read_page(pdf_path, page) for page in pages}
    result["pages_without_grid"] = [p for p in pages if not reads[p].has_grid]
    result["pages_without_schedule_columns"] = [
        p for p in pages if reads[p].rows and not reads[p].is_schedule_page]
    # A table printed sideways has its activities across the top, not down a
    # column: this audit reads rows, so it says so rather than reporting every
    # activity as missing.
    result["pages_with_rotated_text"] = [p for p in pages if reads[p].rotated]
    result["pages_without_text_layer"] = [p for p in pages
                                          if reads[p].has_grid and not reads[p].has_text]

    titles = [e.get("table_metadata", {}).get("table_title", "") for e in extractions]
    anchors = [caption_table(reads[page].caption, titles) for page in pages]
    scores = [[page_score(reads[page].rows, keys)
               if reads[page].is_schedule_page and not reads[page].rotated else 0
               for keys in keyed_per_table] for page in pages]
    # A schedule page that no extraction explains is not a dropped row, it is a
    # dropped page: reporting its every band against the nearest table would
    # bury that. Held out of the assignment and reported as a page.
    orphans = [page for index, page in enumerate(pages)
               if reads[page].is_schedule_page and reads[page].rows and not reads[page].rotated
               and anchors[index] is None
               and max(scores[index]) < PAGE_IN_TABLE_RATE * len(reads[page].rows)]
    result["pages_not_in_any_extraction"] = orphans
    for index, page in enumerate(pages):
        if page in orphans:
            scores[index] = [0] * len(keyed_per_table)
    assignment = assign_pages(scores, anchors)
    result["page_assignment"] = [
        {"page": page, "table_index": assignment[index],
         "source": "caption" if anchors[index] is not None else "inferred"}
        for index, page in enumerate(pages)]

    for index, (extraction, path) in enumerate(zip(extractions, extraction_files)):
        metadata = extraction.get("table_metadata", {})
        assigned = [pages[i] for i, table in enumerate(assignment) if table == index]
        table_result = {
            "table_number": metadata.get("table_number"),
            "table_title": metadata.get("table_title", ""),
            "source_file": path.name,
            "declared_pages": [metadata.get("page_start"), metadata.get("page_end")],
            "activities": len(extraction.get("activities", [])),
        }
        if assigned:
            table_result.update(audit_table(reads, assigned, labels_per_table[index]))
        else:
            table_result.update({"pages": [], "label_columns": [], "page_coverage": [],
                                 "on_page_not_extracted": [], "extracted_not_on_page": [],
                                 "note_bands": [],
                                 "note": "no page of the PDF matches this table's labels"})
        declared = table_result["declared_pages"]
        if assigned and all(isinstance(page, int) for page in declared):
            table_result["declared_page_count"] = declared[1] - declared[0] + 1
            table_result["page_count_agrees"] = table_result["declared_page_count"] == len(assigned)
            if table_result["page_count_agrees"]:
                # What to add to a PDF page to get the document page the
                # extraction cites. Derived, and only where the two agree on
                # how many pages the table has — anywhere else the pages
                # cannot be lined up and no number is offered.
                table_result["doc_page_offset"] = declared[0] - assigned[0]
        result["tables"].append(table_result)
    return result


def audit_collection(collection: str, protocols: list[str] | None = None) -> dict:
    """Row-completeness audit of every protocol in a collection."""
    chosen = protocols or config.list_extractable_protocols(collection)
    results = [audit_protocol(protocol_id, collection) for protocol_id in chosen]
    return {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "collection": collection,
        "counts": {
            "protocols": len(results),
            "protocols_audited": sum(1 for r in results if r["status"] == "ok"),
            "tables": sum(len(r["tables"]) for r in results),
            "tables_without_pages": sum(1 for r in results for t in r["tables"] if not t["pages"]),
            "pages_not_in_any_extraction": sum(len(r.get("pages_not_in_any_extraction", []))
                                               for r in results),
            "on_page_not_extracted": sum(len(t["on_page_not_extracted"])
                                         for r in results for t in r["tables"]),
            "extracted_not_on_page": sum(len(t["extracted_not_on_page"])
                                         for r in results for t in r["tables"]),
        },
        "protocols": results,
    }


def format_summary(report: dict) -> str:
    """One line per table, then its findings — what a reviewer reads first."""
    lines = []
    for protocol in report["protocols"]:
        if protocol["status"] != "ok":
            lines.append(f"{protocol['protocol_id']}: {protocol['status']}")
            continue
        head = protocol["protocol_id"]
        blind = protocol.get("pages_without_text_layer", [])
        if blind:
            head += f"  NO TEXT LAYER on pages {blind} — cannot be audited"
        lines.append(head)
        rotated = protocol.get("pages_with_rotated_text", [])
        if rotated:
            lines.append(f"  ROTATED TABLE on pages {rotated} — rows run across, not down; "
                         f"not audited")
        orphans = protocol.get("pages_not_in_any_extraction", [])
        if orphans:
            lines.append(f"  SCHEDULE PAGES IN NO EXTRACTION: {orphans}")
        for table in protocol["tables"]:
            matched = sum(page["matched"] for page in table["page_coverage"])
            bands = sum(page["bands"] for page in table["page_coverage"])
            note = "" if table.get("page_count_agrees", True) else "  PAGE COUNT DISAGREES"
            if not table["pages"]:
                note = "  NO PAGES MATCHED"
            if table.get("note"):
                note = f"  {table['note'].upper()}"
            lines.append(f"  T{table['table_number']} pages {table['pages']} "
                         f"declared {table['declared_pages']} "
                         f"rows {matched}/{bands} matched{note}")
            offset = table.get("doc_page_offset")
            for finding in table["on_page_not_extracted"]:
                # Both numbers, always: the PDF page opens the file, the doc
                # page is what the extraction and the reports cite, and they
                # are not the same number.
                where = (f"PDF p{finding['page']} / doc p{finding['page'] + offset}"
                         if offset is not None else f"PDF p{finding['page']}")
                lines.append(f"     on page, not extracted  {where} "
                             f"y{finding['y']} col{finding['column']}: {finding['text'][:80]!r}")
            for label in table["extracted_not_on_page"]:
                lines.append(f"     extracted, not on page  {label!r}")
    counts = report["counts"]
    lines.append(f"{counts['protocols_audited']}/{counts['protocols']} protocols, "
                 f"{counts['tables']} tables, "
                 f"{counts['on_page_not_extracted']} on-page-not-extracted, "
                 f"{counts['extracted_not_on_page']} extracted-not-on-page")
    return "\n".join(lines)


class RowAuditStep(PipelineStepBase):
    """Collection-level row-completeness audit; writes row_audit.json."""

    step_name = "row_audit"

    def execute(self, data: dict) -> dict:
        source = data.get("source", {})
        collection = source.get("collection")
        if not collection:
            self._log_error("Missing collection in source")
            return {"output_file": None}
        report = audit_collection(collection, source.get("protocols"))
        output_file = config.get_collection_path(collection) / "row_audit.json"
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        self._analytics.increment("row_audit_findings",
                                  report["counts"]["on_page_not_extracted"])
        return {"output_file": str(output_file), "counts": report["counts"],
                "status": "success"}


def main():
    parser = argparse.ArgumentParser(
        description="Audit extracted activity rows against the rows the source pages print.")
    parser.add_argument("--collection", default=config.DEFAULT_COLLECTION)
    parser.add_argument("--protocol", action="append", dest="protocols",
                        help="Audit one protocol (repeatable); default is the whole collection.")
    parser.add_argument("--json", dest="json_out",
                        help="Write the report here instead of the collection root.")
    args = parser.parse_args()
    report = audit_collection(args.collection, args.protocols)
    output_file = (Path(args.json_out) if args.json_out
                   else config.get_collection_path(args.collection) / "row_audit.json")
    output_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(format_summary(report))
    print(f"Wrote {output_file}")


if __name__ == "__main__":
    main()
