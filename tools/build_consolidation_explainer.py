#!/usr/bin/env python3
"""Build the consolidation explainer page docs/consolidation.html.

One page, read top to bottom:
  1. where consolidation sits, with NCT04184622 as the running example,
  2. how the table type decides the route of a table,
  3. the three axes (rows matched, columns placed, notes deduplicated),
  4. how rows are matched (the four steps, the name score, a calculator),
  5. the match decisions sidecar (keep, split, merge, refines),
  6. what the consolidated file holds, and one row traced back to its page,
  7. the consolidated view, where a reviewer sees and decides the matches.

Everything the page states as a figure or an example is read here:
  - schema versions, ops, block descriptions and field paths from schemas/*.json
    (a field path that no longer exists stops the build),
  - the thresholds and the name score from soa2usdm/consolidate.py,
  - counts and examples from the consolidated files and sidecars of every
    collection under SOA2USDM_COLLECTIONS (default: ../soa2usdm-collections);
    a named example that is no longer there stops the build.
The screenshots in docs/img/consolidation-view-*.webp are static files.

Usage: python tools/build_consolidation_explainer.py
"""
import json
import os
import subprocess
import sys
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from soa2usdm.consolidate import (  # noqa: E402
    AUTO_MATCH_THRESHOLD, CROSS_PARENT_THRESHOLD, REVIEW_THRESHOLD, word_overlap_score,
    find_column_note_differences)

SCHEMAS = ROOT / "schemas"
OUT = ROOT / "docs"
BLOB = "https://github.com/kerfors/soa2usdm/blob/main/schemas/"
SITE = "https://kerfors.github.io/soa2usdm-collections/collections/"
COLLECTIONS = Path(os.environ.get("SOA2USDM_COLLECTIONS", ROOT.parent / "soa2usdm-collections")) / "collections"

FILES = {
    "extraction": "soa-table-extraction.schema.json",
    "resolved": "soa-table-resolved.schema.json",
    "consolidated": "soa-tables-consolidated.schema.json",
    "ccorr": "soa-consolidation-corrections.schema.json",
}

# The running example and the examples of each sidecar op: (protocol, correction id).
EXAMPLE = "NCT04184622"
EXAMPLE_XACT = "xact-012"
OP_EXAMPLES = {
    "keep": ("NCT04184622", "ccorr-001"),
    "keep_near": ("NCT04730349", "ccorr-003"),
    "merge": ("NCT03402841", "ccorr-003"),
    "refines": ("NCT03637764", "ccorr-001"),
    "refines_table": ("NCT03637764", "ccorr-003"),
}
DOMAIN_EXAMPLE = "NCT03283098"
VIEW_EXAMPLES = ["NCT04184622", "NCT04730349", "NCT04557384", "NCT03637764"]

TYPE_ORDER = ["main_soa", "continuation", "domain", "track", "subsidiary", "reference"]

CHECKS = [
    ("extraction", "table_metadata.table_type"), ("extraction", "activities[].source_page"),
    ("extraction", "activities[].row_position"),
    ("resolved", "activities[].activity_id"), ("resolved", "activities[].parent_activity_id"),
    ("resolved", "table_metadata.track_label"),
    ("ccorr", "corrections[].op"), ("ccorr", "corrections[].source.table_number"),
    ("ccorr", "corrections[].source.activity_id"), ("ccorr", "corrections[].source.activity_name"),
    ("ccorr", "corrections[].target.activity_id"),
    ("consolidated", "unified_activities[].xact_id"), ("consolidated", "unified_activities[].qualified_key"),
    ("consolidated", "unified_activities[].source_refs[].match_status"),
    ("consolidated", "unified_activities[].source_refs[].match_confidence"),
    ("consolidated", "unified_activities[].source_refs[].decision.correction_id"),
    ("consolidated", "unified_activities[].near_matches"),
    ("consolidated", "unified_activities[].refines"), ("consolidated", "unified_activities[].refined_by"),
    ("consolidated", "unified_activities[].name_variations"),
    ("consolidated", "timeline_segments{}[].segment"), ("consolidated", "timeline_segments{}[].population_track"),
    ("consolidated", "timeline_segments{}[].source_columns"),
    ("consolidated", "schedule_matrix[].source_values"),
    ("consolidated", "unified_annotations[].source_occurrences"),
    ("consolidated", "consolidation_metadata.review_stats"),
    ("consolidated", "consolidation_metadata.match_stats"),
    ("consolidated", "consolidation_metadata.source_tables[].refines"),
]

