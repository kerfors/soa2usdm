"""Timeline-anchor survey across consolidated SoAs — read-only, printed evidence only.

Usage:  python3 tools/anchor_survey.py [--json PATH]

Applies rules 1 and 2 of documents/timeline-anchors-experiment.md to every consolidated SoA in
every collection, and reports what the printed header says about the schedule's clock:

  clock       which main-segment row carries relative time (property_type study_day or week)
  convention  'zero' (the row prints a 0) or 'day1' (a day row whose anchor is Day 1), or none
  anchor      the first column carrying that zero / Day 1
  day 0       whether a 0 appears anywhere on the row, and whether the row visibly skips it (-1 -> 1)
  restarts    how often the printed value falls back along the column order (cycle / period restarts)
  unsigned    pre-anchor values printed without a sign ('<=28')
  event       what the anchor column marks: randomisation, first dose, or nothing named (rule 2)
  clocks      values measured from something other than the anchor ('after last dose', 'Post TxP')
  hours       a timepoint row counting hours or minutes (a clock inside a day)

Every printed value is kept next to the number read from it. A value the reader cannot read is
reported unread, never guessed. The event classification matches activity names against the two
patterns below; the per-protocol table prints the names so each call can be checked by eye.

Environment:
  SOA2USDM_COLLECTIONS   the collections tree (default: soa2usdm-collections/collections next to
                         this repo, as in soa2usdm/config.py)
"""

import collections
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COLLECTIONS = Path(os.environ.get("SOA2USDM_COLLECTIONS",
                                  REPO.parent / "soa2usdm-collections" / "collections"))

RANDOMISATION = re.compile(r"randomi[sz]", re.I)
FIRST_DOSE = re.compile(r"^(?!.*(schema|training|observe|determine)).*"
                        r"(dosing|study drug administration|dose administration)", re.I)
SECOND_CLOCK = re.compile(r"post|after last|after the last|following|end of", re.I)
HOURS = re.compile(r"\b(\d+\s*)?(hrs?|hours?|min|minutes?)\b", re.I)
WINDOW = re.compile(r"\s*\(\s*(?:[±+\-]|\+/-)\s*\d+[^)]*\)")


def read(value):
    """(kind, numbers) for one printed relative-time value.

    kind: empty | second_clock | unsigned_le | num | range | unread
    """
    s = value.replace("−", "-").replace("–", "-").replace("—", "-").replace("\n", " ").strip()
    if not s or s == "-":
        return ("empty", None)
    if SECOND_CLOCK.search(s):
        return ("second_clock", None)
    if re.match(r"^[≤<]\s*\d+", s):
        return ("unsigned_le", None)
    s = WINDOW.sub("", s)                                           # "(±1)", "(- 1 day)"
    s = re.sub(r"\s*\(HD\)", "", s)                                 # hemodialysis-day qualifier
    s = re.sub(r"\s*±\s*\d+\s*(?:d|days?)?\s*$", "", s)             # "15±3", "±3d"
    s = re.sub(r"\s+days?(\s+prior to day 1)?\s*$", "", s, flags=re.I)
    s = s.strip().strip("()").strip()
    s = re.sub(r"\bD(?:ays?)?\s*(?=-?\d)", "", s, flags=re.I)       # "D1", "Day 3", "D-42"
    m = re.fullmatch(r"(-?\d*\.?\d+)", s)
    if m:
        return ("num", [float(m.group(1))])
    m = re.fullmatch(r"(-?\d+)\s*(?:to|through|-)\s*(?:D\s*)?(-?\d+)", s, re.I)
    if m:
        return ("range", [float(m.group(1)), float(m.group(2))])
    return ("unread", None)


