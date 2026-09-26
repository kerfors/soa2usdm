"""Regenerate documents/re-extraction-baseline.json from the accepted corpus.

Machine facts only: everything here is computed from the collection by the same code the gate
and the row audit use, so running it twice on the same corpus gives the same bytes. No timestamp
is written; the commit that carries the file dates it. Interpretation of the uncertainty reports
(invariants, judgement calls, source defects) lives in a separate file, not here.

  per_table_metrics   gate.check_table metrics for every raw *_extraction.json — what gate.py diffs
                      staged tables against. Raw, not .verified.json: staging holds raw extractions.
  row_audit           soa2usdm.row_audit counts, plus the on-page-not-extracted items themselves,
                      so a rise can be told apart from a changed item.
  quote_verification  gate.check_quotes per study, against the study's own PDF and extractions.
  corrections         inventory of every corrections sidecar: count, ops, targets, match keys.
  extraction_hash     sha256 over the raw extraction files (name + bytes, sorted by name).
  collections         HEAD and the last commit that touched a raw extraction file.

Environment (as for tools/gate.py):
  SOA2USDM_REPO         this repo (default: the tools/ parent)
  SOA2USDM_COLLECTIONS  the collections tree (config.py reads this)
  SOA2USDM_COLLECTION   which collection (default usdm_data)

Usage:  python tools/baseline.py [--out PATH]
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(os.environ.get("SOA2USDM_REPO", Path(__file__).resolve().parents[1]))
COLLECTION = os.environ.get("SOA2USDM_COLLECTION", "usdm_data")
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))

import gate  # noqa: E402
from soa2usdm import config  # noqa: E402
from soa2usdm.row_audit import audit_collection  # noqa: E402

QUOTE_INFO = re.compile(r"^(\d+) verbatim, (\d+) unverified, (\d+) skipped as non-evidence")


def table_number(path):
    return int(re.search(r"_Table_(\d+)_", path.name).group(1))


def raw_extractions(protocols_dir):
    return sorted(protocols_dir.glob("*/SoA2USDM/extracted/*_Table_*_extraction.json"))


def per_table_metrics(files, schema):
    rows = []
    for path in files:
        _, metrics = gate.check_table(path, schema, {})
        rows.append({"study": path.name.split("_Table_")[0], "table": table_number(path), **metrics})
    return rows


def row_audit():
    report = audit_collection(COLLECTION)
    items = [{"study": p["protocol_id"], "table": t["table_number"], "page": i["page"],
              "text": i["text"]}
             for p in report["protocols"] for t in p["tables"] for i in t["on_page_not_extracted"]]
    return {**report["counts"], "on_page_not_extracted_items": items}


def quote_verification(protocols_dir, studies):
    """gate.check_quotes reads STAGING/<study>/ and BLIND/<study>/<study>_soa.pdf. Point STAGING at
    a temp dir of links to each study's extracted/ folder and BLIND at the protocols folder, which
    already holds <study>/<study>_soa.pdf — the check itself runs unchanged."""
    per_study, unverified = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for study in studies:
            (Path(tmp) / study).symlink_to(protocols_dir / study / "SoA2USDM" / "extracted")
        gate.STAGING, gate.BLIND = Path(tmp), protocols_dir
        for study in studies:
            out = gate.check_quotes(study)
            name, level, msg = out[0]
            if level != "INFO":
                sys.exit(f"{study}: quote check did not run — {level} {msg}")
            ok, bad, skip = (int(x) for x in QUOTE_INFO.match(msg).groups())
            per_study.append({"study": study, "verbatim": ok, "unverified": bad, "skipped": skip})
            unverified += [{"study": study, "item": m} for _, lvl, m in out[1:] if lvl == "CHECK"]
    return {
        "checked": sum(s["verbatim"] + s["unverified"] for s in per_study),
        "verbatim": sum(s["verbatim"] for s in per_study),
        "unverified": sum(s["unverified"] for s in per_study),
        "skipped": sum(s["skipped"] for s in per_study),
        "per_study": per_study,
        "unverified_items": unverified,
    }


def corrections(protocols_dir):
    sidecars = []
    for path in sorted(protocols_dir.glob("*/SoA2USDM/extracted/*_corrections.json")):
        items = json.loads(path.read_text(encoding="utf-8"))["corrections"]
        sidecars.append({
            "file": path.name,
            "count": len(items),
            "ops": dict(sorted(Counter(c["op"] for c in items).items())),
            "targets": dict(sorted(Counter(c["target"] for c in items).items())),
            "match_keys": dict(sorted(Counter(",".join(sorted(c["match"])) if c.get("match") else "none"
                                              for c in items).items())),
        })
    return {
        "sidecars": len(sidecars),
        "sidecars_with_content": sum(1 for s in sidecars if s["count"]),
        "total": sum(s["count"] for s in sidecars),
        "files": sidecars,
    }


def extraction_hash(files):
    h = hashlib.sha256()
    for path in sorted(files, key=lambda p: p.name):
        h.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()[:16]


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          check=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(REPO / "documents" / "re-extraction-baseline.json"))
    args = parser.parse_args()

    protocols_dir = config.get_collection_path(COLLECTION)
    files = raw_extractions(protocols_dir)
    studies = sorted({p.name.split("_Table_")[0] for p in files})
    schema = json.loads(gate.SCHEMA.read_text())

    baseline = {
        "collection": COLLECTION,
        "collections": {
            "head": git(protocols_dir, "rev-parse", "--short", "HEAD"),
            "extractions_last_changed": git(protocols_dir, "log", "-1", "--format=%h", "--",
                                            ":(glob)**/extracted/*_extraction.json"),
        },
        "extraction_hash": extraction_hash(files),
        "counts": {"studies": len(studies), "tables": len(files)},
        "row_audit": row_audit(),
        "per_table_metrics": per_table_metrics(files, schema),
        "quote_verification": quote_verification(protocols_dir, studies),
        "corrections": corrections(protocols_dir),
    }
    Path(args.out).write_text(json.dumps(baseline, ensure_ascii=False, indent=1) + "\n",
                              encoding="utf-8")
    print(f"{len(studies)} studies, {len(files)} tables -> {args.out}")


if __name__ == "__main__":
    main()
