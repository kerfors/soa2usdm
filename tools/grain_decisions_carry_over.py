"""
Carry grain decisions over to new grain inputs when their items are unchanged (decisions schema 1.4).

A grain rules change can change the content of a study's grain inputs file while
most of its items stay as they were. Every ai_proposed decision is tied to the
inputs' content_sha256, so all of them go stale and the decisions prompt would
have to run again, with run-to-run drift on items that did not change. This tool
keeps a decision whose item is unchanged and records that it was carried.

Per study, with the grain inputs file on disk still the one the decisions were made from:
  1. every ai_proposed decision's inputs_content_sha256 must equal the content_sha256
     of that file;
  2. the inputs are gathered again with the current rules (not yet written);
  3. collection, protocol_id, study and cdisc domains must be unchanged, and every cdisc
     test row of the new inputs must be in the old ones (nothing new to decide from);
  4. per ai_proposed decision: item unchanged -> carried (inputs_content_sha256 set to the
     new content_sha256, carried_over_from = the old one); phrase no longer an item ->
     dropped and recorded (the rules now give the label a grain with nothing to decide);
     item changed -> the run stops, nothing is written for the study; with --release-changed
     the decision is removed instead and recorded as released (the item is decided again);
  5. the decisions file becomes schema 1.4 (1.5 once a decision was released) with a
     carry_overs record, then the new grain inputs file is written.
reviewed decisions are not touched. A study whose inputs content is unchanged needs no
carry-over (rerun soa2usdm.activity_grain_inputs); the tool says so and writes nothing.

Usage:
  python tools/grain_decisions_carry_over.py --collection cell_gene_therapy [--protocol NCT05714345] [--release-changed]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from soa2usdm import activity_grain as ag  # noqa: E402
from soa2usdm import config  # noqa: E402
from soa2usdm.activity_grain_inputs import build_grain_inputs, content_sha256, write_grain_inputs  # noqa: E402
from soa2usdm.activity_inventory import collect_rows  # noqa: E402


def carry_over(collection: str, protocol_id: str, lk: ag.Lookups, all_rows: list,
               release_changed: bool = False) -> str:
    dpath = ag.decisions_path(protocol_id, collection)
    ipath = ag.inputs_path(protocol_id, collection)
    doc = json.loads(dpath.read_text(encoding="utf-8"))
    if doc["schema_version"] not in ("1.3", "1.4", "1.5"):
        raise ValueError(f"{dpath}: schema {doc['schema_version']}; record content fingerprints first "
                         f"(tools/grain_decisions_record_content_sha.py)")
    old = json.loads(ipath.read_text(encoding="utf-8"))
    old_sha = content_sha256(old)
    ai = [d for d in doc["decisions"] if d["source"] == "ai_proposed"]
    bad = [d["phrase"] for d in ai if d["inputs_content_sha256"] != old_sha]
    if bad:
        raise ValueError(f"{dpath}: {len(bad)} ai_proposed decision(s) not made from the current {ipath.name}: {bad}")
    new = build_grain_inputs(collection, protocol_id, lk, all_rows)
    new_sha = content_sha256(new)
    if new_sha == old_sha:
        return f"{protocol_id}: inputs content unchanged, nothing to carry (rerun soa2usdm.activity_grain_inputs)"
    for k in ("collection", "protocol_id", "study"):
        if old[k] != new[k]:
            raise ValueError(f"{protocol_id}: '{k}' of the grain inputs changed; rerun the decisions prompt")
    if old["cdisc"]["domains"] != new["cdisc"]["domains"]:
        raise ValueError(f"{protocol_id}: cdisc domains of the grain inputs changed; rerun the decisions prompt")
    added = [t for t in new["cdisc"]["tests"] if t not in old["cdisc"]["tests"]]
    if added:
        raise ValueError(f"{protocol_id}: {len(added)} new cdisc test row(s) in the grain inputs; "
                         f"rerun the decisions prompt")
    old_items = {i["phrase"]: i for i in old["items"]}
    new_items = {i["phrase"]: i for i in new["items"]}
    changed, dropped, released, kept = [], [], [], []
    for d in doc["decisions"]:
        if d["source"] != "ai_proposed":
            kept.append(d)
            continue
        p = d["phrase"]
        if p not in new_items:
            lab = ag.label_grain(old_items[p]["spellings"][0], lk)  # the rules read the first spelling
            dropped.append({"phrase": p, "grain": d["grain"], "rule_result": f"{lab['grain']}/{lab['rule_id']}"})
            continue
        if new_items[p] != old_items[p]:
            changed.append(p)
            released.append({"phrase": p, "grain": d["grain"]})
            continue
        kept.append(d | {"inputs_content_sha256": new_sha, "carried_over_from": old_sha})
    if changed and not release_changed:
        raise ValueError(f"{protocol_id}: {len(changed)} item(s) changed, their decisions cannot be carried; "
                         f"rerun the decisions prompt: {changed}")
    doc["schema_version"] = "1.5" if released or doc["schema_version"] == "1.5" else "1.4"
    doc["decisions"] = kept
    doc.setdefault("carry_overs", []).append({
        "from_inputs_content_sha256": old_sha, "to_inputs_content_sha256": new_sha,
        "grain_rules_version": ag.RULES_VERSION, "carried_on": date.today().isoformat(),
        "carried": sum(1 for d in kept if d.get("carried_over_from") == old_sha), "dropped": dropped,
        **({"released": released} if released else {})})
    dpath.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_grain_inputs(collection, protocol_id, lk, all_rows)
    return (f"{dpath}: carried {doc['carry_overs'][-1]['carried']}, dropped {len(dropped)} "
            f"({', '.join(x['phrase'] for x in dropped) or '-'}), released {len(released)} "
            f"({', '.join(x['phrase'] for x in released) or '-'}), inputs {old_sha[:12]}… -> {new_sha[:12]}…")


def main():
    ap = argparse.ArgumentParser(description="Carry grain decisions over to new grain inputs (decisions schema 1.4).")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", help="one study; default: every study of the collection with a decisions file")
    ap.add_argument("--release-changed", action="store_true",
                    help="remove the decision of a changed item (recorded as released) instead of stopping")
    args = ap.parse_args()
    root = config.COLLECTIONS_ROOT / args.collection / "protocols"
    pids = ([args.protocol] if args.protocol else
            sorted(p.parent.parent.parent.name
                   for p in root.glob("*/SoA2USDM/grain/*_activity_grain_decisions.json")))
    lk = ag.Lookups()
    all_rows = collect_rows(args.collection)
    for pid in pids:
        print(carry_over(args.collection, pid, lk, all_rows, args.release_changed))


if __name__ == "__main__":
    main()
