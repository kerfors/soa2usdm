"""
Per-protocol page for the activity grain (soa2usdm-activity-grain).

Renders SoA2USDM/grain/{pid}_activity_grain.json as SoA2USDM/grain/{pid}_activity_grain.html,
with the shared navigation block (soa2usdm.nav). Counts per grain, kind and role; then one
row per activity, as in the inventory: grain or role, kind of finding, the rule that fired,
and its evidence (lookup hits, words, list members, flags) or the decision with its basis.
A decision's basis is shown resolved: footnote text from consolidated.json, the protocol
context entry it points at. Nothing is decided here: the page shows what the JSON holds.

Regenerated with the collection index (index_generator.discover_protocol_outputs), so the
navigation strip stays in step with the protocol's other pages. Standalone:

  python -m soa2usdm.activity_grain_page --collection cell_gene_therapy --protocol NCT03489291
"""

import argparse
import html as html_lib
import json
from pathlib import Path

from . import config
from .activity_grain import FINDING_KINDS, GRAINS, ROLES, SCHEMA_NAME, resolve_pointer
from .nav import NAV_CSS, nav_block, page_title

PAGE_LABEL = "activity grain"
DOC_URL = "https://github.com/kerfors/soa2usdm/blob/main/documents/activity-grain.md"
CONTEXT_HEAD_KEYS = ("measure", "what", "panel_name", "soa_activity", "name", "term", "soa_note")


def esc(v) -> str:
    return html_lib.escape(str(v).translate(config.SYMBOL_FONT))


def grain_paths(protocol_id: str, collection: str) -> tuple:
    gdir = config.get_soa2usdm_folder(protocol_id, collection) / "grain"
    return gdir / f"{protocol_id}_activity_grain.json", gdir / f"{protocol_id}_activity_grain.html"


def _hit(h: dict) -> str:
    where = h.get("codelist") or h["file"]
    dom = f' · {esc(h["domains"])}' if h.get("domains") else ""
    return (f'<code>{esc(h["submission_value"])}</code> {esc(h["code"])} · {esc(where)} '
            f'{esc(h["field"])} ({esc(h["source"])}){dom}')


def _basis(b: dict, annotations: dict, context: dict | None) -> str:
    t = b["type"]
    if t == "label":
        return "label text"
    if t == "annotation":
        return f'footnote <code>{esc(b["xannot_id"])}</code>: {esc(annotations[b["xannot_id"]])}'
    if t == "context":
        e = resolve_pointer(context, b["pointer"])
        head = next((e[k] for k in CONTEXT_HEAD_KEYS if isinstance(e, dict) and k in e), "")
        pages = sorted({ev["page"] for ev in e.get("evidence", [])}) if isinstance(e, dict) else []
        pg = f' (p.&nbsp;{esc(", ".join(map(str, pages)))})' if pages else ""
        return f'protocol context <code>{esc(b["pointer"])}</code>: {esc(head)}{pg}'
    if t == "cdisc":
        key = {"Domain_Coverage": lambda: b["domain"],
               "Codelist_Phrases": lambda: f'{b["codelist"]} {b["code"]}'}.get(
            b["file"], lambda: f'{b["code"]} {b["testcd"]}')()
        return f'cdisc-for-ai {esc(b["file"])} <code>{esc(key)}</code>'
    return f'protocol p.&nbsp;{esc(b["page"])}'


def _evidence(row: dict, lab: dict | None, annotations: dict, context: dict | None) -> str:
    parts = []
    if row["role"]:
        for h in row.get("specimen_hits", []):
            parts.append(f"<div>{_hit(h)}</div>")
        return "".join(parts) + "".join(f'<div class="flag">{esc(f)}</div>' for f in row["flags"])
    d = lab.get("decision")
    if d:
        who = "reviewed" if d["source"] == "reviewed" else "AI proposal"
        basis = "".join(f"<li>{_basis(b, annotations, context)}</li>" for b in d["basis"])
        parts.append(f'<div class="dec"><b>{who}:</b> {esc(d["rationale"])}<ul class="basis">{basis}</ul></div>')
    if lab["hits"]:
        strength = (f' <span class="st {esc(lab["hit_strength"])}">{esc(lab["hit_strength"])}</span>'
                    if lab["hit_strength"] else "")
        parts.append(f'<div>{_hit(lab["hits"][0])}{strength}</div>')
        if lab["weak_reasons"]:
            parts.append(f'<div class="why">weak: {esc(", ".join(lab["weak_reasons"]))}</div>')
    if lab["kind_domains"]:
        parts.append(f'<div class="why">K1 domains: {esc(", ".join(lab["kind_domains"]))}</div>')
    for rule, words in (lab.get("words") or {}).items():
        parts.append(f'<div class="why">{esc(rule)} words: {esc(", ".join(words))}</div>')
    if lab["members"]:
        ms = "; ".join(f'{esc(m["text"])} → <code>{esc(m["hits"][0]["submission_value"])}</code>'
                       if m.get("hits") else f'{esc(m["text"])} → no hit' for m in lab["members"])
        parts.append(f'<div class="why">members: {ms}</div>')
    if lab["qualifiers"]:
        parts.append(f'<div class="why">qualifier: {esc(" · ".join(lab["qualifiers"]))}</div>')
    flags = row["flags"] + lab["flags"]
    if flags:
        parts.append(f'<div class="flag">{esc("; ".join(flags))}</div>')
    return "".join(parts) or '<span class="ns">—</span>'


