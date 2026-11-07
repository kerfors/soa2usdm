"""
Prepare the inputs for protocol context extraction (prompts/PROTOCOL_CONTEXT_CGT_PROMPT.md or
prompts/PROTOCOL_CONTEXT_GENERAL_PROMPT.md; the inputs are the same for both profiles).

For one protocol of a collection, writes:
  {protocol folder}/{NCTID}_pages.txt
      the protocol text page by page ('===== PAGE n ====='), PDF page numbers;
      local only, like the full PDF and the markdown dump (see .gitignore in the collections repo)
  {protocol folder}/SoA2USDM/context/{NCTID}_soa_inputs.json
      from the consolidated SoA: soa_activities, soa_cross_references, soa_notes; published

Usage:
  python tools/protocol_context_inputs.py --collection cell_gene_therapy --protocol NCT03489291 [--pages 268-423]

--pages limits the text to a page range (e.g. when the posted PDF bundles several protocol versions).
Needs pymupdf.
"""

import argparse
import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from soa2usdm import config  # noqa: E402


def write_pages(pdf: Path, out: Path, first: int, last: int) -> int:
    doc = pymupdf.open(pdf)
    if last > doc.page_count:
        raise ValueError(f"{pdf.name} has {doc.page_count} pages; --pages ends at {last}")
    parts = []
    for p in range(first, last + 1):
        text = doc[p - 1].get_text()
        parts.append(f"\n===== PAGE {p} =====\n" + (text if text.strip() else "[no text layer on this page]\n"))
    out.write_text("".join(parts), encoding="utf-8")
    return last - first + 1


def soa_inputs(consolidated: dict) -> dict:
    acts = {a["xact_id"]: a["activity_name"] for a in consolidated["unified_activities"]}
    activities = [a["activity_name"] for a in consolidated["unified_activities"] if not a["is_section_header"]]
    refs, notes = [], []
    for u in consolidated["unified_annotations"]:
        bound = [acts[x] for x in u.get("referenced_xacts", [])]
        bound += [acts[c["xact_id"]] for c in u.get("cell_references", []) if c.get("xact_id") in acts and acts[c["xact_id"]] not in bound]
        notes.append({"marker": u["display_markers"], "type": u["annotation_type"], "text": u["annotation_text"], "activities": bound})
        if u.get("document_references"):
            refs.append({"annotation_text": u["annotation_text"], "document_references": u["document_references"]})
    return {"soa_activities": activities, "soa_cross_references": refs, "soa_notes": notes}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--pages", help="first-last PDF pages to include (default: all)")
    a = ap.parse_args()
    pdir = config.get_protocol_path(a.protocol, a.collection)
    pdf = pdir / f"{a.protocol}.pdf"
    if not pdf.exists():
        raise FileNotFoundError(f"{pdf} not found (the full protocol PDF is local only)")
    cons = config.find_consolidated_file(a.protocol, a.collection)
    if cons is None:
        raise FileNotFoundError(f"no consolidated SoA for {a.protocol} in {a.collection}: run Layers 1-3 first")
    if a.pages:
        first, last = (int(x) for x in a.pages.split("-"))
    else:
        first, last = 1, pymupdf.open(pdf).page_count
    n = write_pages(pdf, pdir / f"{a.protocol}_pages.txt", first, last)
    soa = soa_inputs(json.loads(Path(cons).read_text(encoding="utf-8")))
    cdir = config.get_soa2usdm_folder(a.protocol, a.collection) / "context"
    cdir.mkdir(exist_ok=True)
    (cdir / f"{a.protocol}_soa_inputs.json").write_text(json.dumps(soa, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{a.protocol}: {n} pages; {len(soa['soa_activities'])} activities, "
          f"{len(soa['soa_cross_references'])} cross-references, {len(soa['soa_notes'])} notes")


if __name__ == "__main__":
    main()
