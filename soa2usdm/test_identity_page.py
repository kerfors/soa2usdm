"""
Per-protocol page for the test identity (soa2usdm-test-identity), step 6a-2.

Renders SoA2USDM/test_identity/{pid}_test_identity.json as {pid}_test_identity.html, with the shared
navigation block (soa2usdm.nav). Nothing is decided here: the page shows what the JSON holds, and quotes
no protocol text beyond it (values as printed, pointers, pages).

Layout (Kerstin, 2026-11-08): a summary of the specialization levels, split into standalone rows, panel
members and ECG components (every level listed, also at 0), and the facet figures; then three sections:
standalone named tests; panel members, grouped under their panel row (the panel and its group head once
per group); ECG activity rows with their components. Per row: routing status and domain (linked to the
routing row), component (codes, hit part, strength and reasons, restated words, collisions), facets (one
line each: variable, value as printed -> CDISC term or none, Kind and Position from Variable_Meaning as
our position or 'Kind not set', where it came from, ambiguous_with), the specialization level with the
COSMoS specializations, and conditions, unread words, practice text and a group head not read.

Open, not coded: the dated list of documents/activity-grain.md is shown once at the top. One entry has a
hook in the JSON and is badged on the rows: a stated SERUM or PLASMA where no COSMoS specialization takes it
(level 'stated facet matches no specialization'). A group head not read is shown once in its group header
and can be filtered; it is not badged, because the JSON does not tell a method word ('dipstick') from a
panel name ('Vital signs').

The page is rendered only from a test identity file that is current against the study's routing file
(inputs.activity_routing.sha256); a stale one stops the build.

Regenerated with the collection index (index_generator.discover_protocol_outputs). Standalone:

  python -m soa2usdm.test_identity_page --collection cell_gene_therapy --protocol NCT03489291
"""

import argparse
import hashlib
import html as html_lib
import json
from collections import Counter
from pathlib import Path

from . import config
from .nav import NAV_CSS, nav_block, page_title
from .test_identity import SCHEMA_NAME, test_identity_path

PAGE_LABEL = "test identity"
DOC_URL = "https://github.com/kerfors/soa2usdm/blob/main/documents/test-identity.md"
OPEN_URL = "https://github.com/kerfors/soa2usdm/blob/main/documents/activity-grain.md"
LEVELS = ("no component", "component open", "domain open", "no specialization", "one specialization",
          "selected by stated facets", "facet not stated", "stated facet matches no specialization",
          "stated facets conflict")
SETTLED = ("one specialization", "selected by stated facets")
ECG_LEVELS = ("test code", "test family, beat not stated", "component open", "no component")
# The dated open-not-coded list of documents/activity-grain.md (2026-11-08), shown once at the top.
OPEN_NOT_CODED = (
    "British spellings",
    "urinalysis “Blood” (Occult Blood or not is knowledge)",
    "“Mean cell volume” (CDISC names the erythrocyte)",
    "T cells / B cells (CP or LB: the CP-A2 question)",
    "bare ECG forms (QT, QRS, RR, QTcF)",
    "SERUM or PLASMA against SERUM OR PLASMA",
    "group heads that are not a CDISC METHOD term (“dipstick”, “microscopic examination”)",
    "a group head routed as a test (“microscopic examination” → MI MIEXAM)",
)
WHERE = {"label": "label", "member qualifier": "member qualifier", "context panel": "context panel",
         "lab_and_purpose": "lab_and_purpose", "measurements": "measurements", "group head": "group head"}
SERUM_OR_PLASMA = {"C13325", "C13356"}   # SPECTYPE SERUM, PLASMA


def esc(v) -> str:
    return html_lib.escape(str(v).translate(config.SYMBOL_FONT))


def page_path(protocol_id: str, collection: str) -> Path:
    return test_identity_path(protocol_id, collection).with_suffix(".html")


def level_class(level: str) -> str:
    return "lv-ok" if level in SETTLED or level == "test code" else (
        "lv-part" if level in ("facet not stated", "test family, beat not stated") else "lv-open")


