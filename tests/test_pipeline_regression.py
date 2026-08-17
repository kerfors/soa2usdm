"""
Regression fixture for the deterministic pipeline (resolve -> consolidate).

For every protocol in the collection that has a verified extraction plus golden
resolved + consolidated JSON, re-running resolve+consolidate on the verified
extraction must reproduce the golden output exactly (timestamps scrubbed).

Runs against a temp copy via a throwaway collection key, so the real golden
files are never touched. To bank a new protocol: drop its verified extraction
and golden resolved/consolidated into place; this test discovers it automatically.

On top of the golden diff, every discovered protocol is checked for annotation
text integrity — adjacent-pair containment, over-merge, and degenerate
source_note typing. The two banked fixture protocols are clean current goldens:
NCT04677179 (the hardest source in the corpus — raster pages, tiled tables,
reworked annotation layer) and NCT03637764 (clean from the start).

Every detector also has a negative control in fixtures/negative/ — a real
historical bad state, taken from the collections git history, on which the
detector must fire. A detector that only ever returns nothing is
indistinguishable from a clean corpus.
"""
import json
import shutil
from pathlib import Path

import pytest

from soa2usdm import config
from soa2usdm.errors import Errors
from soa2usdm.analytics import Analytics
from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import (
    ResolveStep,
    find_partial_marker_bindings,
    is_legend_annotation,
    is_redacted_activity_name,
    resolve_extraction,
    validate_extraction,
)
from soa2usdm.consolidate import (
    ConsolidateStep,
    find_adjacent_text_overlaps,
    find_cross_table_binding_conflicts,
    find_header_bound_annotations,
    find_over_merged_annotations,
    is_degenerate_annotation_typing,
    OVERLAP_PAIR_THRESHOLD,
)

VOLATILE = {"resolved_at", "consolidated_at", "extracted_at"}


def discover_cases():
    """(collection, protocol) for every protocol, in any registered collection,
    that has a verified extraction AND golden resolved + consolidated."""
    cases = []
    for collection, protocols_dir in config.COLLECTIONS.items():
        if not Path(protocols_dir).is_dir():
            continue
        for d in sorted(p for p in Path(protocols_dir).iterdir()
                        if p.is_dir() and not p.name.startswith(".")):
            soa = d / "SoA2USDM"
            if (list((soa / "extracted").glob("*_extraction.json"))
                    and list((soa / "resolved").glob("*_resolved.json"))
                    and list((soa / "consolidated").glob("*_consolidated.json"))):
                cases.append((collection, d.name))
    return cases


CASES = discover_cases()


def scrub(obj):
    """Recursively drop volatile timestamp keys for stable comparison."""
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


@pytest.fixture(params=CASES, ids=[f"{c}/{p}" for c, p in CASES])
def pipeline_output(request, tmp_path):
    """Copy one protocol's extraction into a temp collection, run resolve+consolidate,
    and yield (case_id, produced_dir, golden_dir), where case_id is "<collection>/<protocol>" —
    the same string pytest uses as the test id. The two pinned expectation tables below are keyed
    by it, so a banked fixture (a frozen snapshot) keeps its own expected values while the live
    collection is free to move."""
    collection, protocol = request.param
    golden = Path(config.COLLECTIONS[collection]) / protocol / "SoA2USDM"

    coll = tmp_path / "protocols"
    extracted = coll / protocol / "SoA2USDM" / "extracted"
    extracted.mkdir(parents=True)
    for f in (golden / "extracted").glob("*_extraction.json"):
        shutil.copy(f, extracted / f.name)
    for f in (golden / "extracted").glob("*_corrections.json"):
        shutil.copy(f, extracted / f.name)

    key = "regression_tmp"
    config.COLLECTIONS[key] = coll
    errors = Errors()
    analytics = Analytics()
    data = {"source": {"protocol_id": protocol, "collection": key}}
    for step_cls in (ApplyCorrectionsStep, ResolveStep, ConsolidateStep):
        data[step_cls.step_name] = step_cls(errors, analytics).execute(data)
    assert not errors.has_errors(), [(e.step, e.message) for e in errors.all]

    yield f"{collection}/{protocol}", coll / protocol / "SoA2USDM", golden
    config.COLLECTIONS.pop(key, None)


def test_resolved_matches_golden(pipeline_output):
    protocol, produced, golden = pipeline_output
    golden_files = sorted((golden / "resolved").glob("*_resolved.json"))
    assert golden_files, f"{protocol}: no golden resolved files"
    for gf in golden_files:
        pf = produced / "resolved" / gf.name
        assert pf.exists(), f"{protocol}: resolve did not produce {gf.name}"
        assert scrub(json.loads(pf.read_text())) == scrub(json.loads(gf.read_text())), \
            f"{protocol}: resolved mismatch in {gf.name}"


