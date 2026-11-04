"""
Record the content fingerprint on existing grain decisions (one-time, 2026-11-04).

Decisions files of schema 1.1 / 1.2 tie each ai_proposed decision to the sha256
of the whole grain inputs file (inputs_sha256). That sha256 also covers the
recorded versions (sources), so any new cdisc-for-ai commit made every decision
"made from another file", even when nothing the prompt reads had changed.
Decisions schema 1.3 ties a decision to the inputs' content_sha256 instead
(soa2usdm.activity_grain_inputs.content_sha256).

Per study, before the grain inputs file is gathered again:
  1. every ai_proposed decision's inputs_sha256 must equal the sha256 of the
     study's current grain inputs file (proof it was made from that file);
     any mismatch stops the run, and nothing is written for that study;
  2. inputs_content_sha256 = content_sha256 of that file is added to each
     ai_proposed decision, and the file becomes schema 1.3.
Nothing else changes: no decision is altered, inputs_sha256 stays as a record.

Usage:
  python tools/grain_decisions_record_content_sha.py --collection cell_gene_therapy [--protocol NCT03489291]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from soa2usdm import activity_grain as ag  # noqa: E402
from soa2usdm import config  # noqa: E402
from soa2usdm.activity_grain_inputs import content_sha256  # noqa: E402


def record(collection: str, protocol_id: str) -> str:
    dpath = ag.decisions_path(protocol_id, collection)
    ipath = ag.inputs_path(protocol_id, collection)
    doc = json.loads(dpath.read_text(encoding="utf-8"))
    if doc["schema_version"] == "1.3":
        raise ValueError(f"{dpath}: already schema 1.3")
    if doc["schema_version"] not in ("1.1", "1.2"):
        raise ValueError(f"{dpath}: schema {doc['schema_version']}; only 1.1 / 1.2 files are recorded")
    raw = ipath.read_bytes()
    whole, content = hashlib.sha256(raw).hexdigest(), content_sha256(json.loads(raw))
    ai = [d for d in doc["decisions"] if d["source"] == "ai_proposed"]
    bad = [d["phrase"] for d in ai if d["inputs_sha256"] != whole]
    if bad:
        raise ValueError(f"{dpath}: {len(bad)} ai_proposed decision(s) not made from the current {ipath.name} "
                         f"(inputs_sha256 differs): {bad}")
    for d in ai:
        d["inputs_content_sha256"] = content
    doc["schema_version"] = "1.3"
    dpath.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return f"{dpath}: {len(ai)} ai_proposed decision(s), inputs_content_sha256 {content[:12]}…, schema 1.3"


def main():
    ap = argparse.ArgumentParser(description="Record inputs_content_sha256 on existing grain decisions (schema 1.3).")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", help="one study; default: every study of the collection with a decisions file")
    args = ap.parse_args()
    root = config.COLLECTIONS_ROOT / args.collection / "protocols"
    pids = ([args.protocol] if args.protocol else
            sorted(p.parent.parent.parent.name
                   for p in root.glob("*/SoA2USDM/grain/*_activity_grain_decisions.json")))
    for pid in pids:
        print(record(args.collection, pid))


if __name__ == "__main__":
    main()