def _codes(codes: list) -> str:
    return ", ".join(f'<b>{esc(c["testcd"])}</b> <span class="ns">{esc(c["code"])}</span>' for c in codes) or "—"


def _component(c: dict | None) -> str:
    if not c:
        return '<span class="ns">no test code</span>'
    out = [f'<div>{_codes(c["codes"])}</div>']
    if c["hit_part"]:
        out.append(f'<div class="ctx">hit: “{esc(c["hit_part"])}”</div>')
    st = c["hit_strength"]
    if st:
        out.append(f'<div class="ctx"><span class="hs hs-{esc(st)}">{esc(st)}</span>'
                   + (f' {esc(", ".join(c["weak_reasons"]))}' if c["weak_reasons"] else "") + '</div>')
    if c["restated"]:
        out.append(f'<div class="ctx">restated: {esc(", ".join(c["restated"]))}</div>')
    col = c.get("collisions")
    if col:
        rows = "; ".join(f'{esc(r["TESTCD"])} {esc(r["TEST"])} ({esc(r["NCIt_Code"])})' for r in col["rows"])
        out.append(f'<div class="ctx">Test_String_Collisions “{esc(col["string"])}”: {rows} '
                   f'<span class="tag">{esc(col["relation"])}</span></div>')
    return "".join(out)


def _facet(f: dict) -> str:
    term = (f'<b>{esc(f["term"]["submission_value"])}</b> <span class="ns">{esc(f["term"]["codelist"])} '
            f'{esc(f["term"]["concept_id"])}</span>' if f["term"] else
            ("several: " + ", ".join(f'{esc(t["submission_value"])} <span class="ns">{esc(t["concept_id"])}</span>'
                                     for t in f["terms"]) if f["terms"] else '<span class="ns">no term</span>'))
    if f.get("reading") is not None or f["generic"] == "--FAST":
        term += f' <span class="ns">reading {esc(f.get("reading") or "none")}</span>'
    kind = (f'<span class="kd" title="our position (Variable_Meaning)">{esc(f["kind"])} · {esc(f["position"])}</span>'
            if f["kind"] else '<span class="kd kd-unset" title="the domain has no Variable_Meaning row">Kind not set</span>')
    where = esc(WHERE[f["where"]])
    if f.get("pointer"):
        where += f' <span class="ns">{esc(f["pointer"])}</span>'
    if f.get("pages"):
        where += f' <span class="ns">p.&nbsp;{esc(", ".join(str(p) for p in f["pages"]))}</span>'
    if f.get("group_head"):
        where += f' <span class="ns">{esc(f["group_head"])}</span>'
    amb = (f' <span class="tag tag-amb">ambiguous with {esc(", ".join(f["ambiguous_with"]))}</span>'
           if f.get("ambiguous_with") else "")
    return (f'<div class="fc"><code>{esc(f["variable"])}</code> “{esc(f["value"])}” → {term} '
            f'{kind} <span class="wh">{where}</span>{amb}</div>')


def _part(p: dict) -> str:
    weak = (f' <span class="tag tag-amb">weak: {esc(", ".join(p["weak_reasons"]))}</span>' if p["weak_reasons"] else "")
    return (f'<div class="ctx">component part ({esc(p["basis"])}):</div>'
            + _facet(p).replace('</div>', weak + '</div>', 1))


def _spec(s: dict) -> str:
    lv = s["level"]
    out = [f'<span class="lv {level_class(lv)}">{esc(lv)}</span>']
    if s.get("specializations"):
        out.append(f'<div class="ctx">COSMoS: {esc(", ".join(s["specializations"]))}'
                   + (f' <span class="ns">differ by {esc(", ".join(s["differ_by"]))}</span>' if s.get("differ_by") else "")
                   + '</div>')
    if s.get("stated"):
        out.append('<div class="ctx">narrowed by: ' + esc(", ".join(f'{x["position"]} {x["concept_id"]}'
                                                                     for x in s["stated"])) + '</div>')
    for key, label in (("selected", "selected"), ("remaining", "remaining"), ("not_stated", "not stated"),
                       ("conflicting_positions", "conflicting"), ("codes", "codes")):
        if s.get(key):
            out.append(f'<div class="ctx">{label}: {esc(", ".join(s[key]))}</div>')
    return "".join(out)


