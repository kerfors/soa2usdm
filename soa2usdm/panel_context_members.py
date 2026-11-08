"""
SoA2USDM Panel Members from Protocol Context (per-study sidecar)

For a grain `panel` row whose label lists no members (routing: "panel, not split"), the members
are taken from the study's protocol context (context/<id>_protocol_context.json, panels[]): the
SoA panel names are linked to the context panels by a name rule, and the analytes of the linked
context panels become members, with the rules of the label members (grain rules 1.2.0).
Decisions D1-D8 of 2026-11-06; design: documents/activity-routing.md, "Panel members from
protocol context".

Name rule 1.0.0 (D1, no AI):
  - SoA label: parentheses that hold only lab codes (CL, LL) are dropped. The whole label, without
    its trailing parentheses, is tried first. When no context panel has that name, the label is
    split into panel names at ',', 'and', '&' outside parentheses (not at '/': 'CBC
    w/differential'); a trailing parenthesis that is not a qualifier gives panel names too
    ('Laboratory Safety Panels (Lipid Panel)').
  - Context panel name: its trailing parentheses (source notes such as '(SoA note)') are dropped.
  - Both sides: normalised as in the grain (activity_grain.normalise), 'haematology' read as
    'hematology', trailing generic words dropped (GENERIC_WORDS), spaces ignored in the comparison
    ('auto-antibodies' = 'autoantibodies'). A name links every context panel with the same key.
    No containment, no plural, no stemming.

Members (D2, D3): the analytes of all context panels linked to one SoA panel name, each read with the
analyte rules below and looked up with the label-member rules (activity_grain.label_members,
_member_lookup); the union by phrase, member ids c01, c02 ... per SoA row. Each member keeps its sources
(context panel, analyte). Where several context panels are linked to one name, the phrases found in only
one of them are listed as differences, not resolved.

Analyte rules 1.0.0 (step 4, 2026-11-08). An analyte is one entry of a context list, already split from
the lab table by the protocol context, so a comma inside it is mostly a qualifier, not a separator:
  A3  text before a colon is a group heading ('Absolute count of: Lymphocytes'): the heading is a
      member of its own ('from' analyte heading), the text after the colon is read with these rules,
      in the heading's group.
  A4  a trailing list parenthesis whose every item, read with the head's last word, is a CDISC test
      ('Cell morphology (RBC and WBC)' -> 'RBC morphology', 'WBC morphology', NCIt synonyms of
      RBCMORPH / WBCMORPH) gives those tests ('from' analyte parenthesis distributed), in the head's group.
  A1  an analyte whose whole text is a test (whole or compact, activity_grain Lookups.test_hit) is one
      member ('Neutrophils, segmented' = NEUTSG).
  A2  'X, Y' with one comma and one word after it that is not a test itself ('Bilirubin, direct'): Y is
      a qualifier. The inverted
      'Y X' is looked up first ('Direct Bilirubin', BILDIR); otherwise X is the member with Y (and any
      parenthesis after it) as its qualifiers ('Creatinine, enzymatic').
  A5  in a member of a list, text after ';' that starts with a qualifier cue is the member's qualifier
      ('NK cells; if the test is available at the site').
  A6  'and/or' is one separator (activity_grain.LIST_SEPARATORS, grain rules 1.3.0).
  A7  under one SoA panel name linked to several context panels, a named-test member whose hits give one
      code is merged with the member of another of those context panels that gives the same code
      ('AST (SGOT)' / 'AST'); its sources are joined.
Stated facets (D5): the specimen and lab of each source context panel, as stated, with the context
panel pointer and its evidence pages. Not used for routing.

The file exists only where protocol context exists (D4, D8); the grain file stays label-only.
Input: the study's grain file (checked current) and protocol context.
Output: SoA2USDM/panels/<id>_panel_context_members.json (schema soa2usdm-panel-context-members 1.0; 1.2: member
restated / abbreviation, grain rules 1.4.0 — members are read with the study's own abbreviations).
"""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .activity_grain import (LIST_INTRO, QUALIFIER_CUES, Lookups, _is_list, _member_lookup, context_path,
                             grain_path, label_members, load_current_grain, normalise, split_top,
                             split_trailing_parens)

