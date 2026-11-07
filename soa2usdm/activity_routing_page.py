"""
Per-protocol page for the activity routing (soa2usdm-activity-routing).

Renders SoA2USDM/routing/{pid}_activity_routing.json as SoA2USDM/routing/{pid}_activity_routing.html,
with the shared navigation block (soa2usdm.nav). Counts per status; then one row per routed
named test: status, domain or candidates, the question that stays open, each fired rule with
our reading, and each matched phrase in its source (label, parent label, footnote text from
consolidated.json), and the test codes of the label (SDTM_Test_Identity) where the file has them;
then the rows not reached, and the cited SDTMIG v3.4 statements verbatim. Member rows from protocol
context (1.5) show their context panels with pages and the stated specimen and lab.
Each statement text is checked against its text_sha256 before it is shown. Nothing is decided
here: the page shows what the JSON holds.

Regenerated with the collection index (index_generator.discover_protocol_outputs). Standalone:

  python -m soa2usdm.activity_routing_page --collection cell_gene_therapy --protocol NCT03489291
"""

import argparse
import html as html_lib
import json
from pathlib import Path

from . import config
from .activity_routing import PANEL_RULES, RULES, SCHEMA_NAME, STATUSES, sha256_text
from .nav import NAV_CSS, nav_block, page_title

PAGE_LABEL = "activity routing"
DOC_URL = "https://github.com/kerfors/soa2usdm/blob/main/documents/activity-routing.md"
MEMBERS_URL = DOC_URL + "#members-only-material"
WHERE_LABEL = {"label": "activity label", "parent_label": "parent label", "annotation": "footnote",
               "panel_label": "panel label"}
RULE_BY_ID = {r["rule_id"]: r for r in RULES + PANEL_RULES}


def esc(v) -> str:
    return html_lib.escape(str(v).translate(config.SYMBOL_FONT))


def routing_paths(protocol_id: str, collection: str) -> tuple:
    rdir = config.get_soa2usdm_folder(protocol_id, collection) / "routing"
    return rdir / f"{protocol_id}_activity_routing.json", rdir / f"{protocol_id}_activity_routing.html"


def _domains(r: dict) -> str:
    if r["domain"]:
        return f'<b>{esc(r["domain"])}</b>'
    out = " · ".join(esc(d) for d in r["candidates"] or []) or '<span class="ns">—</span>'
    if r["hints"]:
        out += f'<span class="ns sub">hints: {esc(" · ".join(r["hints"]))}</span>'
    if r["fallback"]:
        kinds = " · ".join(r["fallback"]["kinds"]) or "none"
        out += f'<span class="ns sub">from grain kind ({esc(kinds)})</span>'
    return out


def _basis(r: dict, annotations: dict) -> str:
    parts = []
    for b in r["basis"]:
        rule = RULE_BY_ID[b["rule_id"]]
        sts = " · ".join(f'<a href="#st-{esc(s["statement_id"])}">{esc(s["statement_id"])}</a> → {esc("/".join(s["domains"]))}'
                         for s in b["statements"])
        by_source = {}
        for m in b["matched"]:
            by_source.setdefault((m["where"], m["xannot_id"]), []).append(m["phrase"])
        hits = []
        for (where, xannot_id), phrases in by_source.items():
            src = f'<code>{esc(xannot_id)}</code>: {esc(annotations[xannot_id])}' if where == "annotation" else ""
            hits.append(f'<li>{", ".join(f"<b>{esc(ph)}</b>" for ph in phrases)} in {WHERE_LABEL[where]} {src}</li>')
        parts.append(f'<div class="rb"><span class="rid">{esc(b["rule_id"])}</span> {esc(rule["name"])}: {sts}'
                     f'<div class="why">{esc(rule["our_reading"])}</div><ul class="m">{"".join(hits)}</ul></div>')
    for rid, d in r["dropped"].items():
        parts.append(f'<div class="ns">{esc(rid)} set aside by {esc(d["by_rule"])} ({esc(d["statement_id"])})</div>')
    if not parts:
        parts.append('<span class="ns">no rule fired</span>')
    ti = r.get("test_identity")
    if ti:
        codes = " · ".join(f'{esc(c["testcd"])} <span class="ns">{esc(c["code"])}</span> → {esc("/".join(c["domains"]))}'
                           for c in ti["codes"])
        if r["basis"]:
            use = "recorded; the rule ranks above it"
        elif r.get("route_source") == "test identity, weak hit":
            use = "routes the row: one code in one domain, the hit itself is weak"
        elif r.get("route_source") == "test identity":
            use = "routes the row" if r["status"] == "routed" else "candidates: the protocol must say which"
        else:
            use = "hints only"
        reasons = f' ({esc(", ".join(ti["weak_reasons"]))})' if ti["weak_reasons"] else ""
        parts.append(f'<div class="rb"><span class="rid">SDTM_Test_Identity</span> test code of the label: {codes}'
                     f'<div class="why">{esc(ti["hit_strength"])} hit{reasons} on {esc(", ".join(ti["matched_on"]))}: '
                     f'{esc(use)}</div></div>')
    return "".join(parts)