# Top-level blocks of the consolidated schema shown in part 6, with the construct colour.
BLOCKS = [
    ("consolidation_metadata", "other"), ("property_hierarchy", "properties"),
    ("unified_activities", "activities"), ("timeline_segments", "grid"),
    ("schedule_matrix", "schedule"), ("unified_annotations", "annotations"),
    ("review_items", "other"),
]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def deref(schema, node):
    while "$ref" in node:
        target = schema
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def child(schema, node, name):
    node = deref(schema, node)
    if name in node.get("properties", {}):
        return node["properties"][name]
    for comb in ("oneOf", "anyOf", "allOf"):
        for option in node.get(comb, []):
            found = child(schema, option, name)
            if found is not None:
                return found
    return None


def resolve(schema, path):
    """Return the schema node at path. 'a[]' steps into array items, 'a{}' into the values of a keyed object."""
    node = schema
    for token in path.split("."):
        name = token.replace("[]", "").replace("{}", "")
        node = child(schema, node, name)
        if node is None:
            raise KeyError(f"{schema['title']}: no field '{name}' in path '{path}'")
        if "{}" in token:
            node = deref(schema, node)["additionalProperties"]
        if "[]" in token:
            node = deref(schema, node)["items"]
    target = dict(deref(schema, node))
    if "description" in node:
        target["description"] = node["description"]
    return target


def version(schema):
    prop = schema["properties"]["schema_version"]
    return prop["enum"][-1] if "enum" in prop else prop["const"]


def schema_link(key, schemas):
    name = FILES[key].replace(".schema.json", "")
    return f'<a href="{BLOB}{FILES[key]}">{escape(name)}</a> v{escape(version(schemas[key]))}'


def code(text, title=""):
    tip = f' title="{escape(title, quote=True)}"' if title else ""
    return f"<code{tip}>{escape(str(text))}</code>"


def num(n):
    return f"{n:,}"


def load_corpus():
    """Every consolidated protocol of every collection, with its sidecar when it has one."""
    corpus = {}
    for path in sorted(COLLECTIONS.glob("*/protocols/*/SoA2USDM/consolidated/*_consolidated.json")):
        data = load(path)
        pid = data["protocol_id"]
        if pid in corpus:
            raise ValueError(f"{pid} is consolidated in two collections")
        sidecar = path.with_name(f"{pid}_consolidation_corrections.json")
        corpus[pid] = {
            "collection": path.parts[-6],
            "dir": path.parent.parent,
            "data": data,
            "sidecar": load(sidecar) if sidecar.exists() else None,
        }
    if not corpus:
        raise FileNotFoundError(f"no consolidated files under {COLLECTIONS}")
    return corpus


