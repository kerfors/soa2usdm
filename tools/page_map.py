"""Derive the PDF-page → document-page map for each study's `_soa.pdf`, and flag what needs eyes.

Extraction agents must never read a page number off a printed page footer. Measured across the 22
protocols of `usdm_data`: one protocol's footer runs one LOWER than the document page, another's
runs one HIGHER, one prints a protocol number (5020) instead of a page number, and 15 print nothing
at all. So the map has to be computed and handed to the agent.

The trap this script exists for
------------------------------
The obvious rule — anchor the excerpt at its last page, `doc_page(pdf i) = B - (N - i)` — is WRONG
whenever the excerpt carries extra pages at the BACK, and it fails silently: every page number in
the extraction shifts by a constant and nothing downstream notices. **The manifest's `soa_pages`
describes the SoA TABLE pages, not the excerpt.** An excerpt can carry context at either end:
a cover or section-intro page at the front, or an appendix, flow chart or notes page at the back.
Only the content says which. Four of 22 protocols had back matter; two were extracted against a
shifted map and had to be re-run.

So this script does NOT guess. Where the excerpt has more pages than the declared range, it prints
both candidate mappings, shows the first and last lines of the pages in question, and asks for a
decision. Confirm by writing the answer into the manifest or by passing --front / --back.

Usage:
    python3 tools/page_map.py --collection usdm_data                 # report, decide nothing
    python3 tools/page_map.py --collection usdm_data --write         # write blind/<STUDY>/PAGEMAP.md
    python3 tools/page_map.py --collection usdm_data --back NCT04184622 --back NCT03637764
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from soa2usdm import config  # noqa: E402


def pdf_pages(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def page_text(pdf, i, layout=True):
    cmd = ["pdftotext"] + (["-layout"] if layout else []) + ["-f", str(i), "-l", str(i), str(pdf), "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


# Running headers repeat on every page and say nothing about which page this is; the deciding
# evidence is the first line of real content (a section heading, an appendix title, a table caption).
BOILERPLATE = re.compile(r"^(confidential|clinical (study )?protocol|amended clinical|protocol\s|"
                         r"page \d+|.{0,3}$)", re.I)


def first_lines(pdf, i, n=3):
    lines = [l.strip() for l in page_text(pdf, i).splitlines() if l.strip()]
    meaty = [l for l in lines if not BOILERPLATE.match(l)]
    return (meaty or lines)[:n]


def read_manifest(collection):
    """(nct_id -> (first_doc_page, last_doc_page)) from the collection's studies_protocols.xlsx."""
    import openpyxl
    root = Path(config.COLLECTIONS[collection])
    book = openpyxl.load_workbook(root.parent / "studies_protocols.xlsx")
    sheet = book["protocols"]
    header = [c.value for c in sheet[1]]
    out = {}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        r = dict(zip(header, row))
        if not r.get("nct_id") or not r.get("soa_pages"):
            continue
        text = str(r["soa_pages"])
        a, b = (int(x) for x in text.split("-")) if "-" in text else (int(text), int(text))
        out[r["nct_id"]] = (a, b)
    return out, root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collection", default="usdm_data")
    ap.add_argument("--blind", default=os.environ.get("SOA2USDM_BLIND", "blind"))
    ap.add_argument("--write", action="store_true", help="write blind/<STUDY>/PAGEMAP.md")
    ap.add_argument("--front", action="append", default=[], help="extra pages are at the FRONT")
    ap.add_argument("--back", action="append", default=[], help="extra pages are at the BACK")
    ap.add_argument("--explicit", default=None, help='JSON {"STUDY": [63,64,72,78]} for a non-contiguous excerpt')
    args = ap.parse_args()

    explicit = json.loads(Path(args.explicit).read_text()) if args.explicit else {}
    manifest, root = read_manifest(args.collection)
    undecided = []

    for study, (a, b) in sorted(manifest.items()):
        pdf = root / study / f"{study}_soa.pdf"
        if not pdf.exists():
            print(f"  {study:<14} no _soa.pdf — skipped")
            continue
        n = pdf_pages(pdf)
        declared = b - a + 1
        extra = n - declared

        if study in explicit:
            pages, how = explicit[study], "explicit (non-contiguous excerpt)"
        elif extra == 0:
            pages, how = [a + i for i in range(n)], "contiguous; excerpt == declared range"
        elif extra < 0:
            pages, how = None, f"NON-CONTIGUOUS: {n} PDF pages for a declared span of {declared}"
        elif study in args.front:
            pages, how = [b - (n - 1 - i) for i in range(n)], f"{extra} extra page(s) at the FRONT"
        elif study in args.back:
            pages, how = [a + i for i in range(n)], f"{extra} extra page(s) at the BACK"
        else:
            pages, how = None, f"{extra} extra page(s) — front or back NOT decided"

        print(f"  {study:<14} pdf {n:>2}p  declared {a}-{b:<5} {how}")
        if pages is None:
            undecided.append(study)
            front = [b - (n - 1 - i) for i in range(n)]
            back = [a + i for i in range(n)]
            print(f"      if FRONT: doc {front[0]}-{front[-1]}   if BACK: doc {back[0]}-{back[-1]}")
            for i in (1, n):
                print(f"      pdf p{i}: {' | '.join(first_lines(pdf, i, 2))[:110]}")
            continue

        if args.write:
            d = Path(args.blind) / study
            d.mkdir(parents=True, exist_ok=True)
            lines = [f"# {study} — PDF page → document page", "",
                     f"This excerpt has {n} PDF page(s). {how}.", "",
                     "| PDF page | document page |", "|---:|---:|"]
            lines += [f"| {i + 1} | {p} |" + ("  ← beyond the declared SoA range" if p > b else "")
                      for i, p in enumerate(pages)]
            lines += ["", "Use the **document page** number in `table_metadata.page_start` / `page_end`",
                      "and in every activity's `source_page`. Do NOT read page numbers off the printed",
                      "page footers — in this corpus footers have been measured running one lower than",
                      "the document page, one higher, and in one case showing a protocol number instead.",
                      "This table is authoritative.", ""]
            (d / "PAGEMAP.md").write_text("\n".join(lines))

    if undecided:
        print(f"\n{len(undecided)} study(ies) need a decision before extraction: {', '.join(undecided)}")
        print("Read the pages shown above, then re-run with --front/--back (or --explicit for a")
        print("non-contiguous excerpt). Guessing here shifts every page number in the extraction.")
        return 1
    print("\nall studies mapped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