SCHEMA_NAME = "soa2usdm-panel-context-members"
SCHEMA_VERSION = "1.2"
SCHEMA_VERSIONS = ("1.0", "1.1", "1.2")
NAME_RULE_VERSION = "1.0.0"
ANALYTE_RULE_VERSION = "1.0.0"
SPELLINGS = {"haematology": "hematology"}
GENERIC_WORDS = ("parameters", "tests", "test", "assessments", "assessment")
LAB_CODES = {"cl", "ll"}
NAME_SEPARATORS = re.compile(r",|\band\b|&", re.I)
LINKS = ("linked", "linked partly", "not linked")
MEMBER_GRAINS = ("named test", "instrument", "panel", None)


def panels_path(protocol_id: str, collection: str) -> Path:
    return config.get_soa2usdm_folder(protocol_id, collection) / "panels" / f"{protocol_id}_panel_context_members.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Name rule (D1)
# ---------------------------------------------------------------------------
def name_key(name: str) -> str:
    """Key of a panel name: normalised, spelling, trailing generic words dropped, spaces ignored."""
    toks = [SPELLINGS.get(t, t) for t in normalise(name).split()]
    while len(toks) > 1 and toks[-1] in GENERIC_WORDS:
        toks.pop()
    return "".join(toks)


def drop_lab_codes(label: str) -> str:
    """Drop parentheses that hold only lab codes: '(CL)', '(CL, LL)'."""
    return re.sub(r"\s*\(([^()]*)\)",
                  lambda m: "" if set(normalise(m.group(1)).split()) <= LAB_CODES else m.group(0), label).strip()


def _split_names(text: str) -> list:
    """Split at NAME_SEPARATORS outside parentheses."""
    out, depth, start, i = [], 0, 0, 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            m = NAME_SEPARATORS.match(text, i)
            if m:
                out.append(text[start:i])
                i = start = m.end()
                continue
        i += 1
    out.append(text[start:])
    return [p.strip(" .:;-") for p in out if p.strip(" .:;-")]


def soa_panel_names(label: str) -> list:
    """The panel names of an SoA label: each piece without its trailing parentheses, and the names in
    a trailing parenthesis that is not a qualifier."""
    out = []
    for piece in _split_names(drop_lab_codes(label)):
        head, quals = split_trailing_parens(piece)
        out.append(head)
        for q in quals:
            q = LIST_INTRO.sub("", q)
            if not q.strip().lower().startswith(QUALIFIER_CUES):
                out += _split_names(q)
    return [n for n in out if n]


def context_panel_name(name: str) -> str:
    """A context panel name without its trailing parentheses (source notes)."""
    return split_trailing_parens(name)[0]


def link_names(label: str, context_panels: list) -> list:
    """[(name, [context panel index])] for an SoA panel label: the whole label when a context panel has
    its name, otherwise each panel name of the label."""
    keys = [name_key(context_panel_name(p["panel_name"])) for p in context_panels]

    def hits(n):
        return [i for i, k in enumerate(keys) if k == name_key(n)]

    whole = split_trailing_parens(drop_lab_codes(label))[0]
    names = [whole] if hits(whole) else soa_panel_names(label)
    return [(n, hits(n)) for n in names]


# ---------------------------------------------------------------------------
# Members (D2, D3, D5)
# ---------------------------------------------------------------------------
def _member(text: str, frm: str, lk: Lookups, qualifiers: list | None = None, in_group: str | None = None,
            lookup_text: str | None = None) -> dict:
    return {"member_id": "m01", "text": text, "phrase": normalise(text), "from": frm, "in_group": in_group,
            "qualifiers": split_trailing_parens(text)[1] if qualifiers is None else qualifiers} \
        | _member_lookup(lookup_text or text, lk)


def _renumber(ms: list) -> list:
    """Member ids m01, m02 ... in order, in_group following."""
    ids = {id(m): f"m{i + 1:02d}" for i, m in enumerate(ms)}
    old = {m["member_id"]: ids[id(m)] for m in ms}
    return [m | {"member_id": ids[id(m)], "in_group": old.get(m["in_group"], m["in_group"])} for m in ms]


