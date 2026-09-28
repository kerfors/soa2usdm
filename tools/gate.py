"""Per-table promotion gate — mechanical checks only, no judgement.

Implements the checks of the acceptance checklist's promotion gate (§8) that run on freshly
extracted tables in the staging area: 1-7, 9, 10, 12, 13, 14 and quote fidelity, under the
ids printed here. Checks 8 (row audit) and 11 (deterministic layers) run in dryrun.py because
they need the corpus, not the staging area; 15 (study criteria) and 16 (corrections) are
review steps.

Every check here is deterministic. Nothing in this file decides whether a delta is
acceptable — it only reports what the delta is.
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import jsonschema

# Paths come from the environment so the harness is not tied to one machine. Defaults are derived
# from this file's location inside the repo.
#   SOA2USDM_COLLECTIONS  the collections tree being read/rebuilt   (config.py reads this too)
#   SOA2USDM_STAGING      where extraction agents write             (never the corpus)
#   SOA2USDM_BLIND        blind/<STUDY>/ — the PDF and PAGEMAP.md the agents see
#   SOA2USDM_CALIB        a copy of the ACCEPTED corpus, for calibrating checks
#   SOA2USDM_SCRATCH      throwaway collection for rehearsals
#   SOA2USDM_BASELINE     per-table baseline JSON (default documents/re-extraction-baseline.json)
REPO = Path(os.environ.get("SOA2USDM_REPO", Path(__file__).resolve().parents[1]))
STAGING = Path(os.environ.get("SOA2USDM_STAGING", "staging"))
BLIND = Path(os.environ.get("SOA2USDM_BLIND", "blind"))
BASELINE = Path(os.environ.get("SOA2USDM_BASELINE", REPO / "documents" / "re-extraction-baseline.json"))
SCHEMA = REPO / "schemas" / "soa-table-extraction.schema.json"
PROMPT = REPO / "prompts" / "PDF_TO_JSON_PROMPT.md"
TAXONOMY = REPO / "documents" / "soa_table_type_definitions.md"
_pv = re.search(r"Prompt version (\d+\.\d+\.\d+)", PROMPT.read_text())
if not _pv:
    sys.exit(f"cannot read the prompt version from {PROMPT}")
PROMPT_VERSION = _pv.group(1)

sys.path.insert(0, str(REPO))
from soa2usdm.resolve import find_partial_marker_bindings

MARKER_ARRAYS = ("schedule_properties", "activities", "activity_schedule", "schedule_grid")

# Baseline tables the Phase 3 kickoff agrees should NOT reappear. Absent here means "the decision
# was taken before the sweep", not "the gate was relaxed to make a failure go away".
EXPECTED_ABSENT = {
    ("CDISC_Pilot", 2): "doc p.54 '(concluded)' reprints Table 1's rows under later columns — "
                        "one horizontally tiled table (§5), not main_soa + continuation. "
                        "Marks must be conserved: baseline 71 + 68 = 139 in the single table.",
}

POINTER_LEAD = re.compile(r"^(see|refer to|as (described|specified|detailed|defined) in)\b", re.I)


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def markers_on_rows(data):
    """marker -> set of row_positions carrying it in any annotation_markers string."""
    out = {}
    for name in MARKER_ARRAYS:
        for row in data.get(name, []):
            for m in (row.get("annotation_markers") or "").split(","):
                if m.strip():
                    out.setdefault(m.strip(), set()).add(row.get("row_position"))
    return out


def check_table(path, schema, base):
    """Return (findings, metrics) for one extraction JSON."""
    f = []
    data = json.loads(path.read_text())

    # 1 — schema valid, header fields
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        f.append(("1 schema", "FAIL", f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message[:180]}"))
    if data.get("schema_name") != "soa-table-extraction":
        f.append(("1 schema", "FAIL", f"schema_name={data.get('schema_name')!r}"))
    if str(data.get("schema_version")) != "1.0":
        f.append(("1 schema", "FAIL", f"schema_version={data.get('schema_version')!r}"))
    status = data.get("extraction_metadata", {}).get("extraction_status")
    if status != "ready_for_resolution":
        f.append(("1 schema", "FAIL", f"extraction_status={status!r}"))

    # 1c — no private-use code points (prompt §1c, Symbol-font glyphs). A symbol font's glyph copied
    # from the text layer (U+F0B1 where the page shows '±') is not a character anyone can read
    # downstream; the 3.9.0 and 3.9.1 acceptance runs both shipped one while the report claimed '±'.
    strings = []
    json_strings(data, strings)
    pua = sorted({f"U+{ord(c):04X}" for s in strings for c in s if 0xE000 <= ord(c) <= 0xF8FF})
    if pua:
        f.append(("1c characters", "FAIL", f"private-use code point(s) in text fields: {', '.join(pua)}"))

    # 14 — provenance (prompt v3.8.1+). The accepted corpus predates both fields, so their joint
    # absence is CHECK, not FAIL — otherwise calibration against calib/ would fail every table.
    # Once either field is present the table is v3.8.1+ output: prompt_version must match the repo
    # prompt, and model must have been stamped by tools/stamp_model.py.
    em = data.get("extraction_metadata", {})
    pv, mdl = em.get("prompt_version"), em.get("model")
    if pv is None and mdl is None:
        f.append(("14 provenance", "CHECK", "no model / prompt_version (pre-v3.8.1 output?)"))
    else:
        if pv != PROMPT_VERSION:
            f.append(("14 provenance", "FAIL", f"prompt_version={pv!r}, repo prompt is {PROMPT_VERSION}"))
        if not mdl:
            f.append(("14 provenance", "FAIL", "model not stamped — run tools/stamp_model.py"))

    annots = data.get("annotations", [])
    meta = data.get("table_metadata", {})

    # 2 — no orphan annotations
    for a in annots:
        if not a.get("marker_locations"):
            f.append(("2 orphan", "FAIL", f"annotation {a.get('annotation_marker')!r} has no marker_locations"))

    # 3 — markers agree both ways
    for msg in find_partial_marker_bindings(data):
        f.append(("3 binding", "FAIL", msg))
    on_rows = markers_on_rows(data)
    for a in annots:
        m = a.get("annotation_marker", "")
        # legend and abbreviation entries do not bind through annotation_markers: a legend-defined
        # in-grid mark stays in cell_value (§5) and an abbreviation binds through the term printed
        # in the label. Only footnote and source_note markers are cleaned out into annotation_markers.
        if a.get("annotation_type") in ("legend", "abbreviation"):
            continue
        declared = [l for l in a.get("marker_locations", []) if l.get("location_type") != "unresolved"]
        if declared and not on_rows.get(m):
            # §6 table-scope exception: a note printed on the Notes-column HEADER has no modelled
            # element, so the prompt mandates exactly this shape — one schedule_property location
            # with method 'synthesized', and the marker deliberately NOT on any element's
            # annotation_markers. Calibration against the accepted corpus found 8 of these across
            # 6 studies (note1/note2/'c' in NCT03421379, NCT03817853, NCT04004988, NCT04320615,
            # NCT04573309, NCT04730349) — the check as first written failed all 8, i.e. it would
            # have failed a perfect re-extraction.
            scoped = all(l.get("location_type") == "schedule_property" for l in declared)
            if scoped and all(l.get("method") == "synthesized" for l in declared):
                continue
            if scoped and all(l.get("method") is None for l in declared):
                # legacy shape: right convention, but §1e provenance is missing. On v3.7.2 output
                # that absence is itself the finding, so report rather than pass silently.
                f.append(("3 binding", "CHECK",
                          f"annotation {m!r} is a table-scope note bound only to a schedule_property "
                          f"and to no element — the §6 convention, but the location carries no "
                          f"method: 'synthesized' (§1e requires it)"))
                continue
            f.append(("3 binding", "FAIL",
                      f"annotation {m!r} declares {len(declared)} location(s) but the marker appears "
                      f"in no annotation_markers string anywhere — it binds nothing"))

    # 4 — no containment pairs
    texts = [(a.get("annotation_marker"), norm(a.get("annotation_text"))) for a in annots]
    # Strict containment only. Two annotations carrying the SAME text are not a split note —
    # a note that genuinely prints twice is source-faithful (the corpus has a documented case),
    # so equal texts are reported separately for eyes, not as a gate failure.
    for i, (mi, ti) in enumerate(texts):
        for j, (mj, tj) in enumerate(texts):
            if i != j and ti and tj and len(ti) >= 25 and ti != tj and ti in tj:
                # CHECK, not FAIL. §8 reads containment as "one note cell was split across rows",
                # but the baseline corpus contains a containment pair that is source-faithful:
                # NCT04677179 T1 c14/c15, where doc p.20 prints the short note on the serum-
                # pregnancy row and doc p.21 opens the urine-pregnancy note with the same
                # sentence. Verified against the de-glyphed text layer of both pages. So a
                # containment pair needs page verification; it cannot be auto-failed.
                f.append(("4 containment", "CHECK", f"text of {mi!r} is strictly contained in {mj!r} — verify against the page"))
    seen = {}
    for m, t in texts:
        if t and len(t) >= 25:
            seen.setdefault(t, []).append(m)
    for t, ms in seen.items():
        if len(ms) > 1:
            f.append(("4 duplicate-text", "CHECK", f"annotations {ms} carry identical text — {t[:90]!r}"))

    # 5a — a bare pointer is a source_note, not a footnote (§6). Single-sentence test: no
    # period-space after the final stop, so "See Section 8.2.2." counts as one sentence while
    # "See Appendix 2 for details. Day 1 predose sample is for baseline only." does not — the
    # latter explains as well as points, and footnote is right for it.
    for a in annots:
        t = norm(a.get("annotation_text"))
        if not POINTER_LEAD.match(t) or len(t) > 130:
            continue
        body = t[:-1] if t.endswith(".") else t
        if ". " in body or "; " in body:
            continue
        if a.get("annotation_type") != "source_note":
            f.append(("5a typing", "CHECK",
                      f"{a.get('annotation_marker')!r} is a bare cross-reference typed "
                      f"{a.get('annotation_type')!r} — §6 types these source_note: {t!r}"))

    # 5 — typing not degenerate
    by_type = Counter(a.get("annotation_type") for a in annots)
    if len(annots) > 20 and len(by_type) == 1 and "source_note" in by_type:
        f.append(("5 typing", "FAIL", f"all {len(annots)} annotations are source_note"))

    # 6 — page coverage
    ps, pe = meta.get("page_start"), meta.get("page_end")
    pages = Counter(a.get("source_page") for a in data.get("activities", []))
    n_acts = len(data.get("activities", []))
    if pages.get(None) == n_acts and n_acts:
        # no source_page anywhere — pre-v3.6.0 shape; the per-page check cannot run at all
        f.append(("6 coverage", "WARN", "no activity carries source_page — page coverage not checkable"))
    else:
        if None in pages:
            f.append(("6 coverage", "WARN", f"{pages[None]} of {n_acts} activities carry no source_page"))
        if isinstance(ps, int) and isinstance(pe, int):
            empty = [p for p in range(ps, pe + 1) if not pages.get(p)]
            if empty:
                f.append(("6 coverage", "WARN",
                          f"doc page(s) {empty} contributed no activity rows — report must say why"))

    # 9 — a merged mark is distributed consistently. activity_schedule has no is_merged_cell (the
    # schema defines it only on schedule_grid), so the first version of this check read a field
    # that is never there and could not fire. What activity_schedule does carry is source_range
    # "a:b" on each column a merged value was distributed to: the entry's own column must lie in
    # the range, and every column of the range must be present on the row with the same value and
    # the same range. Calibrated 0 findings over 471 such entries in 45 accepted tables (2026-09-27).
    cells = {(e.get("row_position"), e.get("column_position")): e for e in data.get("activity_schedule", [])}
    for e in data.get("activity_schedule", []):
        sr = e.get("source_range")
        if not sr:
            continue
        r, c = e.get("row_position"), e.get("column_position")
        a, b = (int(x) for x in sr.split(":"))
        if not a <= c <= b:
            f.append(("9 merged", "FAIL", f"activity_schedule r{r}c{c} lies outside its source_range {sr}"))
            continue
        for k in range(a, b + 1):
            o = cells.get((r, k))
            if o is None or o.get("cell_value") != e.get("cell_value") or o.get("source_range") != sr:
                f.append(("9 merged", "FAIL",
                          f"activity_schedule r{r}c{c} source_range {sr}: column {k} "
                          f"{'missing' if o is None else 'differs'}"))
                break

    # 10 — track_label only on track
    tt, tl = meta.get("table_type"), meta.get("track_label")
    if tt == "track" and not tl:
        f.append(("10 track", "FAIL", "table_type track without track_label"))
    if tt != "track" and tl:
        f.append(("10 track", "FAIL", f"table_type {tt} carries track_label {tl!r}"))
    # Review signal, not a gate: §2 asks for a concise identifier and agents drift into restating
    # the table title. These strings surface as population_track on every column of the table.
    # Count meaningful words: a slash-joined compound ("Early Termination / Unscheduled /
    # Post-Treatment") is one identifier listing three phases, not six words, and that label is
    # accepted corpus content — a naive split() flags it.
    if tl:
        n = len([w for w in re.split(r"[\s/,]+", tl) if w and w.lower() not in ("and", "-", "&")])
        if n > 4:
            f.append(("10 track", "CHECK",
                      f"track_label is {n} words — §2 asks for a short identifier: {tl!r}"))

    # 12 — bindings did not vanish wholesale.
    #
    # `resolve` links an annotation to its element through the ROW's annotation_markers string, so
    # the number of distinct markers actually carried on rows is the count that decides whether the
    # notes reach anything. Checks 2 and 3 cannot see this collapse: check 2 only asks that an
    # annotation declares a location, and check 3 fires on DISAGREEMENT between the two sides — when
    # BOTH sides are empty there is nothing partial and it passes. NCT04184622 T1 went from 27
    # markers on rows to 1 while its 27 notes were re-emitted as a separate table's rows, and the
    # whole gate passed. Only this count showed it.
    #
    # Reported as a metric on every table so the delta table carries it; a finding only when the
    # bindings fall away while the ROWS are still there, which is the signature of markers being
    # stripped rather than of the table's content genuinely changing.
    bind = len(on_rows)
    # `base` is the whole {(study, table): row} map, not one row — look this table's row up from the
    # filename. (Fetching base.get("bind") off the map silently yields None, which made this check
    # pass on the very collapse it was written for. Caught by running it as a negative control.)
    b_row = base.get((path.name.split("_Table_")[0], int(re.search(r"_Table_(\d+)_", path.name).group(1))))
    if b_row is not None:
        b_bind, b_acts = b_row.get("bind"), b_row.get("acts")
        n_acts = len(data.get("activities", []))
        if isinstance(b_bind, int) and b_bind > 0 and isinstance(b_acts, int) and n_acts >= b_acts:
            if bind == 0:
                f.append(("12 bindings", "FAIL",
                          f"every marker binding is gone: baseline carried {b_bind} distinct marker(s) "
                          f"on rows, this table carries none, while activities went {b_acts} -> {n_acts}"))
            elif bind * 2 < b_bind:
                f.append(("12 bindings", "FAIL",
                          f"marker bindings collapsed {b_bind} -> {bind} while activities went "
                          f"{b_acts} -> {n_acts} — the rows are still here, so the notes that bound to "
                          f"them have gone somewhere else"))
            elif bind < b_bind:
                f.append(("12 bindings", "CHECK",
                          f"marker bindings {b_bind} -> {bind} with activities {b_acts} -> {n_acts}"))

    metrics = {
        "ttype": tt,
        "pages": f"{ps}-{pe}",
        "acts": len(data.get("activities", [])),
        "bind": bind,
        # Non-empty marks only. Whether an empty cell is emitted as an entry is a convention that
        # flips between runs (NCT04004988: 90 marks, 280 entries), so counting entries reports a
        # delta where the schedule is unchanged.
        "marks": sum(1 for e in data.get("activity_schedule", []) if norm(e.get("cell_value"))),
        "props": len(data.get("schedule_properties", [])),
        "grid": len(data.get("schedule_grid", [])),
        "ann": len(annots),
        "fn": by_type.get("footnote", 0),
        "sn": by_type.get("source_note", 0),
        "ab": by_type.get("abbreviation", 0),
        "lg": by_type.get("legend", 0),
    }
    return f, metrics


def json_strings(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            json_strings(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            json_strings(v, acc)
    elif isinstance(obj, str):
        acc.append(norm(obj))


# Only double-quoted natural-language spans are treated as evidence quotes. Backticked spans in
# these reports are field names and code (`annotation_markers`, `location_type: "unresolved"`),
# and quoting the prompt or the schema is not quoting the source — neither is evidence about the
# PDF, and including them buries the real misses in noise.
QUOTE_RE = re.compile(r'"([^"\n]{30,400})"|“([^”\n]{30,400})”')

# Discards, in order: markdown emphasis or table pipes (the span crossed formatting, so it was
# never a contiguous quote); snake_case / dotted identifiers; paths and filenames; spans quoting
# the prompt's own rule text rather than the protocol.
QUOTE_SKIP = re.compile(r'\*\*|\||`|_[a-z]|\.(json|md|pdf)\b|/root/|§|→|\bschedule_|\bactivity_|\bannotation_|\bmarker_|\bproperty_|\bsource_range\b|\btable_type\b|\bcell_value\b'
                        r'|\bthe term printed as a marker\b|\bmarker referenced but not defined\b'
                        r'|\bread the boundaries from a\b|\bmerely occurring inside running text\b')

# An ellipsis marks a deliberately abridged quote ("An overview … Table 2-1, 2-2, 2-3"). The whole
# string is not a substring of anything by construction, so match each fragment instead. Calibration
# against the accepted corpus: 4 of the 21 unverified quotes were abridged this way, not composed.
ELLIPSIS = re.compile(r'\s*(?:…|\.\.\.)\s*')


def quoted_spans(text):
    """Yield the INSIDE of each quoted span, line by line.

    A regex that matches "..." finds a first span, resumes after its closing quote, and then pairs
    the NEXT two quote characters — which on a line carrying two quotations
    (`the header reads "A" — and footnote e says "B"`) makes the connective prose between them look
    like a third quotation. Every one of the 23 "unverified" quotes in the first full-corpus run was
    this artefact or an agent quoting the prompt's own rule text; none was composed evidence about a
    PDF. Splitting each line on the quote character and taking the odd-index pieces alternates
    outside/inside correctly, which a resuming regex cannot do.
    """
    # Quotations WRAP across source lines, so per-line parity is wrong for any line that opens
    # inside a quotation — that was the residual 9 of the original 23. Join each blank-line-separated
    # block into one line first, so an opening quote and its closing quote land in the same string.
    blocks = [" ".join(b.split()) for b in re.split(r"\n\s*\n", text)]
    for line in blocks:
        for ch in ('"', '“”'):
            if len(ch) == 2:
                parts = re.split(r"[“”]", line)
            else:
                parts = line.split(ch)
            if len(parts) < 3:
                continue
            for inside in parts[1::2]:
                q = norm(inside)
                if 30 <= len(q) <= 400:
                    yield q


DECISION_ROW = re.compile(r"^\|\s*(D\d+)\s*\|", re.M)


def check_review_items(study):
    """Check 13: the report's Decisions-needed block and the review_items arrays agree one-to-one.

    Ids are protocol-unique by contract, so they are compared as sets across all tables of the
    study. An extraction with no review_items key at all (pre-v3.8.0) is reported once as CHECK,
    not FAIL, so older studies can still pass the gate; a present-but-mismatching set FAILS.
    """
    d = STAGING / study
    reports = sorted(d.glob("*_uncertainty_report.md"))
    if not reports:
        return [("13 review", "WARN", "no report found")]
    # A study can carry more than one report (NCT03637764 since item 19: the protocol report and the
    # flow-chart report). Every report's block counts; the ids are compared over their union (item 21d).
    blocks = []
    for rp in reports:
        m = re.search(r"^## Decisions needed \((\d+)\)(.*?)(?=^## |\Z)", rp.read_text(), re.M | re.S)
        if m:
            blocks.append((rp.name, int(m.group(1)), set(DECISION_ROW.findall(m.group(2)))))
    block = bool(blocks)
    in_report = set().union(*(rows for _, _, rows in blocks))
    in_data, carried = [], 0
    for p in sorted(d.glob("*_extraction.json")):
        doc = json.loads(p.read_text())
        if "review_items" in doc:
            carried += 1
            in_data.extend(i["id"] for i in doc["review_items"])
    out = []
    if not carried:
        # Pre-v3.8.0 output: neither the block nor the arrays are required, so nothing here can
        # FAIL — the accepted corpus must keep gating at 0 FAIL (the calibration rule).
        out.append(("13 review", "CHECK", f"no table carries review_items (pre-v3.8.0 output?); "
                    f"report {'lists ' + str(sorted(in_report)) if block else 'has no Decisions-needed block'}"))
        return out
    if not block:
        out.append(("13 review", "FAIL", "report has no '## Decisions needed (N)' block"))
    for name, n, rows in blocks:
        if n != len(rows):
            out.append(("13 review", "FAIL", f"{name}: block says ({n}) but lists {len(rows)} rows"))
    if len(in_data) != len(set(in_data)):
        out.append(("13 review", "FAIL", f"duplicate review_items ids across tables: {sorted(in_data)}"))
    only_report, only_data = in_report - set(in_data), set(in_data) - in_report
    if only_report or only_data:
        out.append(("13 review", "FAIL", f"report-only {sorted(only_report)}, data-only {sorted(only_data)}"))
    if not out:
        out.append(("13 review", "OK", f"{len(in_report)} decision(s), block and review_items agree"))
    return out


def check_quotes(study):
    """Every quotation in the uncertainty report must be a verbatim substring of the source."""
    d = STAGING / study
    reports = sorted(d.glob("*_uncertainty_report.md")) + sorted(d.glob("*_notes.md"))
    if not reports:
        return [("quotes", "WARN", "no report found")]

    pdf = BLIND / study / f"{study}_soa.pdf"
    haystack = [norm(subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                                    capture_output=True, text=True).stdout)]
    for p in sorted(d.glob("*_extraction.json")):
        acc = []
        json_strings(json.loads(p.read_text()), acc)
        haystack.append(" ⏎ ".join(acc))
    hay = " ⏎ ".join(haystack)
    hay_tight = re.sub(r"\s+", "", hay)
    # The extractor also reads the prompt and the taxonomy. A span quoted from them is verbatim
    # but is not evidence about the PDF, so it is skipped like the rule text in QUOTE_SKIP, not
    # counted as verified. Before this, such a span showed as unverified (sweep 2: 2 false positives).
    # Markdown emphasis and code marks are stripped: a report quoting a rule sentence drops the
    # backticks around a term (3.9.1 acceptance: 1 false positive).
    instr = norm(re.sub(r"[`*]", "", PROMPT.read_text() + " ⏎ " + TAXONOMY.read_text()))
    instr_tight = re.sub(r"\s+", "", instr)

    out, n_ok, n_bad, n_skip = [], 0, 0, 0
    for rp in reports:
        for q in quoted_spans(rp.read_text()):
            if QUOTE_SKIP.search(q) or len(q.split()) < 4:
                n_skip += 1
                continue
            frags = [x for x in ELLIPSIS.split(q) if len(x) >= 15]
            if not frags:
                n_skip += 1
                continue
            if all(x in hay or re.sub(r"\s+", "", x) in hay_tight for x in frags):
                n_ok += 1
            elif all(x in instr or re.sub(r"\s+", "", x) in instr_tight for x in frags):
                n_skip += 1
            else:
                n_bad += 1
                out.append(("quotes", "CHECK", f"{rp.name}: not a verbatim substring — {q[:160]!r}"))
    out.insert(0, ("quotes", "INFO",
                   f"{n_ok} verbatim, {n_bad} unverified, {n_skip} skipped as non-evidence "
                   f"across {len(reports)} report file(s)"))
    return out


def main():
    schema = json.loads(SCHEMA.read_text())
    base = {(r["study"], r["table"]): r for r in json.loads(BASELINE.read_text())["per_table_metrics"]}
    studies = sys.argv[1:] or sorted(p.name for p in STAGING.iterdir() if p.is_dir())

    # The committed baseline JSON predates the binding metric, so derive it from the accepted corpus
    # rather than editing a signed-off artefact. Absent CALIB, check 12 simply does not run.
    calib = Path(os.environ.get("SOA2USDM_CALIB", "calib"))
    if calib.is_dir():
        n_derived = 0
        for p in sorted(calib.glob("*/*_Table_*_extraction.json")):
            s = p.name.split("_Table_")[0]
            t = int(re.search(r"_Table_(\d+)_", p.name).group(1))
            if (s, t) in base:
                base[(s, t)]["bind"] = len(markers_on_rows(json.loads(p.read_text())))
                n_derived += 1
        print(f"binding baseline derived from the accepted corpus for {n_derived} table(s)")
    else:
        print(f"NOTE: {calib} not found — check 12 (bindings) will not run")

    KEYS = ["ttype", "pages", "acts", "bind", "marks", "props", "grid", "ann", "fn", "sn", "ab", "lg"]
    total_fail = 0

    for study in studies:
        print(f"\n{'=' * 78}\n{study}\n{'=' * 78}")
        files = sorted((STAGING / study).glob(f"{study}_Table_*_extraction.json"))
        if not files:
            print("  no extraction JSON in staging")
            continue

        for path in files:
            tno = int(re.search(r"_Table_(\d+)_", path.name).group(1))
            findings, metrics = check_table(path, schema, base)
            b = base.get((study, tno))
            print(f"\n-- Table {tno:02d} --")
            if b:
                print(f"  {'metric':<8} {'baseline':>12} {'new':>12}   delta")
                for k in KEYS:
                    bv, nv = b.get(k), metrics.get(k)
                    if isinstance(bv, int) and isinstance(nv, int):
                        d = nv - bv
                        flag = "" if d == 0 else f"  {d:+d}"
                    else:
                        flag = "" if str(bv) == str(nv) else "  CHANGED"
                    print(f"  {k:<8} {str(bv):>12} {str(nv):>12}{flag}")
            else:
                print(f"  no baseline row for table {tno} — NEW TABLE")
                for k in KEYS:
                    print(f"  {k:<8} {'-':>12} {str(metrics.get(k)):>12}   NEW")
            if findings:
                print("  gate findings:")
                for name, level, msg in findings:
                    print(f"    [{level}] {name}: {msg}")
                    total_fail += level == "FAIL"
            else:
                print("  gate: all mechanical checks pass")

        # baseline tables with no counterpart in staging
        got = {int(re.search(r"_Table_(\d+)_", p.name).group(1)) for p in files}
        for (s, t) in sorted(base):
            if s == study and t not in got:
                why = EXPECTED_ABSENT.get((s, t))
                if why:
                    print(f"\n-- Table {t:02d} -- absent from staging, EXPECTED: {why}")
                else:
                    print(f"\n-- Table {t:02d} -- MISSING from staging (baseline has it)")
                    total_fail += 1

        for name, level, msg in check_quotes(study) + check_review_items(study):
            print(f"  [{level}] {name}: {msg}")
            total_fail += level == "FAIL"

    print(f"\n{'=' * 78}\n{total_fail} FAIL-level finding(s)")


if __name__ == "__main__":
    main()