def test_consolidated_matches_golden(pipeline_output):
    protocol, produced, golden = pipeline_output
    gf = next((golden / "consolidated").glob("*_consolidated.json"))
    pf = produced / "consolidated" / gf.name
    assert pf.exists(), f"{protocol}: consolidate produced no output"
    assert scrub(json.loads(pf.read_text())) == scrub(json.loads(gf.read_text())), \
        f"{protocol}: consolidated mismatch"


def consolidated_annotations(produced):
    """The unified annotations the pipeline just produced for this protocol."""
    pf = next((produced / "consolidated").glob("*_consolidated.json"))
    return json.loads(pf.read_text())["unified_annotations"]


def test_annotations_not_fragmented(pipeline_output):
    """A single notes-column cell split across the rows it overlaps surfaces as
    consecutive annotations whose text contains one another. Measured over 22
    protocols: clean ones score 0-1, the fragmented NCT04677179 extraction scored 13."""
    protocol, produced, _ = pipeline_output
    pairs = find_adjacent_text_overlaps(consolidated_annotations(produced))
    assert len(pairs) < OVERLAP_PAIR_THRESHOLD, \
        f"{protocol}: {len(pairs)} adjacent annotation pairs share contained text: {pairs}"


def test_annotations_not_over_merged(pipeline_output):
    """The opposite of fragmentation: two adjacent note cells read as one annotation.
    A merged pair repeats a shared sentence block; a single cell does not repeat itself."""
    protocol, produced, _ = pipeline_output
    hits = find_over_merged_annotations(consolidated_annotations(produced))
    assert not hits, f"{protocol}: annotations carry repeated text blocks: {hits}"


def test_over_merge_detector_fires_on_known_bad():
    """Negative control — the detector is worthless if it only ever returns nothing.

    These are NCT04677179's annotations as committed before the notes were re-bounded
    by rule-line geometry; three of them concatenate two source cells.
    """
    path = (Path(__file__).parent / "fixtures" / "negative"
            / "NCT04677179_overmerged_annotations.json")
    annotations = json.loads(path.read_text())["unified_annotations"]
    hits = find_over_merged_annotations(annotations)
    assert len(hits) == 3, f"expected the 3 known over-merges, got {hits}"


def test_annotation_typing_not_degenerate(pipeline_output):
    """All-source_note means a notes/comments column was read as cross-references
    instead of footnotes. All-footnote is normal and must not trip this."""
    protocol, produced, _ = pipeline_output
    annotations = consolidated_annotations(produced)
    assert not is_degenerate_annotation_typing(annotations), \
        f"{protocol}: all {len(annotations)} annotations typed source_note"


def negative_fixture(name):
    path = Path(__file__).parent / "fixtures" / "negative" / name
    return json.loads(path.read_text())


def test_fragmentation_detector_fires_on_known_bad():
    """Negative control — NCT04677179's consolidated annotations as committed at
    2d0f58d, before the 2026-07-28 annotation re-extraction: each Comment cell was
    split across the rows it overlapped, yielding 77 fragments and 13 adjacent
    pairs where one text contains the other."""
    annotations = negative_fixture(
        "NCT04677179_fragmented_annotations.json")["unified_annotations"]
    pairs = find_adjacent_text_overlaps(annotations)
    assert len(pairs) == 13, f"expected 13 fragmentation pairs, got {len(pairs)}"


def test_degenerate_typing_detector_fires_on_known_bad():
    """Negative control — the same 2d0f58d state also mis-typed every one of its
    77 annotations as source_note (the notes column read as cross-references)."""
    annotations = negative_fixture(
        "NCT04677179_fragmented_annotations.json")["unified_annotations"]
    assert is_degenerate_annotation_typing(annotations), \
        "detector must fire on the all-source_note historical state"


def test_cross_table_conflict_detector_fires_on_known_bad():
    """Negative control — NCT04677179's consolidated output as committed at a96cf0c,
    before the missing Genetics sample row was restored in Tables 2-4. The DNA
    pharmacogenetics note (xannot-024) then bound to Genetics sample in Table 1 but
    to Flow cytometry panel / CCI in the tables missing the row — the fingerprint
    of a dropped row. xannot-023 is the known co-detection: identical PK note text
    legitimately printed on two adjacent rows, a documented detector limitation."""
    data = negative_fixture("NCT04677179_conflicting_bindings.json")
    conflicts = dict(find_cross_table_binding_conflicts(data))
    assert set(conflicts) == {"xannot-023", "xannot-024"}, \
        f"expected xannot-023 and xannot-024, got {sorted(conflicts)}"
    assert "Genetics sample" in conflicts["xannot-024"]