def _extras(r: dict) -> str:
    out = []
    for c in r["conditions"]:
        out.append(f'<div class="ex"><span class="tag">{esc(c["class"])}</span> “{esc(c["phrase"])}” '
                   f'<span class="ns">{esc(c["where"])}{(" " + esc(c["pointer"])) if c.get("pointer") else ""}</span></div>')
    for p in r["practice_text"]:
        out.append(f'<div class="ex"><span class="tag">practice text</span> <code>{esc(p["variable"])}</code> '
                   f'“{esc(p["value"])}” <span class="ns">{esc(p["statement_id"])}, {esc(p["where"])}</span></div>')
    if r["unread"]:
        out.append(f'<div class="ex"><span class="tag tag-un">unread</span> {esc(" ".join(r["unread"]))}</div>')
    return "".join(out)


def _badges(r: dict) -> list:
    """Open-not-coded entries with a hook in the JSON (see the module docstring)."""
    out = []
    s = r["specialization"]
    if s["level"] == "stated facet matches no specialization":
        stated = {f["term"]["concept_id"] for f in r["facets"] if f["position"] == "system" and f["term"]}
        if stated and stated <= SERUM_OR_PLASMA:
            out.append("SERUM or PLASMA against SERUM OR PLASMA")
    return out


def _flags(r: dict) -> str:
    keys = []
    if r["unread"]:
        keys.append("unread")
    if any(f.get("ambiguous_with") for f in r["facets"]):
        keys.append("ambiguous")
    if r["conditions"]:
        keys.append("conditions")
    if (r["component"] or {}).get("collisions"):
        keys.append("collisions")
    if r.get("group_head") and not r["group_head"]["read"]:
        keys.append("group head not read")
    if r["practice_text"]:
        keys.append("practice text")
    return "|".join(keys)


def _row(r: dict, routing_html: str) -> str:
    rid = r["xact_id"] + (f'.{r["member_id"]}' if "member_id" in r else "")
    dom = esc(r["domain"]) if r["domain"] else '<span class="ns">open</span>'
    badges = "".join(f'<div class="ob">open, not coded: {esc(b)}</div>' for b in _badges(r))
    return (f'<tr id="{esc(rid)}" data-l="{esc(r["specialization"]["level"])}" data-s="{esc(r["routing_status"])}" '
            f'data-f="{esc(_flags(r))}">'
            f'<td class="x">{esc(rid)}</td>'
            f'<td class="act">{esc(r["activity_name"])}{badges}</td>'
            f'<td class="rt"><a href="{routing_html}#{esc(rid)}" title="Show on the routing page">'
            f'<span class="s s-{esc(r["routing_status"].replace(" ", "-"))}">{esc(r["routing_status"])}</span></a>'
            f'<div class="dm">{dom}</div></td>'
            f'<td class="cp">{_component(r["component"])}{"".join(_part(p) for p in r.get("component_parts", []))}</td>'
            f'<td class="fcs">{"".join(_facet(f) for f in r["facets"]) or "<span class=ns>none stated</span>"}{_extras(r)}</td>'
            f'<td class="sp">{_spec(r["specialization"])}</td></tr>')


HEAD = '<thead><tr><th>row</th><th>activity</th><th>routing</th><th>component</th><th>facets · conditions · unread</th><th>specialization</th></tr></thead>'


