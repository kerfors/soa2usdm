"""
Review page — one per protocol: the extraction reviewed against its printed pages.

The page shows nothing that is not already in the pipeline's files. Every
highlight is an existing field drawn where it refers to on the rendered source
page: activity rows on their rule-line bands (page_grid), marks compared cell
by cell with the page text layer, annotations on the rows they were bound to,
review_items as the reviewer's worklist, and consolidation's cross-table folds
as relations between two rows on two pages.

The page writes nothing. A decision drafts a corrections-sidecar entry for the
reviewer to paste into `*_corrections.json`; the sidecar remains the only
write path and the raw extraction stays immutable (see corrections.py).

Inputs (all read, never modified):
    {NCT}_soa.pdf                       page geometry and text layer (page_grid)
    {NCT}_soa_pages/pNN.png + pages.json   pages pre-rendered at ingest by tools/page_map.py --render
    extracted/*_extraction[.verified].json   structure, marks, annotations, review_items
    extracted/*_corrections.json        applied corrections, decided review items
    resolved/*_resolved.json            table ids (for cross-table references)
    consolidated/{NCT}_consolidated.json   unified activities, review_queue
    row_audit.audit_protocol            page assignment, doc-page offset, audit lists
    page_grid                           bands, columns, words

Output: extracted/{NCT}_review.html. Pages are not rendered here: the page
images come pre-rendered (and stamped with their document page number) from
{NCT}_soa_pages/ beside the PDF, referenced relatively. Each image carries a
synthetic caption strip below the verbatim page bitmap; pages.json records the
page fraction so the overlay maps onto the page region only.
"""
import html as html_lib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .base import PipelineStepBase
from .corrections import raw_to_corrections_path, review_status
from .nav import nav_block
from .page_grid import (cell_text, drop_superscripts, join_words, page_grid, page_words,
                        words_in)
from .row_audit import audit_protocol, best_matches, keyed, normalise


# =============================================================================
# Model
# =============================================================================

def _load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _markers(value) -> list[str]:
    """annotation_markers is a comma-separated string in the extraction schema."""
    return [m.strip() for m in (value or "").split(",") if m.strip()]


def _column_map(g, words, props: dict, grid: dict) -> tuple[dict, list, str]:
    """Which extraction column_position each page column carries, read off the header rows.

    A table tiled across pages prints a different run of visits on each page
    (V10-V19 on one, V20-V29 on the next), so page column c is NOT column
    position c+1 in general. The mapping is read from the page: the band whose
    label is a schedule_property name is a header band, and its cell texts are
    matched to that property's schedule_grid values. Returns (header_bands
    {band_index: property_row}, col_map [column_position or None per page
    column], method) where method is 'header' when read from the page or
    'position' when no header row could be read and the page has exactly the
    table's column count (the only case where positional identity is safe).
    """
    header_bands, col_map, method = {}, [None] * len(g.columns), "position"
    if not g.columns:
        return header_bands, col_map, "none"
    by_label = {normalise(p["property_name"]): rp for rp, p in props.items()}
    for i in range(len(g.rows)):
        label = normalise(cell_text(g, words, i, 0))
        if label in by_label:
            header_bands[i] = by_label[label]
    for band_i, prop_row in header_bands.items():
        values = {normalise(v): cp for cp, v in grid.get(prop_row, {}).items() if normalise(v)}
        if not values:
            continue
        mapped = [None]
        for c in range(1, len(g.columns)):
            mapped.append(values.get(normalise(cell_text(g, words, band_i, c))))
        if sum(1 for m in mapped if m is not None) > sum(1 for m in col_map if m is not None):
            col_map, method = mapped, "header"
    if method == "position":
        ncols = len({cp for row in grid.values() for cp in row} | {1})
        if len(g.columns) == ncols:
            col_map = [None] + [c + 1 for c in range(1, len(g.columns))]
        else:
            method = "none"
    return header_bands, col_map, method


