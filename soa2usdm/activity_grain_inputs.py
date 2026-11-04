"""
SoA2USDM Activity Grain Inputs (per study)

Gathers, by code, everything the activity grain decisions prompt
(prompts/ACTIVITY_GRAIN_DECISIONS_PROMPT.md) may use for one study, into one
self-contained file:

    SoA2USDM/grain/<id>_grain_inputs.json   (schema soa2usdm-activity-grain-inputs 1.2)

The prompt reads this file and nothing else. The generator
(soa2usdm.activity_grain) accepts an ai_proposed decision only for a phrase
listed here, and stops when this file differs from the inputs rebuilt from the
study's files as they are now.

Items are the labels whose rule result leaves something to decide (rules
alone, decisions ignored), and that have at least one row without a role:

    grain unsure              the rules give no grain
    kind unsure               the rules give a named test, but rule K1 no single kind
    sample collection         the rules give sample collection (a finding may be named in it)
    procedure by word list    the rules give procedure from a word list or a weak hit, not
                              from a strong whole-label METHOD phrase (L3); a measure may be
                              named in it ("ALLO-501A in BM aspirate")

Per item: the label's spellings and rows (xact_id, parent), the rule result,
the SoA annotations bound to its rows or to their parents, the protocol context
entries of category lab_and_purpose whose soa_activity is one of its
spellings, and the abbreviations whose term occurs in the label. Per study:
the protocol context categories that have no link to an SoA row (product,
immunogenicity, endpoint_assays, genetic_testing), whole. CDISC: every
Domain_Coverage row with the kind it gives, and the test / instrument rows the
rules hit for the items. Every context entry carries its JSON Pointer, so a
decision can cite it.

Only public files are read: the study's inventory rows, consolidated.json and
protocol context, and the cdisc-for-ai lookups. The file has no generation
time, so the same inputs give the same file (and the same sha256).

content_sha256 (1.2) is the SHA-256 of what the prompt decides from
(CONTENT_KEYS: collection, protocol_id, items, study, cdisc) as canonical JSON.
It leaves out the version records in sources, so a decision made from the same
content stays valid when only a recorded version changes.
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from . import activity_grain as ag
from . import config

SCHEMA_NAME = "soa2usdm-activity-grain-inputs"
SCHEMA_VERSION = "1.2"
# What the prompt decides from; content_sha256 covers these keys only (not sources).
CONTENT_KEYS = ("collection", "protocol_id", "items", "study", "cdisc")
ITEM_TYPES = ("grain unsure", "kind unsure", "sample collection", "procedure by word list")
STUDY_CATEGORIES = ("product", "immunogenicity", "endpoint_assays", "genetic_testing")
RULE_KEYS_LEFT_OUT = ("phrase", "spellings", "decision")


def content_sha256(doc: dict) -> str:
    """SHA-256 of the CONTENT_KEYS of a grain inputs file as canonical JSON (sorted keys, compact)."""
    content = {k: doc[k] for k in CONTENT_KEYS}
    text = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def item_type(label: dict) -> str | None:
    """The item type of a label's rule result, or None when there is nothing to decide."""
    if label["grain"] == "unsure":
        return "grain unsure"
    if label["grain"] == "named test" and label["finding_kind"] == "unsure":
        return "kind unsure"
    if label["grain"] == "sample collection":
        return "sample collection"
    if label["grain"] == "procedure" and not (label["rule_id"] == "L3" and label["hit_strength"] == "strong"):
        return "procedure by word list"
    return None


def _entries(doc: dict, category: str) -> list:
    return [{"pointer": f"/{category}/{i}", "entry": e} for i, e in enumerate(doc[category])]


def _test_rows(hits: list, lk: ag.Lookups) -> list:
    out = []
    for h in hits:
        if h["file"] == "SDTM_Test_Identity":
            r = lk.test_by_code[h["code"]]
        elif h["file"] == "SDTM_Instrument_Identity":
            r = lk.instrument_by_code[h["code"]]
        else:
            continue
        out.append({"file": h["file"], "code": h["code"], "testcd": r["testcd"], "test": r["test"],
                    "domains": r["domains"]})
    return out