def _condition_cut(m: dict, lk: Lookups) -> dict:
    """A5: text after ';' that starts with a qualifier cue is the member's qualifier."""
    head, sep, tail = m["text"].partition(";")
    if not sep or not tail.strip().lower().startswith(QUALIFIER_CUES) or not head.strip():
        return m
    head = head.strip()
    base = {k: m[k] for k in ("member_id", "from", "in_group")}
    return base | {"text": head, "phrase": normalise(head), "qualifiers": m["qualifiers"] + [tail.strip()]} \
        | _member_lookup(head, lk)


def _analyte_members(text: str, lk: Lookups) -> list:
    """Analyte rules A3, A4, A1, A2, then the label-member rules (with A5)."""
    # A3: text before a colon is a group heading
    head, sep, rest = text.partition(":")
    if sep and re.search(r"[A-Za-z]", head) and rest.strip():
        h = _member(head.strip(), "analyte heading", lk, qualifiers=[])
        h["member_id"] = "h"
        subs = _analyte_members(rest.strip(), lk)
        return [h] + [m | {"in_group": m["in_group"] or "h"} for m in subs]
    # A4: a trailing list parenthesis distributed over the head's last word
    outer, quals = split_trailing_parens(text)
    lists = [q for q in quals if _is_list(q)]
    if len(lists) == 1 and normalise(outer):
        noun = normalise(outer).split()[-1]
        items = split_top(LIST_INTRO.sub("", lists[0]))
        combos = [f"{it} {noun}" for it in items]
        if len(items) >= 2 and all(lk.test_hit(c)[0] in ("whole", "compact") for c in combos):
            g = _member(outer, "analyte", lk, qualifiers=[q for q in quals if q not in lists])
            g["member_id"] = "g"
            return [g] + [_member(c, "analyte parenthesis distributed", lk, qualifiers=[], in_group="g")
                          for c in combos]
    # A1: the whole analyte is a test
    if lk.test_hit(text)[0] in ("whole", "compact"):
        return [_member(text, "analyte", lk)]
    # A2: 'X, Y' with one word after the only comma: Y qualifies X
    if split_top(text) != [text] and text.count(",") == 1:
        x, y = (p.strip() for p in text.split(","))
        y_head, y_quals = split_trailing_parens(y)
        if (x and len(y_head.split()) == 1 and not re.search(r"\band\b|&|/", x, re.I)
                and not lk.test_hit(y_head)[1]):
            inv = f"{y_head} {x}"
            if lk.test_hit(inv)[0] in ("whole", "compact"):
                return [_member(text, "analyte", lk, qualifiers=[], lookup_text=inv)]
            return [_member(x, "analyte", lk, qualifiers=[y_head] + y_quals)]
    ms, _, _ = label_members(text, lk)
    if ms:
        return [_condition_cut(m, lk) | {"from": "analyte list" if m["from"] == "label" else "analyte parenthesis"}
                for m in ms]
    return [_member(text, "analyte", lk)]


def analyte_members(text: str, lk: Lookups) -> list:
    """Members of one analyte (analyte rules 1.0.0, then the label-member rules): a list analyte gives its
    members ('from' analyte list / analyte parenthesis), any other analyte one member ('from' analyte);
    A3 adds a heading member, A4 distributed members."""
    return _renumber(_analyte_members(text, lk))


def _stated_facets(sources: list, context_panels: list) -> list:
    """D5: specimen and lab of each source context panel, as stated, when stated."""
    out = []
    for src in sources:
        cp = context_panels[int(src["context_panel"].rsplit("/", 1)[1])]
        for facet in ("specimen", "lab"):
            if cp.get(facet):
                f = {"facet": facet, "value": cp[facet], "context_panel": src["context_panel"],
                     "pages": sorted({e["page"] for e in cp["evidence"]})}
                if f not in out:
                    out.append(f)
    return out


