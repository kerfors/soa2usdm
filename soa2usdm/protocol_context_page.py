"""
Per-protocol page for the protocol context, either profile: soa2usdm-protocol-context-cgt (cell and
gene therapy) or soa2usdm-protocol-context-general (schema_name tells which).

Renders SoA2USDM/context/{pid}_protocol_context.json as
SoA2USDM/context/{pid}_protocol_context.html, with the shared navigation block (soa2usdm.nav).
One section per category; every value shows the protocol's wording, "not stated" where the
extraction recorded null, and its evidence (page + verbatim quote). Entries read from page
images are marked. Nothing is interpreted here: the page shows what the JSON holds.

Regenerated with the collection index (index_generator.discover_protocol_outputs), so the
navigation strip stays in step with the protocol's other pages. Standalone:

  python -m soa2usdm.protocol_context_page --collection cell_gene_therapy --protocol NCT03489291
"""

import argparse
import html as html_lib
import json
from pathlib import Path

from . import config
from .nav import NAV_CSS, nav_block, page_title

PAGE_LABEL = "protocol context"

# (key, heading, fields shown as columns — in schema order, evidence last)
CGT_SECTIONS = [
    ("product", "Product", ["name", "other_names", "type", "vector_or_capsid", "transgene", "manufacturing_or_source"]),
    ("immunogenicity", "Immunogenicity", ["measure", "target", "specimen", "method", "units", "purpose", "timing", "lab"]),
    ("panels", "Lab panels", ["panel_name", "analytes", "specimen", "lab"]),
    ("endpoint_assays", "Endpoint assays", ["topic", "what", "matrix", "method", "units", "endpoint_text"]),
    ("genetic_testing", "Genetic testing", ["what", "gene_variant_or_hla", "purpose", "method", "specimen"]),
    ("lab_and_purpose", "Lab and purpose per SoA activity", ["soa_activity", "lab", "purpose", "specimen", "method"]),
    ("cross_references", "SoA cross-references", ["soa_note", "target_as_printed", "target_found", "target_heading", "target_page", "what_it_says"]),
]
GENERAL_SECTIONS = [
    ("panels", "Lab panels", ["panel_name", "analytes", "specimen", "lab"]),
    ("instruments", "Instruments", ["name", "kind", "abbreviation", "version", "type", "respondent_or_rater", "recall_period", "mode",
                                    "scoring_or_range", "purpose", "soa_activities"]),
    ("measurements", "Measurements", ["name", "components", "position_or_condition", "method", "units", "soa_activities"]),
    ("lab_and_purpose", "Lab and purpose per SoA activity", ["soa_activity", "lab", "purpose", "specimen", "method"]),
    ("cross_references", "SoA cross-references", ["soa_note", "target_as_printed", "target_found", "target_heading", "target_page", "what_it_says"]),
]
# Profile (schema_name) -> its sections
PROFILES = {"soa2usdm-protocol-context-cgt": CGT_SECTIONS, "soa2usdm-protocol-context-general": GENERAL_SECTIONS}


def esc(v) -> str:
    return html_lib.escape(str(v).translate(config.SYMBOL_FONT))


def context_paths(protocol_id: str, collection: str) -> tuple:
    cdir = config.get_soa2usdm_folder(protocol_id, collection) / "context"
    return cdir / f"{protocol_id}_protocol_context.json", cdir / f"{protocol_id}_protocol_context.html"


def _value(v) -> str:
    if v is None:
        return '<span class="ns">not stated</span>'
    if isinstance(v, bool):
        return "yes" if v else '<span class="no">no</span>'
    if isinstance(v, list):
        if not v:
            return '<span class="ns">none</span>'
        return '<ul class="vl">' + "".join(f"<li>{esc(x)}</li>" for x in v) + "</ul>"
    return esc(v)


def _evidence(ev: list) -> str:
    if not ev:
        return '<span class="ns">none</span>'
    out = []
    for e in ev:
        img = ' <span class="img" title="read from the page image; not text-checked">page image</span>' \
            if e.get("read_from") == "page image" else ""
        out.append(f'<div class="ev"><span class="pg">p.&nbsp;{esc(e["page"])}</span>{img} '
                   f'<q>{esc(e["quote"])}</q></div>')
    return "".join(out)


def _section(key: str, heading: str, fields: list, items: list) -> str:
    head = "".join(f"<th>{esc(f.replace('_', ' '))}</th>" for f in fields) + "<th>evidence</th>"
    if not items:
        body = f'<tr><td colspan="{len(fields) + 1}" class="ns">none recorded (see notes)</td></tr>'
    else:
        body = "".join("<tr>" + "".join(f"<td>{_value(it.get(f))}</td>" for f in fields)
                       + f'<td class="evc">{_evidence(it.get("evidence", []))}</td></tr>' for it in items)
    return (f'<section id="{key}"><h2>{esc(heading)} <span class="n">{len(items)}</span></h2>'
            f'<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>')