def test_partial_binding_detector_fires_on_desynced_row():
    """Negative control — the failure find_partial_marker_bindings exists for:
    a corrected marker_locations that was not carried into the row-side
    annotation_markers (the two fields record the same fact; resolve believes
    the row). The historical desync (rev2, 2026-07-30) was repaired before it
    was committed, so this reconstructs its exact shape on the banked real
    extraction: the annotation declares an extra row in marker_locations that
    no row's annotation_markers carries — the declared-only row will not bind."""
    path = (Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179"
            / "SoA2USDM" / "extracted" / "NCT04677179_Table_01_extraction.json")
    data = json.loads(path.read_text())
    assert not find_partial_marker_bindings(data), "banked extraction must be consistent"
    annot = next(a for a in data["annotations"]
                 if a["annotation_marker"] == "c1"
                 and a["marker_locations"][0]["location_type"] == "activity_name")
    moved_to = annot["marker_locations"][0]["row_position"] + 2
    annot["marker_locations"].append(
        {"table_number": 1, "location_type": "activity_name",
         "row_position": moved_to})
    findings = find_partial_marker_bindings(data)
    assert len(findings) == 1 and "'c1'" in findings[0] \
        and str(moved_to) in findings[0], \
        f"expected the declared-only row {moved_to} to be named, got {findings}"


def test_method_provenance_summary_warnings_and_unresolved():
    """Method provenance is exception-based: an extraction recording nothing
    reports nothing; a recorded deviation appears in method_provenance; only the
    geometry-less methods (proximity) warn; an 'unresolved' marker location is an
    allowed answer — counted, not warned, and never a lost binding."""
    path = (Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179"
            / "SoA2USDM" / "extracted" / "NCT04677179_Table_01_extraction.json")
    data = json.loads(path.read_text())

    baseline = validate_extraction(data)
    assert baseline.method_provenance == [], "banked extraction records no deviations"
    baseline_warnings = len(baseline.warnings)

    # A deviation with a sound method: recorded, no warning.
    data["annotations"][0]["annotation_text_source"] = {"method": "deglyph_reconstruction"}
    # The known failure source: recorded AND warned.
    data["annotations"][1]["annotation_text_source"] = {"method": "proximity_bounded"}
    # An honest non-answer: position kept as evidence, no scope claim.
    data["annotations"][2]["marker_locations"].append(
        {"table_number": 1, "location_type": "unresolved", "row_position": 40})

    result = validate_extraction(data)
    assert result.method_provenance == [
        "annotation_text:deglyph_reconstruction: 1",
        "annotation_text:proximity_bounded: 1",
        "marker_location:unresolved: 1",
    ], result.method_provenance
    new_warnings = [w for w in result.warnings if "proximity-bounded" in w]
    assert len(new_warnings) == 1, "exactly the proximity-bounded note warns"
    assert len(result.warnings) == baseline_warnings + 1, \
        "unresolved and sound methods add no warnings"
    assert not find_partial_marker_bindings(data), \
        "an unresolved location must not read as a lost binding"


# ---------------------------------------------------------------------------
# Legend typing (inventory-improvements item 4, detector i)
# ---------------------------------------------------------------------------

# The only annotations resolve may retype legend, per protocol, as
# (resolved filename suffix, annotation_id). Calibrated over the 22-protocol
# corpus (752 resolved annotations): the pattern matches 8 — these 4 fragments
# mistyped footnote, plus 4 legend lists already typed abbreviation, which the
# guard leaves untouched. Everything else must keep its extracted type.
# The banked fixture keeps the four fragments and stays the end-to-end positive control for the
# retype path. The LIVE collection no longer contains them: prompt v3.7.0 §6 stops an abbreviation
# block whose terms carry no in-grid marker from emitting annotations at all, so the corrupt
# abbreviation-key fragments (NCT04677179 T1 c23, T2/T3 c13, T4 c12) are simply not extracted any
# more. Nothing in usdm_data should need retyping.
EXPECTED_LEGEND_RETYPES = {
    "fixtures/NCT04677179": {
        ("Table_01", "annot-031"),
        ("Table_02", "annot-014"),
        ("Table_03", "annot-014"),
        ("Table_04", "annot-012"),
    },
}