def panel_row(a: dict, context_panels: list, lk: Lookups) -> dict:
    """The sidecar entry of one name-only panel row: names linked, members, differences."""
    names = link_names(a["activity_name"], context_panels)
    union, differences = {}, []
    for name, idx in names:
        per = {}
        by_code = {}
        for i in idx:
            ptr = f"/panels/{i}"
            per[ptr] = set()
            for analyte in context_panels[i]["analytes"]:
                ids = {}
                for m in analyte_members(analyte, lk):
                    per[ptr].add(m["phrase"])
                    src = {"context_panel": ptr, "analyte": analyte}
                    codes = {h["code"] for h in m.get("hits", [])}
                    if len(idx) > 1 and m["member_grain"] == "named test" and len(codes) == 1:
                        (code,) = codes
                        other = by_code.get(code)
                        if other and other[0] != ptr and m["phrase"] not in union:
                            u = union[other[1]]   # A7: same single code from another context panel of this name
                            u["sources"].append(src)
                            ids[m["member_id"]] = u["member_id"]
                            continue
                        by_code.setdefault(code, (ptr, m["phrase"]))
                    if m["phrase"] in union:
                        u = union[m["phrase"]]
                        if src not in u["sources"]:
                            u["sources"].append(src)
                        ids[m["member_id"]] = u["member_id"]
                        continue
                    ids[m["member_id"]] = f"c{len(union) + 1:02d}"
                    union[m["phrase"]] = m | {"member_id": ids[m["member_id"]],
                                              "in_group": ids[m["in_group"]] if m["in_group"] else None,
                                              "sources": [src]}
        if len(idx) > 1:
            common = set.intersection(*per.values())
            differences.append({
                "name": name, "context_panels": list(per), "common": len(common),
                "only_in": [{"context_panel": p, "phrases": sorted(ph - set().union(*[per[o] for o in per if o != p]))}
                            for p, ph in per.items()]})
    members = [m | {"stated_facets": _stated_facets(m["sources"], context_panels)} for m in union.values()]
    linked = [n for n, idx in names if idx]
    return {
        "xact_id": a["xact_id"], "activity_name": a["activity_name"],
        "link": "not linked" if not linked else ("linked" if len(linked) == len(names) else "linked partly"),
        "names": [{"name": n, "key": name_key(n), "context_panels": [f"/panels/{i}" for i in idx]} for n, idx in names],
        "members": members,
        "differences": differences,
    }