def _ecg(r: dict, routing_html: str) -> str:
    rid = r["xact_id"]
    comps = "".join(
        f'<tr><td>“{esc(c["text"])}” <span class="ns">{esc(c["pointer"])}</span></td>'
        f'<td>{_codes(c["codes"])}'
        + (f' <span class="ns">via {esc(c["via"])}</span>' if c.get("via") else "")
        + (f'<div class="ctx">outside EG: {esc(", ".join(o["testcd"] + " (" + o["domains"] + ")" for o in c["outside_eg"]))}</div>'
           if c.get("outside_eg") else "")
        + '</td><td>'
        + (f'{esc(c["family"]["head"])}: {esc(", ".join(c["family"]["testcds"]))}'
           + f'<div class="ctx">not stated: {esc(", ".join(c["family"]["tails"]))}</div>'
           if c.get("family") else '<span class="ns">—</span>')
        + f'</td><td><span class="lv {level_class(c["level"])}">{esc(c["level"])}</span></td></tr>'
        for c in r["components"])
    comp_tbl = (f'<table class="sub"><thead><tr><th>component as printed</th><th>EG test</th><th>family</th><th>level</th>'
                f'</tr></thead><tbody>{comps}</tbody></table>' if r["components"]
                else '<span class="ns">no components listed in the protocol context</span>')
    return (f'<tr id="{esc(rid)}" data-l="" data-s="{esc(r["routing_status"])}" data-f="{esc(_flags(r))}">'
            f'<td class="x">{esc(rid)}</td>'
            f'<td class="act">{esc(r["activity_name"])}<div class="rt"><a href="{routing_html}#{esc(rid)}">'
            f'<span class="s s-{esc(r["routing_status"].replace(" ", "-"))}">{esc(r["routing_status"])}</span></a> '
            f'{esc(r["domain"] or "")}</div></td>'
            f'<td>{comp_tbl}</td>'
            f'<td class="fcs">{"".join(_facet(f) for f in r["facets"]) or "<span class=ns>none stated</span>"}{_extras(r)}</td></tr>')


def index_counts(d: dict) -> dict:
    """For the collection index: {unit: (settled, all)}; settled = one specialization or selected by stated
    facets; ecg = components with an EG test code or family, of all components."""
    out = {"standalone": [0, 0], "member": [0, 0], "ecg": [0, 0]}
    for r in d["rows"]:
        if r["unit"] == "activity":
            for c in r["components"]:
                out["ecg"][1] += 1
                out["ecg"][0] += c["level"] != "no component"
        else:
            out[r["unit"]][1] += 1
            out[r["unit"]][0] += r["specialization"]["level"] in SETTLED
    return {u: tuple(v) for u, v in out.items()}


def _summary(d: dict) -> str:
    rows = d["rows"]
    by = {"standalone": Counter(), "member": Counter(), "ecg": Counter()}
    for r in rows:
        if r["unit"] == "activity":
            by["ecg"].update(c["level"] for c in r["components"])
        else:
            by[r["unit"]][r["specialization"]["level"]] += 1
    for u, levels in (("standalone", LEVELS), ("member", LEVELS), ("ecg", ECG_LEVELS)):
        unknown = set(by[u]) - set(levels)
        if unknown:
            raise ValueError(f"{d['protocol_id']}: unknown {u} level(s) {sorted(unknown)}")
    lv = "".join(f'<tr><td><span class="lv {level_class(l)}">{esc(l)}</span></td>'
                 f'<td class="n">{by["standalone"][l]}</td><td class="n">{by["member"][l]}</td></tr>' for l in LEVELS)
    lv += (f'<tr class="tot"><td>rows</td><td class="n">{sum(by["standalone"].values())}</td>'
           f'<td class="n">{sum(by["member"].values())}</td></tr>')
    ecg = " · ".join(f'{esc(l)} {by["ecg"][l]}' for l in ECG_LEVELS)
    n_ecg_rows = sum(1 for r in rows if r["unit"] == "activity")
    facets = [f for r in rows for f in r["facets"]]
    c = d["counts"]
    gh = c.get("group_heads", {})
    figs = (f'{len(facets)} facets, {sum(1 for f in facets if f["term"])} with a CDISC term, '
            f'{sum(1 for f in facets if f.get("ambiguous_with"))} ambiguous, '
            f'{sum(1 for f in facets if f["where"] == "group head")} from a group head, '
            f'{sum(1 for f in facets if not f["kind"])} with Kind not set · '
            f'rows with unread words {c["rows_with_unread"]} · with conditions {c["rows_with_conditions"]} · '
            f'with collisions {c["rows_with_collisions"]} · practice text {c["practice_text"]} · '
            f'group heads read {gh.get("read", 0)}, not read {gh.get("not read", 0)}')
    return (f'<table class="lvt"><thead><tr><th>specialization level</th><th class="n">standalone</th>'
            f'<th class="n">members</th></tr></thead><tbody>{lv}</tbody></table>'
            f'<div class="sum">ECG: {n_ecg_rows} activity rows, {sum(by["ecg"].values())} components: {ecg}</div>'
            f'<div class="sum">{figs}</div>')


