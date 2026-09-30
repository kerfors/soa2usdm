"""
SoA2USDM Activity Inventory (collection-scoped)

Generates a self-contained activities.html + activities.json for a collection:
one row per distinct activity per study (unified_activities of the consolidated
layer), with its source-table occurrences folded in as provenance. The page is
for searching activities across the collection's protocols; each row links to
its row in the protocol's consolidated view.
Annotations are listed under their activity: bound to the name, or to a mark (with
its column); header-cell annotations and legends are not.

activities.json (schema_name soa2usdm-activity-inventory, schema_version 1.0):
  collection, generated_at, counts, activities[] — one entry per unified
  activity: protocol_id, sponsor, d4k_folder, therapeutic_area, xact_id,
  activity_name, parent_name, hierarchy_level, is_section_header, is_redacted,
  match_status, table_count, tables, any_marks, variants (verbatim wordings),
  occurrences[] (table_number, table_title, table_type after corrections,
  track_label, row_position, verbatim_name, has_schedule_data) and
  annotations[] (marker, table_number, text, columns for an annotation bound to a mark).

No cross-protocol clustering. Mirrors index_generator.py: a collection-level
step that discovers per-protocol outputs and writes to the collection root.
"""

import json
from datetime import datetime, timezone

from .base import PipelineStepBase
from . import config
from .index_generator import load_study_metadata, esc, TABLE_TYPE_SHORT


def _first_token(value: str) -> str:
    return value.split("_")[0] if value else ""


def _last_token_unless_nct(value: str) -> str:
    parts = value.split("_") if value else []
    return parts[-1] if (len(parts) >= 2 and not parts[-1].startswith("NCT")) else ""


# Closed rule vocabulary for descriptor-declared metadata derivation. A
# collection whose manifest lacks a column may declare which naming convention
# fills it (e.g. usdm_data derives sponsor/TA from the d4k folder name). An
# unknown rule name fails fast with KeyError.
_DERIVATION_RULES = {
    "first_token": _first_token,
    "last_token_unless_nct": _last_token_unless_nct,
}


def _study_fields(meta: dict, descriptor: dict) -> tuple[str, str]:
    """Resolve sponsor and therapeutic_area for one study.

    Manifest column first; otherwise the collection descriptor's
    derived_metadata rule for that field; otherwise blank.
    """
    derived = descriptor.get("derived_metadata", {})
    values = {}
    for field in ("sponsor", "therapeutic_area"):
        value = str(meta.get(field) or "").strip()
        if not value and field in derived:
            spec = derived[field]
            value = _DERIVATION_RULES[spec["rule"]](str(meta.get(spec["from"]) or ""))
        values[field] = value
    return values["sponsor"], values["therapeutic_area"]


