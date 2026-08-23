"""
Shared navigation for the generated HTML pages.

Every page below a collection carries the same two-line navigation block:

    breadcrumb  Collections › {collection} › {protocol} › {page label}
    siblings    extraction data: T1 T2 · resolved: T1 T2 · consolidated · review · extraction log

The breadcrumb links every ancestor: "Collections" is the repository root
index, the collection name is the collection index, and the protocol name
links to the protocol's own row on the collection index (the rows carry
id="{protocol_id}" anchors, highlighted via tr:target). The sibling strip
is discovered from the protocol folder on disk, so a page never links to
an artifact that does not exist; the current page is shown unlinked.

Directory layout the relative paths rely on (see config):

    <root>/index.html
    <root>/collections/{collection}/protocols/index.html
    <root>/collections/{collection}/protocols/{pid}/SoA2USDM/{extracted,resolved,consolidated}/...

`depth` is the number of directories the page sits below the collection
index (protocols/). Pages in extracted/, resolved/ and consolidated/ have
depth 3; a markdown report rendered at the protocol root has depth 1.

One skin, one markup. Generators embed NAV_CSS as-is; the review page
restyles the same classes to match its full-bleed bar layout (markup and
class names stay shared — only container cosmetics differ).
"""

import html as html_lib
import re
from pathlib import Path

from . import config

# Default skin: a boxed white bar matching the visualize/index pages.
NAV_CSS = """
    .pnav { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
            padding: 8px 16px; margin-bottom: 14px; font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #666; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    .pnav a { color: #1F4788; text-decoration: none; }
    .pnav a:hover { text-decoration: underline; }
    .pnav-sep { color: #999; margin: 0 4px; }
    .pnav-cur { font-weight: 600; color: #333; }
    .pnav-sib { margin-top: 4px; }
    .pnav-grp { color: #888; font-size: 11px; }
"""


def _esc(text) -> str:
    return html_lib.escape(str(text)) if text else ""


def _table_num(name: str):
    """Table number from a per-table artifact filename (Table_02 -> 2)."""
    m = re.search(r"Table_(\d+)", name)
    return int(m.group(1)) if m else None


def page_title(protocol_id: str, page_label: str, collection: str) -> str:
    """Uniform <title>: most specific first, so tabs and history scan well."""
    return f"{protocol_id} · {page_label} · {collection}"


def discover_siblings(protocol_id: str, collection: str) -> dict:
    """What exists for this protocol, as hrefs relative to the protocol root.

    extraction: [(n, href)] JSON viewers (from the *_extraction.json files —
    the viewer HTML is regenerated with the index, in the same batch).
    resolved: [(n, href)] per-table resolved pages. consolidated / review /
    log: href or None. The log href is emitted when the uncertainty report
    exists as .md or already-rendered .html (the .html is rendered with the
    index, same batch).
    """
    soa = config.get_protocol_path(protocol_id, collection) / "SoA2USDM"
    ext_dir, res_dir, cons_dir = soa / "extracted", soa / "resolved", soa / "consolidated"

    extraction = []
    for f in sorted(ext_dir.glob("*_extraction.json")) if ext_dir.is_dir() else []:
        n = _table_num(f.name)
        if n is not None:
            extraction.append((n, f"SoA2USDM/extracted/{f.stem}_viewer.html"))

    resolved = []
    for f in sorted(res_dir.glob("*_resolved.html")) if res_dir.is_dir() else []:
        n = _table_num(f.name)
        if n is not None:
            resolved.append((n, f"SoA2USDM/resolved/{f.name}"))

    cons = cons_dir / f"{protocol_id}_consolidated.html"
    review = ext_dir / f"{protocol_id}_review.html"
    log_html = ext_dir / f"{protocol_id}_uncertainty_report.html"
    log_md = ext_dir / f"{protocol_id}_uncertainty_report.md"

    return {
        "extraction": extraction,
        "resolved": resolved,
        "consolidated": f"SoA2USDM/consolidated/{cons.name}" if cons.exists() else None,
        "review": f"SoA2USDM/extracted/{review.name}" if review.exists() else None,
        "log": f"SoA2USDM/extracted/{log_html.name}"
               if (log_html.exists() or log_md.exists()) else None,
    }


def nav_block(collection: str, protocol_id: str, page_label: str, depth: int,
              current: tuple = (None, None)) -> str:
    """Breadcrumb + sibling strip for a per-protocol page.

    current = (kind, table_num): kind in {'extraction', 'resolved',
    'consolidated', 'review', 'log'} marks that strip entry as the current
    page (rendered unlinked); table_num applies to the per-table kinds.
    """
    coll_index = "../" * depth + "index.html"
    root_index = "../" * (depth + 3) + "index.html"
    to_protocol = "../" * (depth - 1)
    pid = _esc(protocol_id)
    sep = '<span class="pnav-sep">›</span>'

    crumb = (f'<a href="{root_index}">Collections</a>{sep}'
             f'<a href="{coll_index}">{_esc(collection)}</a>{sep}'
             f'<a href="{coll_index}#{pid}" title="This protocol\'s row on the collection index">{pid}</a>{sep}'
             f'<span class="pnav-cur">{_esc(page_label)}</span>')

    sib = discover_siblings(protocol_id, collection)
    kind, cur_n = current
    dot = '<span class="pnav-sep">·</span>'

    def link(href, label, is_cur):
        if is_cur:
            return f'<span class="pnav-cur">{label}</span>'
        return f'<a href="{to_protocol}{href}">{label}</a>'

    groups = []
    if sib["extraction"]:
        items = " ".join(link(h, f"T{n}", kind == "extraction" and n == cur_n)
                         for n, h in sib["extraction"])
        groups.append(f'<span class="pnav-grp">extraction data:</span> {items}')
    if sib["resolved"]:
        items = " ".join(link(h, f"T{n}", kind == "resolved" and n == cur_n)
                         for n, h in sib["resolved"])
        groups.append(f'<span class="pnav-grp">resolved:</span> {items}')
    if sib["consolidated"]:
        groups.append(link(sib["consolidated"], "consolidated", kind == "consolidated"))
    if sib["review"] or kind == "review":
        groups.append(link(sib["review"] or "", "review", kind == "review"))
    if sib["log"]:
        groups.append(link(sib["log"], "extraction log", kind == "log"))

    strip = f'<div class="pnav-sib">{f" {dot} ".join(groups)}</div>' if groups else ""
    return (f'<nav class="pnav" aria-label="Breadcrumb">'
            f'<div class="pnav-crumb">{crumb}</div>{strip}</nav>')
