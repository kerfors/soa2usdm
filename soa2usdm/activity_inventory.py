"""
SoA2USDM Activity Inventory (collection-scoped)

Generates a self-contained activities.html + activities.json for a collection:
every activity extracted from the SoA tables, at two granularities —
  * Consolidated  : one row per distinct activity per study (unified_activities),
                    with its source-table occurrences folded in as provenance.
  * Source-table  : every activity verbatim, one row per activity per table.

No cross-protocol clustering. Mirrors index_generator.py: a collection-level
step that discovers per-protocol outputs and writes to the collection root.
"""

import json
from datetime import datetime, timezone

from .base import PipelineStepBase
from . import config
from .index_generator import load_study_metadata, esc


def _sponsor_ta(d4k: str):
    """Derive sponsor (leading token) and therapeutic area (trailing token) from d4k_folder."""
    parts = d4k.split("_") if d4k else []
    sponsor = parts[0] if parts else ""
    ta = parts[-1] if (len(parts) >= 2 and not parts[-1].startswith("NCT")) else ""
    return sponsor, ta


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

    source_rows = []
    resolved_lookup = {}
    for pid in config.list_protocols(collection):
        meta = study_meta.get(pid, {})
        d4k = meta.get("d4k_folder", "") or ""
        sponsor, ta = _sponsor_ta(d4k)
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
                    "has_schedule_data": a.get("has_schedule_data"),
                    "annotation_markers": a.get("annotation_markers", "") or "",
                })

    consolidated_rows = []
    for pid in config.list_protocols(collection):
        meta = study_meta.get(pid, {})
        d4k = meta.get("d4k_folder", "") or ""
        sponsor, ta = _sponsor_ta(d4k)
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
                consolidated_rows.append({
                    "protocol_id": pid, "sponsor": sponsor, "d4k_folder": d4k,
                    "therapeutic_area": ta, "xact_id": ua.get("xact_id"),
                    "activity_name": ua.get("activity_name", ""),
                    "parent_name": ua.get("parent_name", ""),
                    "hierarchy_level": ua.get("hierarchy_level", 0),
                    "is_section_header": ua.get("is_section_header", False),
                    "match_status": ua.get("match_status", ""),
                    "table_count": len(occ),
                    "tables": sorted({o["table_number"] for o in occ}),
                    "any_marks": any(o["has_schedule_data"] is True for o in occ),
                    "variants": variants, "occurrences": occ,
                })

    return consolidated_rows, source_rows


def generate_activity_inventory(collection: str):
    """Build (html, payload) for the collection activity inventory."""
    cons, src = _collect(collection)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    protocols = sorted({r["protocol_id"] for r in src})
    counts = {
        "protocols": len(protocols),
        "consolidated_activities": len(cons),
        "source_table_rows": len(src),
        "folded": len(src) - len(cons),
        "multi_table_activities": sum(1 for c in cons if c["table_count"] > 1),
        "activities_with_wording_variants": sum(1 for c in cons if len(c["variants"]) > 1),
    }
    sp_counts = {}
    prot_sponsor = {r["protocol_id"]: r["sponsor"] for r in src}
    for s in prot_sponsor.values():
        if s:
            sp_counts[s] = sp_counts.get(s, 0) + 1
    spopts = "".join(f'<option value="{esc(s)}">{esc(s)} ({n})</option>'
                     for s, n in sorted(sp_counts.items()))
    propts = "".join(f'<option value="{esc(p)}">{esc(p)}</option>' for p in protocols)

    payload = {"collection": collection, "generated_at": generated_at,
               "counts": counts, "consolidated": cons, "source": src}
    data_json = json.dumps({"consolidated": cons, "source": src}, ensure_ascii=False).replace("</", "<\\/")

    html = _TEMPLATE
    rep = {"__DATA__": data_json, "__SPOPTS__": spopts, "__PROPTS__": propts,
           "__COLLECTION__": esc(collection), "__GENERATED__": generated_at,
           "__PROT__": counts["protocols"], "__CON__": counts["consolidated_activities"],
           "__SRC__": counts["source_table_rows"], "__FOLD__": counts["folded"],
           "__MT__": counts["multi_table_activities"],
           "__WV__": counts["activities_with_wording_variants"]}
    for k, v in rep.items():
        html = html.replace(k, str(v))
    return html, payload