def name_only_panel(a: dict, labels: dict) -> bool:
    """A grain panel row whose label lists no named-test member: routing's "panel, not split"."""
    return a["grain"] == "panel" and not any(
        m.get("member_grain") == "named test" for m in (labels.get(a["phrase"]) or {}).get("members", []))


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------
def generate_study_panel_members(collection: str, protocol_id: str, lk: Lookups | None = None,
                                 all_rows: list | None = None) -> dict:
    """Build the <id>_panel_context_members.json payload for one study."""
    ctx_file = context_path(protocol_id, collection)
    if not ctx_file.exists():
        raise FileNotFoundError(f"{collection}/{protocol_id}: no protocol context; the file exists only where "
                                f"protocol context exists")
    g = load_current_grain(collection, protocol_id, all_rows)
    if g is None:
        raise FileNotFoundError(f"{collection}/{protocol_id}: no activity grain file; run soa2usdm.activity_grain")
    lk = lk or Lookups()
    if g["inputs"]["cdisc_for_ai"]["commit"] != lk.provenance["commit"]:
        raise RuntimeError(f"{collection}/{protocol_id}: grain made at cdisc-for-ai "
                           f"{g['inputs']['cdisc_for_ai']['commit'][:7]}, lookups at {lk.provenance['commit'][:7]}; "
                           f"rerun python -m soa2usdm.activity_grain --collection {collection} --protocol {protocol_id}")
    ctx_raw = ctx_file.read_bytes()
    ctx = json.loads(ctx_raw)
    lk = lk.for_study(ctx)
    cps = ctx["panels"]
    labels = {lb["phrase"]: lb for lb in g["labels"]}
    rows = [panel_row(a, cps, lk) for a in g["activities"] if name_only_panel(a, labels)]
    used = sorted({int(p.rsplit("/", 1)[1]) for r in rows for n in r["names"] for p in n["context_panels"]})
    members = [m for r in rows for m in r["members"]]
    return {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
        "collection": collection, "protocol_id": protocol_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "name_rule_version": NAME_RULE_VERSION,
        "analyte_rule_version": ANALYTE_RULE_VERSION,
        "name_rule": {"spellings": SPELLINGS, "generic_words": list(GENERIC_WORDS), "lab_codes": sorted(LAB_CODES)},
        "inputs": {
            "activity_grain": {"schema_version": g["schema_version"], "rules_version": g["rules_version"],
                               "sha256": _sha256(grain_path(protocol_id, collection))},
            "protocol_context": {"schema_version": ctx["schema_version"],
                                 "prompt_version": ctx["provenance"]["prompt_version"],
                                 "sha256": hashlib.sha256(ctx_raw).hexdigest()},
            "cdisc_for_ai": lk.provenance,
        },
        "counts": {
            "panel_rows": len(rows),
            "by_link": {k: sum(1 for r in rows if r["link"] == k) for k in LINKS},
            "context_panels": len(cps), "context_panels_used": len(used),
            "members": len(members),
            "by_member_grain": {str(k) if k else "none": sum(1 for m in members if m["member_grain"] == k)
                                for k in MEMBER_GRAINS},
            "names_with_several_context_panels": sum(len(r["differences"]) for r in rows),
        },
        "context_panels": [{"pointer": f"/panels/{i}", "panel_name": cps[i]["panel_name"],
                            "specimen": cps[i].get("specimen"), "lab": cps[i].get("lab"),
                            "evidence": cps[i]["evidence"]} for i in used],
        "rows": rows,
    }


def load_current_panel_members(collection: str, protocol_id: str) -> dict | None:
    """The study's panel context members file, checked against the grain file and the protocol context
    as they are now. None where the study has no protocol context; fails where it has protocol context
    and a grain file but no panel context members file, or when an input changed since."""
    path = panels_path(protocol_id, collection)
    rerun = (f"rerun: python -m soa2usdm.panel_context_members --collection {collection} "
             f"--protocol {protocol_id}")
    if not path.exists():
        if context_path(protocol_id, collection).exists() and grain_path(protocol_id, collection).exists():
            raise FileNotFoundError(f"{path}: missing (the study has protocol context); {rerun}")
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    if d["schema_name"] != SCHEMA_NAME or d["schema_version"] not in SCHEMA_VERSIONS:
        raise ValueError(f"{path}: expected {SCHEMA_NAME} {' or '.join(SCHEMA_VERSIONS)}")
    sha = lambda f: _sha256(f) if f.exists() else None
    now = {"activity grain": sha(grain_path(protocol_id, collection)),
           "protocol context": sha(context_path(protocol_id, collection))}
    was = {"activity grain": d["inputs"]["activity_grain"]["sha256"],
           "protocol context": d["inputs"]["protocol_context"]["sha256"]}
    changed = [k for k in now if now[k] != was[k]]
    if changed:
        raise RuntimeError(f"{path}: stale ({', '.join(changed)} changed since it was generated); {rerun}")
    return d


def write_study_panel_members(collection: str, protocol_id: str, lk: Lookups | None = None,
                              all_rows: list | None = None) -> Path:
    payload = generate_study_panel_members(collection, protocol_id, lk, all_rows)
    out = panels_path(protocol_id, collection)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Panel members from protocol context, per study.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", help="one study; default: every study with protocol context and a grain file")
    args = ap.parse_args()
    from .activity_inventory import collect_rows
    all_rows = collect_rows(args.collection)
    pids = [args.protocol] if args.protocol else sorted(
        {r["protocol_id"] for r in all_rows
         if context_path(r["protocol_id"], args.collection).exists()
         and grain_path(r["protocol_id"], args.collection).exists()})
    lk = Lookups()
    for pid in pids:
        print(write_study_panel_members(args.collection, pid, lk, all_rows))


if __name__ == "__main__":
    main()
