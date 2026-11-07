"""
Cross-study consistency check (C) — the same phrase, a different routing outcome, a review queue.

Mechanical: it decides nothing. Every SoA activity of every study with a grain file is one item
(section headers left out), keyed by its grain phrase (the Codelist_Phrases normalisation); every
panel member row of the routing file is one item too, keyed by normalise(member text). A phrase met
in two or more studies whose items do not all have the same outcome goes into the queue.

The outcome is what changes routing, not the grain or the finding kind (reflection 2026-11-07,
§2.5.1):

    routed       (routed, domain)
    open, weak   (status, candidate domains) — the candidates are the open question
    not routed   (not routed) — its candidates come only from the grain-kind fallback
    no own row   every activity without a routing row of its own: grain other, procedure,
                 instrument, sample collection, unsure, every panel (its members are items of
                 their own), and a named-test parent

Phrases are compared exactly; near phrases ("body weight", "weight") are not joined. Standalone
items and panel members of the same phrase are compared in one group; every count is split.

Also listed: phrases with different outcomes inside one study, and the flags kept by hand in
collections/consistency_flags.json (each flag names a phrase and the studies it was raised for;
every item with that phrase is shown).

Reads the published grain, grain decisions and routing files; a routing file not made from the
grain file now on disk stops the run. Writes collections/consistency_queue.json and .html. Run after
activity_routing, before the collections index:

  python -m soa2usdm.consistency
"""

import hashlib
import html as html_lib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .activity_grain import normalise
from .nav import NAV_CSS

SCHEMA_NAME = "soa2usdm-consistency-queue"
SCHEMA_VERSION = "1.0"
CHECK_VERSION = "1.0.0"
FLAGS_SCHEMA_NAME = "soa2usdm-consistency-flags"
DOC_URL = "https://github.com/kerfors/soa2usdm/blob/main/soa2usdm/consistency.py"

NO_OWN_ROW = "no own row"
OUTCOME_STATUSES = ("routed", "open", "weak", "not routed", NO_OWN_ROW)


def queue_paths() -> tuple:
    root = config.COLLECTIONS_ROOT
    return root / "consistency_queue.json", root / "consistency_queue.html"


def flags_path() -> Path:
    return config.COLLECTIONS_ROOT / "consistency_flags.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome(row: dict | None) -> dict:
    """The routing outcome of an item: its own routing row, or None for no own row."""
    if row is None:
        return {"status": NO_OWN_ROW, "domain": None, "candidates": []}
    st = row["status"]
    if st == "routed":
        return {"status": st, "domain": row["domain"], "candidates": []}
    if st in ("open", "weak"):
        return {"status": st, "domain": None, "candidates": sorted(row["candidates"] or [])}
    if st == "not routed":
        return {"status": st, "domain": None, "candidates": []}
    raise ValueError(f"unknown routing status {st!r}")


def outcome_key(o: dict) -> tuple:
    return (o["status"], o["domain"], tuple(o["candidates"]))


def outcome_label(o: dict) -> str:
    if o["status"] == "routed":
        return f"routed {o['domain']}"
    if o["candidates"]:
        return f"{o['status']} {'|'.join(o['candidates'])}"
    return o["status"]


def study_items(collection: str, grain: dict, routing: dict, decisions: dict | None) -> list:
    """One item per non-header activity and one per panel member row of one study."""
    pid = grain["protocol_id"]
    if routing["protocol_id"] != pid:
        raise ValueError(f"{collection}/{pid}: routing file is for {routing['protocol_id']}")
    prompts = {d["phrase"]: d["prompt_version"] for d in (decisions or {}).get("decisions", [])}
    acts = {a["xact_id"]: a for a in grain["activities"]}
    own, members = {}, []
    for r in routing["rows"]:
        if "member_id" in r:
            members.append(r)
            continue
        a = acts[r["xact_id"]]
        if a["grain"] != "named test" or r["xact_id"] in own:
            raise ValueError(f"{collection}/{pid} {r['xact_id']}: own routing row for grain {a['grain']!r}")
        own[r["xact_id"]] = r
    not_reached = {n["xact_id"]: n["reason"] for n in routing["not_reached"]}

    def base(unit, phrase, activity_name, xact_id, a):
        return {"collection": collection, "protocol_id": pid, "unit": unit, "phrase": phrase,
                "activity_name": activity_name, "xact_id": xact_id, "member_id": None, "panel_name": None, "members_from": None,
                "grain": a["grain"], "grain_source": a["source"],
                "prompt_version": prompts.get(a["phrase"]) if a["source"] == "ai_proposed" else None}

    items = []
    for x, a in acts.items():
        if a["role"] == "section header":
            continue
        it = base("standalone", a["phrase"], a["activity_name"], x, a)
        r = own.get(x)
        if r is not None:
            it |= {"route_source": r["route_source"], "reach": None}
        elif x in not_reached:
            it |= {"route_source": None, "reach": not_reached[x]}
        elif a["grain"] == "named test":
            raise ValueError(f"{collection}/{pid} {x}: named test with no routing row and not listed as not reached")
        else:
            it |= {"route_source": None, "reach": f"grain {a['grain']}"}
        it["outcome"] = outcome(r)
        items.append(it)
    for r in members:
        a = acts[r["xact_id"]]
        it = base("member", normalise(r["activity_name"]), r["activity_name"], r["xact_id"], a)
        it |= {"member_id": r["member_id"], "panel_name": r["panel_name"],
               "grain": r["grain"]["grain"], "grain_source": r["grain"]["source"],
               "members_from": r.get("members_from", "label"),
               "route_source": r["route_source"], "reach": None, "outcome": outcome(r)}
        items.append(it)
    return items