def build_html(protocol_id: str, collection: str) -> str:
    """The page for one study, from its current test identity file."""
    src = test_identity_path(protocol_id, collection)
    out = page_path(protocol_id, collection)
    d = json.loads(src.read_text(encoding="utf-8"))
    if d.get("schema_name") != SCHEMA_NAME:
        raise ValueError(f"{src}: schema_name {d.get('schema_name')!r}, expected {SCHEMA_NAME!r}")
    soa = src.parent.parent
    routing_json = soa / "routing" / f"{protocol_id}_activity_routing.json"
    if hashlib.sha256(routing_json.read_bytes()).hexdigest() != d["inputs"]["activity_routing"]["sha256"]:
        raise RuntimeError(f"{src}: stale (routing changed since it was generated); rerun "
                           f"python -m soa2usdm.test_identity --collection {collection} --protocol {protocol_id}")
    routing_html = f"../routing/{protocol_id}_activity_routing.html"
    depth = len(out.relative_to(config.get_collection_path(collection)).parts) - 1
    nav = nav_block(collection, protocol_id, PAGE_LABEL, depth=depth, current=("test_identity", None))
    rows = d["rows"]
    standalone = [r for r in rows if r["unit"] == "standalone"]
    members = [r for r in rows if r["unit"] == "member"]
    ecg = [r for r in rows if r["unit"] == "activity"]

    st_html = "".join(_row(r, routing_html) for r in standalone)
    groups, order = {}, []
    for r in members:
        if r["xact_id"] not in groups:
            groups[r["xact_id"]] = []
            order.append(r["xact_id"])
        groups[r["xact_id"]].append(r)
    mb_html = ""
    for x in order:
        g = groups[x]
        heads = {}
        for r in g:
            if r.get("group_head"):
                heads.setdefault(r["group_head"]["member_id"], r["group_head"])
        head_txt = "; ".join(f'{esc(h["member_id"])} “{esc(h["text"])}” '
                             + ("read" if h["read"] else "not read") for h in heads.values())
        mb_html += (f'<tr class="grp" data-g="1"><td class="x">{esc(x)}</td><td colspan="5"><b>{esc(g[0]["panel_name"])}</b>'
                    f' <span class="ns">{len(g)} member row{"" if len(g) == 1 else "s"}</span>'
                    + (f' <span class="ctx">group heads: {head_txt}</span>' if head_txt else "")
                    + '</td></tr>' + "".join(_row(r, routing_html) for r in g))
    ecg_html = "".join(_ecg(r, routing_html) for r in ecg)

    cdisc = d["inputs"]["cdisc_for_ai"]
    level_opts = "".join(f'<option value="{esc(l)}">{esc(l)}</option>' for l in LEVELS)
    status_opts = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in ("routed", "open", "weak", "not routed"))
    flag_opts = "".join(f'<option value="{esc(f)}">has {esc(f)}</option>'
                        for f in ("unread", "ambiguous", "conditions", "collisions", "group head not read", "practice text"))
    open_list = "; ".join(esc(x) for x in OPEN_NOT_CODED)

    def section(title, n, body, head=HEAD, empty="none"):
        return (f'<section><h2>{title} ({n})</h2>'
                + (f'<div class="tw"><table>{head}<tbody class="tb">{body}</tbody></table></div>' if n
                   else f'<div class="ns">{empty}</div>') + '</section>')

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
    .meta a, .rt a {{ color: #1F4788; text-decoration: none; }}
    .meta code {{ font-size: 11px; }}
    .sum {{ font-size: 12.5px; margin: 6px 0 2px; }}
    .note {{ color: #555; font-size: 12px; margin-top: 6px; }}
    .tw {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; }}
    table.lvt {{ width: auto; margin: 6px 0; }}
    table.lvt td, table.lvt th {{ padding: 2px 10px 2px 0; border: none; }}
    table.lvt tr.tot td {{ border-top: 1px solid #ddd; font-weight: 600; }}
    td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
    th {{ text-align: left; font-size: 11px; color: #666; font-weight: 600; border-bottom: 2px solid #e0e0e0; padding: 5px 8px; white-space: nowrap; }}
    td {{ vertical-align: top; border-bottom: 1px solid #eee; padding: 6px 8px; }}
    tr:target td {{ background: #fff8e1; }}
    tr.grp td {{ background: #f3f6fb; border-top: 2px solid #dfe6f1; }}
    td.x {{ font-family: Menlo, Consolas, monospace; font-size: 11.5px; color: #666; white-space: nowrap; }}
    td.act {{ min-width: 180px; }}
    td.rt {{ white-space: nowrap; }}
    td.cp {{ min-width: 160px; }}
    td.fcs {{ min-width: 360px; max-width: 640px; font-size: 12px; }}
    td.sp {{ min-width: 170px; font-size: 12px; }}
    .ctx {{ color: #777; font-size: 11.5px; margin-top: 2px; }}
    .dm {{ margin-top: 3px; font-weight: 600; }}
    .fc {{ margin-bottom: 3px; line-height: 1.45; }}
    .fc code, .ex code {{ font-size: 11px; color: #1F4788; }}
    .wh {{ color: #777; font-size: 11.5px; }}
    .kd {{ font-size: 10.5px; background: #eef3fb; color: #1F4788; border-radius: 8px; padding: 0 6px; white-space: nowrap; }}
    .kd-unset {{ background: #f1f1f1; color: #999; }}
    .tag {{ font-size: 10.5px; background: #f1f1f1; color: #555; border-radius: 8px; padding: 0 6px; }}
    .tag-amb {{ background: #fff3d6; color: #8a5a00; }}
    .tag-un {{ background: #fdecea; color: #a33; }}
    .ex {{ margin-top: 3px; }}
    .ob {{ margin-top: 3px; font-size: 11px; color: #8a5a00; }}
    .hs {{ font-size: 10.5px; border-radius: 8px; padding: 0 6px; }}
    .hs-strong {{ background: #e2f4f2; color: #0f6a63; }}
    .hs-weak {{ border: 1px dashed #c58a00; color: #8a5a00; }}
    .lv {{ border-radius: 9px; padding: 1px 8px; white-space: nowrap; font-size: 11.5px; }}
    .lv-ok {{ background: #e2f4f2; color: #0f6a63; font-weight: 600; }}
    .lv-part {{ background: #fff3d6; color: #8a5a00; }}
    .lv-open {{ background: #fff; border: 1px dashed #999; color: #777; }}
    .s {{ border-radius: 9px; padding: 1px 8px; white-space: nowrap; font-size: 11.5px; }}
    .s-routed {{ background: #e2f4f2; color: #0f6a63; font-weight: 600; }}
    .s-open {{ background: #fff3d6; color: #8a5a00; }}
    .s-weak {{ background: #fff; border: 1px dashed #c58a00; color: #8a5a00; }}
    .s-not-routed {{ background: #fff; border: 1px dashed #999; color: #777; }}
    table.sub {{ width: auto; font-size: 12px; }}
    table.sub td, table.sub th {{ padding: 2px 8px 2px 0; border-bottom: 1px solid #f2f2f2; }}
    .ns {{ color: #999; }}
    .ctl {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .ctl input, .ctl select {{ font-size: 12px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }}
    .ctl input {{ flex: 1; min-width: 180px; }}
    #n {{ color: #666; font-size: 12px; align-self: center; margin-left: auto; }}
    @media (max-width: 700px) {{ body {{ padding: 10px; }} }}
</style>
</head>
<body>
{nav}
<header>
<h1>{esc(protocol_id)} — test identity</h1>
{_summary(d)}
<div class="meta">Rules {esc(d["rules_version"])} · word lists {esc(d["word_lists_date"])} · cdisc-for-ai <code>{esc(cdisc["commit"][:7])}</code> ·
<a href="{esc(src.name)}">JSON</a> · <a href="{routing_html}">activity routing</a> · <a href="{DOC_URL}">how test identity is read</a></div>
<div class="note">Test identity = test code + facets + specialization level. Kind and Position of a facet are our position
(cdisc-for-ai Variable_Meaning), not the IG's. The level reads identity facets only (system, method, scale); a facet the
protocol does not state stays open and is never filled. Nothing is decided on this page.</div>
<div class="note">Open, not coded (<a href="{OPEN_URL}">activity grain</a>, 2026-11-08): {open_list}. Rows with a hook in
the data are marked “open, not coded”; a group head not read is shown in its group header.</div>
</header>
<section>
<div class="ctl"><input id="q" type="search" placeholder="Search activity, code, facet, term…" aria-label="Search">
<select id="lf" aria-label="Level"><option value="">all levels</option>{level_opts}</select>
<select id="sf" aria-label="Routing status"><option value="">all routing statuses</option>{status_opts}</select>
<select id="ff" aria-label="Has"><option value="">any row</option>{flag_opts}</select><span id="n"></span></div>
</section>
{section("Standalone named tests", len(standalone), st_html)}
{section("Panel members", len(members), mb_html)}
{section("ECG activity rows", len(ecg), ecg_html,
         head='<thead><tr><th>row</th><th>activity</th><th>components</th><th>facets · conditions · unread</th></tr></thead>')}
<script>
  const q = document.getElementById('q'), lf = document.getElementById('lf'), sf = document.getElementById('sf'),
        ff = document.getElementById('ff'), n = document.getElementById('n');
  const rows = [...document.querySelectorAll('.tb tr:not([data-g])')], grps = [...document.querySelectorAll('.tb tr[data-g]')];
  function apply() {{
    const s = q.value.trim().toLowerCase(), l = lf.value, st = sf.value, f = ff.value; let k = 0;
    rows.forEach(r => {{ const on = (!l || r.dataset.l === l) && (!st || r.dataset.s === st)
                                   && (!f || r.dataset.f.split('|').includes(f))
                                   && (!s || r.textContent.toLowerCase().includes(s));
                        r.style.display = on ? '' : 'none'; k += on; }});
    grps.forEach(g => {{ let e = g.nextElementSibling, any = false;
                        while (e && !e.dataset.g) {{ if (e.style.display !== 'none') any = true; e = e.nextElementSibling; }}
                        g.style.display = any ? '' : 'none'; }});
    n.textContent = k + ' of ' + rows.length + ' rows';
  }}
  [q].forEach(e => e.addEventListener('input', apply)); [lf, sf, ff].forEach(e => e.addEventListener('change', apply)); apply();
</script>
</body>
</html>
"""
    return html


def render(protocol_id: str, collection: str) -> Path:
    out = page_path(protocol_id, collection)
    out.write_text(build_html(protocol_id, collection), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="Render the test identity page for one protocol.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", required=True)
    args = ap.parse_args()
    print(render(args.protocol, args.collection))


if __name__ == "__main__":
    main()
