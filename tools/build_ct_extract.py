"""Build ct/usdm-borrowed-codelists.tsv — the members of the codelists USDM borrows.

Usage:  python3 tools/build_ct_extract.py

USDM v4 binds 20 coded attributes to codelists whose members are published in NCI EVS CDISC
packages (SDTM CT, Protocol Terminology), not in the DDF deliverables. usdm-rdf publishes those
bindings as deactivated SHACL shapes; tools/usdm_gate.py checks coded values on them against this
extract. The list of codelists is read from the pinned usdm-rdf checkout, so the extract covers
exactly the bindings the gate reports as unchecked.

Input: the full NCI EVS tab-separated files in ct/downloads/ (not committed), each named
'<Package> Terminology <YYYY-MM-DD>.txt', one release per package. Run only when re-pinning a
package. Every codelist must be found in exactly one package, or the build stops.
"""

import csv
import hashlib
import re
import sys
from pathlib import Path

import rdflib
from rdflib.namespace import RDFS, SH

sys.path.insert(0, str(Path(__file__).resolve().parent))
from usdm_gate import REPO, USDM_RDF, USDM_RDF_TAG, check_pin

DOWNLOADS = REPO / "ct" / "downloads"
EXTRACT = REPO / "ct" / "usdm-borrowed-codelists.tsv"
NAME = re.compile(r"(.+) Terminology (\d{4}-\d{2}-\d{2})\.txt")
COLUMNS = ["codelist", "codelist_extensible", "codelist_name", "code",
           "submission_value", "nci_preferred_term", "package"]


def borrowed_codelists():
    g = rdflib.Graph()
    g.parse(USDM_RDF / "usdm_v4.shapes-ct.ttl", format="turtle")
    return sorted({str(g.value(s, RDFS.seeAlso)).rsplit("/", 1)[1]
                   for s in g.subjects(SH.deactivated, rdflib.Literal(True))})


def main():
    wrong = check_pin()
    if wrong:
        sys.exit(f"usdm-rdf is not at {USDM_RDF_TAG}: " + "; ".join(wrong))
    wanted = borrowed_codelists()

    sources = []
    for f in sorted(DOWNLOADS.glob("*.txt")):
        m = NAME.fullmatch(f.name)
        if not m:
            sys.exit(f"{f.name}: expected '<Package> Terminology <YYYY-MM-DD>.txt'")
        sources.append((m.group(1), m.group(2), f))
    packages = [p for p, _, _ in sources]
    if len(set(packages)) != len(packages):
        sys.exit(f"more than one release of the same package in {DOWNLOADS}: {packages}")

    # A codelist may be published in more than one package (SDTM CT and Protocol Terminology
    # share several). Identical copies are kept once, with every package named; copies that
    # differ stop the build, because which one governs USDM is then a decision.
    found = {}   # codelist -> (members, [packages])
    for package, release, f in sources:
        entries = list(csv.DictReader(f.open(encoding="utf-8"), delimiter="\t"))
        heads = {e["Code"]: e for e in entries if not e["Codelist Code"]}
        for cl in wanted:
            if cl not in heads:
                continue
            head = heads[cl]
            members = sorted(
                (cl, head["Codelist Extensible (Yes/No)"], head["Codelist Name"], e["Code"],
                 e["CDISC Submission Value"], e["NCI Preferred Term"])
                for e in entries if e["Codelist Code"] == cl)
            if cl in found and found[cl][0] != members:
                sys.exit(f"{cl} differs between {'/'.join(found[cl][1])} and {package}")
            found.setdefault(cl, (members, []))[1].append(package)
    missing = [cl for cl in wanted if cl not in found]
    if missing:
        sys.exit(f"codelist(s) not in any package in {DOWNLOADS}: {missing}")

    rows = [list(m) + ["/".join(pkgs)] for cl in wanted for m in found[cl][0]
            for pkgs in [found[cl][1]]]
    rows.sort(key=lambda r: (r[0], r[3]))
    with EXTRACT.open("w", encoding="utf-8", newline="") as out:
        out.write("# Members of the codelists USDM v4 borrows from NCI EVS CDISC packages: the "
                  f"bindings usdm-rdf {USDM_RDF_TAG} publishes as sh:deactivated.\n")
        out.write("# Built by tools/build_ct_extract.py from the files below. Do not edit by hand.\n")
        for package, release, f in sources:
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            out.write(f"# source\t{package} Terminology\t{release}\tsha256:{digest}\n")
        w = csv.writer(out, delimiter="\t", lineterminator="\n")
        w.writerow(COLUMNS)
        w.writerows(rows)
    print(f"{EXTRACT.relative_to(REPO)}: {len(wanted)} codelists, {len(rows)} members")


if __name__ == "__main__":
    main()