def collections_commit():
    out = subprocess.run(["git", "-C", str(COLLECTIONS.parent), "log", "-1", "--format=%h %cs"],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def page_url(pid, corpus):
    entry = corpus[pid]
    return f'{SITE}{entry["collection"]}/protocols/{pid}/SoA2USDM/consolidated/{pid}_consolidated.html'


def entry_of(corpus, pid, cid):
    sidecar = corpus[pid]["sidecar"]
    if sidecar is None:
        raise KeyError(f"{pid} has no consolidation corrections sidecar")
    hits = [c for c in sidecar["corrections"] if c["id"] == cid]
    if len(hits) != 1:
        raise KeyError(f"{pid} {cid}: not in the sidecar")
    return hits[0]


def corpus_figures(corpus):
    types = Counter()
    type_protocols = {t: [] for t in TYPE_ORDER}
    match = Counter()
    review = Counter()
    ops = Counter()
    segments = Counter()
    cells = multi_cells = 0
    single = 0
    src_rows = unified = 0
    for pid, entry in corpus.items():
        meta = entry["data"]["consolidation_metadata"]
        tables = meta["source_tables"]
        if len(tables) == 1:
            single += 1
        for t in tables:
            if t["table_type"] not in type_protocols:
                raise ValueError(f"{pid}: unknown table_type {t['table_type']}")
            types[t["table_type"]] += 1
            if pid not in type_protocols[t["table_type"]]:
                type_protocols[t["table_type"]].append(pid)
        match.update(meta["match_stats"])
        review.update(meta["review_stats"])
        src_rows += meta["source_activity_count"]
        unified += meta["unified_activity_count"]
        types_here = {t["table_num"]: t["table_type"] for t in tables}
        for seg, cols in entry["data"]["timeline_segments"].items():
            segments[seg] += len(cols)
            for c in cols:
                first, *rest = c["source_columns"]
                if (types_here[first["table_num"]] in ("domain", "continuation")
                        or any(types_here[sc["table_num"]] not in ("domain", "continuation") for sc in rest)):
                    raise ValueError(f"{pid} {c['xcol_id']}: part 3 says only domain and continuation "
                                     "columns join a main column")
        cells += len(entry["data"]["schedule_matrix"])
        multi_cells += sum(1 for c in entry["data"]["schedule_matrix"] if len(c["source_values"]) > 1)
        if entry["sidecar"]:
            ops.update(c["op"] for c in entry["sidecar"]["corrections"])
    if multi_cells:
        raise ValueError("a matrix cell has more than one source table; part 3 says none in the published collections")
    return {
        "protocols": len(corpus), "tables": sum(types.values()), "types": types,
        "type_protocols": type_protocols, "single": single, "match": match, "review": review,
        "ops": ops, "segments": segments, "cells": cells, "src_rows": src_rows, "unified": unified,
        "sidecars": sum(1 for e in corpus.values() if e["sidecar"]),
    }


def review_matches(corpus):
    """The matches a reviewer can decide, as the consolidated files record them:
    every source row merged on a fuzzy score or by a decision, and every near match."""
    out = []
    for pid, entry in corpus.items():
        data = entry["data"]
        by_xact = {u["xact_id"]: u for u in data["unified_activities"]}
        decisions = {c["id"]: c for c in (entry["sidecar"] or {"corrections": []})["corrections"]}
        for ua in data["unified_activities"]:
            base_name = ua["name_variations"][0]
            for ref in ua["source_refs"]:
                if "fuzzy" not in ref["match_status"] and "decision" not in ref:
                    continue
                if ref["match_status"] == "new":
                    continue  # a split row; none in the corpus, and nothing to score
                row_name = name_in_table(entry, ref["table_num"], ref["activity_id"])
                out.append(match_record(pid, ref["match_status"], row_name, base_name,
                                        ref["match_confidence"], ref.get("decision"), decisions))
            for hint in ua.get("near_matches", []):
                other = by_xact[hint["xact_id"]]
                out.append(match_record(pid, "near", ua["activity_name"], other["activity_name"],
                                        hint["score"], hint.get("decision"), decisions))
    return out


_row_names = {}


def name_in_table(entry, table_num, activity_id):
    key = (str(entry["dir"]), table_num)
    if key not in _row_names:
        files = list((entry["dir"] / "resolved").glob(f"*_Table_{table_num:02d}_resolved.json"))
        if len(files) != 1:
            raise FileNotFoundError(f"{entry['dir']}: resolved file of table {table_num}")
        _row_names[key] = {a["activity_id"]: a["activity_name"] for a in load(files[0])["activities"]}
    return _row_names[key][activity_id]


def match_record(pid, status, row, other, score, decision, decisions):
    rec = {"p": pid, "s": status, "a": row, "b": other, "f": round(score, 4),
           "py": round(word_overlap_score(row, other), 4)}
    if status != "decision" and abs(rec["py"] - rec["f"]) > 1e-3:
        raise ValueError(f"{pid}: score in file {rec['f']} differs from word_overlap_score {rec['py']} for '{row}' / '{other}'")
    if decision:
        entry = decisions[decision["correction_id"]]
        rec["d"] = f'{decision["correction_id"]} {decision["op"]}'
        rec["r"] = entry["reason"]
    return rec


def running_example(corpus):
    data = corpus[EXAMPLE]["data"]
    meta = data["consolidation_metadata"]
    tables = meta["source_tables"]
    if [t["table_type"] for t in tables] != ["main_soa", "track"]:
        raise ValueError(f"{EXAMPLE}: the page describes it as main_soa + track")
    t1, t2 = tables
    t2_status = Counter(r["match_status"] for u in data["unified_activities"]
                        for r in u["source_refs"] if r["table_num"] == 2)
    ann = meta["annotation_stats"]
    seg = {s: len(c) for s, c in data["timeline_segments"].items()}
    return {
        "EX_T1_TITLE": escape(t1["table_title"]), "EX_T2_TITLE": escape(t2["table_title"]),
        "EX_T2_TRACK": escape(t2["track_label"]),
        "EX_T1_ROWS": num(t1["activity_count"]), "EX_T2_ROWS": num(t2["activity_count"]),
        "EX_T1_COLS": num(t1["column_count"]), "EX_T2_COLS": num(t2["column_count"]),
        "EX_T1_NOTES": num(t1["annotation_count"]), "EX_T2_NOTES": num(t2["annotation_count"]),
        "EX_ACTS": num(meta["unified_activity_count"]),
        "EX_T2_MATCHED": num(t2["activity_count"] - t2_status["new"]), "EX_T2_NEW": num(t2_status["new"]),
        "EX_EXACT": num(t2_status["exact"]), "EX_FUZZY": num(t2_status["fuzzy_auto"]),
        "EX_CROSS": num(t2_status["fuzzy_cross_parent"]),
        "EX_COLS": num(sum(seg.values())), "EX_MAIN_COLS": num(seg["main"]), "EX_TRACK_COLS": num(seg["track"]),
        "EX_NOTES": num(ann["unified_annotation_count"]), "EX_NOTES_DEDUP": num(ann["deduplicated_count"]),
        "EX_URL": page_url(EXAMPLE, corpus),
        "EX_PID": EXAMPLE,
    }


def trace_example(corpus):
    """One unified activity traced back to the printed page."""
    entry = corpus[EXAMPLE]
    ua = [u for u in entry["data"]["unified_activities"] if u["xact_id"] == EXAMPLE_XACT][0]
    ref = [r for r in ua["source_refs"] if r["table_num"] == 2][0]
    resolved = load(next((entry["dir"] / "resolved").glob("*_Table_02_resolved.json")))
    act = [a for a in resolved["activities"] if a["activity_id"] == ref["activity_id"]][0]
    ext_dir = entry["dir"] / "extracted"
    verified = list(ext_dir.glob("*_Table_02_extraction.verified.json"))
    extraction = load(verified[0] if verified else next(ext_dir.glob("*_Table_02_extraction.json")))
    row = [a for a in extraction["activities"] if a["row_position"] == act["row_position"]][0]
    if row["activity_name"] != act["activity_name"]:
        raise ValueError(f"{EXAMPLE}: trace row name differs between extraction and resolved")
    dec = ref["decision"]
    return {
        "TR_XACT": escape(ua["xact_id"]), "TR_NAME": escape(ua["activity_name"]),
        "TR_ROW_NAME": escape(act["activity_name"]), "TR_ACT": escape(act["activity_id"]),
        "TR_STATUS": escape(ref["match_status"]), "TR_SCORE": f'{ref["match_confidence"]:.2f}',
        "TR_DEC": escape(f'{dec["correction_id"]} {dec["op"]}'),
        "TR_ROWPOS": str(row["row_position"]), "TR_PAGE": str(row["source_page"]),
        "TR_FILE_X": escape(verified[0].name if verified else "extraction.json"),
    }


def op_examples(corpus):
    out = {}
    for key, (pid, cid) in OP_EXAMPLES.items():
        c = entry_of(corpus, pid, cid)
        expected = key.split("_")[0]
        if c["op"] != expected:
            raise ValueError(f"{pid} {cid}: op is {c['op']}, the page shows it as {expected}")
        src, tgt = c["source"], c["target"]
        out[f"OPX_{key.upper()}"] = (
            f'<div class="ex"><span class="pid">{escape(pid)} {escape(cid)}</span>'
            f'<div><span class="t">T{src["table_number"]}</span> '
            f'{escape(src.get("activity_name", "the whole table"))}</div>'
            f'<div><span class="t">T{tgt["table_number"]}</span> {escape(tgt["activity_name"])}</div>'
            f'<div class="why">{escape(c["reason"])}</div></div>')
    pid, cid = OP_EXAMPLES["merge"]
    entry = dict(entry_of(corpus, pid, cid))
    out["OP_JSON"] = escape(json.dumps(entry, indent=2, ensure_ascii=False))
    out["OP_JSON_FILE"] = escape(f"{pid}_consolidation_corrections.json")
    return out


def type_cards(fig):
    text = {
        "main_soa": ("The primary activity &times; timepoint grid. A protocol can have several, e.g. one per study period that every participant passes through.",
                     "The lowest-numbered main_soa is the <b>base</b>: its rows become the first activities and are never matched. A further main_soa is matched against them.",
                     "Segment <code>main</code>."),
        "continuation": ("The same table carried on under its own number or caption: same columns, the rows continue.",
                         "Matched.", "Joins the main columns it repeats: compared value by value with each main_soa table; exactly one must match, or consolidation stops."),
        "domain": ("Same columns, same participants, another category of activities (e.g. a laboratory table next to a non-laboratory table).",
                   "Matched.", "Joins the main columns it repeats, as a continuation does. Segment <code>main</code>; no columns of its own."),
        "track": ("A branch only some participants take: a cohort, responders vs non-responders, a later phase entered on a condition.",
                  "Matched.", "Segment <code>track</code>, each column with a <code>population_track</code>: the table's track_label, else read from its purpose or title, else <code>Track-T&lt;n&gt;</code>."),
        "subsidiary": ("Finer timing for a subset of activities, e.g. hour-by-hour PK sampling for days of the main table.",
                       "Matched.", "Segment <code>subsidiary</code>."),
        "reference": ("Rows that are not activities: sample specifications, timing parameters, abbreviations.",
                      "Not consolidated: no activities.", "Not consolidated: no columns. A match decision may not name the table."),
    }
    out = []
    for t in TYPE_ORDER:
        printed, rows, cols = text[t]
        n = fig["types"][t]
        pids = fig["type_protocols"][t]
        where = (f'{n} table{"s" if n != 1 else ""} in {len(pids)} protocol{"s" if len(pids) != 1 else ""}'
                 if n else "none in the published collections")
        out.append(
            f'<div class="tt{" off" if t == "reference" else ""}"><div class="tt-h"><code>{t}</code><span class="cnt">{where}</span></div>'
            f'<p class="pr">{printed}</p>'
            f'<div class="rc"><span class="lbl c-activities">rows</span><span>{rows}</span></div>'
            f'<div class="rc"><span class="lbl c-grid">columns</span><span>{cols}</span></div></div>')
    return "\n".join(out)


def block_list(schemas):
    schema = schemas["consolidated"]
    out = []
    for name, construct in BLOCKS:
        desc = schema["properties"][name]["description"]
        out.append(f'<div class="blk-row c-{construct}"><code>{escape(name)}</code><span>{escape(desc)}</span></div>')
    return "\n".join(out)


def main():
    schemas = {key: load(SCHEMAS / name) for key, name in FILES.items()}
    for key, path in CHECKS:
        resolve(schemas[key], path)
    ops = resolve(schemas["ccorr"], "corrections[].op")["enum"]
    if ops != ["keep", "split", "merge", "refines"]:
        raise ValueError(f"the page describes the ops keep, split, merge, refines; the schema has {ops}")

    corpus = load_corpus()
    fig = corpus_figures(corpus)
    matches = review_matches(corpus)
    if len(matches) != fig["review"]["total"]:
        raise ValueError(f"{len(matches)} review matches listed, review_stats total is {fig['review']['total']}")
    domain = corpus[DOMAIN_EXAMPLE]["data"]
    dom_types = {t["table_num"]: t["table_type"] for t in domain["consolidation_metadata"]["source_tables"]}
    dom_tables = sorted(n for n, t in dom_types.items() if t == "domain")
    if list(domain["timeline_segments"]) != ["main"] or len(dom_tables) != 2:
        raise ValueError(f"{DOMAIN_EXAMPLE}: the page describes one main segment and two domain tables")
    dom_main = len(domain["timeline_segments"]["main"])
    dom_joined = sum(len(c["source_columns"]) - 1 for c in domain["timeline_segments"]["main"])
    dom_warn = len(find_column_note_differences(domain))

    parts = {
        "CONS_SCHEMA": schema_link("consolidated", schemas),
        "RES_SCHEMA": schema_link("resolved", schemas),
        "CCORR_SCHEMA": schema_link("ccorr", schemas),
        "AUTO": f"{AUTO_MATCH_THRESHOLD:.2f}", "CROSS": f"{CROSS_PARENT_THRESHOLD:.2f}",
        "REVIEW": f"{REVIEW_THRESHOLD:.2f}",
        "N_PROTOCOLS": num(fig["protocols"]), "N_TABLES": num(fig["tables"]), "N_SINGLE": num(fig["single"]),
        "N_CELLS": num(fig["cells"]),
        "M_EXACT": num(fig["match"]["exact"]), "M_FUZZY": num(fig["match"]["fuzzy_auto"]),
        "M_CROSS": num(fig["match"]["fuzzy_cross_parent"]), "M_DECISION": num(fig["match"]["decision"]),
        "R_TOTAL": num(fig["review"]["total"]), "R_DECIDED": num(fig["review"]["decided"]),
        "R_OPEN": num(fig["review"]["open"]), "R_NEAR": num(fig["review"]["near_matches"]),
        "N_SIDECARS": num(fig["sidecars"]),
        "OPS_KEEP": num(fig["ops"]["keep"]), "OPS_SPLIT": num(fig["ops"]["split"]),
        "OPS_MERGE": num(fig["ops"]["merge"]), "OPS_REFINES": num(fig["ops"]["refines"]),
        "DOM_PID": DOMAIN_EXAMPLE, "DOM_MAIN": num(dom_main), "DOM_JOINED": num(dom_joined),
        "DOM_TABLES": " and ".join(str(n) for n in dom_tables), "DOM_WARN": num(dom_warn),
        "TYPE_CARDS": type_cards(fig),
        "BLOCKS": block_list(schemas),
        "MATCHES_JSON": json.dumps(matches, ensure_ascii=False).replace("</", "<\\/"),
        "VIEW_LINKS": " &middot; ".join(f'<a href="{page_url(p, corpus)}">{p}</a>' for p in VIEW_EXAMPLES),
        "URL_MATCHES": page_url("NCT04730349", corpus),
        "COMMIT": escape(collections_commit()),
    }
    parts.update(running_example(corpus))
    parts.update(trace_example(corpus))
    parts.update(op_examples(corpus))

    html = (Path(__file__).parent / "explainer_consolidation.template.html").read_text(encoding="utf-8")
    for key, value in parts.items():
        token = "{{" + key + "}}"
        if token not in html:
            raise KeyError(f"template has no placeholder {token}")
        html = html.replace(token, value)
    if "{{" in html:
        left = html[html.index("{{"):html.index("{{") + 40]
        raise KeyError(f"template placeholder not filled: {left}")
    OUT.mkdir(exist_ok=True)
    target = OUT / "consolidation.html"
    target.write_text(html, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} ({len(html):,} bytes) from {fig['protocols']} protocols")


if __name__ == "__main__":
    main()