def load_study(collection: str, protocol_id: str) -> tuple:
    """(items, inputs entry) of one study from its published files; stale routing stops."""
    soa = config.get_soa2usdm_folder(protocol_id, collection)
    gp = soa / "grain" / f"{protocol_id}_activity_grain.json"
    dp = soa / "grain" / f"{protocol_id}_activity_grain_decisions.json"
    rp = soa / "routing" / f"{protocol_id}_activity_routing.json"
    if not rp.exists():
        raise FileNotFoundError(f"{collection}/{protocol_id}: grain file without routing file; "
                                f"run python -m soa2usdm.activity_routing --collection {collection} "
                                f"--protocol {protocol_id}")
    routing = json.loads(rp.read_text())
    g_sha = _sha256(gp)
    if routing["inputs"]["activity_grain"]["sha256"] != g_sha:
        raise RuntimeError(f"{collection}/{protocol_id}: routing file made from another grain file; "
                           f"rerun python -m soa2usdm.activity_routing --collection {collection} "
                           f"--protocol {protocol_id}")
    decisions = json.loads(dp.read_text()) if dp.exists() else None
    items = study_items(collection, json.loads(gp.read_text()), routing, decisions)
    entry = {"collection": collection, "protocol_id": protocol_id, "grain_sha256": g_sha,
             "decisions_sha256": _sha256(dp) if dp.exists() else None, "routing_sha256": _sha256(rp)}
    return items, entry


def study_ids() -> list:
    """(collection, protocol_id) of every study with a grain file, all collections."""
    out = []
    for coll in sorted(c for c in config.COLLECTIONS if c != "fixtures"):
        for gp in sorted(config.get_collection_path(coll).glob("*/SoA2USDM/grain/*_activity_grain.json")):
            out.append((coll, gp.name[:-len("_activity_grain.json")]))
    if not out:
        raise FileNotFoundError(f"no grain files under {config.COLLECTIONS_ROOT}")
    return out


def _split(items: list) -> dict:
    return {"standalone": sum(1 for i in items if i["unit"] == "standalone"),
            "member": sum(1 for i in items if i["unit"] == "member")}


