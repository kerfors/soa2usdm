"""USDM Instantiation gate — mechanical checks only, no judgement.

Usage:  python3 tools/usdm_gate.py MANIFEST USDM_JSON

The last step of the manual USDM Instantiation procedure. MANIFEST is the hand-written
<ID>_usdm_manifest.yaml, USDM_JSON the <ID>_usdm.json that soa2usdm.usdmgen wrote from it.
Checks, in order:

  M   the manifest validates against schemas/usdm-manifest.schema.json
  P   the usdm-rdf checkout is the pinned release (content hashes, below)
  C   context conformance: every instanceType is a model class, every key a model attribute,
      every object has an id, every id-based cross-reference resolves
  S   structural SHACL (usdm_v4.shapes.ttl) conforms
  T   terminology SHACL (usdm_v4.shapes-ct.ttl) has no Violation
  B   coded values on the codelists USDM borrows from NCI EVS CDISC packages (the bindings
      usdm-rdf leaves sh:deactivated) are members, per ct/usdm-borrowed-codelists.tsv; a
      non-member fails on a non-extensible codelist and is reported on an extensible one

C, S and T are usdm-rdf's notebooks/60_validate_study.ipynb, executed from the pinned checkout
with only STUDY_JSON and BASE_IRI set — not a copy of it. Duplicate ids and subjects outside the
base IRI stop the notebook before any shape runs. Terminology Warnings (extensible codelists) and
non-members of extensible borrowed codelists are reported, not judged.

Exit 0 when every check passes, 1 otherwise.

Environment:
  SOA2USDM_USDM_RDF   the usdm-rdf checkout (default: usdm-rdf next to this repo)
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import jsonschema
import yaml

REPO = Path(os.environ.get("SOA2USDM_REPO", Path(__file__).resolve().parents[1]))
USDM_RDF = Path(os.environ.get("SOA2USDM_USDM_RDF", REPO.parent / "usdm-rdf"))
MANIFEST_SCHEMA = REPO / "schemas" / "usdm-manifest.schema.json"
CT_EXTRACT = REPO / "ct" / "usdm-borrowed-codelists.tsv"
INSTANCE_BASE = "https://kerfors.github.io/soa2usdm/instances/"

# usdm-rdf v0.7.1. Same shapes and context as v0.7.0; notebook 60 adds occurrence and distinct-
# code counts to the unchecked-values table (d8d8075). Re-pin by replacing tag and hashes together.
USDM_RDF_TAG = "v0.7.1"
USDM_RDF_SHA256 = {
    "notebooks/60_validate_study.ipynb": "20c2828176ecf8c5216fd6121323a52166e94787739927bebf19219a8845d08f",
    "usdm_v4.context.jsonld": "1919be9f0b24b3db80f2e1815f7057cae08b32e9c28b2ad07fecbe65f91694eb",
    "usdm_v4.ttl": "7c6c7b2f79ecc9908a5b7cc7f75011a93245b34c54713d7ee9a19b00dc261deb",
    "usdm_v4.shapes.ttl": "a147ce44252c959d1d9e85954ea2a01be640eedb5d9dc7597ab15a428093b404",
    "usdm_v4.shapes-ct.ttl": "7985e9c2dee3bc1b2a47210368a0937d388c09269a3cf1a2b90da7cba3c4ac6d",
}

# The two input lines of notebook 60 the gate sets; every other line runs as published.
NB_STUDY_JSON = 'STUDY_JSON = "../downloads/CDISC_Pilot_Study.json"   # <-- point this at your own file'
NB_BASE_IRI = 'BASE_IRI = ""   # <-- required, e.g. "https://sponsor.example/studies/H2Q-MC-LZZT/"'
NB_CODE_CELLS = (2, 4, 6)


def check_manifest(path):
    schema = json.loads(MANIFEST_SCHEMA.read_text())
    manifest = yaml.safe_load(Path(path).read_text())
    errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(manifest),
                    key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(top)'}: {e.message}" for e in errors]


def check_pin():
    wrong = []
    for rel, expected in USDM_RDF_SHA256.items():
        f = USDM_RDF / rel
        if not f.exists():
            wrong.append(f"{rel}: missing")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != expected:
            wrong.append(f"{rel}: content differs from {USDM_RDF_TAG}")
    return wrong


def check_borrowed(unchecked):
    """Membership of the codes notebook 60 could not check, against the committed extract."""
    lines = CT_EXTRACT.read_text(encoding="utf-8").splitlines()
    sources = [l.split("\t")[1:3] for l in lines if l.startswith("# source\t")]
    table = [l.split("\t") for l in lines if not l.startswith("#")]
    cols = table[0]
    lists = {}
    for r in (dict(zip(cols, row)) for row in table[1:]):
        lists.setdefault(r["codelist"], (r["codelist_extensible"], set()))[1].add(r["code"])
    fails, warnings = [], []
    for r in unchecked.itertuples():
        if r.codelist not in lists:
            fails.append(f"{r.property}: codelist {r.codelist} not in {CT_EXTRACT.name}")
            continue
        extensible, members = lists[r.codelist]
        for code in r.codes.split():
            if code not in members:
                msg = f"{r.property}: {code} not in {r.codelist} (extensible={extensible})"
                (fails if extensible == "No" else warnings).append(msg)
    return fails, warnings, sources


def run_notebook_60(study_json, base_iri):
    nb = json.loads((USDM_RDF / "notebooks" / "60_validate_study.ipynb").read_text())
    cells = ["".join(nb["cells"][i]["source"]) for i in NB_CODE_CELLS]
    for line in (NB_STUDY_JSON, NB_BASE_IRI):
        if cells[0].count(line) != 1:
            raise RuntimeError(f"notebook 60 input line not found: {line!r}")
    cells[0] = (cells[0]
                .replace(NB_STUDY_JSON, f"STUDY_JSON = {str(Path(study_json).resolve())!r}")
                .replace(NB_BASE_IRI, f"BASE_IRI = {base_iri!r}"))
    ns = {"display": lambda df: print(df.to_string(index=False))}
    cwd = os.getcwd()
    os.chdir(USDM_RDF / "notebooks")   # the notebook reads the deliverables by relative path
    try:
        for i, src in zip(NB_CODE_CELLS, cells):
            print(f"\n--- notebook 60, cell {i}")
            exec(compile(src, f"60_validate_study.ipynb[{i}]", "exec"), ns)
    finally:
        os.chdir(cwd)
    return ns


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__.split("\n\n")[1])
    manifest_path, study_json = sys.argv[1], sys.argv[2]
    m = re.fullmatch(r"(.+)_usdm\.json", Path(study_json).name)
    if not m:
        sys.exit(f"{study_json}: expected a file named <ID>_usdm.json")
    base_iri = f"{INSTANCE_BASE}{m.group(1)}/"

    results = []

    manifest_errors = check_manifest(manifest_path)
    results.append(("M", "manifest schema", manifest_errors))

    pin_errors = check_pin()
    results.append(("P", f"usdm-rdf pinned at {USDM_RDF_TAG}", pin_errors))
    if pin_errors:
        report(results)
        sys.exit(1)

    print(f"base IRI:    {base_iri}")
    ns = run_notebook_60(study_json, base_iri)

    context_errors = (
        [f"unknown instanceType: {t}" for t in sorted(ns["unknown_types"])]
        + [f"unmapped key: {cls}.{k}" for cls, keys in sorted(ns["unmapped"].items()) for k in sorted(keys)]
        + [f"object with null id: {t}" for t in ns["null_ids"]]
        + [f"dangling: {p} -> {o}" for p, o in ns["dangling"]]
    )
    results.append(("C", "context conformance", context_errors))

    findings = ns["findings"]
    structural = findings[findings["layer"] == "structural"]
    results.append(("S", "structural SHACL", [
        f"{r.severity} {r.constraint} {r.path} on {r.focus}" for r in structural.itertuples()]))
    terminology = findings[findings["layer"] == "terminology"]
    violations = terminology[terminology["severity"] == "Violation"]
    results.append(("T", "terminology SHACL, violations", [
        f"{r.constraint} {r.path} on {r.focus}: {r.value}" for r in violations.itertuples()]))

    unchecked = ns["unchecked"]
    borrowed_fails, borrowed_warnings, sources = check_borrowed(unchecked)
    results.append(("B", "borrowed codelists, " + ", ".join(f"{p} {r}" for p, r in sources),
                    borrowed_fails))

    warnings = terminology[terminology["severity"] != "Violation"]
    print(f"\nborrowed codelists: {int(unchecked['distinct_codes'].sum())} distinct code(s) on "
          f"{len(unchecked)} binding(s) checked against {CT_EXTRACT.relative_to(REPO)}")
    print(f"reported, not judged: {len(warnings)} terminology warning(s); "
          f"{len(borrowed_warnings)} non-member(s) of extensible borrowed codelists")
    for w in borrowed_warnings:
        print(f"        {w}")

    report(results)
    sys.exit(0 if all(not errs for _, _, errs in results) else 1)


def report(results):
    print("\n=== USDM Instantiation gate")
    for check_id, name, errs in results:
        print(f"{'PASS' if not errs else 'FAIL'}  {check_id}  {name}")
        for e in errs:
            print(f"        {e}")


if __name__ == "__main__":
    main()
