"""Verify documents/re-extraction-baseline-mined.json against the uncertainty reports it was mined from.

Checks, per study: the exact key set at top level and in every item; `table` is an int or "all";
every `evidence_quote` is a verbatim substring of that study's report (after collapsing
whitespace); and the file's `counts` block matches the items. Exits 1 on any failure.

The mined file is interpretation, not machine baseline — this script checks that it quotes its
sources faithfully, not that its claims are right.

Environment (as for tools/gate.py):
  SOA2USDM_REPO         this repo (default: the tools/ parent)
  SOA2USDM_COLLECTIONS  the collections tree (config.py reads this)

Usage:  python tools/verify_mined.py [--mined PATH]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(os.environ.get("SOA2USDM_REPO", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO))

from soa2usdm import config  # noqa: E402

KINDS = {
    "invariants": {"table", "claim", "evidence_quote", "how_to_check"},
    "judgement_calls": {"table", "decision", "alternative", "evidence_quote"},
    "source_defects": {"table", "description", "handling_in_report", "evidence_quote"},
}
STUDY_KEYS = {"study", "report", "report_prompt_version", *KINDS}


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def verify_study(study, protocols_dir):
    """Return a list of failure messages for one study entry."""
    if set(study) != STUDY_KEYS:
        return [f"keys differ: {sorted(set(study) ^ STUDY_KEYS)}"]
    report = protocols_dir / study["study"] / "SoA2USDM" / "extracted" / study["report"]
    text = norm(report.read_text(encoding="utf-8"))
    failures = []
    for kind, keys in KINDS.items():
        for i, item in enumerate(study[kind]):
            if set(item) != keys:
                failures.append(f"{kind}[{i}] keys differ: {sorted(set(item) ^ keys)}")
                continue
            if not (item["table"] == "all" or isinstance(item["table"], int)):
                failures.append(f"{kind}[{i}] table {item['table']!r}")
            if norm(item["evidence_quote"]) not in text:
                failures.append(f"{kind}[{i}] not verbatim: {item['evidence_quote'][:120]!r}")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mined", default=str(REPO / "documents" / "re-extraction-baseline-mined.json"))
    args = parser.parse_args()

    mined = json.loads(Path(args.mined).read_text(encoding="utf-8"))
    protocols_dir = config.get_collection_path(mined["collection"])
    counts = {kind: sum(len(s[kind]) for s in mined["studies"]) for kind in KINDS}

    n_fail = 0
    if counts != mined["counts"]:
        print(f"counts block {mined['counts']} does not match the items {counts}")
        n_fail += 1
    for study in mined["studies"]:
        failures = verify_study(study, protocols_dir)
        n_items = sum(len(study.get(kind, [])) for kind in KINDS)
        print(f"{study['study']}: {n_items} items, {len(failures)} failure(s)")
        for msg in failures:
            print(f"   {msg}")
        n_fail += len(failures)

    print(f"{len(mined['studies'])} studies, {sum(counts.values())} items, {n_fail} failure(s)")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