def test_legend_retypes_exactly_the_known_fragments(pipeline_output):
    """Corpus-wide zero-false-positive gate: every annotation carrying an
    annotation_type_source is one of NCT04677179's four OCR-clipped
    abbreviation-legend fragments, retyped footnote -> legend; no other
    protocol has any retype."""
    protocol, produced, _ = pipeline_output
    # protocol is the "<collection>/<protocol>" case id; the filename carries only the protocol.
    stem = protocol.split("/")[-1]
    found = set()
    for rf in sorted((produced / "resolved").glob("*_resolved.json")):
        data = json.loads(rf.read_text())
        table = rf.name.replace(f"{stem}_", "").replace("_resolved.json", "")
        for annot in data["annotations"]:
            src = annot.get("annotation_type_source")
            if src:
                assert annot["annotation_type"] == "legend"
                assert src == {"method": "legend_pattern",
                               "extracted_type": "footnote"}, src
                found.add((table, annot["annotation_id"]))
    assert found == EXPECTED_LEGEND_RETYPES.get(protocol, set()), \
        f"{protocol}: unexpected legend retypes {found}"


def test_legend_pattern_on_real_corpus_texts():
    """The rule against the corpus texts that define its boundary — all quoted
    verbatim from resolved files. Positives include the hardest case: the
    OCR-clipped T2/T3 fragment whose single '=' survives only in its
    '; ETV =' spine. Negatives are the real footnotes nearest the boundary:
    a single symbol key, a timing anchor, a formula, a <= comparison."""
    # Must match — NCT04677179's legend fragments (T4 c12, T2/T3 c13):
    assert is_legend_annotation(
        "DNA=deoxyribonucleic acid; ETV =early symptomatology–self report; "
        "SoA=schedule of activities;")
    assert is_legend_annotation("Acid; ETV =early quick inventory of depressive")
    # Must NOT match — CDISC_Pilot single symbol key (annot-002):
    assert not is_legend_annotation(
        "Xa = Performed at this visit if patient is an insulin-dependent diabetic.")
    # Must NOT match — NCT03421379 annot-021, a timing anchor:
    assert not is_legend_annotation(
        "-5 mins = stop insulin infusion. Sampling times are relative to the "
        "time of study treatment administration (0 min). Predose time point "
        "will be between insulin infusion stop and study treatment.")
    # Must NOT match — NCT03283098 annot-004, a correction formula:
    assert not is_legend_annotation(
        "Serum samples for albumin and calcium for screening and routine "
        "monitoring of predialysis cCa. When albumin is less than 4.0 g/dL, "
        "the calcium level will be corrected according to the formula: cCa "
        "(mg/dL) = total Ca (mg/dL) + (4 – albumin (g/dL))*0.8. Corrected "
        "calcium results will inform dosing/dose withholding at the next "
        "hemodialysis treatment.")
    # Must NOT match — NCT04557384 annot-010, a <= comparison:
    assert not is_legend_annotation(
        "During study treatment, perform <=3 days prior to treatment.")


def test_legend_retype_preserves_already_definitional_types():
    """An annotation the extractor already typed abbreviation matches the
    pattern but must NOT be retyped — the guard only lifts footnote and
    source_note. Verified directly on the banked extraction by injecting the
    real NCT05324124 abbreviation list."""
    path = (Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179"
            / "SoA2USDM" / "extracted" / "NCT04677179_Table_01_extraction.json")
    data = json.loads(path.read_text())
    abbrev = "Abbreviations: CRU = clinical research unit; ECG = electrocardiogram;"
    assert is_legend_annotation(abbrev), "the guard, not the pattern, must skip it"
    data["annotations"].append({
        "annotation_marker": "zz", "annotation_type": "abbreviation",
        "annotation_text": abbrev, "marker_locations": []})
    resolved = resolve_extraction(data, path.name)
    kept = next(a for a in resolved["annotations"]
                if a["annotation_marker"] == "zz")
    assert kept["annotation_type"] == "abbreviation"
    assert "annotation_type_source" not in kept


# ---------------------------------------------------------------------------
# Redaction flag (inventory-improvements item 2)
# ---------------------------------------------------------------------------

# Consolidated-level redaction counts, measured 2026-08-15 and pinned:
# the corpus' full population of CCI rows. Any other protocol reporting a
# redaction is a false positive.
# Keyed by case id like the other two tables, so the banked fixture keeps its own frozen count.
# The live counts are unchanged by the Phase 3 re-extraction: NCT05176314's 2 and NCT05324124's 1
# are restored by promotion-review corrections sidecars — one placeholder row per OBSERVED
# redaction band, because the re-extraction established that the "CCI" lettering prints outside the
# table's left rule (x = 174-199 px vs a rule at x = 200) and is an overlay, not a cell value. How
# many rows a band conceals is not determinable from the source.
EXPECTED_REDACTED_UNIFIED = {
    "usdm_data/NCT04677179": 6,   # of 64 unified activities
    "usdm_data/NCT05176314": 2,
    "usdm_data/NCT05324124": 1,
    "fixtures/NCT04677179": 6,
}