def _summary(c: dict) -> str:
    """One line of counts after decisions: named tests with their kinds, then the other grains."""
    kinds = " · ".join(f"{k} {c['by_finding_kind'][k]}" for k in FINDING_KINDS if c["by_finding_kind"].get(k))
    nt = c["by_grain"]["named test"]
    others = " · ".join(f"{g} {c['by_grain'][g]}" for g in GRAINS[1:])
    return f'<b>{nt} named tests</b>{f" ({esc(kinds)})" if kinds else ""} · {esc(others)}'


def render(protocol_id: str, collection: str) -> Path:
    src, out = grain_paths(protocol_id, collection)
    g = json.loads(src.read_text(encoding="utf-8"))
    if g.get("schema_name") != SCHEMA_NAME:
        raise ValueError(f"{src}: schema_name {g.get('schema_name')!r}, expected {SCHEMA_NAME!r}")
    soa = src.parent.parent
    cons = json.loads((soa / "consolidated" / f"{protocol_id}_consolidated.json").read_text(encoding="utf-8"))
    annotations = {a["xannot_id"]: a["annotation_text"] for a in cons["unified_annotations"]}
    ctx_file = soa / "context" / f"{protocol_id}_protocol_context.json"
    context = json.loads(ctx_file.read_text(encoding="utf-8")) if ctx_file.exists() else None
    labels = {l["phrase"]: l for l in g["labels"]}
    depth = len(out.relative_to(config.get_collection_path(collection)).parts) - 1
    nav = nav_block(collection, protocol_id, PAGE_LABEL, depth=depth, current=("grain", None))
    cons_html = f"../consolidated/{protocol_id}_consolidated.html"
    c = g["counts"]
    ins = g["inputs"]
    cdisc = ins["cdisc_for_ai"]
    decisions_name = f"{protocol_id}_activity_grain_decisions.json"
    decided = [l["decision"] for l in g["labels"] if l.get("decision")]
    n_ai = sum(1 for d in decided if d["source"] == "ai_proposed")
    n_rv = len(decided) - n_ai
    how = ("Rules + " + " + ".join(([f"{n_ai} AI decisions (not reviewed)"] if n_ai else [])
                                   + ([f"{n_rv} reviewed decisions"] if n_rv else []))
           if decided else 'Rules only: <i>unsure</i> means not yet resolved')
    decisions_link = f' · <a href="{esc(decisions_name)}">decisions</a>' if ins["decisions"] else ""
    if g["schema_version"] != "1.0" and ins["grain_inputs"]:
        decisions_link += f' · <a href="{esc(protocol_id)}_grain_inputs.json">decision inputs</a>'

    rows = []
    for r in g["activities"]:
        lab = labels.get(r["phrase"])
        if r["role"]:
            grain = f'<span class="role">{esc(r["role"])}</span>'
        else:
            ai = ' <span class="ai" title="Set by an AI proposal, not reviewed">AI</span>' if r["source"] == "ai_proposed" else ""
            rv = ' <span class="rv" title="Set by a review decision">reviewed</span>' if r["source"] == "reviewed" else ""
            rules = (f'<span class="ns sub">rules: {esc(lab["grain"])}</span>'
                     if r["source"] != "rule" and lab["grain"] != r["grain"] else "")
            grain = f'<span class="g g-{esc(r["grain"].replace(" ", "-"))}">{esc(r["grain"])}</span>{ai}{rv}{rules}'
        kind = esc(r["finding_kind"]) if r["finding_kind"] else '<span class="ns">—</span>'
        if r.get("kind_candidates"):
            kind += f' <span class="ns sub">{esc(" · ".join(r["kind_candidates"]))}</span>'
        where = f'<div class="ctx">under {esc(" / ".join(r["context"]))}</div>' if r["context"] else ""
        ind = f' style="padding-left:{r["hierarchy_level"] * 14}px"' if r["hierarchy_level"] else ""
        rows.append(
            f'<tr id="{esc(r["xact_id"])}" data-g="{esc(r["role"] or r["grain"])}" class="{"rrole" if r["role"] else ""}">'
            f'<td class="x">{esc(r["xact_id"])}</td>'
            f'<td class="act"><a href="{cons_html}#{esc(r["xact_id"])}" title="Show in the consolidated view"{ind}>{esc(r["activity_name"])}</a>{where}</td>'
            f'<td>{grain}</td><td class="k">{kind}</td><td class="rule">{esc(r["rule_id"])}</td>'
            f'<td class="evc">{_evidence(r, lab, annotations, context)}</td></tr>')

    options = "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in GRAINS + ROLES)
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
    .meta {{ color: #666; font-size: 12px; line-height: 1.6; }}
    .meta a, .act a {{ color: #1F4788; text-decoration: none; }}
    .meta a:hover, .act a:hover {{ text-decoration: underline; }}
    .meta code {{ font-size: 11px; }}
    .sum {{ font-size: 13px; margin: 2px 0 4px; }}
    .tw {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th {{ text-align: left; font-size: 11px; color: #666; font-weight: 600; border-bottom: 2px solid #e0e0e0; padding: 5px 8px; white-space: nowrap; }}
    td {{ vertical-align: top; border-bottom: 1px solid #eee; padding: 6px 8px; }}
    tr:target td {{ background: #fff8e1; }}
    tr.rrole td {{ color: #888; }}
    td.x, td.rule {{ font-family: Menlo, Consolas, monospace; font-size: 11.5px; color: #666; white-space: nowrap; }}
    td.act {{ min-width: 240px; }}
    .ctx {{ color: #888; font-size: 11.5px; margin-top: 2px; }}
    td.k {{ white-space: nowrap; }}
    td.evc {{ min-width: 300px; max-width: 620px; font-size: 12px; }}
    td.evc code {{ font-size: 11px; color: #1F4788; }}
    .g {{ border-radius: 9px; padding: 1px 8px; background: #eef2f8; white-space: nowrap; }}
    .g-named-test {{ background: #e2f4f2; color: #0f6a63; font-weight: 600; }}
    .g-unsure {{ background: #fff; border: 1px dashed #999; color: #777; }}
    .role {{ font-style: italic; }}
    .ai, .rv {{ font-size: 10px; border-radius: 3px; padding: 0 4px; white-space: nowrap; }}
    .ai {{ color: #8a5a00; background: #fff3d6; }}
    .rv {{ color: #2e7d32; background: #e5f3ea; }}
    .sub {{ display: block; font-size: 11px; margin-top: 2px; }}
    .ns {{ color: #999; }}
    .why {{ color: #666; }}
    .flag {{ color: #b3261e; }}
    .st {{ font-size: 10.5px; border-radius: 8px; padding: 0 6px; }}
    .st.strong {{ color: #2e7d32; background: #e5f3ea; }}
    .st.weak {{ color: #8a5a00; background: #fff3d6; }}
    .dec {{ margin-bottom: 4px; }}
    ul.basis {{ margin: 2px 0 0; padding-left: 16px; color: #666; }}
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
<h1>{esc(protocol_id)} — activity grain</h1>
<div class="sum">{_summary(c)}</div>
<div class="meta">{how} · cdisc-for-ai <code>{esc(cdisc["commit"][:7])}</code> (SDTM CT {esc(cdisc["files"][0]["sdtm_ct"])}) ·
<a href="{esc(src.name)}">JSON</a>{decisions_link} · <a href="{DOC_URL}">how the grain is set</a></div>
</header>
<section>
<div class="ctl"><input id="q" type="search" placeholder="Search activity, rule, code, evidence…" aria-label="Search">
<select id="gf" aria-label="Grain or role"><option value="">all grains and roles</option>{options}</select><span id="n"></span></div>
<div class="tw"><table><thead><tr><th>row</th><th>activity</th><th>grain</th><th>kind</th><th>rule</th><th>evidence</th></tr></thead>
<tbody id="tb">{"".join(rows)}</tbody></table></div>
</section>
<script>
  const q = document.getElementById('q'), gf = document.getElementById('gf'), n = document.getElementById('n');
  const rows = [...document.querySelectorAll('#tb tr')];
  function apply() {{
    const s = q.value.trim().toLowerCase(), g = gf.value; let k = 0;
    rows.forEach(r => {{ const on = (!g || r.dataset.g === g) && (!s || r.textContent.toLowerCase().includes(s));
                        r.style.display = on ? '' : 'none'; k += on; }});
    n.textContent = k + ' of ' + rows.length + ' activities';
  }}
  q.addEventListener('input', apply); gf.addEventListener('change', apply); apply();
</script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="Render the activity grain page for one protocol.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", required=True)
    a = ap.parse_args()
    print(render(a.protocol, a.collection))


if __name__ == "__main__":
    main()
