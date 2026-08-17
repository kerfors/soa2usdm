"""Blinding audit — read every subagent transcript and report tool calls that reached outside the
blind tree.

The blinding is physical (the corpus is moved into the vault for the duration of the fan-out), so
this is the check on the physical measure, not a substitute for it. It reports two classes:

  LEAK    a tool call whose input names a path that would reveal prior output for the study being
          extracted, or the vault, or the code repo
  CROSS   a tool call reading another study's blind folder — not a baseline leak (a PDF is source,
          not output) but it means an agent wandered, and the pilot's blinding claim was
          "0 forbidden-path tool calls", so it is worth counting separately

Usage:  python3 audit_blinding.py <transcript_dir> [...]
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Paths that carry prior extraction output, baseline counts, or the checklist. Any of these inside
# a tool input is a leak regardless of which tool made the call.
FORBIDDEN = [
    (r"\.vault-", "the vault"),
    (r"soa2usdm-collections", "the collections repo"),
    (r"/SoA2USDM/(soa2usdm|documents|tests|tools)\b", "the code repo"),
    (r"re-extraction-(baseline|acceptance)", "the checklist / machine baseline"),
    (r"extraction\.verified", "verified extraction output"),
    (r"_corrections\.json", "a corrections sidecar"),
    (r"_resolved(\.|_)", "resolved output"),
    (r"_consolidated(\.|_)", "consolidated output"),
    (r"row_audit", "the row audit"),
    (r"activities\.json", "the collection activity list"),
    (r"tests/fixtures", "the test fixtures"),
    (r"/calib(/|\b)", "the calibration corpus"),
    (r"REDACTIONS\.json", "the redaction log"),
    (r"\bgit\b\s+(show|log|cat-file|grep)", "git history"),
]

STUDY = re.compile(r"(NCT\d{8}|[A-Z][A-Za-z0-9_]*_Pilot)")
BLIND = re.compile(r"/blind/([A-Za-z0-9_]+)")


def tool_inputs(path):
    """Yield (tool_name, serialised_input) for every tool_use in a transcript."""
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        stack = [rec]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("type") == "tool_use":
                    yield node.get("name", "?"), json.dumps(node.get("input", {}), ensure_ascii=False)
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)


def own_study(path):
    """The study an agent was working on, taken from its own transcript filename or first inputs."""
    m = STUDY.search(path.name)
    if m:
        return m.group(1)
    for _, inp in tool_inputs(path):
        m = BLIND.search(inp)
        if m:
            return m.group(1)
    return None


def main():
    dirs = [Path(d) for d in sys.argv[1:]]
    if not dirs:
        print(__doc__)
        return 1

    files = sorted(p for d in dirs for p in d.rglob("*.jsonl") if p.name != "journal.jsonl")
    if not files:
        print("no agent transcripts found")
        return 1

    leaks, crosses = [], []
    calls = Counter()
    for p in files:
        mine = own_study(p)
        for tool, inp in tool_inputs(p):
            calls[tool] += 1
            for pat, what in FORBIDDEN:
                if re.search(pat, inp):
                    leaks.append((p.name, tool, what, inp[:200]))
                    break
            else:
                for m in BLIND.finditer(inp):
                    if mine and m.group(1) != mine:
                        crosses.append((p.name, tool, mine, m.group(1)))
                        break

    print(f"transcripts: {len(files)}   tool calls: {sum(calls.values())}")
    print("  " + ", ".join(f"{k} {v}" for k, v in calls.most_common(10)))
    print(f"\nFORBIDDEN-PATH TOOL CALLS: {len(leaks)}")
    for name, tool, what, inp in leaks[:40]:
        print(f"  [{name}] {tool} -> {what}\n      {inp}")
    print(f"\nCROSS-STUDY READS: {len(crosses)}")
    for name, tool, mine, other in crosses[:40]:
        print(f"  [{name}] {tool}: agent for {mine} read {other}")
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