def _table_model(extraction: dict, sidecar: Path | None, audit_table: dict, pdf: Path,
                 resolved: dict | None, page_imgs: dict, image_rel: str) -> dict:
    """Everything the page needs for one table: structure, pages with geometry, checks."""
    meta = extraction["table_metadata"]
    redacted = {a["row_position"] for a in (resolved or {}).get("activities", []) if a.get("is_redacted")}
    tnum = meta["table_number"]
    activities = {a["row_position"]: a for a in extraction["activities"]}
    props = {p["row_position"]: p for p in extraction["schedule_properties"]}
    marks: dict[int, set[int]] = {}
    for c in extraction["activity_schedule"]:
        marks.setdefault(c["row_position"], set()).add(c["column_position"])
    grid: dict[int, dict[int, str]] = {}
    for g in extraction["schedule_grid"]:
        grid.setdefault(g["row_position"], {})[g["column_position"]] = g["cell_value"]

    # Column headers for the table pane: the visit-typed property row, then the
    # week-typed one; fall back to the last two header rows when types are absent.
    by_type = {p["property_type"]: rp for rp, p in props.items()}
    visit_row = by_type.get("visit") or max(props, default=None)
    week_row = by_type.get("week")
    visit_hdr = grid.get(visit_row, {}) if visit_row else {}
    week_hdr = grid.get(week_row, {}) if week_row else {}
    data_cols = sorted(set(visit_hdr) | set(week_hdr) | {c for cols in marks.values() for c in cols})

    annotations = []
    for an in extraction["annotations"]:
        rows, prop_rows, other = [], [], []
        for loc in an["marker_locations"]:
            entry = {"row": loc.get("row_position"), "col": loc.get("column_position"),
                     "method": loc.get("method"), "type": loc["location_type"]}
            if loc["location_type"] == "activity_name":
                rows.append(entry)
            elif loc["location_type"] == "schedule_property":
                prop_rows.append(entry)
            else:
                other.append(entry)
        annotations.append({"marker": an["annotation_marker"], "type": an["annotation_type"],
                            "text": an["annotation_text"], "rows": rows, "prop_rows": prop_rows,
                            "other": other})

    offset = audit_table.get("doc_page_offset")
    has_source_page = any("source_page" in a for a in activities.values())
    pages, matched, disagreements, page_mark_total = [], {}, [], 0
    for pdf_page in audit_table["pages"]:
        g = page_grid(pdf, pdf_page)
        words = page_words(pdf, pdf_page)
        labels = drop_superscripts(words)
        entry = page_imgs.get(pdf_page)
        if entry is None:
            raise KeyError(f"pages.json has no entry for PDF page {pdf_page} — "
                           f"re-run tools/page_map.py --render")
        if offset is None:
            # The audit abstained from an offset (a page in the declared range
            # carries no activity bands — e.g. a trailing footnotes-only page —
            # so declared and assigned page counts disagree). Its independent
            # drift check cannot run; pages.json carries the page_map decision,
            # which PAGEMAP.md declares authoritative — use it directly.
            doc_page = entry["doc_page"]
        else:
            doc_page = pdf_page + offset
            if entry["doc_page"] != doc_page:
                raise ValueError(f"PDF page {pdf_page}: pages.json says document page "
                                 f"{entry['doc_page']}, row audit says {doc_page} — the stamped "
                                 f"images and the page map disagree; re-run tools/page_map.py --render")
        cand = [(rp, a["activity_name"]) for rp, a in activities.items()
                if not has_source_page or a.get("source_page") == doc_page]
        name_to_row = {}
        for rp, name in cand:
            name_to_row.setdefault(name, rp)
        keyed_labels = keyed([n for _, n in cand])
        header_bands, col_map, col_method = _column_map(g, words, props, grid)
        bands = []
        for i, (y0, y1) in enumerate(g.rows):
            text = cell_text(g, labels, i, 0) if g.columns else ""
            is_header = i in header_bands
            hits = best_matches(normalise(text), keyed_labels) if text and not is_header else []
            row = None
            for name in hits:
                rp = name_to_row.get(name)
                if rp is not None and rp not in matched:
                    row = rp
                    matched[rp] = (pdf_page, i)
                    break
            # Marks are read from the band rectangle, NOT the merged-cell extent:
            # a dashed rule is missed in the data columns and page_grid then records
            # two rows as one merged cell, which would pull the neighbour's marks in.
            page_marks = []
            for c in range(1, len(g.columns)):
                cx0, cx1 = g.columns[c]
                page_marks.append(1 if "x" in normalise(join_words(words_in(words, cx0, y0, cx1, y1))) else 0)
            band = {"i": i, "y0": round(y0, 1), "y1": round(y1, 1), "text": text,
                    "kind": "header" if is_header else "activity", "row": row,
                    "status": ("matched" if row is not None else "header" if is_header
                               else "blank" if not text.strip() and not any(page_marks) else "unmatched")}
            if not is_header:
                page_mark_total += sum(page_marks)
            if row is not None and col_method != "none":
                # Compare only the columns this page carries and the mapping could read.
                on_page = {col_map[c]: v for c, v in zip(range(1, len(g.columns)), page_marks)
                           if col_map[c] is not None}
                page_cols = {cp for cp, v in on_page.items() if v}
                ext_cols = {cp for cp in marks.get(row, set()) if cp in on_page}
                diff = sorted(ext_cols ^ page_cols)
                band["mark_diff"] = [c for c in range(1, len(g.columns)) if col_map[c] in diff]
                for cp in diff:
                    disagreements.append({"page": pdf_page, "row": row, "col": cp,
                                          "extracted": cp in ext_cols, "on_page": cp in page_cols})
            bands.append(band)
        pages.append({"pdf_page": pdf_page, "doc_page": doc_page, "width_pt": g.width_pt,
                      "height_pt": g.height_pt, "columns": [[round(a, 1), round(b, 1)] for a, b in g.columns],
                      "col_map": col_map, "col_method": col_method,
                      "bands": bands, "img": f"{image_rel}/{entry['file']}",
                      "page_frac": round(entry["page_height_px"] / entry["height_px"], 4)})

    applied = []
    if sidecar and sidecar.exists():
        for c in _load(sidecar)["corrections"]:
            applied.append({"id": c["id"], "op": c["op"], "target": c["target"], "reason": c["reason"],
                            "by": c["by"], "at": c["at"], "review_item": c.get("review_item")})

    return {
        "number": tnum, "title": meta["table_title"], "type": meta["table_type"],
        "doc_pages": [meta["page_start"], meta["page_end"]], "sidecar": sidecar.name if sidecar else None,
        "data_cols": data_cols, "visit_hdr": visit_hdr, "week_hdr": week_hdr,
        "props": [{"row": rp, "name": p["property_name"], "type": p["property_type"]}
                  for rp, p in sorted(props.items())],
        "activities": [{"row": rp, "name": a["activity_name"],
                        "indent": a["activity_name_source"].get("indentation_level", 0),
                        "doc_page": a.get("source_page"), "markers": _markers(a.get("annotation_markers")),
                        "marks": sorted(marks.get(rp, set())), "band": list(matched.get(rp, (None, None))),
                        "is_header": bool(a.get("is_section_header")), "is_redacted": rp in redacted,
                        "name_composed": a["activity_name_source"].get("cell_text") != a["activity_name"]}
                       for rp, a in sorted(activities.items())],
        "annotations": annotations,
        "pages": pages,
        "review_items": extraction.get("review_items", []),
        "applied": applied,
        "checks": {
            "on_page_not_extracted": audit_table.get("on_page_not_extracted", []),
            "extracted_not_on_page": [rp for rp in activities if rp not in matched],
            "audit_note": audit_table.get("note"),
            "mark_disagreements": disagreements,
            "marks": len(extraction["activity_schedule"]),
            "page_marks": page_mark_total,
        },
    }


def _across_tables(consolidated: dict | None) -> dict:
    """Cross-table relations consolidation established, as (table, row) pairs."""
    if not consolidated:
        return {"folds": [], "review_queue": [], "stats": {}}
    folds = []
    for ua in consolidated["unified_activities"]:
        refs = ua.get("source_refs", [])
        if len(refs) < 2:
            continue
        folds.append({"xact_id": ua["xact_id"], "name": ua["activity_name"],
                      "status": ua.get("match_status"), "confidence": ua.get("match_confidence"),
                      "variations": ua.get("name_variations", []),
                      "sources": [{"table": r["table_num"], "row": r["row_position"]} for r in refs]})
    return {"folds": folds, "review_queue": consolidated.get("review_queue", []),
            "stats": consolidated["consolidation_metadata"].get("match_stats", {})}


def build_review_model(protocol_id: str, collection: str) -> dict:
    """Model for the page. Page images come pre-rendered from `{NCT}_soa_pages/`
    beside the PDF (tools/page_map.py --render) and are referenced relative to
    the HTML; nothing is rendered here."""
    pdf = config.find_soa_pdf(protocol_id, collection)
    if pdf is None:
        raise FileNotFoundError(f"{protocol_id}: no {protocol_id}_soa.pdf in {collection}")
    extraction_files = config.find_extraction_files(protocol_id, collection)
    if not extraction_files:
        raise FileNotFoundError(f"{protocol_id}: no extraction files in {collection}")
    audit = audit_protocol(protocol_id, collection)
    if audit["status"] != "ok":
        raise RuntimeError(f"{protocol_id}: row audit status {audit['status']!r} — cannot place pages")
    audit_by_table = {t["table_number"]: t for t in audit["tables"]}
    images_dir = pdf.parent / f"{protocol_id}_soa_pages"
    manifest_path = images_dir / "pages.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"{protocol_id}: no {images_dir.name}/pages.json — render the pages first: "
            f"python3 tools/page_map.py --collection {collection} --render")
    page_imgs = {e["pdf_page"]: e for e in _load(manifest_path)["pages"]}
    image_rel = f"../../{images_dir.name}"

    tables = []
    for ef in extraction_files:
        extraction = _load(ef)
        tnum = extraction["table_metadata"]["table_number"]
        raw = ef.with_name(ef.name.replace(".verified.json", ".json"))
        resolved_path = config.get_resolved_dir(protocol_id, collection) / config.extraction_to_resolved_filename(raw.name)
        resolved = _load(resolved_path) if resolved_path.exists() else None
        tables.append(_table_model(extraction, raw_to_corrections_path(raw), audit_by_table[tnum], pdf, resolved,
                                   page_imgs, image_rel))

    status = review_status(config.get_extracted_dir(protocol_id, collection))
    decided = {i["id"]: i["correction_id"] for i in status["items"] if i["decided"]}
    cons_file = config.find_consolidated_file(protocol_id, collection)
    consolidated = _load(cons_file) if cons_file else None

    descriptor = config.load_collection_descriptor(collection)
    return {
        "protocol_id": protocol_id, "collection": collection,
        "collection_title": descriptor.get("title", collection),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pdf": pdf.name, "image_dir": image_rel, "tables": tables, "decided": decided,
        "review_status": {k: status[k] for k in ("total", "open", "decided")},
        "across": _across_tables(consolidated),
    }