def survey_protocol(d):
    acts = {a["xact_id"]: a["activity_name"] for a in d["unified_activities"]}
    marks = collections.defaultdict(set)
    for m in d["schedule_matrix"]:
        if str(m.get("consolidated_value", "")).strip():
            marks[m["xact_id"]].add(m["xcol_id"])

    rows = collections.OrderedDict()      # (segment, type, name) -> [(xcol, label, value, (kind, nums))]
    second_clock, hours = [], []
    for seg, cols in d["timeline_segments"].items():
        for c in cols:
            for pv in c["property_values"]:
                v = pv["value"]
                if pv["property_type"] in ("study_day", "week"):
                    rows.setdefault((seg, pv["property_type"], pv["property_name"]), []).append(
                        (c["xcol_id"], c.get("composite_label", ""), v, read(v)))
                if v and SECOND_CLOCK.search(v) and pv["property_type"] in (
                        "study_day", "week", "timepoint", "other", "period", "visit", "window"):
                    second_clock.append(v.replace("\n", " "))
                if pv["property_type"] == "timepoint" and v and HOURS.search(v):
                    hours.append(v.replace("\n", " "))

    out = {"protocol_id": d["protocol_id"], "clock": None, "second_clock": sorted(set(second_clock)),
           "hours": sorted(set(hours))}
    main = [(k, vals) for k, vals in rows.items() if k[0] == "main"]
    if not main:
        out["types"] = sorted({pv["property_type"] for cols in d["timeline_segments"].values()
                               for c in cols for pv in c["property_values"]})
        return out

    def profile(key, vals):
        singles = [(x, lab, v, n[0]) for x, lab, v, (k, n) in vals if k == "num"]
        ranges = [n for *_, (k, n) in vals if k == "range"]
        seq = [n for *_, n in singles]
        zero = [(x, lab, v) for x, lab, v, n in singles if n == 0]
        one = [(x, lab, v) for x, lab, v, n in singles if n == 1]
        conv = "zero" if zero else ("day1" if one and key[1] == "study_day" else None)
        anchors = zero if zero else (one if conv else [])
        flat = seq + [z for r in ranges for z in r]
        return {
            "type": key[1], "name": key[2], "convention": conv,
            "anchor": anchors[0] if anchors else None, "n_anchor_columns": len(anchors),
            "negative": any(z < 0 for z in flat),
            "zero_in_range": any(0 in r for r in ranges),
            "skips_zero": not zero and 1 in seq and (-1 in seq or any(r[1] == -1 for r in ranges)),
            "restarts": sum(1 for a, b in zip(seq, seq[1:]) if b < a),
            "unsigned_le": [v for *_, v, (k, n) in vals if k == "unsigned_le"],
            "unread": [v.replace("\n", " ") for *_, v, (k, n) in vals if k == "unread"],
        }

    profiles = [profile(k, vals) for k, vals in main]
    clock = (next((p for p in profiles if p["convention"] == "zero"), None)
             or next((p for p in profiles if p["convention"] == "day1"), None)
             or profiles[0])
    out["clock"] = clock
    out["other_rows"] = [{"type": p["type"], "name": p["name"], "convention": p["convention"]}
                         for p in profiles if p is not clock]

    ax = clock["anchor"][0] if clock["anchor"] else None
    at_anchor = [(aid, acts[aid], len(cols)) for aid, cols in marks.items() if ax in cols]
    single = [(aid, name) for aid, name, n in at_anchor if n == 1]
    rand = [(aid, acts[aid], sorted(cols)) for aid, cols in marks.items() if RANDOMISATION.search(acts[aid])]
    rand_at_anchor = [name for aid, name in single if RANDOMISATION.search(name)]
    dose_at_anchor = [name for aid, name in single if FIRST_DOSE.search(name)]
    if rand_at_anchor:
        event = "randomisation"
    elif rand:
        event = "randomisation elsewhere"
    elif dose_at_anchor:
        event = "first dose"
    else:
        event = "not named"
    out["event"] = event
    out["event_evidence"] = (rand_at_anchor if event == "randomisation" else
                             dose_at_anchor if event == "first dose" else
                             [f"{n} at {', '.join(c)}" for _, n, c in rand] if event == "randomisation elsewhere" else [])
    out["single_mark_at_anchor"] = [name for _, name in single]
    out["randomisation_rows"] = [{"name": n, "columns": c} for _, n, c in rand]
    return out


def survey():
    results = []
    for f in sorted(COLLECTIONS.glob("*/protocols/*/SoA2USDM/consolidated/*_consolidated.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        r = survey_protocol(d)
        r["collection"] = f.relative_to(COLLECTIONS).parts[0]
        results.append(r)
    return results


def report(results):
    clocked = [r for r in results if r["clock"]]
    conv = collections.Counter((r["clock"]["type"], r["clock"]["convention"]) for r in clocked)
    print(f"{len(results)} consolidated SoAs in {COLLECTIONS}")
    print(f"  no day or week row: {len(results) - len(clocked)}  "
          f"{[r['protocol_id'] for r in results if not r['clock']]}")
    for (t, c), n in sorted(conv.items(), key=lambda kv: -kv[1]):
        print(f"  clock on a {t} row, convention {c}: {n}")
    days = [r for r in clocked if r["clock"]["type"] == "study_day"]
    print(f"  day rows printing 0 as a column: {sum(1 for r in days if r['clock']['convention'] == 'zero')}; "
          f"0 only inside a range: {[r['protocol_id'] for r in days if r['clock']['zero_in_range']]}; "
          f"visibly skipping 0 (-1 -> 1): {sum(1 for r in days if r['clock']['skips_zero'])}")
    print(f"  anchoring event: {dict(collections.Counter(r['event'] for r in clocked))}")
    print(f"  restarting clocks: {[(r['protocol_id'], r['clock']['restarts']) for r in clocked if r['clock']['restarts']]}")
    print(f"  unsigned pre-anchor values: {[(r['protocol_id'], r['clock']['unsigned_le']) for r in clocked if r['clock']['unsigned_le']]}")
    print(f"  second clocks: {len([r for r in results if r['second_clock']])} protocols")
    print(f"  hour clocks inside a day: {[(r['protocol_id'], r['hours']) for r in results if r['hours']]}")
    print()
    print("| Protocol | Clock row | Conv. | Anchor column (printed) | 0 printed | Restarts | Anchoring event | Second clock |")
    print("|---|---|---|---|---|---|---|---|")
    for r in results:
        pid = r["protocol_id"]
        if not r["clock"]:
            print(f"| {pid} | none ({', '.join(r['types'])}) | | | | | | {'; '.join(r['second_clock'])} |")
            continue
        c = r["clock"]
        anchor = f"{c['anchor'][0]} `{c['anchor'][2]}`" if c["anchor"] else "—"
        zero = "yes" if c["convention"] == "zero" else ("in a range" if c["zero_in_range"] else
                                                        ("no, skips −1→1" if c["skips_zero"] else "no"))
        event = r["event"] + (f" ({'; '.join(r['event_evidence'])})" if r["event_evidence"] else "")
        print(f"| {pid} | {c['type']}: {c['name'][:40]} | {c['convention'] or '—'} | {anchor} | {zero} | "
              f"{c['restarts'] or ''} | {event} | {'; '.join(v[:50] for v in r['second_clock'])} |")


def main():
    results = survey()
    report(results)
    if len(sys.argv) == 3 and sys.argv[1] == "--json":
        Path(sys.argv[2]).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    elif len(sys.argv) != 1:
        sys.exit(__doc__.split("\n\n")[1])


if __name__ == "__main__":
    main()