def test_redaction_counts_match_the_corpus_population(pipeline_output):
    protocol, produced, _ = pipeline_output
    cons = json.loads(
        next((produced / "consolidated").glob("*_consolidated.json")).read_text())
    redacted = [ua for ua in cons["unified_activities"] if ua.get("is_redacted")]
    assert len(redacted) == EXPECTED_REDACTED_UNIFIED.get(protocol, 0), \
        f"{protocol}: {[ua['activity_name'] for ua in redacted]}"
    # Both directions: every flagged name is a placeholder, and every
    # placeholder name is flagged.
    for ua in cons["unified_activities"]:
        names_redacted = all(is_redacted_activity_name(n)
                             for n in ua.get("name_variations", [ua["activity_name"]]))
        assert bool(ua.get("is_redacted")) == names_redacted or not names_redacted, \
            f"{protocol} {ua['xact_id']}: flag/name disagreement"
        if names_redacted:
            assert ua.get("is_redacted") is True, \
                f"{protocol} {ua['xact_id']}: placeholder name not flagged"


def test_redacted_name_pattern_boundaries():
    """The placeholder pattern, exact by design: 'CCI' alone or with a
    parenthetical qualifier. A name merely containing the letters must not
    flag — fail fast on pattern creep."""
    assert is_redacted_activity_name("CCI")
    assert is_redacted_activity_name("CCI (redacted)")
    assert is_redacted_activity_name("  CCI  ")
    assert not is_redacted_activity_name("CCI score")
    assert not is_redacted_activity_name("Colonoscopy")
    assert not is_redacted_activity_name("ECG")
    assert not is_redacted_activity_name("")


# ---------------------------------------------------------------------------
# Header-bound annotations (inventory-improvements item 4, detector ii)
# ---------------------------------------------------------------------------

# Corpus base rate, measured 2026-08-15 and pinned: 5 header-bound annotations
# across 4 protocols, each reading as a deliberate group-scope note (e.g.
# NCT03283098's Pre-HD qualifier says "applying to all laboratory assessments"
# outright). This is why the detector warns instead of erroring. A count
# moving here means a binding changed — look before repinning.
# Base rate, not zero: a note scoping a whole section legitimately binds to that section's header
# row. The Phase 3 re-extraction left the TOTAL at 5 and moved one — NCT03283098 -1 (nothing now
# binds to its 'Laboratory Assessments' header) and NCT04677179 +1 (T2's "Not applicable for
# responders during the time period of V10 through V19" binds to the 'Endoscopic Procedure'
# header). Verified on a 150 dpi render of doc p.27: that row is a shaded section header with NO
# printed marker, and the location carries method "synthesized" — §6's rule for a notes-column
# entry the source gives no marker, link it to the row it sits beside. All five, before and after,
# are the same shape.
EXPECTED_HEADER_BOUND = {
    "usdm_data/NCT04557384": 1,
    "usdm_data/NCT04573309": 2,
    "usdm_data/NCT04677179": 1,
    "usdm_data/NCT04730349": 1,
}


def test_header_bound_annotations_match_base_rate(pipeline_output):
    protocol, produced, _ = pipeline_output
    cons = json.loads(
        next((produced / "consolidated").glob("*_consolidated.json")).read_text())
    findings = find_header_bound_annotations(cons)
    assert len(findings) == EXPECTED_HEADER_BOUND.get(protocol, 0), \
        f"{protocol}: {findings}"


def test_header_bound_detector_fires_on_header_binding():
    """Negative control — the banked NCT04677179 consolidated output has no
    header-bound annotation, so the misbind this detector exists for is
    reconstructed on it explicitly: mark an activity that carries a bound
    annotation as a section header, and the detector must name the pair."""
    path = (Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179"
            / "SoA2USDM" / "consolidated" / "NCT04677179_consolidated.json")
    data = json.loads(path.read_text())
    assert not find_header_bound_annotations(data), \
        "banked consolidated output must be clean"
    annot = next(a for a in data["unified_annotations"] if a["referenced_xacts"])
    target = annot["referenced_xacts"][0]
    ua = next(a for a in data["unified_activities"] if a["xact_id"] == target)
    ua["is_section_header"] = True
    findings = find_header_bound_annotations(data)
    assert findings == [(annot["xannot_id"], [ua["activity_name"]])], findings