# =============================================================================
# HTML
# =============================================================================

def esc(text) -> str:
    return html_lib.escape(str(text), quote=True)


def render_review_html(model: dict) -> str:
    data = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")
    pid = esc(model["protocol_id"])
    n_tables = len(model["tables"])
    pages = sorted({p["doc_page"] for t in model["tables"] for p in t["pages"]})
    page_span = f"{pages[0]}–{pages[-1]}" if pages else "?"
    return (_TEMPLATE
            .replace("__PID__", pid)
            .replace("__NAV__", nav_block(model["collection"], model["protocol_id"],
                                          "Review", depth=3, current=("review", None)))
            .replace("__COLL__", esc(model["collection_title"]))
            .replace("__NTABLES__", f"{n_tables} table{'s' if n_tables != 1 else ''}")
            .replace("__PAGES__", esc(page_span))
            .replace("__GENERATED__", esc(model["generated_at"]))
            .replace("__DATA__", data))


def generate_review_page(protocol_id: str, collection: str) -> Path:
    model = build_review_model(protocol_id, collection)
    out = config.get_extracted_dir(protocol_id, collection) / f"{protocol_id}_review.html"
    out.write_text(render_review_html(model), encoding="utf-8")
    return out


class ReviewPageStep(PipelineStepBase):
    """Per-protocol review page (extraction against its printed pages)."""

    step_name = "review_page"

    def execute(self, data: dict) -> dict:
        source = data.get("source", {})
        protocol_id, collection = source.get("protocol_id"), source.get("collection")
        if not protocol_id or not collection:
            self._log_error("Missing protocol_id or collection in source")
            return {"output_file": None}
        out = generate_review_page(protocol_id, collection)
        self._analytics.increment("review_pages", 1)
        return {"output_file": str(out), "status": "success"}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate the per-protocol review page.")
    parser.add_argument("protocol_id")
    parser.add_argument("--collection", default=config.DEFAULT_COLLECTION)
    args = parser.parse_args()
    print(generate_review_page(args.protocol_id, args.collection))


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>__PID__ · Review · __COLL__</title>
<style>
:root{--blue:#1F4788;--blue2:#2E75B6;--ink:#1f2933;--muted:#5f6b7a;--line:#d9dee5;--bg:#f5f7fa;
 --ok:#2e7d32;--warn:#c77700;--bad:#c62828;--sel:#ffb300;--note:#6a1b9a;--alt:#0277bd;--fold:#00695c}
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header{background:var(--blue);color:#fff;padding:14px 22px}
header h1{margin:0;font-size:20px;font-weight:600}
header .sub{opacity:.85;font-size:13px;margin-top:3px}
.pnav{font-size:12px;padding:8px 22px;background:#fff;border-bottom:1px solid var(--line);color:var(--muted)}
.pnav a{color:var(--blue2);text-decoration:none}.pnav a:hover{text-decoration:underline}
.pnav-cur{font-weight:600;color:var(--ink)}.pnav-sep{color:#9aa4af;margin:0 4px}
.pnav-sib{margin-top:3px}.pnav-grp{font-size:11px;color:#8a94a0}
.tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:14px 22px}
.tile{background:#fff;border:1px solid var(--line);border-radius:6px;padding:10px 12px}
.tile .k{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.tile .v{font-size:22px;font-weight:600;margin:2px 0}
.tile .d{font-size:12px;color:var(--muted)}
.tile.ok .v{color:var(--ok)}.tile.warn .v{color:var(--warn)}.tile.bad .v{color:var(--bad)}
main{display:grid;grid-template-columns:minmax(0,52%) minmax(0,1fr);gap:14px;padding:0 22px 14px;align-items:start}
#right{display:flex;flex-direction:column;gap:14px;min-width:0}
.panel{background:#fff;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.panel h2{font-size:13px;margin:0;padding:9px 12px;border-bottom:1px solid var(--line);background:#fafbfc;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.panel h2 .sp{flex:1}
.tabs button,.layers label{font:inherit;font-size:12px}
.tabs button{border:1px solid var(--line);background:#fff;padding:3px 9px;border-radius:4px;cursor:pointer;color:var(--ink)}
.tabs button.on{background:var(--blue2);color:#fff;border-color:var(--blue2)}
.tabs button.tbl{border-color:var(--blue);color:var(--blue);font-weight:600}
.tabs button.tbl.on{background:var(--blue);color:#fff}
.layers label{margin-left:8px;cursor:pointer;user-select:none}
#pagewrap{position:relative;overflow:auto;height:calc(100vh - 250px);background:#e9ecef;padding:10px}
#pagebox{position:relative;margin:0 auto;box-shadow:0 1px 4px rgba(0,0,0,.25);background:#fff}
#pagebox img{display:block;width:100%;height:auto}
#overlay{position:absolute;inset:0;width:100%;height:100%}
.band{fill:transparent;stroke:transparent;cursor:pointer}
.band:hover{fill:rgba(46,117,182,.12)}
.band.matched{stroke:rgba(46,117,182,.55);stroke-width:.6}
.band.unmatched{fill:rgba(199,119,0,.18);stroke:rgba(199,119,0,.8);stroke-width:.8}
.band.header{stroke:rgba(95,107,122,.5);stroke-width:.5;stroke-dasharray:2 2}
.band.sel{fill:rgba(255,179,0,.28)!important;stroke:var(--sel)!important;stroke-width:1.4!important}
.band.note{fill:rgba(106,27,154,.18)!important;stroke:var(--note)!important;stroke-width:1.2!important}
.band.alt{fill:rgba(2,119,189,.22)!important;stroke:var(--alt)!important;stroke-width:1.4!important;stroke-dasharray:3 2}
.band.fold{fill:rgba(0,105,92,.2)!important;stroke:var(--fold)!important;stroke-width:1.4!important}
.cellbad{fill:rgba(198,40,40,.35);stroke:var(--bad);stroke-width:.6;pointer-events:none}
.hidden{display:none}
#side{display:flex;flex-direction:column;height:44vh}
#side .body{overflow:auto;padding:10px 12px;font-size:13px}
.dec{border:1px solid var(--line);border-radius:6px;padding:9px 10px;margin-bottom:9px;cursor:pointer}
.dec:hover{border-color:var(--blue2)}
.dec.on{border-color:var(--sel);box-shadow:0 0 0 2px rgba(255,179,0,.35)}
.dec.done{opacity:.7;border-style:dashed}
.dec .t{font-weight:600}
.dec .w{font-size:11px;color:var(--muted);margin:2px 0 6px}
.dec .c{margin:4px 0}.dec .c b{color:var(--blue)}.dec .a b{color:var(--alt)}
.dec .btns{margin-top:7px;display:flex;gap:6px;align-items:center}
.dec .btns button{font:inherit;font-size:12px;padding:3px 9px;border-radius:4px;border:1px solid var(--line);background:#fff;cursor:pointer}
.dec .btns button.keep.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.dec .btns button.alt.on{background:var(--alt);color:#fff;border-color:var(--alt)}
.pill{display:inline-block;font-size:10px;padding:0 6px;border-radius:9px;border:1px solid;margin-left:6px;vertical-align:1px}
.pill.high{color:var(--bad);border-color:var(--bad)}.pill.medium{color:var(--warn);border-color:var(--warn)}.pill.low{color:var(--muted);border-color:var(--line)}
.pill.done{color:var(--ok);border-color:var(--ok)}.pill.cons{color:var(--fold);border-color:var(--fold)}
.small{font-size:12px;color:var(--muted)}
ul.plain{padding-left:18px;margin:6px 0}
.notecard{border-left:3px solid var(--note);padding:6px 9px;margin:6px 0;background:#faf7fc;cursor:pointer;border-radius:0 4px 4px 0}
.notecard.on{background:#efe6f5}
.notecard .m{font-weight:600;color:var(--note)}
.notecard .rows{font-size:11px;color:var(--muted)}
.foldcard{border-left:3px solid var(--fold);padding:6px 9px;margin:6px 0;background:#f1f8f7;border-radius:0 4px 4px 0}
.foldcard.on{background:#d9efec}
.foldcard .src{cursor:pointer;color:var(--blue2)}
.foldcard .src:hover{text-decoration:underline}
#tablewrap{overflow:auto;height:calc(56vh - 264px);min-height:220px}
table.soa{border-collapse:collapse;font-size:12px;width:100%;background:#fff}
table.soa th,table.soa td{border:1px solid var(--line);padding:2px 6px;white-space:nowrap}
table.soa thead th{position:sticky;top:0;background:#fafbfc;z-index:2;font-weight:600}
table.soa thead tr:nth-child(2) th{top:24px;font-weight:400;color:var(--muted)}
table.soa td.name{min-width:280px;white-space:normal}
table.soa td.mark{text-align:center;width:26px}
table.soa tr.act{cursor:pointer}
table.soa tr.act:hover td{background:#eef4fb}
table.soa tr.sel td{background:#fff3d6!important}
table.soa tr.note td{background:#f1e7f7!important}
table.soa tr.alt td{background:#e1f2fb!important}
table.soa tr.fold td{background:#d9efec!important}
table.soa tr.hdr td{background:#e9eef5;font-weight:600}
table.soa tr.sect td.name{font-weight:600;background:#f3f5f8}
table.soa td.mark.bad{background:#fde0e0;color:var(--bad);font-weight:600}
.badge{display:inline-block;font-size:10px;padding:0 5px;border-radius:9px;margin-left:5px;vertical-align:1px;border:1px solid}
.badge.nf{color:var(--warn);border-color:var(--warn)}
.badge.cm{color:var(--muted);border-color:var(--line)}
.badge.bad{color:var(--bad);border-color:var(--bad)}
.badge.fold{color:var(--fold);border-color:var(--fold);cursor:pointer}
.badge.red{color:#fff;background:var(--muted);border-color:var(--muted)}
sup.mk{color:var(--note);font-size:9px;cursor:pointer;margin-left:2px}
#draft{width:100%;height:180px;font:11px/1.35 ui-monospace,Menlo,Consolas,monospace;border:1px solid var(--line);border-radius:4px;padding:6px;margin-top:6px}
#reviewer{font:inherit;font-size:12px;padding:3px 6px;border:1px solid var(--line);border-radius:4px;width:100%}
footer{padding:8px 22px 20px;font-size:11px;color:var(--muted)}
</style></head><body>
<header>
 <h1>__PID__ — review of the SoA extraction</h1>
 <div class="sub">__COLL__ · __NTABLES__ · document pages __PAGES__ · generated __GENERATED__</div>
</header>
__NAV__

<div class="tiles" id="tiles"></div>

<main>
 <section class="panel">
  <h2><span class="tabs" id="tabletabs"></span><span class="tabs" id="pagetabs"></span>
   <span class="sp"></span>
   <span class="layers">
    <label><input type="checkbox" id="lyRows" checked> rows</label>
    <label><input type="checkbox" id="lyMarks" checked> mark check</label>
    <label><input type="checkbox" id="lyHdr"> header rows</label>
   </span>
  </h2>
  <div id="pagewrap"><div id="pagebox"><img id="pageimg" alt="source page"><svg id="overlay"></svg></div></div>
 </section>

 <div id="right">
 <aside class="panel" id="side">
  <h2><span class="tabs" id="sidetabs">
   <button class="on" data-t="dec">Decisions (<span id="ndec"></span>)</button>
   <button data-t="notes">Notes (<span id="nnotes"></span>)</button>
   <button data-t="check">Checks</button>
   <button data-t="across">Across tables (<span id="nacross"></span>)</button>
  </span></h2>
  <div class="body">
   <div id="tab-dec"></div>
   <div id="tab-notes" class="hidden"></div>
   <div id="tab-check" class="hidden"></div>
   <div id="tab-across" class="hidden"></div>
  </div>
 </aside>
  <div class="panel" id="tablewrap"><table class="soa" id="soa"></table></div>
 </div>
</main>

<footer>Page images in <code>__PID___soa_pages/</code>, rendered at ingest by <code>tools/page_map.py --render</code>; the caption strip below each page is synthetic, the page bitmap above it is verbatim. Page numbers (p.NN) are document pages — the page's sequence position in the source protocol PDF; printed page footers are unreliable in this corpus and are not used. Generated from the pipeline's own files: page geometry from the rule-line band detector, row matching as in the row audit, marks from the page text layer compared with the extraction, decisions from the extraction's review items, cross-table relations from consolidation. Selecting a row on the page or in the table highlights it in the other. This page writes nothing: a decision only drafts an entry for the protocol's corrections sidecar.</footer>

<script>
const D = __DATA__;
const S = {t:0, page:0, selRow:null, selProp:null, noteRows:[], altRows:[], foldRows:[], choice:{}};
const T = () => D.tables[S.t];
const byRow = () => { const m={}; T().activities.forEach(a=>m[a.row]=a); return m; };
const esc = s => String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const rowLabel = (r, t) => { const tb = t===undefined ? T() : D.tables.find(x=>x.number===t); const a = tb && tb.activities.find(a=>a.row===r); return a ? a.name : ('row '+r); };
const scrollRowIntoView = tr => { const w=document.getElementById('tablewrap'); w.scrollTo({top:Math.max(0,tr.offsetTop-w.clientHeight/2),behavior:'smooth'}); };
const tableIndex = num => D.tables.findIndex(t=>t.number===num);

// ---------- tiles (protocol level)
(function(){
 const acts = D.tables.reduce((n,t)=>n+t.activities.length,0), marks = D.tables.reduce((n,t)=>n+t.checks.marks,0);
 const notes = D.tables.reduce((n,t)=>n+t.annotations.length,0);
 const missed = D.tables.reduce((n,t)=>n+t.checks.on_page_not_extracted.length,0);
 const unplaced = D.tables.reduce((n,t)=>n+t.checks.extracted_not_on_page.length,0);
 const badRows = new Set(); D.tables.forEach(t=>t.checks.mark_disagreements.forEach(d=>badRows.add(t.number+':'+d.row)));
 const badCells = D.tables.reduce((n,t)=>n+t.checks.mark_disagreements.length,0);
 const rs = D.review_status, rq = D.across.review_queue.length;
 document.getElementById('tiles').innerHTML = [
  ['', 'Extracted', `${acts} activities`, `${D.tables.length} table${D.tables.length!==1?'s':''} · ${marks} marks · ${notes} notes`],
  [missed?'bad':'ok', 'Printed rows missed', missed, missed ? 'row bands on the pages with no extracted row' : 'every printed row the checker could read is extracted'],
  [unplaced?'warn':'ok', 'Rows the checker could not place', unplaced, 'extracted rows with no matching page band (section headings, composed names, packed rows)'],
  [badRows.size?'warn':'ok', 'Mark check', badRows.size ? `${badRows.size} row${badRows.size!==1?'s':''}` : 'agrees', badRows.size ? `${badCells} cells differ between page text and extraction — open the row to judge` : 'page text and extraction agree on every mark'],
  [rs.open||rq?'warn':'ok', 'Decisions open', (rs.open+rq), `${rs.decided} of ${rs.total} extraction calls decided · ${rq} consolidation match${rq!==1?'es':''} to review`],
 ].map(([c,k,v,d])=>`<div class="tile ${c}"><div class="k">${k}</div><div class="v">${v}</div><div class="d">${d}</div></div>`).join('');
})();

// ---------- table + page tabs
function buildTabs(){
 const tt=document.getElementById('tabletabs'); tt.innerHTML='';
 D.tables.forEach((t,i)=>{ const b=document.createElement('button'); b.className='tbl'+(i===S.t?' on':''); b.textContent='Table '+t.number; b.title=t.title; b.onclick=()=>showTable(i); tt.appendChild(b); });
 const pt=document.getElementById('pagetabs'); pt.innerHTML='';
 T().pages.forEach((p,i)=>{ const b=document.createElement('button'); b.className=i===S.page?'on':''; b.textContent='p.'+p.doc_page; b.title='document page '+p.doc_page+' — sequence position in the source protocol PDF (printed page footers are not used)'; b.onclick=()=>showPage(i); pt.appendChild(b); });
}
function showTable(i){ S.t=i; S.page=0; S.selRow=null; S.selProp=null; S.noteRows=[]; S.altRows=[]; S.foldRows=[]; buildTabs(); buildTable(); buildDecisions(); buildNotes(); buildChecks(); showPage(0); }

function showPage(i){
 S.page=i; const p=T().pages[i]; if(!p) return;
 [...document.getElementById('pagetabs').children].forEach((b,j)=>b.classList.toggle('on',j===i));
 document.getElementById('pageimg').src=p.img;
 const svg=document.getElementById('overlay');
 // The image carries a caption strip below the page bitmap; the overlay must map onto the page region only.
 svg.style.height=(p.page_frac*100)+'%';
 svg.setAttribute('viewBox',`0 0 ${p.width_pt} ${p.height_pt}`); svg.setAttribute('preserveAspectRatio','none');
 if(!p.columns.length){ svg.innerHTML=''; return; }
 const x0=p.columns[0][0], x1=p.columns[p.columns.length-1][1];
 const showRows=document.getElementById('lyRows').checked, showMarks=document.getElementById('lyMarks').checked, showHdr=document.getElementById('lyHdr').checked;
 let h='';
 p.bands.forEach(b=>{
  const cls=['band', b.kind==='header'?'header':(b.status==='matched'?'matched':(b.status==='unmatched'?'unmatched':'blank'))];
  const hl = b.row!==null && (b.row===S.selRow||S.noteRows.includes(b.row)||S.altRows.includes(b.row)||S.foldRows.includes(b.row));
  if(b.row!==null && b.row===S.selRow) cls.push('sel');
  if(b.row!==null && S.foldRows.includes(b.row)) cls.push('fold');
  if(b.row!==null && S.noteRows.includes(b.row)) cls.push('note');
  if(b.row!==null && S.altRows.includes(b.row)) cls.push('alt');
  if(b.kind==='header' && S.selProp===b.i+1) cls.push('sel');
  const hide = (!showRows && !hl && !(b.kind==='header'&&S.selProp===b.i+1)) || (b.kind==='header' && !showHdr && S.selProp!==b.i+1);
  h+=`<rect class="${cls.join(' ')}" data-i="${b.i}" x="${x0}" y="${b.y0}" width="${x1-x0}" height="${b.y1-b.y0}"${hide?' style="stroke:transparent;fill:transparent"':''}><title>${esc(b.text||'(no label text)')}${b.row!==null?' → '+esc(rowLabel(b.row)):(b.status==='unmatched'?' — not matched to an extracted row':'')}</title></rect>`;
  if(showMarks && b.mark_diff && b.mark_diff.length) b.mark_diff.forEach(c=>{ const col=p.columns[c-1]; if(col) h+=`<rect class="cellbad" x="${col[0]}" y="${b.y0}" width="${col[1]-col[0]}" height="${b.y1-b.y0}"/>`; });
 });
 svg.innerHTML=h;
 svg.querySelectorAll('.band').forEach(r=>r.onclick=()=>{ const b=p.bands[+r.dataset.i]; if(b.row!==null) selectRow(b.row,true); else if(b.kind==='header') selectProp(b.i+1); });
}
['lyRows','lyMarks','lyHdr'].forEach(id=>document.getElementById(id).onchange=()=>showPage(S.page));

function clearHighlights(){ document.querySelectorAll('#soa tr.sel,#soa tr.note,#soa tr.alt,#soa tr.fold').forEach(t=>t.classList.remove('sel','note','alt','fold')); }
function selectRow(r, fromPage){
 S.selRow=r; S.selProp=null;
 const a=byRow()[r];
 if(a && a.band[0]!==null){ const pi=T().pages.findIndex(p=>p.pdf_page===a.band[0]); showPage(pi>=0?pi:S.page); if(!fromPage) scrollToBand(a.band[1]); } else showPage(S.page);
 document.querySelectorAll('#soa tr.sel').forEach(t=>t.classList.remove('sel'));
 const tr=document.querySelector(`#soa tr[data-row="${r}"]`); if(tr){ tr.classList.add('sel'); if(fromPage) scrollRowIntoView(tr); }
}
function selectProp(pr){ S.selProp=pr; S.selRow=null; showPage(S.page); document.querySelectorAll('#soa tr.sel').forEach(t=>t.classList.remove('sel')); const tr=document.querySelector(`#soa tr[data-prop="${pr}"]`); if(tr) tr.classList.add('sel'); }
function scrollToBand(i){ const p=T().pages[S.page], b=p.bands[i]; if(!b) return; const wrap=document.getElementById('pagewrap'), img=document.getElementById('pageimg'); const y=(b.y0/p.height_pt)*img.clientHeight; wrap.scrollTo({top:Math.max(0,y-wrap.clientHeight/2+10),behavior:'smooth'}); }
function gotoRow(tableNum, row, cls){
 const ti=tableIndex(tableNum); if(ti<0) return;
 if(ti!==S.t) showTable(ti);
 S.foldRows=cls==='fold'?[row]:[]; selectRow(row,false);
 const tr=document.querySelector(`#soa tr[data-row="${row}"]`); if(tr){ scrollRowIntoView(tr); if(cls) tr.classList.add(cls); }
 showPage(S.page);
}

// ---------- table pane
function buildTable(){
 const t=T(), el=document.getElementById('soa'), cols=t.data_cols;
 const foldsByRow={}; D.across.folds.forEach(f=>f.sources.forEach(s=>{ if(s.table===t.number) (foldsByRow[s.row]=foldsByRow[s.row]||[]).push(f); }));
 const badByRow={}; t.checks.mark_disagreements.forEach(d=>{(badByRow[d.row]=badByRow[d.row]||[]).push(d.col)});
 let h='<thead><tr><th>Activity</th>'+cols.map(c=>`<th>${esc(t.visit_hdr[c]||'')}</th>`).join('')+'</tr>';
 h+='<tr><th class="small">'+(t.week_hdr && Object.keys(t.week_hdr).length?'week':'')+'</th>'+cols.map(c=>`<th>${esc(t.week_hdr[c]||'')}</th>`).join('')+'</tr></thead><tbody>';
 t.props.forEach(p=>{ h+=`<tr class="hdr" data-prop="${p.row}"><td class="name">${esc(p.name)} <span class="badge cm">header · ${esc(p.type)}</span></td><td colspan="${cols.length}" class="small">header row ${p.row}</td></tr>`; });
 t.activities.forEach(a=>{
  const marks=new Set(a.marks), bad=new Set(badByRow[a.row]||[]);
  const badges=[];
  if(a.is_redacted) badges.push('<span class="badge red" title="activity name redacted in the public protocol">redacted</span>');
  if(a.band[0]===null) badges.push('<span class="badge nf" title="the page checker could not find this row in any rule-line band">not placed on page</span>');
  if(a.name_composed) badges.push('<span class="badge cm" title="the name was composed from more than one printed cell">composed name</span>');
  if(bad.size) badges.push(`<span class="badge bad">${bad.size} marks differ</span>`);
  (foldsByRow[a.row]||[]).forEach(f=>{ const others=f.sources.filter(s=>!(s.table===t.number&&s.row===a.row)); badges.push(`<span class="badge fold" data-x="${f.xact_id}" title="${esc(f.status)} — same activity as: ${esc(others.map(o=>'Table '+o.table+' row '+o.row).join(', '))}">${f.status==='exact'?'also in':'matched to'} ${others.map(o=>'T'+o.table).join(' ')}</span>`); });
  const sups=a.markers.map(m=>`<sup class="mk" data-m="${esc(m)}" title="note ${esc(m)}">${esc(m)}</sup>`).join('');
  h+=`<tr class="act${a.is_header?' sect':''}" data-row="${a.row}"><td class="name" style="padding-left:${a.indent*18+4}px">${esc(a.name)}${sups}${badges.join('')}${a.doc_page?`<span class="small" style="float:right">p.${a.doc_page}</span>`:''}</td>`;
  cols.forEach(c=>{ h+=`<td class="mark${bad.has(c)?' bad':''}">${marks.has(c)?'✕':''}</td>`; });
  h+='</tr>';
 });
 el.innerHTML=h+'</tbody>';
 el.querySelectorAll('tr.act').forEach(tr=>tr.onclick=e=>{ if(e.target.classList.contains('mk')||e.target.classList.contains('fold')) return; S.noteRows=[];S.altRows=[];S.foldRows=[]; clearHighlights(); selectRow(+tr.dataset.row,false); });
 el.querySelectorAll('tr.hdr').forEach(tr=>tr.onclick=()=>selectProp(+tr.dataset.prop));
 el.querySelectorAll('sup.mk').forEach(s=>s.onclick=e=>{e.stopPropagation(); showNote(s.dataset.m); switchTab('notes');});
 el.querySelectorAll('.badge.fold').forEach(b=>b.onclick=e=>{e.stopPropagation(); showFold(b.dataset.x); switchTab('across');});
}

// ---------- side tabs
function switchTab(n){ document.querySelectorAll('#sidetabs button').forEach(b=>b.classList.toggle('on',b.dataset.t===n)); ['dec','notes','check','across'].forEach(k=>document.getElementById('tab-'+k).classList.toggle('hidden',k!==n)); }
document.querySelectorAll('#sidetabs button').forEach(b=>b.onclick=()=>switchTab(b.dataset.t));

// ---------- decisions (review_items of the current table + consolidation's review_queue)
function buildDecisions(){
 const t=T(), el=document.getElementById('tab-dec');
 const items=t.review_items, rq=D.across.review_queue;
 document.getElementById('ndec').textContent = D.review_status.open + rq.length;
 let h='';
 if(!items.length && !t.applied.length) h+=`<p class="small">This table carries no review items${D.review_status.total?'':' — the extraction predates the field (prompt v3.8.0), so its open calls, if any, are only in the extraction log'}.</p>`;
 else h+='<p class="small">Calls the extractor made that could reasonably go the other way. Click one to see it on the page (call in purple, alternative rows in blue where the call names them). Choosing drafts a sidecar entry below; nothing is saved from here.</p>';
 items.forEach(d=>{
  const done=D.decided[d.id];
  const where=[`document page ${d.location.page}`, d.location.row_position?`row ${d.location.row_position}`:'', d.location.row_positions?`rows ${d.location.row_positions.join(', ')}`:'', d.location.annotation_marker?`note ${d.location.annotation_marker}`:''].filter(Boolean).join(' · ');
  h+=`<div class="dec${done?' done':''}" data-id="${d.id}"><div class="t">${d.id} <span class="pill ${d.severity}">${d.severity}</span>${done?`<span class="pill done">decided · ${esc(done)}</span>`:''}</div><div class="w">${esc(where)} · report §${esc(d.report_section)}</div>
   <div class="c"><b>Call made:</b> ${esc(d.call_made)}</div><div class="c a"><b>Alternative:</b> ${esc(d.alternative)}</div>
   ${done?'':`<div class="btns"><button class="keep" data-id="${d.id}" data-c="keep">keep the call</button><button class="alt" data-id="${d.id}" data-c="alt">take the alternative</button></div>`}</div>`;
 });
 rq.forEach((q,i)=>{
  h+=`<div class="dec" data-q="${i}"><div class="t">Consolidation match <span class="pill cons">from consolidation</span></div><div class="w">${esc(q.xact_id)} · similarity ${Number(q.confidence).toFixed(2)}</div>
   <div class="c"><b>Call made:</b> "${esc(q.new_name)}" was treated as the same activity as "${esc(q.existing_name)}".</div><div class="c a"><b>Alternative:</b> keep them as two activities.</div>
   <div class="small">Consolidation has no sidecar yet — record this in the protocol's review notes for now.</div></div>`;
 });
 if(t.applied.length) h+=`<h3 style="font-size:13px;margin:14px 0 4px">Corrections applied to this table (${t.applied.length})</h3><ul class="plain small">${t.applied.map(a=>`<li><b>${esc(a.id)}</b> ${esc(a.op)} ${esc(a.target)}${a.review_item?` → ${esc(a.review_item)}`:''} — ${esc(a.reason)} <i>(${esc(a.by)}, ${esc(a.at.slice(0,10))})</i></li>`).join('')}</ul>`;
 h+=`<h3 style="font-size:13px;margin:14px 0 4px">Draft for <code>${esc(t.sidecar||'the corrections sidecar')}</code></h3><input id="reviewer" placeholder="your name, as it should appear in the sidecar" value="${esc(S.reviewer||'')}"><textarea id="draft" readonly placeholder="Choose 'keep the call' or 'take the alternative' above to draft sidecar entries here. 'Keep' drafts a complete confirm entry; 'alternative' drafts the entry skeleton with the review item and its location filled in."></textarea>`;
 el.innerHTML=h;
 el.querySelectorAll('.dec[data-id]').forEach(c=>c.onclick=e=>{ if(e.target.tagName==='BUTTON') return; showDecision(c.dataset.id); });
 el.querySelectorAll('.dec[data-q]').forEach(c=>c.onclick=()=>showQueue(+c.dataset.q));
 el.querySelectorAll('.btns button').forEach(b=>b.onclick=()=>{ S.choice[b.dataset.id]=b.dataset.c; el.querySelectorAll(`.btns button[data-id="${b.dataset.id}"]`).forEach(x=>x.classList.toggle('on',x===b)); showDecision(b.dataset.id); renderDraft(); });
 document.getElementById('reviewer').oninput=e=>{ S.reviewer=e.target.value; renderDraft(); };
 renderDraft();
}
function showDecision(id){
 const t=T(), d=t.review_items.find(x=>x.id===id); if(!d) return;
 document.querySelectorAll('.dec').forEach(c=>c.classList.toggle('on',c.dataset.id===id));
 const rows=d.location.row_positions||(d.location.row_position?[d.location.row_position]:[]);
 const m=byRow();
 S.noteRows=rows.filter(r=>m[r]); S.altRows=[]; S.foldRows=[]; S.selRow=null; S.selProp=null;
 clearHighlights();
 S.noteRows.forEach(r=>{ const tr=document.querySelector(`#soa tr[data-row="${r}"]`); if(tr) tr.classList.add('note'); });
 if(!S.noteRows.length && d.location.row_position && t.props.some(p=>p.row===d.location.row_position)){ S.selProp=d.location.row_position; const tr=document.querySelector(`#soa tr[data-prop="${S.selProp}"]`); if(tr) tr.classList.add('sel'); }
 if(!rows.length && d.location.annotation_marker){ const a=t.annotations.find(x=>x.marker===d.location.annotation_marker); if(a){ S.noteRows=a.rows.map(r=>r.row).filter(r=>r!=null); if(a.prop_rows.length) S.selProp=a.prop_rows[0].row; } }
 const first=S.noteRows.map(r=>m[r]).find(a=>a&&a.band[0]!==null);
 const pi = first ? t.pages.findIndex(p=>p.pdf_page===first.band[0]) : t.pages.findIndex(p=>p.doc_page===d.location.page);
 showPage(pi>=0?pi:S.page);
 if(first) scrollToBand(first.band[1]); else document.getElementById('pagewrap').scrollTo({top:0,behavior:'smooth'});
 const tr=document.querySelector('#soa tr.note,#soa tr.sel'); if(tr) scrollRowIntoView(tr);
}
function showQueue(i){
 const q=D.across.review_queue[i]; const f=D.across.folds.find(x=>x.xact_id===q.xact_id);
 document.querySelectorAll('.dec').forEach(c=>c.classList.toggle('on',c.dataset.q==i));
 if(f) showFold(f.xact_id, true);
}
function renderDraft(){
 const t=T(), el=document.getElementById('draft'); if(!el) return;
 const now=new Date().toISOString().slice(0,19)+'Z', by=S.reviewer||'<reviewer>';
 const entries=[]; let n=t.applied.length;
 t.review_items.forEach(d=>{
  const ch=S.choice[d.id]; if(!ch) return; n+=1; const id='corr-'+String(n).padStart(3,'0');
  if(ch==='keep') entries.push({id, target:'annotations', op:'confirm', review_item:d.id, reason:'<why the call stands>', source_ref:{page:d.location.page}, by, at:now});
  else {
   const match={}; if(d.location.annotation_marker) match.annotation_marker=d.location.annotation_marker; else if(d.location.row_position) match.row_position=d.location.row_position;
   entries.push({id, target: d.location.annotation_marker?'annotations':'activities', op:'set', match, set:{'<field>':'<value>'}, review_item:d.id, reason:'<why the alternative is right>', source_ref:{page:d.location.page}, by, at:now});
  }
 });
 el.value = entries.length ? JSON.stringify(entries,null,2) : '';
}

// ---------- notes
function buildNotes(){
 const t=T(), el=document.getElementById('tab-notes');
 document.getElementById('nnotes').textContent=t.annotations.length;
 let h='<p class="small">Footnotes and instruction blocks bound to rows. Click one to see which rows it governs. An asterisk marks a binding the extractor inferred rather than read from a printed marker; "by name" means the note names the row rather than marking it.</p>';
 t.annotations.forEach(a=>{
  const rows=a.rows.map(r=>`${esc(rowLabel(r.row))}${r.method==='text_match'?' (by name)':(r.method&&r.method!=='proximity'?'*':'')}`);
  const props=a.prop_rows.map(r=>`header row ${r.row}*`);
  const other=a.other.map(r=>`${esc(r.type)}${r.row?' row '+r.row:''}${r.col?' col '+r.col:''}`);
  h+=`<div class="notecard" data-m="${esc(a.marker)}"><span class="m">${esc(a.marker)}</span> <span class="small">${esc(a.type)}</span> <span class="rows">→ ${[...rows,...props,...other].join('; ')||'no row'}</span><div>${esc(a.text)}</div></div>`;
 });
 el.innerHTML=h;
 el.querySelectorAll('.notecard').forEach(c=>c.onclick=()=>showNote(c.dataset.m));
}
function showNote(m){
 const t=T(), a=t.annotations.find(x=>x.marker===m); if(!a) return;
 document.querySelectorAll('.notecard').forEach(c=>c.classList.toggle('on',c.dataset.m===m));
 document.querySelectorAll('.dec').forEach(c=>c.classList.remove('on'));
 S.noteRows=a.rows.map(r=>r.row).filter(r=>r!=null); S.altRows=[]; S.foldRows=[]; S.selRow=null; S.selProp=a.prop_rows.length?a.prop_rows[0].row:null;
 clearHighlights();
 S.noteRows.forEach(r=>{const tr=document.querySelector(`#soa tr[data-row="${r}"]`); if(tr) tr.classList.add('note');});
 const bm=byRow(), first=S.noteRows.map(r=>bm[r]).find(x=>x&&x.band[0]!==null);
 if(first){ const pi=t.pages.findIndex(p=>p.pdf_page===first.band[0]); showPage(pi>=0?pi:S.page); scrollToBand(first.band[1]); const tr=document.querySelector(`#soa tr[data-row="${first.row}"]`); if(tr) scrollRowIntoView(tr); } else showPage(S.page);
}

// ---------- checks
function buildChecks(){
 const t=T(), c=t.checks, el=document.getElementById('tab-check'), m=byRow();
 const badByRow={}; c.mark_disagreements.forEach(d=>{(badByRow[d.row]=badByRow[d.row]||[]).push(d)});
 let h=`<p class="small">Independent checks for Table ${t.number}, re-derived from the PDF — not the extractor's own report.</p>`;
 if(c.audit_note) h+=`<p class="small"><b>Row audit note:</b> ${esc(c.audit_note)}</p>`;
 h+=`<h3 style="font-size:13px;margin:8px 0 4px">Printed rows not extracted (${c.on_page_not_extracted.length})</h3>`;
 h+=c.on_page_not_extracted.length? `<ul class="plain">${c.on_page_not_extracted.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>` : '<p class="small">None — every row band with a label the checker could read matches an extracted row.</p>';
 h+=`<h3 style="font-size:13px;margin:12px 0 4px">Extracted rows the checker could not place (${c.extracted_not_on_page.length})</h3><p class="small">Usually section headings printed as full-width shaded bands, names composed from two cells, or tightly packed rows the band detector merged. Click to locate in the table.</p><ul class="plain">${c.extracted_not_on_page.map(r=>`<li><a href="#" data-row="${r}">${esc(rowLabel(r))}</a>${m[r]&&m[r].doc_page?` <span class="small">p.${m[r].doc_page}</span>`:''}</li>`).join('')}</ul>`;
 const nb=Object.keys(badByRow).length;
 h+=`<h3 style="font-size:13px;margin:12px 0 4px">Mark check (${nb} row${nb!==1?'s':''})</h3><p class="small">Every ✕ in the page's text layer, binned into the detected row band and column, compared with the extracted marks. A difference is either an extraction error or a band drawn at the wrong rule — look at the page before deciding.</p>`;
 Object.entries(badByRow).forEach(([r,ds])=>{ h+=`<div><a href="#" data-row="${r}">${esc(rowLabel(+r))}</a>: ${ds.length} cells — ${ds.filter(d=>d.on_page).length} on page only, ${ds.filter(d=>d.extracted).length} extracted only</div>`; });
 if(!nb) h+='<p class="small">No differences.</p>';
 h+=`<p class="small" style="margin-top:12px">${c.marks} extracted marks in this table. Column identity per page: ${t.pages.map(p=>`p.${p.doc_page} ${p.col_method==='header'?'read from the header row':p.col_method==='position'?'by position':'<b>could not be read — marks unchecked</b>'}`).join('; ')}.</p>`;
 el.innerHTML=h;
 el.querySelectorAll('a[data-row]').forEach(a=>a.onclick=e=>{e.preventDefault(); S.noteRows=[];S.altRows=[];S.foldRows=[]; clearHighlights(); selectRow(+a.dataset.row,false); const tr=document.querySelector(`#soa tr[data-row="${a.dataset.row}"]`); if(tr) scrollRowIntoView(tr);});
}

// ---------- across tables (protocol level)
(function(){
 const el=document.getElementById('tab-across'), A=D.across;
 const nonexact=A.folds.filter(f=>f.status!=='exact'), exact=A.folds.filter(f=>f.status==='exact');
 document.getElementById('nacross').textContent=A.folds.length;
 const st=A.stats||{};
 let h=`<p class="small">Rows consolidation treated as the same activity across tables. Exact name matches are collapsed below; anything matched on similarity is listed first. Click a source to see that row on its page.</p>`;
 if(!A.folds.length) h+='<p class="small">Single-table protocol, or no activity appears in more than one table.</p>';
 const card=f=>`<div class="foldcard" data-x="${f.xact_id}"><b>${esc(f.name)}</b> <span class="pill cons">${esc(f.status)}${f.status!=='exact'?' · '+Number(f.confidence).toFixed(2):''}</span>${f.variations.length>1?`<div class="small">printed as: ${f.variations.map(esc).join(' / ')}</div>`:''}<div class="small">${f.sources.map(s=>`<span class="src" data-t="${s.table}" data-r="${s.row}">Table ${s.table} row ${s.row}</span>`).join(' · ')}</div></div>`;
 if(nonexact.length) h+=`<h3 style="font-size:13px;margin:8px 0 4px">Matched on similarity (${nonexact.length})</h3>`+nonexact.map(card).join('');
 if(exact.length) h+=`<details style="margin-top:10px"><summary style="cursor:pointer;font-weight:600;font-size:13px">Same name in more than one table (${exact.length})</summary>${exact.map(card).join('')}</details>`;
 if(Object.keys(st).length) h+=`<p class="small" style="margin-top:12px">Consolidation counts: ${Object.entries(st).map(([k,v])=>`${esc(k)} ${v}`).join(' · ')}.</p>`;
 el.innerHTML=h;
 el.querySelectorAll('.src').forEach(s=>s.onclick=e=>{ e.stopPropagation(); gotoRow(+s.dataset.t,+s.dataset.r,'fold'); });
 el.querySelectorAll('.foldcard').forEach(c=>c.onclick=()=>showFold(c.dataset.x));
})();
function showFold(x, jump){
 const f=D.across.folds.find(y=>y.xact_id===x); if(!f) return;
 document.querySelectorAll('.foldcard').forEach(c=>c.classList.toggle('on',c.dataset.x===x));
 const here=f.sources.filter(s=>s.table===T().number);
 if(here.length && !jump){ S.foldRows=here.map(s=>s.row); S.noteRows=[]; S.altRows=[]; S.selRow=null; clearHighlights(); here.forEach(s=>{const tr=document.querySelector(`#soa tr[data-row="${s.row}"]`); if(tr) tr.classList.add('fold');}); const m=byRow(), a=m[here[0].row]; if(a&&a.band[0]!==null){ const pi=T().pages.findIndex(p=>p.pdf_page===a.band[0]); showPage(pi>=0?pi:S.page); scrollToBand(a.band[1]); } else showPage(S.page); const tr=document.querySelector('#soa tr.fold'); if(tr) scrollRowIntoView(tr); }
 else gotoRow(f.sources[0].table, f.sources[0].row, 'fold');
}

showTable(0);
</script>
</body></html>
"""


if __name__ == "__main__":
    main()