def _group(phrase: str, items: list) -> dict:
    by = defaultdict(list)
    for i in items:
        by[outcome_key(i["outcome"])].append(i)
    outcomes = [{"outcome": v[0]["outcome"], "studies": len({(i["collection"], i["protocol_id"]) for i in v}),
                 "items": _split(v)} for k, v in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    order = {outcome_key(o["outcome"]): n for n, o in enumerate(outcomes)}
    return {"phrase": phrase, "studies": len({(i["collection"], i["protocol_id"]) for i in items}),
            "items_count": _split(items), "outcomes": outcomes,
            "items": sorted(items, key=lambda i: (order[outcome_key(i["outcome"])], i["unit"],
                                                  i["collection"], i["protocol_id"], i["xact_id"],
                                                  i["member_id"] or ""))}


def check_flags(flags: dict, items: list) -> list:
    if flags["schema_name"] != FLAGS_SCHEMA_NAME:
        raise ValueError(f"flags file schema_name {flags['schema_name']!r}, expected {FLAGS_SCHEMA_NAME!r}")
    by_phrase = defaultdict(list)
    for i in items:
        by_phrase[i["phrase"]].append(i)
    out = []
    for f in flags["flags"]:
        if f["phrase"] != normalise(f["phrase"]):
            raise ValueError(f"flag phrase {f['phrase']!r} is not normalised")
        have = {(i["collection"], i["protocol_id"]) for i in by_phrase[f["phrase"]]}
        for s in f["studies"]:
            if (s["collection"], s["protocol_id"]) not in have:
                raise ValueError(f"flag {f['phrase']!r}: no item with this phrase in "
                                 f"{s['collection']}/{s['protocol_id']}")
        out.append({"phrase": f["phrase"], "studies": f["studies"], "note": f["note"],
                    "raised_in": f["raised_in"], "group": _group(f["phrase"], by_phrase[f["phrase"]])})
    return out


def build_queue(items: list, flags: dict) -> dict:
    """Cross-study queue, within-study differences, flags and counts — no inputs, no timestamp."""
    by_phrase = defaultdict(list)
    for i in items:
        by_phrase[i["phrase"]].append(i)
    multi = {p: v for p, v in by_phrase.items() if len({(i["collection"], i["protocol_id"]) for i in v}) >= 2}
    queue = [_group(p, v) for p, v in multi.items() if len({outcome_key(i["outcome"]) for i in v}) > 1]
    queue.sort(key=lambda g: (-g["studies"], g["phrase"]))
    by_study = defaultdict(list)
    for i in items:
        by_study[(i["collection"], i["protocol_id"], i["phrase"])].append(i)
    within = [{"collection": c, "protocol_id": p} | _group(ph, v) for (c, p, ph), v in sorted(by_study.items())
              if len({outcome_key(i["outcome"]) for i in v}) > 1]
    for w in within:
        del w["studies"]
    flagged = check_flags(flags, items)
    return {
        "counts": {
            "studies": len({(i["collection"], i["protocol_id"]) for i in items}),
            "items": _split(items),
            "phrases_in_two_or_more_studies": len(multi),
            "items_in_those_phrases": _split([i for v in multi.values() for i in v]),
            "queue_phrases": len(queue),
            "queue_items": _split([i for g in queue for i in g["items"]]),
            "within_study": len(within),
            "flags": len(flagged),
        },
        "queue": queue,
        "within_study": within,
        "flags": flagged,
    }


def generate() -> dict:
    items, inputs = [], []
    for coll, pid in study_ids():
        its, entry = load_study(coll, pid)
        items += its
        inputs.append(entry)
    fp = flags_path()
    flags = json.loads(fp.read_text())
    return {"schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION, "check_version": CHECK_VERSION,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "inputs": {"studies": inputs, "flags_sha256": _sha256(fp)}} | build_queue(items, flags)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def esc(v) -> str:
    return html_lib.escape(str(v).translate(config.SYMBOL_FONT)) if v is not None else ""


def _href(i: dict, kind: str) -> str:
    pid = i["protocol_id"]
    anchor = i["xact_id"] + (f".{i['member_id']}" if kind == "routing" and i["member_id"] else "")
    return f"{i['collection']}/protocols/{pid}/SoA2USDM/{kind}/{pid}_activity_{kind}.html#{anchor}"


def _item_rows(items: list) -> str:
    rows, prev = [], None
    for i in items:
        o = outcome_label(i["outcome"])
        first = o != prev
        prev = o
        grain = esc(i["grain"]) + f'<span class="ns sub">{esc(i["grain_source"])}'
        grain += (f' · prompt {esc(i["prompt_version"])}' if i["prompt_version"] else "") + "</span>"
        how = esc(i["route_source"]) if i["route_source"] else f'<span class="ns">{esc(i["reach"])}</span>'
        label = f'<a href="{_href(i, "grain")}">{esc(i["activity_name"])}</a>'
        if i["unit"] == "member":
            label += (f'<span class="ns sub">member of {esc(i["panel_name"])} '
                      f'(from {esc(i["members_from"])})</span>')
        own = (f'<a href="{_href(i, "routing")}">{esc(o)}</a>' if i["outcome"]["status"] != NO_OWN_ROW
               else esc(o))
        rows.append(f'<tr class="{"first" if first else ""}"><td class="oc">{own if first else ""}</td>'
                    f'<td>{esc(i["collection"])}</td><td>{esc(i["protocol_id"])}</td>'
                    f'<td>{esc(i["unit"])}</td><td>{label}</td><td>{grain}</td><td>{how}</td></tr>')
    return "".join(rows)


def _split_txt(s: dict) -> str:
    return f'{s["standalone"]} standalone · {s["member"]} members'


def _group_block(g: dict, title: str, extra: str = "") -> str:
    outs = "; ".join(f'{esc(outcome_label(o["outcome"]))} ({_split_txt(o["items"])})' for o in g["outcomes"])
    return (f'<section class="grp" id="{esc(title)}"><h3>{esc(g["phrase"])}{extra}</h3>'
            f'<p class="ns">{outs}</p>{_TABLE_HEAD}{_item_rows(g["items"])}</tbody></table></section>')


_TABLE_HEAD = ('<table><thead><tr><th>outcome</th><th>collection</th><th>study</th><th>item</th>'
               '<th>activity / member</th><th>grain</th><th>route source / why no own row</th></tr></thead><tbody>')


def render(q: dict) -> str:
    c = q["counts"]
    queue = "".join(_group_block(g, "q-" + g["phrase"], f' <span class="ns">· {g["studies"]} studies</span>')
                    for g in q["queue"]) or '<p class="ns">None.</p>'
    within = "".join(_group_block(w, f'w-{w["protocol_id"]}-{w["phrase"]}',
                                  f' <span class="ns">· {esc(w["collection"])} / {esc(w["protocol_id"])}</span>')
                     for w in q["within_study"]) or '<p class="ns">None.</p>'
    flags = "".join(
        _group_block(f["group"], "f-" + f["phrase"],
                     f' <span class="ns">· raised for '
                     f'{esc(", ".join(s["protocol_id"] for s in f["studies"]))}</span>')
        .replace("</h3>", f'</h3><p class="note">{esc(f["note"])} <span class="ns">({esc(f["raised_in"])})</span></p>', 1)
        for f in q["flags"]) or '<p class="ns">None.</p>'
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Consistency queue · all collections</title>
<style>
{NAV_CSS}
  body {{ margin:0; padding:18px 22px; background:#f5f7fa; color:#1f2933;
         font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
  h1 {{ font-size:20px; margin:4px 0 6px; }}
  h2 {{ font-size:15px; margin:22px 0 6px; }}
  h3 {{ font-size:14px; margin:0 0 2px; }}
  a {{ color:#2E75B6; text-decoration:none; }} a:hover {{ text-decoration:underline; }}
  .ns {{ color:#5f6b7a; }} .sub {{ display:block; font-size:11px; }}
  .box, .grp {{ background:#fff; border:1px solid #d9dee5; border-radius:6px; padding:10px 14px; margin:0 0 10px; }}
  .note {{ margin:2px 0 6px; }}
  table {{ border-collapse:collapse; width:100%; margin-top:6px; }}
  th, td {{ text-align:left; vertical-align:top; padding:3px 8px; border-bottom:1px solid #eef1f4; }}
  th {{ font-size:11px; color:#5f6b7a; font-weight:600; }}
  tr.first td {{ border-top:1px solid #c9d1db; }}
  td.oc {{ font-weight:600; white-space:nowrap; }}
  .counts td {{ border:0; padding:1px 10px 1px 0; }}
  .wrap {{ overflow-x:auto; }}
</style>
</head>
<body>
<nav class="pnav" aria-label="Breadcrumb"><div class="pnav-crumb"><a href="../index.html">Collections</a><span class="pnav-sep">›</span><span class="pnav-cur">consistency queue</span></div></nav>
<h1>Cross-study consistency queue</h1>
<div class="box">
<p>The same phrase in two or more studies with a different routing outcome. Mechanical: the queue decides
nothing. The outcome is what changes routing — routed and domain; open or weak and the candidate domains;
not routed; no row of its own (grain other, procedure, instrument, sample collection, unsure, a panel, a
named-test parent). Grain and finding kind are shown, not compared. Phrases are compared exactly after
normalisation; standalone activities and panel members of one phrase are compared together.
<a href="{DOC_URL}">How it works</a>.</p>
<table class="counts">
<tr><td>studies</td><td><b>{c["studies"]}</b></td><td>items</td><td>{_split_txt(c["items"])}</td></tr>
<tr><td>phrases in ≥2 studies</td><td><b>{c["phrases_in_two_or_more_studies"]}</b></td><td>their items</td><td>{_split_txt(c["items_in_those_phrases"])}</td></tr>
<tr><td>queue phrases</td><td><b>{c["queue_phrases"]}</b></td><td>their items</td><td>{_split_txt(c["queue_items"])}</td></tr>
<tr><td>within one study</td><td><b>{c["within_study"]}</b></td><td>flags</td><td><b>{c["flags"]}</b></td></tr>
</table>
</div>
<h2>Same phrase, different outcome across studies</h2>
<div class="wrap">{queue}</div>
<h2>Same phrase, different outcome within one study</h2>
<div class="wrap">{within}</div>
<h2>Flags kept by hand</h2>
<p class="ns">From <code>collections/consistency_flags.json</code>: every item with the flagged phrase.</p>
<div class="wrap">{flags}</div>
<p class="ns">Generated {esc(q["generated_at"])} by <code>soa2usdm.consistency</code> {esc(q["check_version"])}
from {len(q["inputs"]["studies"])} studies' grain, grain decisions and routing files.</p>
</body>
</html>
'''


def write() -> tuple:
    q = generate()
    jp, hp = queue_paths()
    jp.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    hp.write_text(render(q), encoding="utf-8")
    return jp, hp


def main():
    for p in write():
        print(p)


if __name__ == "__main__":
    main()
