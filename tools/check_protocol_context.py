"""
Check a protocol context file (soa2usdm-protocol-context-cgt) against its sources.

  1. The file validates against schemas/soa2usdm-protocol-context-cgt.schema.json.
  2. Every evidence quote is found on the page it cites in {NCTID}_pages.txt
     (whitespace collapsed on both sides, soft hyphens and ligatures folded; nothing else).
  3. Every abbreviation's term and definition are found on its cited page.
  4. Every cross-reference with target_found = true has evidence; every other item has evidence.
  5. provenance.pages_file_sha256 matches the pages file.

Items marked read_from = "page image" (page without a text layer) cannot be text-checked; they are listed, not failed.

Usage:
  python tools/check_protocol_context.py --collection cell_gene_therapy --protocol NCT03489291

Exits 1 on any failure and prints each failing item.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from soa2usdm import config  # noqa: E402

SCHEMA = ROOT / "schemas" / "soa2usdm-protocol-context-cgt.schema.json"
EVIDENCE_CATS = ["product", "immunogenicity", "cross_references", "panels",
                 "endpoint_assays", "genetic_testing", "lab_and_purpose"]


def norm(s: str) -> str:
    s = s.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    return re.sub(r"\s+", " ", s).strip()


def read_pages(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return {int(m.group(1)): norm(m.group(2))
            for m in re.finditer(r"===== PAGE (\d+) =====\n(.*?)(?=\n===== PAGE |\Z)", text, re.S)}


def check(ctx_path: Path, pages_path: Path) -> list:
    d = json.loads(ctx_path.read_text(encoding="utf-8"))
    fails = [("schema", None, None, e.message[:160])
             for e in jsonschema.Draft7Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).iter_errors(d)]
    sha = hashlib.sha256(pages_path.read_bytes()).hexdigest()
    if d.get("provenance", {}).get("pages_file_sha256") != sha:
        fails.append(("provenance", None, None, "pages_file_sha256 does not match the pages file"))
    P = read_pages(pages_path)
    visual = []
    for cat in EVIDENCE_CATS:
        for i, it in enumerate(d.get(cat, [])):
            ev = it.get("evidence", [])
            if not ev and (cat != "cross_references" or it.get("target_found")):
                fails.append((cat, i, None, "no evidence"))
            for e in ev:
                if e.get("read_from") == "page image":
                    visual.append((cat, i, e.get("page")))
                    continue
                q, p = norm(e.get("quote", "")), e.get("page")
                if not q or p not in P or q not in P[p]:
                    fails.append((cat, i, p, e.get("quote", "")[:120]))
    for i, a in enumerate(d.get("abbreviations", [])):
        p = a.get("page")
        if a.get("read_from") == "page image":
            visual.append(("abbreviations", i, p))
            continue
        if p not in P or norm(a.get("term", "")) not in P[p] or norm(a.get("definition", "")) not in P[p]:
            fails.append(("abbreviations", i, p, f"{a.get('term')} = {a.get('definition')}"[:120]))
    return fails, visual


def main():
    ap = argparse.ArgumentParser(description="Check a protocol context file against its sources.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", required=True)
    a = ap.parse_args()
    pdir = config.get_protocol_path(a.protocol, a.collection)
    ctx = config.get_soa2usdm_folder(a.protocol, a.collection) / "context" / f"{a.protocol}_protocol_context.json"
    pages = pdir / f"{a.protocol}_pages.txt"
    for f in (ctx, pages):
        if not f.exists():
            raise FileNotFoundError(f)
    fails, visual = check(ctx, pages)
    d = json.loads(ctx.read_text(encoding="utf-8"))
    counts = {c: len(d.get(c, [])) for c in EVIDENCE_CATS + ["abbreviations"]}
    print(f"{a.protocol}: {len(fails)} failing; {len(visual)} read from page images (not checked); counts {counts}")
    for f in fails:
        print("  FAIL", f)
    for v in visual:
        print("  VISUAL", v)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