def _members(x: dict) -> str:
    """Members of a split panel (1.3): named-test members link to their rows. Members from protocol
    context (1.5): the linked context panels and the panel names no context panel has come first."""
    if "members" not in x:
        return ""
    head = ""
    if "context_panels" in x:
        head = (f'<div class="ctx">from protocol context: {esc("; ".join(x["context_panels"]))}'
                + (f' <span class="ns">(no context panel: {esc("; ".join(x["names_not_linked"]))})</span>'
                   if x["names_not_linked"] else "") + '</div>')
    ms = "; ".join(f'<a href="#{esc(x["xact_id"])}.{esc(m["member_id"])}">{esc(m["member_id"])} {esc(m["text"])}</a>'
                   if m["member_grain"] == "named test" else
                   f'{esc(m["member_id"])} {esc(m["text"])} <span class="ns">({esc(m["member_grain"] or "no hit")})</span>'
                   for m in x["members"])
    return f'{head}<div class="ctx">{ms}</div>'


def render(protocol_id: str, collection: str) -> Path:
    src, out = routing_paths(protocol_id, collection)
    d = json.loads(src.read_text(encoding="utf-8"))
    if d.get("schema_name") != SCHEMA_NAME:
        raise ValueError(f"{src}: schema_name {d.get('schema_name')!r}, expected {SCHEMA_NAME!r}")
    for sid, s in d["statements"].items():
        if sha256_text(s["text"]) != s["text_sha256"]:
            raise ValueError(f"{src}: statement {sid} text does not match its text_sha256")
    soa = src.parent.parent
    cons = json.loads((soa / "consolidated" / f"{protocol_id}_consolidated.json").read_text(encoding="utf-8"))
    annotations = {a["xannot_id"]: a["annotation_text"] for a in cons["unified_annotations"]}
    depth = len(out.relative_to(config.get_collection_path(collection)).parts) - 1
    nav = nav_block(collection, protocol_id, PAGE_LABEL, depth=depth, current=("routing", None))
    grain_html = f"../grain/{protocol_id}_activity_grain.html"
    pcm_link = (f' · <a href="../panels/{protocol_id}_panel_context_members.json">panel members from protocol context</a>'
                if d["inputs"].get("panel_context_members") else "")
    c = d["counts"]
    cdisc = d["inputs"]["cdisc_for_ai"]
    from_members = c["rows_from_panel_members"]
    from_context = c["rows_from_context_members"]

    def unit_line(label: str, n: int, u: dict, note: str = "") -> str:
        by = ", ".join(t for t in ((f'{u["routed_by_test_identity"]} by test code'
                                    if u["routed_by_test_identity"] else ""),
                                   (f'{u["routed_by_weak_test_identity"]} by weak test code'
                                    if u["routed_by_weak_test_identity"] else "")) if t)
        return (f'<div><b>{label} {n}</b>{note}: '
                + " · ".join(f'{st} {u[st]}' + (f' ({by})' if st == "routed" and by else "") for st in STATUSES)
                + '</div>')

    # 1.7: published figures are always split into standalone rows and panel member rows.
    summary = (unit_line("standalone named tests", c["rows"] - from_members, c["by_unit"]["standalone"])
               + unit_line("panel members", from_members, c["by_unit"]["member"],
                           f' ({from_context} from protocol context)' if from_context else "")
               + f'<div class="ns">not reached {c["not_reached"]}</div>')

    order = {st: i for i, st in enumerate(("open", "weak", "routed", "not routed"))}
    rows = []
    for r in sorted(d["rows"], key=lambda r: order[r["status"]]):
        g = r["grain"]
        kind = esc(g["finding_kind"] or "—") + (f' <span class="ns sub">{esc(" · ".join(g["kind_candidates"]))}</span>'
                                                 if g["kind_candidates"] else "")
        parent = (f'<div class="ctx">under {esc(r["parent_name"])}</div>' if r["parent_name"] else "")
        if "member_id" in r:
            sup = "; ".join(f'{esc(s["rule_id"])} → {esc("/".join(s["domains"]))}' for s in r["panel_label_support"])
            asup = "; ".join(f'{esc(s["rule_id"])} → {esc("/".join(s["domains"]))} '
                             f'({esc(", ".join(sorted({m["xannot_id"] for m in s["matched"]})))})'
                             for s in r.get("panel_annotation_support", []))
            parent = (f'<div class="ctx">member of {esc(r["panel_name"])}'
                      + (f' <span class="ns">(panel label supports {sup})</span>' if sup else "")
                      + (f' <span class="ns">(panel annotations support {asup})</span>' if asup else "")
                      + '</div>' + parent)
            if r.get("members_from") == "protocol context":
                srcs = "; ".join(f'{esc(cs["panel_name"])} p.&nbsp;{esc(", ".join(str(pg) for pg in cs["pages"]))}'
                                 for cs in r["context_sources"])
                csup = "; ".join(f'{esc(s["rule_id"])} → {esc("/".join(s["domains"]))}' for s in r["context_panel_support"])
                facets = "; ".join(f'{esc(f["facet"])} {esc(f["value"])}' for f in r["stated_facets"])
                parent = (f'<div class="ctx">from protocol context: {srcs}'
                          + (f' <span class="ns">(context panel supports {csup})</span>' if csup else "")
                          + (f'<span class="ns sub">as stated: {facets}</span>' if facets else "")
                          + '</div>' + parent)
        rid = r["xact_id"] + (f'.{r["member_id"]}' if "member_id" in r else "")
        q = f'<div class="q">{esc(r["question"])}</div>' if r["question"] else ""
        rows.append(
            f'<tr id="{esc(rid)}" data-s="{esc(r["status"])}" data-u="{"member" if "member_id" in r else "standalone"}">'
            f'<td class="x">{esc(rid)}</td>'
            f'<td class="act"><a href="{grain_html}#{esc(r["xact_id"])}" title="Show on the grain page">{esc(r["activity_name"])}</a>{parent}</td>'
            f'<td class="k">{kind}</td>'
            f'<td><span class="s s-{esc(r["status"].replace(" ", "-"))}">{esc(r["status"])}</span></td>'
            f'<td class="dm">{_domains(r)}</td>'
            f'<td class="evc">{q}{_basis(r, annotations)}</td></tr>')

    nr = "".join(f'<tr><td class="x">{esc(x["xact_id"])}</td><td class="act"><a href="{grain_html}#{esc(x["xact_id"])}">'
                 f'{esc(x["activity_name"])}</a></td><td>{esc(x["reason"])}{_members(x)}</td></tr>' for x in d["not_reached"])
    excl = "; ".join(f'{esc(e["domain"])} ({esc(", ".join(e["statement_ids"]))})' for e in d["fallback_excluded"])
    sts = "".join(f'<div class="st" id="st-{esc(sid)}"><b>{esc(sid)}</b> <span class="ns">[{esc(s["domain"])}] '
                  f'{esc(s["source"])} {esc(s["section"])}, p.&nbsp;{esc(s["page"])}</span>'
                  f'<div>{esc(s["text"])}</div></div>' for sid, s in d["statements"].items())
    options = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in STATUSES)
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
    header, section {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; }}
    h1 {{ font-size: 17px; color: #1F4788; margin: 0 0 4px; }}
    h2 {{ font-size: 14px; color: #1F4788; margin: 0 0 8px; }}
    .meta {{ color: #666; font-size: 12px; line-height: 1.6; }}
    .meta a, .act a, .rb a {{ color: #1F4788; text-decoration: none; }}
    .meta a:hover, .act a:hover {{ text-decoration: underline; }}
    .meta code {{ font-size: 11px; }}
    .sum {{ font-size: 13px; margin: 2px 0 4px; }}
    .tw {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th {{ text-align: left; font-size: 11px; color: #666; font-weight: 600; border-bottom: 2px solid #e0e0e0; padding: 5px 8px; white-space: nowrap; }}
    td {{ vertical-align: top; border-bottom: 1px solid #eee; padding: 6px 8px; }}
    tr:target td, .st:target {{ background: #fff8e1; }}
    td.x {{ font-family: Menlo, Consolas, monospace; font-size: 11.5px; color: #666; white-space: nowrap; }}
    td.act {{ min-width: 220px; }}
    .ctx {{ color: #888; font-size: 11.5px; margin-top: 2px; }}
    td.k, td.dm {{ white-space: nowrap; }}
    td.evc {{ min-width: 320px; max-width: 680px; font-size: 12px; }}
    td.evc code {{ font-size: 11px; color: #1F4788; }}
    .s {{ border-radius: 9px; padding: 1px 8px; white-space: nowrap; }}
    .s-routed {{ background: #e2f4f2; color: #0f6a63; font-weight: 600; }}
    .s-open {{ background: #fff3d6; color: #8a5a00; }}
    .s-weak {{ background: #fff; border: 1px dashed #c58a00; color: #8a5a00; }}
    .s-not-routed {{ background: #fff; border: 1px dashed #999; color: #777; }}
    .sub {{ display: block; font-size: 11px; margin-top: 2px; }}
    .ns {{ color: #999; }}
    .q {{ color: #8a5a00; margin-bottom: 4px; }}
    .rb {{ margin-bottom: 4px; }}
    .rid {{ font-family: Menlo, Consolas, monospace; font-size: 11px; }}
    .why {{ color: #666; }}
    ul.m {{ margin: 2px 0 0; padding-left: 16px; color: #555; }}
    .st {{ margin-bottom: 8px; line-height: 1.45; }}
    .note {{ color: #555; font-size: 12px; margin-top: 6px; }}
    .ctl {{ display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }}
    .ctl input, .ctl select {{ font-size: 12px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }}
    .ctl input {{ flex: 1; min-width: 180px; }}
    #n {{ color: #666; font-size: 12px; align-self: center; margin-left: auto; }}
    @media (max-width: 700px) {{ body {{ padding: 10px; }} }}
</style>
</head>
<body>
{nav}
<header>
<h1>{esc(protocol_id)} — activity routing</h1>
<div class="sum">{summary}</div>
<div class="meta">Rules {esc(d["rules_version"])} · public SDTMIG v3.4 statements and SDTM test codes only · cdisc-for-ai <code>{esc(cdisc["commit"][:7])}</code> ·
<a href="{esc(src.name)}">JSON</a> · <a href="{grain_html}">activity grain</a>{pcm_link} · <a href="{DOC_URL}">how routing is done</a></div>
<div class="note">CDISC members-only material also bears on routing (for example on vector shedding and
replication-competent vectors). It is not used here; <a href="{MEMBERS_URL}">what it is</a>.</div>
</header>
<section>
<div class="ctl"><input id="q" type="search" placeholder="Search activity, rule, statement, phrase…" aria-label="Search">
<select id="sf" aria-label="Status"><option value="">all statuses</option>{options}</select>
<select id="uf" aria-label="Standalone or panel member"><option value="">standalone and members</option><option value="standalone">standalone</option><option value="member">panel members</option></select><span id="n"></span></div>
<div class="tw"><table><thead><tr><th>row</th><th>activity</th><th>grain kind</th><th>status</th><th>domain</th><th>question · basis</th></tr></thead>
<tbody id="tb">{"".join(rows)}</tbody></table></div>
</section>
<section>
<h2>Not reached ({c["not_reached"]})</h2>
<div class="tw"><table><thead><tr><th>row</th><th>activity</th><th>reason</th></tr></thead><tbody>{nr}</tbody></table></div>
</section>
<section>
<h2>Cited statements</h2>
<div class="meta" style="margin-bottom:8px">From cdisc-for-ai SDTMIG_Statements, verbatim. Left out of the fallback: {excl}.</div>
{sts}
</section>
<script>
  const q = document.getElementById('q'), sf = document.getElementById('sf'), uf = document.getElementById('uf'),
        n = document.getElementById('n');
  const rows = [...document.querySelectorAll('#tb tr')];
  function apply() {{
    const s = q.value.trim().toLowerCase(), f = sf.value, u = uf.value; let k = 0;
    rows.forEach(r => {{ const on = (!f || r.dataset.s === f) && (!u || r.dataset.u === u)
                                   && (!s || r.textContent.toLowerCase().includes(s));
                        r.style.display = on ? '' : 'none'; k += on; }});
    n.textContent = k + ' of ' + rows.length + ' named tests';
  }}
  q.addEventListener('input', apply); sf.addEventListener('change', apply); uf.addEventListener('change', apply); apply();
</script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="Render the activity routing page for one protocol.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", required=True)
    a = ap.parse_args()
    print(render(a.protocol, a.collection))


if __name__ == "__main__":
    main()