_TEMPLATE = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>__COLLECTION__ — SoA activities inventory</title>
<style>
:root{--fg:#333;--pri:#1F4788;--sec:#2E75B6;--muted:#888;--line:#e0e0e0;--bg:#f8f9fa;--panel:#fff;--secrow:#fbf7e8;--secfg:#8d6e00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:13.5px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{padding:16px 22px;background:var(--panel);border-bottom:1px solid var(--line)}
.back{font-size:12px;margin-bottom:8px}.back a{color:var(--pri);text-decoration:none}.back a:hover{text-decoration:underline}
h1{margin:0 0 3px;font-size:18px;color:var(--pri)}
.sub{color:var(--muted);font-size:12px}.sub code{background:#f4f4f4;padding:1px 5px;border-radius:3px}
.stats{margin-top:9px;display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--muted)}.stats b{color:var(--fg)}
.controls{padding:10px 22px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:9px;align-items:center;background:var(--panel);position:sticky;top:0;z-index:6}
.seg{display:flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{padding:8px 12px;background:#fff;color:var(--sec);border:0;border-right:1px solid var(--line);cursor:pointer;font-size:12.5px}
.seg button:last-child{border-right:0}.seg button.on{background:var(--pri);color:#fff;font-weight:600}
#q{flex:1;min-width:210px;padding:8px 12px;border:1px solid var(--line);background:#fff;color:var(--fg);border-radius:7px;font-size:14px}
#q:focus{outline:none;border-color:var(--sec);box-shadow:0 0 0 2px rgba(46,117,182,.15)}
select{padding:8px 10px;border:1px solid var(--line);background:#fff;color:var(--fg);border-radius:7px;font-size:12px;cursor:pointer}
label.chk{font-size:12px;color:var(--muted);display:flex;gap:5px;align-items:center;cursor:pointer}
#count{color:var(--muted);font-size:12px;margin-left:auto;white-space:nowrap}
.wrap{padding:0 22px 40px}
table{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--panel)}
thead th{position:sticky;top:53px;background:#f0f0f0;color:#555;font-weight:600;font-size:10.5px;text-transform:uppercase;letter-spacing:.03em;text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;user-select:none;z-index:5}
thead th:hover{color:var(--pri)}.ar{opacity:.6;font-size:9px}
tbody td{padding:6px 9px;border-bottom:1px solid #eee;vertical-align:top}
tbody tr.r:hover{background:#f8f9fa}
tr.sec td{color:var(--secfg);font-weight:600;background:var(--secrow)}
td.pid,td.pid a{color:var(--pri);font-family:ui-monospace,Menlo,monospace;white-space:nowrap;text-decoration:none}
td .d4k{display:block;color:var(--muted);font-size:10px}
.spb{font-size:10.5px;padding:1px 6px;border-radius:20px;border:1px solid #c7d2fe;color:#3730a3;background:#eef2ff;white-space:nowrap}
td.tbl{color:var(--muted)}td.tbl b{color:var(--fg);font-family:ui-monospace,Menlo,monospace}
.tt{display:block;max-width:320px;color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rp{color:var(--muted);font-family:ui-monospace,Menlo,monospace}
.act{color:var(--fg)}
.exp{cursor:pointer}.exp .chev{color:var(--muted);display:inline-block;width:12px;transition:transform .12s}
tr.open .chev{transform:rotate(90deg)}
.nT{font-size:10.5px;padding:1px 7px;border:1px solid #cfe0fc;background:#e8f0fe;color:var(--pri);border-radius:20px;white-space:nowrap}
.nT.one{color:var(--muted);border-color:#e0e0e0;background:#f5f5f5}
.mt{font-size:9.5px;font-weight:700;padding:1px 6px;border-radius:20px;text-transform:uppercase;margin-left:6px}
.mt.fuzzy_auto{color:#8d6e00;background:#fff8e1;border:1px solid #ffe0a3}
.mt.fuzzy_review{color:#c62828;background:#fce4ec;border:1px solid #f8bbd0}
.mt.fuzzy_cross_parent{color:#6a1b9a;background:#f3e5f5;border:1px solid #e1bee7}
.flag{font-size:9.5px;padding:1px 5px;border-radius:4px;border:1px solid var(--line);color:var(--muted);margin-left:6px;background:#fafafa}
.flag.nod{color:#aaa}
.detail td{background:#fbfcfe;padding:8px 12px 10px 30px}
.detail .var{color:#555;font-size:11.5px;margin-bottom:6px}.detail .var b{color:var(--secfg)}
.otab{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:2px;background:transparent}
.otab th{position:static;background:transparent;border-bottom:1px solid var(--line);padding:4px 8px;font-size:9.5px;color:#888}
.otab td{border-bottom:1px solid #eee;padding:4px 8px}
footer{padding:16px 22px;color:var(--muted);font-size:11.5px;border-top:1px solid var(--line);background:var(--panel)}
</style></head><body>
<header>
<div class="back"><a href="index.html">&larr; __COLLECTION__ collection index</a></div>
<h1>Schedule-of-Activities — Activities inventory</h1>
<div class="sub"><b>Consolidated</b> = one row per distinct activity per study (source-table rows folded in as provenance; intra-protocol, mostly exact). <b>Source-table</b> = every activity exactly as it sits in each SoA table. No cross-protocol clustering. Built from the <code>consolidated/</code> and <code>resolved/</code> pipeline layers.</div>
<div class="stats"><span><b>__PROT__</b> protocols</span><span><b>__CON__</b> consolidated activities</span><span><b>__SRC__</b> source-table rows</span><span><b>__FOLD__</b> folded</span><span><b>__MT__</b> span &gt;1 table</span><span><b>__WV__</b> folded across differing wording</span></div>
</header>
<div class="controls">
<div class="seg"><button id="mCon" class="on">Consolidated (per study)</button><button id="mSrc">Source-table (every row)</button></div>
<input id="q" placeholder="Search activity, parent, protocol, sponsor, table…" autocomplete="off">
<select id="sponsorf"><option value="">all sponsors</option>__SPOPTS__</select>
<select id="protof"><option value="">all protocols</option>__PROPTS__</select>
<label class="chk"><input type="checkbox" id="hidesec"> hide section headers</label>
<label class="chk"><input type="checkbox" id="onlydata"> only with marks</label>
<span id="count"></span>
</div>
<div class="wrap"><table><thead id="thead"></thead><tbody id="tb"></tbody></table></div>
<footer>Generated __GENERATED__ by <code>soa2usdm.activity_inventory</code>. Built iteratively with Claude (Anthropic). Content under CC-BY-4.0.</footer>
<script>
const D=__DATA__;
let MODE='con', sortk='__default__', asc=true;
const q=document.getElementById('q'),sponsorf=document.getElementById('sponsorf'),protof=document.getElementById('protof'),
 hidesec=document.getElementById('hidesec'),onlydata=document.getElementById('onlydata'),tb=document.getElementById('tb'),
 thead=document.getElementById('thead'),cnt=document.getElementById('count'),mCon=document.getElementById('mCon'),mSrc=document.getElementById('mSrc');
function eh(s){return (s===null||s===undefined?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
const HEAD={con:[['protocol_id','Protocol'],['sponsor','Sponsor'],['activity_name','Activity (consolidated)'],['parent_name','Parent'],['table_count','Tables'],['match_status','Fold']],
 src:[['protocol_id','Protocol'],['sponsor','Sponsor'],['table_number','Table'],['row_position','Row'],['activity_name','Activity (verbatim)'],['parent_name','Parent'],['annotation_markers','Fn']]};
function setHead(){thead.innerHTML='<tr>'+HEAD[MODE].map(([k,l])=>`<th data-k="${k}">${l}<span class="ar"></span></th>`).join('')+'</tr>';
 thead.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(sortk===k)asc=!asc;else{sortk=k;asc=true;}
  thead.querySelectorAll('.ar').forEach(a=>a.textContent='');th.querySelector('.ar').textContent=asc?' ▲':' ▼';render();});}
function firstOcc(r){return r.occurrences&&r.occurrences.length?r.occurrences[0]:{table_number:0,row_position:0};}
function cmp(a,b){
 if(sortk==='__default__'){
  if(MODE==='con'){const fa=firstOcc(a),fb=firstOcc(b);return a.protocol_id.localeCompare(b.protocol_id)||((fa.table_number||0)-(fb.table_number||0))||((fa.row_position||0)-(fb.row_position||0));}
  return a.protocol_id.localeCompare(b.protocol_id)||(a.table_number-b.table_number)||(a.row_position-b.row_position);
 }
 let x=a[sortk],y=b[sortk];
 if(sortk==='table_count'){return (x||0)-(y||0);}
 if(typeof x==='number'||typeof y==='number'){x=x==null?-1:x;y=y==null?-1:y;return x-y;}
 return String(x||'').toLowerCase().localeCompare(String(y||'').toLowerCase());
}
function passes(r){
 const term=q.value.trim().toLowerCase(),sp=sponsorf.value,pr=protof.value,hs=hidesec.checked,od=onlydata.checked;
 if(sp&&r.sponsor!==sp)return false; if(pr&&r.protocol_id!==pr)return false;
 if(hs&&r.is_section_header)return false;
 if(od){ if(MODE==='con'){if(!r.any_marks)return false;} else if(r.has_schedule_data!==true)return false; }
 if(term){let h;
  if(MODE==='con')h=(r.activity_name+' '+r.parent_name+' '+r.protocol_id+' '+r.sponsor+' '+(r.variants||[]).join(' ')+' '+(r.occurrences||[]).map(o=>o.table_title).join(' ')).toLowerCase();
  else h=(r.activity_name+' '+r.parent_name+' '+r.protocol_id+' '+r.sponsor+' '+r.table_title).toLowerCase();
  if(!h.includes(term))return false;}
 return true;
}
function conRow(r,i){
 const ind=r.hierarchy_level?('padding-left:'+(r.hierarchy_level*16)+'px'):'';
 const nT=`<span class="nT ${r.table_count>1?'':'one'}">×${r.table_count}${r.table_count>1?' · '+r.tables.map(t=>'T'+t).join(','):''}</span>`;
 const mt=(['fuzzy_auto','fuzzy_review','fuzzy_cross_parent'].includes(r.match_status))?`<span class="mt ${r.match_status}">${r.match_status.replace('fuzzy_','')}</span>`:'';
 const sec=r.is_section_header?'<span class="flag">section</span>':'';
 const canExp=r.table_count>1||(r.variants||[]).length>1;
 return `<tr class="r ${r.is_section_header?'sec':''} ${canExp?'exp':''}" data-i="${i}"><td class="pid">${canExp?'<span class="chev">▸</span> ':'<span class="chev" style="visibility:hidden">▸</span> '}${eh(r.protocol_id)}<span class="d4k">${eh(r.d4k_folder)}</span></td>`+
  `<td><span class="spb">${eh(r.sponsor)}</span></td>`+
  `<td><span class="act" style="${ind}">${eh(r.activity_name)}</span>${sec}${(r.variants||[]).length>1?'<span class="flag">'+r.variants.length+' wordings</span>':''}</td>`+
  `<td>${eh(r.parent_name)}</td><td>${nT}</td><td>${mt||'<span class="rp">—</span>'}</td></tr>`;
}
function detailRow(r){
 const vars=(r.variants||[]).length>1?`<div class="var">wording variants folded: <b>${r.variants.map(eh).join('</b> · <b>')}</b></div>`:'';
 const orows=(r.occurrences||[]).map(o=>`<tr><td class="tbl"><b>T${eh(o.table_number)}</b>${o.track_label?' · '+eh(o.track_label):''} <span class="tt" style="display:inline" title="${eh(o.table_title)}">${eh(o.table_title)}</span></td><td class="rp">${eh(o.row_position)}</td><td>${eh(o.verbatim_name)}</td><td class="rp">${o.has_schedule_data===false?'no marks':(o.has_schedule_data===true?'✓':'')}</td></tr>`).join('');
 return `<tr class="detail"><td colspan="6">${vars}<table class="otab"><thead><tr><th>Source table</th><th>Row</th><th>As extracted (verbatim)</th><th>Marks</th></tr></thead><tbody>${orows}</tbody></table></td></tr>`;
}
function srcRow(r){
 const ind=r.hierarchy_level?('padding-left:'+(r.hierarchy_level*16)+'px'):'';
 const flags=(r.is_section_header?'<span class="flag">section</span>':'')+(r.has_schedule_data===false?'<span class="flag nod">no marks</span>':'');
 return `<tr class="r ${r.is_section_header?'sec':''}"><td class="pid">${eh(r.protocol_id)}<span class="d4k">${eh(r.d4k_folder)}</span></td>`+
  `<td><span class="spb">${eh(r.sponsor)}</span></td>`+
  `<td class="tbl"><b>T${eh(r.table_number)}</b>${r.track_label?' · '+eh(r.track_label):''}<span class="tt" title="${eh(r.table_title)}">${eh(r.table_title)}</span></td>`+
  `<td class="rp">${eh(r.row_position)}</td><td><span class="act" style="${ind}">${eh(r.activity_name)}</span>${flags}</td>`+
  `<td>${eh(r.parent_name)}</td><td class="rp">${eh(r.annotation_markers)}</td></tr>`;
}
function render(){
 const arr=(MODE==='con'?D.consolidated:D.source).filter(passes);
 arr.sort((a,b)=>{const c=cmp(a,b);return asc?c:-c;});
 let html='';
 if(MODE==='con'){arr.forEach((r,i)=>{html+=conRow(r,i);});window.__arr=arr;}
 else{arr.forEach(r=>{html+=srcRow(r);});}
 tb.innerHTML=html;
 if(MODE==='con'){
  tb.querySelectorAll('tr.exp').forEach(tr=>tr.onclick=()=>{
   const i=+tr.dataset.i; const nx=tr.nextElementSibling;
   if(nx&&nx.classList.contains('detail')){nx.remove();tr.classList.remove('open');}
   else{tr.classList.add('open');tr.insertAdjacentHTML('afterend',detailRow(window.__arr[i]));}
  });
 }
 cnt.textContent=`${arr.length} of ${MODE==='con'?D.consolidated.length:D.source.length} ${MODE==='con'?'activities':'rows'}`;
}
function setMode(m){MODE=m;sortk='__default__';asc=true;mCon.classList.toggle('on',m==='con');mSrc.classList.toggle('on',m==='src');setHead();render();}
mCon.onclick=()=>setMode('con');mSrc.onclick=()=>setMode('src');
q.oninput=render;[sponsorf,protof,hidesec,onlydata].forEach(e=>e.onchange=render);
setHead();render();
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
    print(f"  {c['consolidated_activities']} consolidated / {c['source_table_rows']} source rows / {c['protocols']} protocols")


if __name__ == "__main__":
    main()