def _collect(collection: str):
    """Read resolved + consolidated outputs for every protocol.

    Returns (consolidated_rows, source_rows). Source-table rows come from the
    resolved layer (verbatim per-table activities); consolidated rows come from
    unified_activities, each joined back to its resolved source rows by
    (protocol, table_id, activity_id) so every consolidated entry carries its
    exact source occurrences.
    """
    collection_path = config.get_collection_path(collection)
    study_meta = load_study_metadata(collection_path)
    descriptor = config.load_collection_descriptor(collection)

    source_rows = []
    resolved_lookup = {}
    ann_lookup = {}
    for pid in config.list_protocols(collection):
        meta = study_meta.get(pid, {})
        d4k = meta.get("d4k_folder", "") or ""
        sponsor, ta = _study_fields(meta, descriptor)
        try:
            resolved_dir = config.get_resolved_dir(pid, collection)
        except FileNotFoundError:
            continue
        if not resolved_dir.exists():
            continue
        for f in sorted(resolved_dir.glob("*_resolved.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            tm = d.get("table_metadata", {})
            tid = tm.get("table_id")
            by_id = {a["activity_id"]: a for a in d.get("activities", [])}
            ann_by_id = {an["annotation_id"]: an for an in d.get("annotations", [])}
            # Notes bound to a mark (activity_schedule cell) belong to that activity too; they
            # carry the column(s) they bind to. Items 18 / 24c: without this, moving a note from
            # the row to the cell it names dropped it from the inventory.
            # The composite label joins every header row's value; empty and lone-dash values
            # ('ETV / — / — / —') carry nothing for a reader and are left out.
            col_label = {c["column_id"]: " / ".join(
                             v for v in c.get("composite_label", "").split(" / ")
                             if v.strip() not in ("", "—", "–", "-"))
                         for c in d.get("schedule_columns", [])}
            cell_anns = {}
            for s in d.get("activity_schedule", []):
                for aid in s.get("linked_annotation_ids") or []:
                    cols = cell_anns.setdefault(s["activity_id"], {}).setdefault(aid, [])
                    label = col_label.get(s["column_id"], "")
                    if label not in cols:
                        cols.append(label)
            for a in d.get("activities", []):
                resolved_lookup[(pid, tid, a["activity_id"])] = {
                    "table_number": tm.get("table_number"),
                    "table_title": tm.get("table_title", ""),
                    "table_type": tm.get("table_type", ""),
                    "track_label": tm.get("track_label"),
                    "row_position": a.get("row_position"),
                    "verbatim_name": a.get("activity_name", ""),
                    "has_schedule_data": a.get("has_schedule_data"),
                }
                # Legend-typed annotations are definitional (abbreviation keys),
                # and their row binding is the marker's printed position, not
                # scope — carrying them onto rows put "ulcerative colitis" on a
                # Dosing row. Excluded from row lists, counts and search; they
                # remain in the resolved/consolidated data and viewers.
                row_ids = a.get("linked_annotation_ids", [])
                row_anns = [{"marker": ann_by_id[aid]["annotation_marker"],
                             "table_number": tm.get("table_number"),
                             "text": ann_by_id[aid]["annotation_text"]}
                            for aid in row_ids
                            if ann_by_id[aid]["annotation_type"] != "legend"]
                row_anns += [{"marker": ann_by_id[aid]["annotation_marker"],
                              "table_number": tm.get("table_number"),
                              "text": ann_by_id[aid]["annotation_text"],
                              "columns": cols}
                             for aid, cols in cell_anns.get(a["activity_id"], {}).items()
                             if aid not in row_ids and ann_by_id[aid]["annotation_type"] != "legend"]
                ann_lookup[(pid, tid, a["activity_id"])] = row_anns
                par = by_id.get(a.get("parent_activity_id"))
                source_rows.append({
                    "protocol_id": pid, "sponsor": sponsor, "d4k_folder": d4k,
                    "therapeutic_area": ta,
                    "table_number": tm.get("table_number"),
                    "table_title": tm.get("table_title", ""),
                    "table_type": tm.get("table_type", ""),
                    "track_label": tm.get("track_label"),
                    "row_position": a.get("row_position"),
                    "activity_name": a.get("activity_name", ""),
                    "parent_name": (par or {}).get("activity_name", "") if par else "",
                    "hierarchy_level": a.get("hierarchy_level", 0),
                    "is_section_header": a.get("is_section_header", False),
                    "is_redacted": a.get("is_redacted", False),
                    "has_schedule_data": a.get("has_schedule_data"),
                    "annotation_markers": a.get("annotation_markers", "") or "",
                    "annotations": row_anns,
                })

    consolidated_rows = []
    for pid in config.list_protocols(collection):
        meta = study_meta.get(pid, {})
        d4k = meta.get("d4k_folder", "") or ""
        sponsor, ta = _study_fields(meta, descriptor)
        try:
            consolidated_dir = config.get_consolidated_dir(pid, collection)
        except FileNotFoundError:
            continue
        if not consolidated_dir.exists():
            continue
        for f in sorted(consolidated_dir.glob("*_consolidated.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            for ua in d.get("unified_activities", []):
                occ = []
                for sr in ua.get("source_refs", []):
                    rec = resolved_lookup.get((pid, sr.get("table_id"), sr.get("activity_id")))
                    if rec:
                        occ.append(rec)
                occ.sort(key=lambda o: (o["table_number"] or 0, o["row_position"] or 0))
                variants = []
                for o in occ:
                    if o["verbatim_name"] and o["verbatim_name"] not in variants:
                        variants.append(o["verbatim_name"])
                anns = []
                for sr in ua.get("source_refs", []):
                    anns.extend(ann_lookup.get((pid, sr.get("table_id"), sr.get("activity_id")), []))
                anns.sort(key=lambda x: x["table_number"] or 0)
                annotations = []
                seen_texts = set()
                for an in anns:
                    if an["text"] not in seen_texts:
                        seen_texts.add(an["text"])
                        annotations.append(an)
                consolidated_rows.append({
                    "protocol_id": pid, "sponsor": sponsor, "d4k_folder": d4k,
                    "therapeutic_area": ta, "xact_id": ua.get("xact_id"),
                    "activity_name": ua.get("activity_name", ""),
                    "parent_name": ua.get("parent_name", ""),
                    "hierarchy_level": ua.get("hierarchy_level", 0),
                    "is_section_header": ua.get("is_section_header", False),
                    "is_redacted": ua.get("is_redacted", False),
                    "match_status": ua.get("match_status", ""),
                    "table_count": len(occ),
                    "tables": sorted({o["table_number"] for o in occ}),
                    "any_marks": any(o["has_schedule_data"] is True for o in occ),
                    "variants": variants, "occurrences": occ,
                    "annotations": annotations,
                })

    return consolidated_rows, source_rows


def generate_activity_inventory(collection: str):
    """Build (html, payload) for the collection activity inventory."""
    cons, src = _collect(collection)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    protocols = sorted({r["protocol_id"] for r in cons})
    counts = {
        "protocols": len(protocols),
        "activities": len(cons),
        "multi_table_activities": sum(1 for c in cons if c["table_count"] > 1),
        "activities_with_wording_variants": sum(1 for c in cons if len(c["variants"]) > 1),
        "redacted_activities": sum(1 for c in cons if c["is_redacted"]),
    }
    sp_counts = {}
    prot_sponsor = {r["protocol_id"]: r["sponsor"] for r in cons}
    for s in prot_sponsor.values():
        if s:
            sp_counts[s] = sp_counts.get(s, 0) + 1
    spopts = "".join(f'<option value="{esc(s)}">{esc(s)} ({n})</option>'
                     for s, n in sorted(sp_counts.items()))
    propts = "".join(f'<option value="{esc(p)}">{esc(p)}</option>' for p in protocols)

    payload = {"schema_name": "soa2usdm-activity-inventory", "schema_version": "1.0",
               "collection": collection, "generated_at": generated_at,
               "counts": counts, "activities": cons}
    data_json = json.dumps(cons, ensure_ascii=False).replace("</", "<\\/")
    types_json = json.dumps(TABLE_TYPE_SHORT)

    html = _TEMPLATE
    rep = {"__DATA__": data_json, "__TYPES__": types_json, "__SPOPTS__": spopts, "__PROPTS__": propts,
           "__COLLECTION__": esc(collection), "__GENERATED__": generated_at,
           "__PROT__": counts["protocols"], "__CON__": counts["activities"]}
    for k, v in rep.items():
        html = html.replace(k, str(v))
    return html, payload


_TEMPLATE = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>__COLLECTION__ · activities · SoA2USDM</title>
<style>
:root{--blue:#1F4788;--blue2:#2E75B6;--ink:#1f2933;--muted:#5f6b7a;--line:#d9dee5;--bg:#f5f7fa;--head:#fafbfc;--red:#c62828}
*{box-sizing:border-box;margin:0;padding:0}
body{font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}
.header{background:var(--blue);color:#fff;padding:14px 22px}
.header h1{font-size:20px;font-weight:600}
.header .sub{font-size:13px;opacity:.85;margin-top:3px}
.crumbs{background:#fff;border-bottom:1px solid var(--line);padding:8px 22px;font-size:12px;color:var(--muted)}
.crumbs a{color:var(--blue2);text-decoration:none}.crumbs a:hover{text-decoration:underline}
.crumbs .cur{font-weight:600;color:var(--ink)}.crumbs .sep{color:#9aa4af;margin:0 4px}
.content{padding:14px 22px 20px}
.section{background:#fff;border:1px solid var(--line);border-radius:6px}
.controls{padding:9px 12px;background:var(--head);border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;align-items:center;position:sticky;top:0;z-index:6;border-radius:6px 6px 0 0}
#q{flex:1;min-width:220px;padding:6px 10px;border:1px solid var(--line);border-radius:4px;font-size:13px;background:#fff;color:var(--ink)}
#q:focus{outline:none;border-color:var(--blue2)}
select{padding:5px 8px;border:1px solid var(--line);border-radius:4px;font-size:12px;background:#fff;color:var(--ink)}
label.chk{font-size:12px;color:var(--muted);display:flex;gap:5px;align-items:center;cursor:pointer}
#count{color:var(--muted);font-size:12px;margin-left:auto;white-space:nowrap}
table{width:100%;border-collapse:collapse;font-size:12px}
thead th{position:sticky;top:0;background:var(--head);padding:6px 10px;text-align:left;font-size:11px;font-weight:600;color:var(--muted);border-bottom:1px solid var(--line);white-space:nowrap;cursor:pointer;user-select:none;z-index:5}
thead th:hover{color:var(--blue)}.ar{font-size:9px}
tbody td{padding:6px 10px;border-bottom:1px solid #eef1f4;vertical-align:top}
tr.r:hover td{background:#eef4fb}
tr.sec td{background:var(--head)}tr.sec .act{font-weight:600}
td.pid{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-weight:600;white-space:nowrap}
td.pid a{color:var(--blue);text-decoration:none}td.pid a:hover{text-decoration:underline}
td.sp{white-space:nowrap;color:var(--muted)}
.act a{color:var(--ink);text-decoration:none}.act a:hover{color:var(--blue2);text-decoration:underline}
td.par{color:var(--muted)}
td.tables>span{display:block;white-space:nowrap}
.ttype{color:var(--muted);font-size:11px}
.flag{font-size:10.5px;color:var(--muted);margin-left:6px}
.flag.red{color:var(--red)}
td.nt{white-space:nowrap}
.nbtn{font-size:11px;color:var(--blue2);cursor:pointer;white-space:nowrap}
.nbtn:hover{text-decoration:underline}
.nhit{font-size:10.5px;color:#8a5a00;background:#fff3d6;border-radius:3px;padding:0 4px;margin-left:4px;white-space:nowrap}
mark{background:#fff3d6;color:inherit;padding:0}
tr.open .nbtn{font-weight:600}
.detail td{background:#fbfcfe;padding:8px 12px 10px 28px}
.detail .var{color:var(--muted);font-size:11.5px;margin-bottom:6px}.detail .var b{color:var(--ink);font-weight:600}
.detail .dh{font-size:11px;font-weight:600;color:var(--muted);margin:8px 0 3px;border-bottom:1px solid var(--line);padding-bottom:2px}
.detail .dh:first-child{margin-top:0}
.otab{width:auto;border-collapse:collapse;font-size:11.5px}
.otab td{border:0;padding:2px 14px 2px 0;background:transparent}
.fn{font-size:11.5px;margin:3px 0}.fn b{color:#6a1b9a;font-family:ui-monospace,Menlo,monospace;margin-right:4px}
.fn .where{color:var(--muted);font-family:ui-monospace,Menlo,monospace;margin-right:6px}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;color:var(--muted)}
footer{padding:12px 22px 20px;color:var(--muted);font-size:11.5px}
</style></head><body>
<div class="header"><h1>Activities — __COLLECTION__</h1>
<div class="sub">__CON__ activities across __PROT__ protocols · one row per activity per protocol, as consolidated · no matching across protocols · generated __GENERATED__</div></div>
<div class="crumbs"><a href="../../../index.html">Collections</a><span class="sep">›</span><a href="index.html">__COLLECTION__</a><span class="sep">›</span><span class="cur">Activities</span></div>
<div class="content"><div class="section">
<div class="controls">
<input id="q" placeholder="Search activity, parent, wording, annotation, protocol, sponsor…" autocomplete="off">
<select id="sponsorf"><option value="">all sponsors</option>__SPOPTS__</select>
<select id="protof"><option value="">all protocols</option>__PROPTS__</select>
<label class="chk"><input type="checkbox" id="showsec" checked> section headers</label>
<span id="count"></span>
</div>
<table><thead id="thead"></thead><tbody id="tb"></tbody></table>
</div></div>
<footer>Generated __GENERATED__ by <code>soa2usdm.activity_inventory</code> · data: <a href="activities.json">activities.json</a> · Built iteratively with Claude (Anthropic). Content under CC-BY-4.0.</footer>
<script>
const D=__DATA__, TT=__TYPES__;
let sortk='__default__', asc=true;
const $=id=>document.getElementById(id);
const q=$('q'),sponsorf=$('sponsorf'),protof=$('protof'),showsec=$('showsec'),tb=$('tb'),thead=$('thead'),cnt=$('count');
function eh(s){return (s===null||s===undefined?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
const HEAD=[['protocol_id','Protocol'],['sponsor','Sponsor'],['activity_name','Activity'],['parent_name','Parent'],['table_count','Tables'],['n_notes','Annotations']];
thead.innerHTML='<tr>'+HEAD.map(([k,l])=>`<th data-k="${k}">${l}<span class="ar"></span></th>`).join('')+'</tr>';
thead.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(sortk===k)asc=!asc;else{sortk=k;asc=true;}
 thead.querySelectorAll('.ar').forEach(a=>a.textContent='');th.querySelector('.ar').textContent=asc?' ▲':' ▼';render();});
D.forEach(r=>{r.n_notes=(r.annotations||[]).length;
 const o=r.occurrences&&r.occurrences.length?r.occurrences[0]:{table_number:0,row_position:0};r._t=o.table_number||0;r._p=o.row_position||0;
 r._h=(r.activity_name+' '+r.parent_name+' '+r.protocol_id+' '+r.sponsor+' '+(r.variants||[]).join(' ')+' '+(r.occurrences||[]).map(o=>o.table_title).join(' ')+' '+(r.annotations||[]).map(a=>a.text).join(' ')).toLowerCase();});
function cmp(a,b){
 if(sortk==='__default__')return a.protocol_id.localeCompare(b.protocol_id)||(a._t-b._t)||(a._p-b._p);
 let x=a[sortk],y=b[sortk];
 if(typeof x==='number'||typeof y==='number')return (x||0)-(y||0);
 return String(x||'').toLowerCase().localeCompare(String(y||'').toLowerCase());
}
function passes(r,term){
 if(sponsorf.value&&r.sponsor!==sponsorf.value)return false;
 if(protof.value&&r.protocol_id!==protof.value)return false;
 if(!showsec.checked&&r.is_section_header)return false;
 return !term||r._h.includes(term);
}
function tableLine(o){
 const t=o.table_type!=='main_soa'?` <span class="ttype">${eh(TT[o.table_type])}</span>`:'';
 const hover=o.table_type+(o.track_label?': '+o.track_label:'')+' — '+o.table_title;
 return `<span title="${eh(hover)}">T${eh(o.table_number)}${t}</span>`;
}
function hl(s,term){const e=eh(s);if(!term)return e;const t=eh(term).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');return e.replace(new RegExp(t,'gi'),m=>`<mark>${m}</mark>`);}
function row(r,i,term){
 const cv=`${encodeURIComponent(r.protocol_id)}/SoA2USDM/consolidated/${encodeURIComponent(r.protocol_id)}_consolidated.html#${r.xact_id}`;
 const ind=r.hierarchy_level?` style="padding-left:${r.hierarchy_level*14}px"`:'';
 const flags=(r.is_redacted?'<span class="flag red">redacted</span>':'')+((r.variants||[]).length>1?`<span class="flag">${r.variants.length} wordings</span>`:'');
 const seen=new Set(),tl=[];(r.occurrences||[]).forEach(o=>{if(!seen.has(o.table_number)){seen.add(o.table_number);tl.push(tableLine(o));}});
 const canExp=r.n_notes>0||(r.variants||[]).length>1||r.table_count>1;
 const nhit=term&&(r.annotations||[]).some(a=>(a.text||'').toLowerCase().includes(term))?'<span class="nhit" title="The search term is in an annotation of this activity">in annotation</span>':'';
 const nb=canExp?`<span class="nbtn" data-i="${i}">${r.n_notes?r.n_notes+' annotation'+(r.n_notes>1?'s':''):'details'} ▸</span>${nhit}`:'';
 return `<tr class="r${r.is_section_header?' sec':''}"><td class="pid"><a href="index.html#${eh(r.protocol_id)}" title="${eh(r.d4k_folder)} — this protocol's row on the collection index">${eh(r.protocol_id)}</a></td>`+
  `<td class="sp">${eh(r.sponsor)}</td>`+
  `<td class="act"><a href="${cv}" title="Show in the consolidated view"${ind}>${hl(r.activity_name,term)}</a>${flags}</td>`+
  `<td class="par">${hl(r.parent_name,term)}</td><td class="tables">${tl.join('')}</td><td class="nt">${nb}</td></tr>`;
}
function detail(r){const term=q.value.trim().toLowerCase();
 const vars=(r.variants||[]).length>1?`<div class="var">wordings in the source tables: <b>${r.variants.map(v=>hl(v,term)).join('</b> · <b>')}</b></div>`:'';
 const occ=`<div class="dh">As printed</div><table class="otab">`+(r.occurrences||[]).map(o=>`<tr><td class="mono">T${eh(o.table_number)} row ${eh(o.row_position)}</td><td>${hl(o.verbatim_name,term)}</td><td class="mono">${o.has_schedule_data===false?'no marks':''}</td></tr>`).join('')+'</table>';
 const fns=r.n_notes?`<div class="dh">Annotations</div>`+r.annotations.map(a=>`<div class="fn"><b>${eh(a.marker)}</b><span class="where">T${eh(a.table_number)}${a.columns?' · '+eh(a.columns.join('; ')):''}</span>${hl(a.text,term)}</div>`).join(''):'';
 return `<tr class="detail"><td colspan="6">${vars}${occ}${fns}</td></tr>`;
}
let ARR=[];
function toggle(i,tr){const nx=tr.nextElementSibling;
 if(nx&&nx.classList.contains('detail')){nx.remove();tr.classList.remove('open');}
 else{tr.classList.add('open');tr.insertAdjacentHTML('afterend',detail(ARR[i]));}}
function render(){
 const term=q.value.trim().toLowerCase();
 ARR=D.filter(r=>passes(r,term));
 ARR.sort((a,b)=>{const c=cmp(a,b);return asc?c:-c;});
 tb.innerHTML=ARR.map((r,i)=>row(r,i,term)).join('');
 tb.querySelectorAll('.nbtn').forEach(b=>b.onclick=()=>toggle(+b.dataset.i,b.closest('tr')));
 cnt.textContent=`${ARR.length} of ${D.length} activities`;
}
q.oninput=render;[sponsorf,protof,showsec].forEach(e=>e.onchange=render);
// Column headings stick just below the sticky search bar, whatever its wrapped height.
function stick(){const h=document.querySelector('.controls').offsetHeight;thead.querySelectorAll('th').forEach(th=>th.style.top=h+'px');}
window.addEventListener('resize',stick);stick();
render();
</script></body></html>'''


class ActivityInventoryStep(PipelineStepBase):
    """Generate collection-level activities.html + activities.json."""

    step_name = "activity_inventory"

    def execute(self, data: dict) -> dict:
        source = data.get("source", {})
        collection = source.get("collection")
        if not collection:
            self._log_error("Missing collection in source")
            return {"output_file": None}
        try:
            html, payload = generate_activity_inventory(collection)
            collection_path = config.get_collection_path(collection)
            html_file = collection_path / "activities.html"
            json_file = collection_path / "activities.json"
            html_file.write_text(html, encoding="utf-8")
            json_file.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            self._analytics.increment("activity_inventory_generated")
            return {"output_file": str(html_file), "json_file": str(json_file),
                    "status": "success"}
        except Exception as e:
            self._log_error(f"Activity inventory generation failed: {e}")
            return {"output_file": None, "status": "failed", "error": str(e)}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate the collection activity inventory (activities.html + activities.json).")
    ap.add_argument("--collection", default=config.DEFAULT_COLLECTION)
    args = ap.parse_args()
    html, payload = generate_activity_inventory(args.collection)
    collection_path = config.get_collection_path(args.collection)
    (collection_path / "activities.html").write_text(html, encoding="utf-8")
    (collection_path / "activities.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    c = payload["counts"]
    print(f"Wrote {collection_path / 'activities.html'}")
    print(f"  {c['activities']} activities / {c['protocols']} protocols")


if __name__ == "__main__":
    main()