def _abbreviations(items: list) -> str:
    rows = "".join(
        f'<tr><td class="term">{esc(a["term"])}</td><td>{esc(a["definition"])}</td><td class="pg">p.&nbsp;{esc(a["page"])}'
        + (' <span class="img">page image</span>' if a.get("read_from") == "page image" else "")
        + "</td></tr>" for a in items)
    return (f'<section id="abbreviations"><h2>Abbreviations <span class="n">{len(items)}</span>'
            f'<input id="abq" type="search" placeholder="filter abbreviations" aria-label="filter abbreviations"></h2>'
            f'<div class="tw"><table id="abt"><thead><tr><th>term</th><th>definition</th><th>page</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div></section>")


def render(protocol_id: str, collection: str) -> Path:
    src, out = context_paths(protocol_id, collection)
    d = json.loads(src.read_text(encoding="utf-8"))
    if d.get("schema_name") not in PROFILES:
        raise ValueError(f"{src}: schema_name {d.get('schema_name')!r}, expected one of {sorted(PROFILES)}")
    SECTIONS = PROFILES[d["schema_name"]]
    depth = len(out.relative_to(config.get_collection_path(collection)).parts) - 1
    nav = nav_block(collection, protocol_id, PAGE_LABEL, depth=depth, current=("context", None))
    p = d["provenance"]
    toc = " · ".join([f'<a href="#{k}">{esc(h)}&nbsp;({len(d[k])})</a>' for k, h, _ in SECTIONS]
                     + [f'<a href="#abbreviations">Abbreviations&nbsp;({len(d["abbreviations"])})</a>'])
    sections = "".join(_section(k, h, f, d[k]) for k, h, f in SECTIONS) + _abbreviations(d["abbreviations"])
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title(protocol_id, PAGE_LABEL, collection))}</title>
<style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
           margin: 0; padding: 20px; background: #f8f9fa; color: #333; font-size: 13px; }}
    {NAV_CSS}
    header {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px 18px; margin-bottom: 14px; }}
    h1 {{ font-size: 17px; color: #1F4788; margin: 0 0 4px; }}
    .meta {{ color: #666; font-size: 12px; line-height: 1.6; }}
    .meta code {{ font-size: 11px; }}
    .notes {{ margin-top: 8px; padding: 8px 10px; background: #fff8e1; border-left: 3px solid #f0b400; font-size: 12px; white-space: pre-wrap; }}
    .notes summary {{ cursor: pointer; font-weight: 600; color: #8a6d00; white-space: normal; }}
    .toc {{ margin-top: 8px; font-size: 12px; }}
    .toc a, .raw a {{ color: #1F4788; text-decoration: none; }}
    section {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; }}
    h2 {{ font-size: 14px; color: #1F4788; margin: 0 0 8px; display: flex; align-items: center; gap: 8px; }}
    .n {{ font-size: 11px; color: #fff; background: #1F4788; border-radius: 9px; padding: 1px 7px; font-weight: 500; }}
    .tw {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th {{ text-align: left; font-size: 11px; color: #666; font-weight: 600; border-bottom: 2px solid #e0e0e0; padding: 5px 8px; white-space: nowrap; }}
    td {{ vertical-align: top; border-bottom: 1px solid #eee; padding: 6px 8px; }}
    td.evc {{ min-width: 280px; max-width: 520px; }}
    .ev {{ margin-bottom: 4px; color: #444; }}
    .ev q {{ quotes: "\\201C" "\\201D"; font-style: italic; }}
    .pg {{ color: #1F4788; font-weight: 600; white-space: nowrap; }}
    .ns {{ color: #999; font-style: italic; }}
    .no {{ color: #b3261e; font-weight: 600; }}
    .img {{ font-size: 10px; background: #fde7e9; color: #b3261e; border-radius: 3px; padding: 0 4px; white-space: nowrap; }}
    ul.vl {{ margin: 0; padding-left: 16px; }}
    td.term {{ font-family: Menlo, Consolas, monospace; font-weight: 600; white-space: nowrap; }}
    #abq {{ margin-left: auto; font-size: 12px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; width: 220px; }}
    @media (max-width: 700px) {{ body {{ padding: 10px; }} #abq {{ width: 140px; }} }}
</style>
</head>
<body>
{nav}
<header>
<h1>{esc(protocol_id)} — protocol context</h1>
<div class="meta">{esc(d["document"])} · PDF pages {esc(d["pages_covered"])} ({esc(d["page_numbers"])})<br>
Extracted with prompt {esc(p["prompt_version"])} ({esc(p["model"] or "model not stated")}, {esc(p["extracted_at"] or "date not stated")}) ·
schema <code>{esc(d["schema_name"])} {esc(d["schema_version"])}</code> ·
values are the protocol's wording; <span class="ns">not stated</span> = the protocol does not say ·
<span class="raw"><a href="{esc(src.name)}">raw JSON</a></span></div>
<details class="notes"><summary>Extraction notes — conflicts, what was not found, pages that could not be read</summary>{esc(d["notes"])}</details>
<div class="toc">{toc}</div>
</header>
{sections}
<script>
  const q = document.getElementById('abq'), rows = document.querySelectorAll('#abt tbody tr');
  q.addEventListener('input', () => {{
    const s = q.value.trim().toLowerCase();
    rows.forEach(r => {{ r.style.display = !s || r.textContent.toLowerCase().includes(s) ? '' : 'none'; }});
  }});
</script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="Render the protocol context page for one protocol.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", required=True)
    a = ap.parse_args()
    print(render(a.protocol, a.collection))


if __name__ == "__main__":
    main()