def build_grain_inputs(collection: str, protocol_id: str, lk: ag.Lookups | None = None,
                       all_rows: list | None = None) -> dict:
    """The <id>_grain_inputs.json payload for one study."""
    lk = lk or ag.Lookups()
    ctx_file = ag.context_path(protocol_id, collection)
    if not ctx_file.exists():
        raise FileNotFoundError(f"{collection}/{protocol_id}: no protocol context file ({ctx_file}); "
                                f"grain inputs need it")
    ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
    cons = json.loads(config.find_consolidated_file(protocol_id, collection).read_text(encoding="utf-8"))
    unified = {u["xact_id"]: u for u in cons["unified_activities"]}
    g = ag.generate_study_grain(collection, protocol_id, lk, all_rows, use_decisions=False)

    rows_by_phrase = defaultdict(list)
    for r in g["activities"]:
        if r["role"] is None:
            rows_by_phrase[r["phrase"]].append(r)

    items, test_rows = [], {}
    for lab in g["labels"]:
        t = item_type(lab)
        rows = rows_by_phrase[lab["phrase"]]
        if t is None or not rows:
            continue
        xacts = [r["xact_id"] for r in rows]
        parents = {unified[x]["parent_xact_id"] for x in xacts} - {None}
        row_info = []
        for x in xacts:
            pid = unified[x]["parent_xact_id"]
            row_info.append({"xact_id": x, "activity_name": unified[x]["activity_name"],
                             "parent_xact_id": pid,
                             "parent_name": unified[pid]["activity_name"] if pid else None,
                             "parent_is_section_header": unified[pid]["is_section_header"] if pid else None})
        annotations = []
        for a in cons["unified_annotations"]:
            refs = set(a["referenced_xacts"])
            via = "row" if refs & set(xacts) else ("parent" if refs & parents else None)
            if via:
                annotations.append({"xannot_id": a["xannot_id"], "annotation_type": a["annotation_type"],
                                    "via": via, "text": a["annotation_text"]})
        spellings = set(lab["spellings"])
        lap = [e for e in _entries(ctx, "lab_and_purpose") if e["entry"]["soa_activity"] in spellings]
        padded = f" {lab['phrase']} "
        abbrev = [e for e in _entries(ctx, "abbreviations")
                  if ag.normalise(e["entry"]["term"]).strip() and f" {ag.normalise(e['entry']['term'])} " in padded]
        hits = lab["hits"] + [h for m in lab["members"] for h in m.get("hits", [])]
        for tr in _test_rows(hits, lk):
            test_rows[(tr["file"], tr["code"])] = tr
        items.append({"phrase": lab["phrase"], "item_type": t, "spellings": lab["spellings"], "rows": row_info,
                      "rule": {k: v for k, v in lab.items() if k not in RULE_KEYS_LEFT_OUT},
                      "annotations": annotations, "lab_and_purpose": lap, "abbreviations": abbrev})

    domains = [row | {"kind": ag.domain_kind(d, lk)} for d, row in sorted(lk.domain_rows.items())]
    doc = {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
        "collection": collection, "protocol_id": protocol_id,
        "sources": {
            "inventory_rows": g["inputs"]["inventory_rows"],
            "consolidated": g["inputs"]["consolidated"],
            "protocol_context": g["inputs"]["protocol_context"],
            "cdisc_for_ai": g["inputs"]["cdisc_for_ai"],
            "rules_version": g["rules_version"], "word_lists_date": g["word_lists_date"],
        },
        "items": items,
        "study": {c: _entries(ctx, c) for c in STUDY_CATEGORIES},
        "cdisc": {"domains": domains, "tests": [test_rows[k] for k in sorted(test_rows)]},
    }
    doc["content_sha256"] = content_sha256(doc)
    return doc


def write_grain_inputs(collection: str, protocol_id: str, lk: ag.Lookups | None = None,
                       all_rows: list | None = None) -> Path:
    payload = build_grain_inputs(collection, protocol_id, lk, all_rows)
    out = ag.inputs_path(protocol_id, collection)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Gather the inputs of the grain decisions prompt, per study.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", help="one study; default: every study of the collection with a protocol context")
    args = ap.parse_args()
    from .activity_inventory import collect_rows
    all_rows = collect_rows(args.collection)
    pids = ([args.protocol] if args.protocol else
            sorted(p for p in {r["protocol_id"] for r in all_rows}
                   if ag.context_path(p, args.collection).exists()))
    lk = ag.Lookups()
    for pid in pids:
        print(write_grain_inputs(args.collection, pid, lk, all_rows))


if __name__ == "__main__":
    main()
